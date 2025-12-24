"""AI CLIツール ニュースレポートシステム

毎日AI系CLIツールのニュースを収集し、レポートを生成します。
"""

import argparse
import sys
from datetime import datetime

import yaml

from src.collector.gemini_search import collect_all_news
from src.models.news_item import ToolConfig
from src.publisher.html_generator import generate_report
from src.summarizer.claude_summarizer import summarize_news


def load_config(config_path: str = "config/tools.yaml") -> dict:
    """設定ファイルを読み込む"""
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="AI CLIツール ニュースレポートシステム"
    )
    parser.add_argument(
        "--config",
        default="config/tools.yaml",
        help="設定ファイルのパス",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/reports",
        help="出力ディレクトリ",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="何日前までのニュースを取得するか",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実行せずに設定を確認",
    )
    parser.add_argument(
        "--github-repo",
        default="",
        help="GitHubリポジトリ名（例: username/repo）",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("AI CLI Tools News Report Generator")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Config: {args.config}")
    print(f"Output: {args.output_dir}")
    print(f"Days back: {args.days_back}")
    print("=" * 60)

    # 設定を読み込む
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Config file not found: {args.config}")
        return 1
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in config file: {e}")
        return 1

    # ツール設定を取得
    tool_configs = [
        ToolConfig.from_dict(tool)
        for tool in config.get("tools", [])
    ]

    print(f"\nTarget tools ({len(tool_configs)}):")
    for tc in tool_configs:
        print(f"  - {tc.name} ({tc.vendor})")

    if args.dry_run:
        print("\n[Dry run] Exiting without generating report.")
        return 0

    # Step 1: ニュース収集
    print("\n[Step 1] Collecting news with Gemini...")
    search_config = config.get("search", {})
    news_items = collect_all_news(
        tool_configs=tool_configs,
        days_back=args.days_back,
        max_results_per_tool=search_config.get("max_results_per_tool", 10),
    )
    print(f"Collected {len(news_items)} news items")

    if not news_items:
        print("No news found. Creating empty report.")

    # Step 2: 要約・分類
    print("\n[Step 2] Summarizing with Claude...")
    if news_items:
        news_items = summarize_news(news_items)
        print(f"Summarized {len(news_items)} items")

    # Step 3: レポート生成
    print("\n[Step 3] Generating HTML reports...")

    generated_files = generate_report(
        news_items=news_items,
        date=datetime.now(),
        output_dir=args.output_dir,
        github_repo=args.github_repo,
    )

    print("\nGenerated files:")
    for lang, path in generated_files.items():
        print(f"  - {lang}: {path}")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
