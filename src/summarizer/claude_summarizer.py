"""Claude APIを使った要約・分類"""

import json
import os
from typing import Optional

import anthropic

from src.models.news_item import Category, Importance, NewsItem


class ClaudeSummarizer:
    """Claude APIでニュースを要約・分類"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    def summarize_and_categorize(
        self,
        news_items: list[NewsItem],
    ) -> list[NewsItem]:
        """ニュースを要約・分類"""
        if not news_items:
            return []

        # バッチ処理（一度に複数のニュースを処理）
        batch_size = 10
        processed_items: list[NewsItem] = []

        for i in range(0, len(news_items), batch_size):
            batch = news_items[i : i + batch_size]
            processed = self._process_batch(batch)
            processed_items.extend(processed)

        return processed_items

    def _process_batch(self, news_items: list[NewsItem]) -> list[NewsItem]:
        """バッチで処理"""
        # 入力データを準備
        items_data = []
        for idx, item in enumerate(news_items):
            items_data.append({
                "id": idx,
                "title": item.title,
                "url": item.url,
                "tool_name": item.tool_name,
                "content": item.content[:500] if item.content else "",
            })

        prompt = f"""
以下のAI開発ツールに関するニュース項目を分析して、日本語と英語の要約を作成し、重要度とカテゴリを判定してください。

ニュース項目:
```json
{json.dumps(items_data, ensure_ascii=False, indent=2)}
```

各ニュースについて以下のJSON形式で返してください:
```json
[
  {{
    "id": 0,
    "summary_ja": "日本語の要約（2-3文）",
    "summary_en": "English summary (2-3 sentences)",
    "importance": "critical|high|medium|low",
    "category": "release|feature|update|bugfix|security|documentation|announcement|other",
    "tags": ["タグ1", "タグ2"]
  }}
]
```

重要度の基準:
- critical: メジャーバージョンリリース、重大な機能変更、セキュリティ脆弱性
- high: 新機能追加、重要なアップデート、パフォーマンス改善
- medium: バグ修正、マイナーアップデート
- low: ドキュメント更新、軽微な変更

カテゴリの基準:
- release: 新バージョンリリース
- feature: 新機能追加
- update: アップデート・改善
- bugfix: バグ修正
- security: セキュリティ関連
- documentation: ドキュメント更新
- announcement: 発表・お知らせ
- other: その他
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            return self._parse_response(response.content[0].text, news_items)
        except Exception as e:
            print(f"Claude API error: {e}")
            return news_items  # エラー時は元のアイテムを返す

    def _parse_response(
        self,
        response_text: str,
        original_items: list[NewsItem],
    ) -> list[NewsItem]:
        """レスポンスをパース"""
        import re

        # JSONブロックを抽出
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response_text

        try:
            results = json.loads(json_str)
            if not isinstance(results, list):
                results = [results]

            # 結果をマージ
            result_map = {r["id"]: r for r in results}
            for idx, item in enumerate(original_items):
                if idx in result_map:
                    r = result_map[idx]
                    item.summary_ja = r.get("summary_ja", "")
                    item.summary_en = r.get("summary_en", "")
                    item.importance = Importance(r.get("importance", "medium"))
                    item.category = Category(r.get("category", "other"))
                    item.tags = r.get("tags", [])

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")

        return original_items


def summarize_news(
    news_items: list[NewsItem],
    api_key: Optional[str] = None,
) -> list[NewsItem]:
    """ニュースを要約（ヘルパー関数）"""
    summarizer = ClaudeSummarizer(api_key=api_key)
    return summarizer.summarize_and_categorize(news_items)
