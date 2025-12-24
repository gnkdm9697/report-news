"""Gemini APIを使ったGoogle検索によるニュース収集"""

import os
from datetime import datetime, timedelta
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from src.models.news_item import NewsItem, ToolConfig


class GeminiSearchCollector:
    """Gemini APIでGoogle検索を行いニュースを収集"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        genai.configure(api_key=self.api_key)
        # Gemini 2.0 Flash with Google Search grounding
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def search_tool_news(
        self,
        tool_config: ToolConfig,
        days_back: int = 1,
        max_results: int = 10,
    ) -> list[NewsItem]:
        """特定のツールに関するニュースを検索"""
        news_items: list[NewsItem] = []
        date_filter = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        for query in tool_config.search_queries:
            try:
                items = self._search_and_parse(
                    query=query,
                    tool_name=tool_config.name,
                    date_filter=date_filter,
                    max_results=max_results,
                )
                news_items.extend(items)
            except Exception as e:
                print(f"Error searching for '{query}': {e}")

        # 重複除去（URLベース）
        seen_urls: set[str] = set()
        unique_items: list[NewsItem] = []
        for item in news_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)

        return unique_items[:max_results]

    def _search_and_parse(
        self,
        query: str,
        tool_name: str,
        date_filter: str,
        max_results: int,
    ) -> list[NewsItem]:
        """検索を実行してパース"""
        prompt = f"""
You are a tech news researcher. Search for the latest news and updates about:
"{query}"

Focus on:
- Official announcements and releases
- Blog posts from the official website
- News articles from tech media
- GitHub releases and updates

Filter for news from {date_filter} onwards.

For each news item found, provide in JSON format:
```json
[
  {{
    "title": "News title",
    "url": "https://...",
    "published_date": "YYYY-MM-DD",
    "snippet": "Brief description of the news (2-3 sentences)"
  }}
]
```

Return up to {max_results} most relevant and recent items.
If no recent news is found, return an empty array: []
"""

        try:
            # Google Search groundingを使用
            response: GenerateContentResponse = self.model.generate_content(
                prompt,
                tools="google_search_retrieval",
            )

            return self._parse_response(response, tool_name)
        except Exception as e:
            print(f"Gemini API error: {e}")
            return []

    def _parse_response(
        self,
        response: GenerateContentResponse,
        tool_name: str,
    ) -> list[NewsItem]:
        """レスポンスをパース"""
        news_items: list[NewsItem] = []

        if not response.text:
            return news_items

        import json
        import re

        # JSONブロックを抽出
        text = response.text
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # JSONブロックがない場合、全体をJSONとして試す
            json_str = text

        try:
            items = json.loads(json_str)
            if not isinstance(items, list):
                items = [items]

            for item in items:
                if not item.get("title") or not item.get("url"):
                    continue

                published_at = None
                if item.get("published_date"):
                    try:
                        published_at = datetime.strptime(
                            item["published_date"], "%Y-%m-%d"
                        )
                    except ValueError:
                        pass

                news_item = NewsItem(
                    title=item["title"],
                    url=item["url"],
                    tool_name=tool_name,
                    source="gemini_search",
                    published_at=published_at,
                    content=item.get("snippet", ""),
                    raw_data=item,
                )
                news_items.append(news_item)

        except json.JSONDecodeError:
            print(f"Failed to parse JSON response: {text[:200]}...")

        return news_items


def collect_all_news(
    tool_configs: list[ToolConfig],
    days_back: int = 1,
    max_results_per_tool: int = 10,
    api_key: Optional[str] = None,
) -> list[NewsItem]:
    """すべてのツールのニュースを収集"""
    collector = GeminiSearchCollector(api_key=api_key)
    all_news: list[NewsItem] = []

    for config in tool_configs:
        print(f"Collecting news for: {config.name}")
        news = collector.search_tool_news(
            tool_config=config,
            days_back=days_back,
            max_results=max_results_per_tool,
        )
        all_news.extend(news)
        print(f"  Found {len(news)} items")

    return all_news
