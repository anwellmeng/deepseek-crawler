import asyncio
import re
import csv
import os.path
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
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
    directory = './scraped_sites'
    # READ CSV FILE
    websites = []
    try:
        with open('authors.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            # Skip header
            for row in reader:
                if reader.line_num == 1:
                    continue  # skip header
                # Append only the first element (the URL) of the row
                websites.append(row[0])
    except FileNotFoundError:
        print("Error: CSV file not found")
        return

    # Now, if there are no websites, we can exit
    if not websites:
        print("No websites to crawl")
        return

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
                        file_path = os.path.join(directory, f"{base}.md")
                        try:
                            with open(file_path, "x") as f:
                                f.write(combined_markdown)
                            print(f"Saved combined markdown for {url} to {base}.md")
                        except FileExistsError:
                            print(f"File {base}.md already exists, skipping.")
                else:
                    if getattr(result, "success", False):
                        file_path = os.path.join(directory, f"{base}_p1.md")
                        with open(file_path, "x") as f:
                            f.write(result.markdown)
                        print(f"Saved {url} to {base}_p1.md")
            except FileExistsError:
                print(f"File for {url} already exists, skipping this one and moving on...")
                continue

if __name__ == "__main__":
    asyncio.run(main())
