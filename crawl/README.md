# Crawl the source style guide

From the repository root, export the source guide for manual review:

```shell
uv run --script crawl/crawl_to_markdown.py \
    --base-url https://developers.google.com/style \
    --output-dir /tmp/docs-style-crawl
```

The output can contain
navigation elements and duplicate pages. Curate changes before copying them into
[the active references](../skills/docs-style/references/style/). Do not replace
those references in full with unedited crawler output.
