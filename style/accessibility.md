# Write accessible documentation  

We write our developer documentation with accessibility in mind. This page is not an exhaustive
reference, but describes some general guidelines and examples that illustrate best practices to
follow. The
[World Health Organization](https://www.who.int/en/news-room/fact-sheets/detail/disability-and-health)
estimates that 15% of the world's population (more than 1 billion people) have an accessibility
need. When documentation is written with accessibility in mind, it improves the overall
experience for all readers.

## General dos and don'ts

* Don't use *&* instead of *and* in headings, text, navigation, or
  tables of contents. However, it's OK to use *&* when referencing UI
  elements that use *&*, or in table headings and diagram labels where space
  constraints require abbreviation. Of course, it's fine to use `&`
  for technical purposes in code.

## Ease of reading

* Break up walls of text to aid in scannability. For example, separate
  [paragraphs](/style/paragraph-structure),
  create
  [headings](/style/headings),
  and use
  [lists](/style/lists).
* Use shorter sentences. Try to use fewer than 26 words per sentence.
* Define acronyms and abbreviations on first usage and if they're used infrequently.
* Use parallel writing structures for similar things. For example, start each list in the same
  format.
* Place distinguishing and important information of a paragraph in the first sentence to aid in
  scannability.
* Use clear and direct language. Avoid the use of double negatives and exceptions for exceptions.

  Recommended: You can continue without a
  path.

  Not recommended: A missing path won't
  prevent you from continuing.
* Left-align text for readability. Don't center or full-justify text.

## Headings and titles

Use descriptive headings and titles because they help a reader navigate their browser and the
page. It's easier to jump between pages and sections of a page if the headings and titles are
unique.

* Use a heading hierarchy.
* Don't skip levels of the heading hierarchy. For example, put an `###` element
  only after an `##` element.
* To change the visual formatting of a heading, use CSS rather than using a heading level that
  doesn't fit the hierarchy.
* Don't have empty headings or headings with no associated content.
* Tag headings using heading elements.In Markdown: `#`, `##`, and so on.
* Use a level-1 heading for the page title or main content heading.


## Links

* Use [meaningful link text](/style/cross-references#descriptive-link-text).
  Links should make sense when read out of context.
* Don't use *click here* or *read this document*. Some people who use screen readers
  jump from link to link to scan a page and need to understand what a link contains.
* Use *see* to refer to links and cross-references.
* When a link does anything that the reader might not expect, such as downloading a file,
  opening in a new tab, or jumping to another section on the same page, explain that behavior when
  you link.
* When possible, avoid adjacent links. Instead, put a character in between to separate them.

## Lists

* In a
  [procedure](/style/procedures),
  make each instruction a
  [list item](/style/lists).
* Use lists to make it easier for the reader to follow the steps.

## Tables

* Introduce tables in the text preceding the table because not all screen readers preannounce
  tables.
* Use table headings for the first column and the first row only. Use the
  [`th` element](https://www.w3.org/TR/html4/struct/tables.html#edef-TH).
* If your tables include both row and column headings, then mark heading cells with the
  [`scope`
  attribute](https://www.w3.org/WAI/tutorials/tables/two-headers/).
* If your tables have more than one row containing column headings, then use the
  [`headers`
  attribute](https://www.w3.org/WAI/tutorials/tables/multi-level/) and make sure that the headings have unique IDs.
* Avoid when possible tables in the middle of a numbered procedure.
* Don't use tables unless it's the best method to present your information. Tables are
  challenging for screen readers.
* Don't present new information in tables through images or symbols alone; always provide a
  descriptive `alt` attribute for the image or symbol.
