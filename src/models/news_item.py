"""ニュースアイテムのデータモデル"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Importance(Enum):
    """ニュースの重要度"""
    CRITICAL = "critical"  # メジャーリリース、重大な変更
    HIGH = "high"          # 新機能、重要なアップデート
    MEDIUM = "medium"      # バグ修正、マイナーアップデート
    LOW = "low"            # ドキュメント更新、軽微な変更


class Category(Enum):
    """ニュースのカテゴリ"""
    RELEASE = "release"           # 新バージョンリリース
    FEATURE = "feature"           # 新機能追加
    UPDATE = "update"             # アップデート
    BUGFIX = "bugfix"             # バグ修正
    SECURITY = "security"         # セキュリティ関連
    DOCUMENTATION = "documentation"  # ドキュメント更新
    ANNOUNCEMENT = "announcement"    # 発表・お知らせ
    OTHER = "other"               # その他


@dataclass
class NewsItem:
    """ニュースアイテム"""
    title: str
    url: str
    tool_name: str
    source: str  # 検索元（gemini, rss, etc.）
    published_at: Optional[datetime] = None
    content: str = ""
    summary_ja: str = ""
    summary_en: str = ""
    importance: Importance = Importance.MEDIUM
    category: Category = Category.OTHER
    tags: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "title": self.title,
            "url": self.url,
            "tool_name": self.tool_name,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "content": self.content,
            "summary_ja": self.summary_ja,
            "summary_en": self.summary_en,
            "importance": self.importance.value,
            "category": self.category.value,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NewsItem":
        """辞書から生成"""
        published_at = None
        if data.get("published_at"):
            published_at = datetime.fromisoformat(data["published_at"])

        return cls(
            title=data["title"],
            url=data["url"],
            tool_name=data["tool_name"],
            source=data["source"],
            published_at=published_at,
            content=data.get("content", ""),
            summary_ja=data.get("summary_ja", ""),
            summary_en=data.get("summary_en", ""),
            importance=Importance(data.get("importance", "medium")),
            category=Category(data.get("category", "other")),
            tags=data.get("tags", []),
        )


@dataclass
class ToolConfig:
    """ツール設定"""
    name: str
    vendor: str
    keywords: list[str]
    search_queries: list[str]
    official_links: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "ToolConfig":
        """辞書から生成"""
        return cls(
            name=data["name"],
            vendor=data.get("vendor", ""),
            keywords=data.get("keywords", []),
            search_queries=data.get("search_queries", []),
            official_links=data.get("official_links", []),
        )


@dataclass
class DailyReport:
    """日次レポート"""
    date: datetime
    news_items: list[NewsItem]
    generated_at: datetime = field(default_factory=datetime.now)

    def get_by_tool(self, tool_name: str) -> list[NewsItem]:
        """ツール名でフィルタ"""
        return [item for item in self.news_items if item.tool_name == tool_name]

    def get_by_importance(self, importance: Importance) -> list[NewsItem]:
        """重要度でフィルタ"""
        return [item for item in self.news_items if item.importance == importance]

    def get_critical_and_high(self) -> list[NewsItem]:
        """重要なニュースのみ取得"""
        return [
            item for item in self.news_items
            if item.importance in (Importance.CRITICAL, Importance.HIGH)
        ]
