import asyncio
import re
import csv
import os.path
from crawl4ai import AsyncWebCrawler
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

    run_config = CrawlerRunConfig( # Run Configuration (Custom)
        deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=1,
            include_external=False,
            url_scorer=keyword_scorer
        ),
        markdown_generator = DefaultMarkdownGenerator()
    )
    directory = './scraped_sites'
    # Read the CSV file
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
                # Create a safe filename for the URL
                safe_name = re.sub(r"\W+", '_', url).strip("_")
                os.makedirs(directory, exist_ok=True)
                file_path = os.path.join(directory, f"{safe_name}.md")

                if os.path.exists(file_path):
                    print(f"File for {url} already exists, skipping this one and moving on...")
                    continue

                # Now, crawl the URL
                result = await crawler.arun(
                    url=url,
                    config=run_config
                )
                markdown = None

                if isinstance(result, list):
                    for item in result:
                        if item.success:
                            markdown = item.markdown
                            break
                elif result.success:
                    markdown = result.markdown

                if markdown:
                    with open(file_path, "w") as f:
                        f.write(markdown)
                    print(f"Saved {url} to {safe_name}.md")
                else:
                    print(f"Failed to crawl {url} or other.")
            except FileExistsError:
                print(f"File for {url} already exists, skipping this one and moving on...")
                continue


if __name__ == "__main__":
    asyncio.run(main())
