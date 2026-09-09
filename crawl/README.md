# Crawl the source style guide

From the repository root, export the source guide for manual review:

```shell
uv run --script crawl/crawl_to_markdown.py \
    --base-url https://developers.google.com/style \
    --output-dir /tmp/docs-style-crawl
```

The crawler exports source pages for manual review. Its output can contain
navigation elements and duplicate pages. Curate changes before copying them into
[the active references](../skills/docs-style/references/style/); do not replace
those references wholesale with a fresh crawl.
