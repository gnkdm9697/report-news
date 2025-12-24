"""HTMLレポート生成"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from src.models.news_item import DailyReport, Importance, NewsItem


class HTMLReportGenerator:
    """HTMLレポートを生成"""

    def __init__(
        self,
        template_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        github_repo: str = "",
    ):
        self.template_dir = Path(template_dir or "templates")
        self.output_dir = Path(output_dir or "docs/reports")
        self.github_repo = github_repo

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
        )

    def generate_report(
        self,
        report: DailyReport,
        languages: list[str] = None,
    ) -> dict[str, Path]:
        """レポートを生成"""
        if languages is None:
            languages = ["ja", "en"]

        # 出力ディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)

        date_str = report.date.strftime("%Y-%m-%d")
        generated_files: dict[str, Path] = {}

        # ニュースをツールごとにグループ化
        news_by_tool = defaultdict(list)
        for item in report.news_items:
            news_by_tool[item.tool_name].append(item)

        # 統計情報
        total_count = len(report.news_items)
        critical_count = len([
            item for item in report.news_items
            if item.importance in (Importance.CRITICAL, Importance.HIGH)
        ])
        tools_count = len(news_by_tool)

        for lang in languages:
            output_path = self._generate_single_report(
                date_str=date_str,
                lang=lang,
                news_by_tool=dict(news_by_tool),
                total_count=total_count,
                critical_count=critical_count,
                tools_count=tools_count,
                generated_at=report.generated_at,
            )
            generated_files[lang] = output_path

        # インデックスページを更新
        self._update_index(languages)

        return generated_files

    def _generate_single_report(
        self,
        date_str: str,
        lang: str,
        news_by_tool: dict[str, list[NewsItem]],
        total_count: int,
        critical_count: int,
        tools_count: int,
        generated_at: datetime,
    ) -> Path:
        """単一言語のレポートを生成"""
        template = self.env.get_template("report.html")

        # タイトルと日付フォーマット
        if lang == "ja":
            title = "AI CLIツール ニュースレポート"
            report_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")
        else:
            title = "AI CLI Tools News Report"
            report_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")

        # ファイル名
        filename = f"{date_str}_{lang}.html"
        output_path = self.output_dir / filename

        # レンダリング
        html = template.render(
            title=title,
            report_date=report_date,
            lang=lang,
            ja_url=f"{date_str}_ja.html",
            en_url=f"{date_str}_en.html",
            news_by_tool=news_by_tool,
            total_count=total_count,
            critical_count=critical_count,
            tools_count=tools_count,
            generated_at=generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            github_repo=self.github_repo,
        )

        output_path.write_text(html, encoding="utf-8")
        print(f"Generated: {output_path}")

        return output_path

    def _update_index(self, languages: list[str]) -> None:
        """インデックスページを更新"""
        index_path = self.output_dir.parent / "index.html"

        # 既存のレポート一覧を取得
        reports = []
        for file in sorted(self.output_dir.glob("*_ja.html"), reverse=True):
            date_str = file.stem.replace("_ja", "")
            reports.append({
                "date": date_str,
                "ja_url": f"reports/{date_str}_ja.html",
                "en_url": f"reports/{date_str}_en.html",
            })

        # インデックスHTML生成
        html = self._generate_index_html(reports[:30])  # 最新30件
        index_path.write_text(html, encoding="utf-8")
        print(f"Updated: {index_path}")

    def _generate_index_html(self, reports: list[dict]) -> str:
        """インデックスHTMLを生成"""
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI CLI Tools News</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --border-color: #30363d;
            --accent-blue: #58a6ff;
            --accent-purple: #a371f7;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 2rem; }}
        header {{ text-align: center; margin-bottom: 3rem; }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ color: var(--text-secondary); }}
        .report-list {{ list-style: none; }}
        .report-item {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .report-item:hover {{ border-color: var(--accent-blue); }}
        .report-date {{ font-weight: 600; }}
        .report-links a {{
            color: var(--accent-blue);
            text-decoration: none;
            margin-left: 1rem;
        }}
        .report-links a:hover {{ text-decoration: underline; }}
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI CLI Tools News</h1>
            <p class="subtitle">Daily news reports for AI-powered CLI development tools</p>
        </header>
        <ul class="report-list">
            {"".join([f'''
            <li class="report-item">
                <span class="report-date">{r["date"]}</span>
                <span class="report-links">
                    <a href="{r["ja_url"]}">日本語</a>
                    <a href="{r["en_url"]}">English</a>
                </span>
            </li>''' for r in reports])}
        </ul>
        <footer>
            <p>Updated daily at 9:00 AM JST</p>
        </footer>
    </div>
</body>
</html>"""


def generate_report(
    news_items: list[NewsItem],
    date: Optional[datetime] = None,
    template_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    github_repo: str = "",
) -> dict[str, Path]:
    """レポートを生成（ヘルパー関数）"""
    report = DailyReport(
        date=date or datetime.now(),
        news_items=news_items,
    )

    generator = HTMLReportGenerator(
        template_dir=template_dir,
        output_dir=output_dir,
        github_repo=github_repo,
    )

    return generator.generate_report(report)
