# Code in text

Use code font to signal verbatim text, show boundaries, and separate code entities from surrounding prose.

* **Use code font for:** Classes, methods, commands (`gcloud`), filenames, paths, HTTP codes (`404`), SQL keywords, parameters, attributes, environment variables, DNS record types, database elements, IAM roles, data types, placeholders.
* **Do not use code font for:** Product names, domain names (unless in code/configuration), URLs meant to be clicked (use links with descriptive text).
* **UI Elements:** If a UI element displays code (filename, instance name), use bold code font (**`filename.txt`**).
* **Plurals/Possessives:** Do not inflect code terms. Add a noun ("Value of the `wordCount` variable" not "`wordCount`'s value").

## Context-dependent formatting

* **Booleans:** Use code font for literal values (`true`, `false`). Use regular font when describing evaluation ("If the condition is true").
* **Commands vs Products:** Code font for the command (`gcc`), regular font for the product (GCC compiler).
* **Email addresses:** Code font for input/output (`alex@example.com`). Regular font + link for contact information ([support@example.com](mailto:support@example.com)).
* **Method names:** Omit the class name unless necessary to prevent ambiguity ("Call the `get` method" not "Call the `animal.get` method").
* **HTTP status codes:** Use format `Code Name` ("Returns a `404 Not Found` status code"). For ranges, use `Nxx` format ("Returns a `2xx` status code").
