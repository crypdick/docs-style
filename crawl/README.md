# Crawl the style guide

This directory contains a script to crawl the style guide and save the pages to the `style/` directory.

```shell
uv run crawl_to_markdown.py --base-url https://developers.google.com/style \
                            --output-dir ./out
```

Note that the script is not perfect. It creates a few duplicate pages, includes unwanted elements, etc. I manually cleaned up the output and saved the pages to the `style/` directory.
