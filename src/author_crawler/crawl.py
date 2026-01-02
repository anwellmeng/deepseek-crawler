from __future__ import annotations

import asyncio
import csv
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .config import AUTHORS_CSV, SCRAPED_SITES_DIR

def load_websites(csv_path: Path) -> list[str]:
    websites: list[str] = []
    with csv_path.open(newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if reader.line_num == 1:
                continue
            if not row:
                continue
            websites.append(row[0])
    return websites


async def run_crawl(websites: list[str], output_dir: Path) -> None:
    browser_config = BrowserConfig()  # Default browser configuration

    keyword_scorer = KeywordRelevanceScorer( 
        keywords=["contact","email"],
        weight=0.8
    )
    """
    adaptive_config = AdaptiveConfig(
        max_pages = 5
        top_k_links = 3
    )
    """
    run_config = CrawlerRunConfig( # Run Configuration (Custom)
        deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=1,
            include_external=False,
            url_scorer=keyword_scorer
        ),
        markdown_generator = DefaultMarkdownGenerator()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in websites:
            try:
                # START CRAWLING
                result = await crawler.arun(
                    url=url,
                    config=run_config
                )
                base = re.sub(r"\W+", "_", url.rstrip("/")).strip("_")

                if isinstance(result, list):
                    combined_markdown = ""
                    for item in result:
                        if getattr(item, "success", False):
                            if combined_markdown:
                                combined_markdown += "\n\n--- PAGE BREAK ---\n\n"
                            combined_markdown += item.markdown
                    if combined_markdown:
                        file_path = output_dir / f"{base}.md"
                        try:
                            with file_path.open("x", encoding="utf-8") as f:
                                f.write(combined_markdown)
                            print(f"Saved combined markdown for {url} to {base}.md")
                        except FileExistsError:
                            print(f"File {base}.md already exists, skipping.")
                else:
                    if getattr(result, "success", False):
                        file_path = output_dir / f"{base}_p1.md"
                        with file_path.open("x", encoding="utf-8") as f:
                            f.write(result.markdown)
                        print(f"Saved {url} to {base}_p1.md")
            except FileExistsError:
                print(f"File for {url} already exists, skipping this one and moving on...")
                continue


def main() -> int:
    if not AUTHORS_CSV.exists():
        print("Error: CSV file not found")
        return 1

    try:
        websites = load_websites(AUTHORS_CSV)
    except OSError as exc:
        print(f"Error reading CSV: {exc}")
        return 1

    if not websites:
        print("No websites to crawl")
        return 0

    asyncio.run(run_crawl(websites, SCRAPED_SITES_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
