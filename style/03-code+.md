# Code documentation

## Code in text

Use code font to signal verbatim text, show boundaries, and separate code entities from surrounding prose.

* **Use code font for:** Classes, methods, commands (`gcloud`), filenames, paths, HTTP codes (`404`), SQL keywords, parameters, attributes, environment variables, DNS record types, database elements, IAM roles, data types, placeholders.
* **Do not use code font for:** Product names, domain names (unless in code/configuration), URLs meant to be clicked (use links with descriptive text).
* **UI Elements:** If a UI element displays code (filename, instance name), use bold code font (**`filename.txt`**).
* **Plurals/Possessives:** Do not inflect code terms. Add a noun ("Value of the `wordCount` variable" not "`wordCount`'s value").

### Context-dependent formatting

* **Booleans:** Use code font for literal values (`true`, `false`). Use regular font when describing evaluation ("If the condition is true").
* **Commands vs Products:** Code font for the command (`gcc`), regular font for the product (GCC compiler).
* **Email addresses:** Code font for input/output (`alex@example.com`). Regular font for contact information (support@example.com).
* **Method names:** Omit the class name unless necessary to prevent ambiguity ("Call the `get` method" not "Call the `animal.get` method").
* **HTTP status codes:** Use format `Code Name` ("Returns a `404 Not Found` status code"). For ranges, use `Nxx` format ("Returns a `2xx` status code").

## Code samples

* **Formatting:** Wrap lines at 80 characters.
* **Omissions:** Use comments (e.g., `# Code omitted`) instead of ellipses (`...`).
* **Introductions:** Precede with an introductory sentence/paragraph.
  * End with a **colon** if the sample follows immediately.
  * End with a **period** if there is text between (e.g., a note) or if the sentence isn't a direct lead-in.
* **Markdown:** Ensure multiline code blocks are surrounded by triple backticks.
* **Copyable:** Ensure samples are valid and copyable (unless they contain omissions/placeholders that break syntax).

## Command-line syntax

### Formatting

* Use code blocks with language-specific syntax highlighting (`shell` for console commands, `bash` for bash scripts, `python` for Python).
* Indent code inside fences by 4 spaces.
* Break lines at 80 characters when possible. After the first line, indent continuation lines by 4 spaces.
* End each line (except the last) with the continuation character: `\` (Linux/Cloud Shell) or `^` (Windows).
* Link to the command reference when introducing a command.
* Minimize arguments to what's needed for the task. Let the reference cover all options.

### Prompts

* Use `$` for shell prompts (optional for single-line commands).
* Don't show directory paths before the prompt unless context changes (e.g., local to remote).
* Use separate code blocks for input and output.

### Syntax notation

Use these characters to document syntax, not in click-to-copy examples:

* `[optional]` — optional argument
* `{choice1|choice2}` — mutually exclusive options
* `...` — repeating argument

### Click-to-copy examples

Never use `[]`, `{}`, `|`, or `...` in copyable examples—they break if not removed. Instead:

* **Remove optional arguments** and note alternatives in prose.
* **Use separate code blocks** for each variant.
* **Document options in separate tasks** (e.g., separate sections for different flags).
* **Use placeholders** like `INSTANCE_NAME` (not `[INSTANCE_NAME]`).

### Output

* Only show output if it adds value (e.g., reader needs to verify or copy a value).
* Introduce with "The output is the following:" or "The output is similar to the following:".
* Use `...` on a separate line to indicate omitted lines.

## Command-line terminology

### General guidance

* **Prefer explaining what the command does** rather than naming each element, especially for complex Linux commands.
* **Ask whether readers need terminology** or just need to understand the command's behavior.

### gcloud CLI

* **Structure:** `gcloud GROUP COMMAND --flag=VALUE ARGUMENT`
  * Groups can be nested (e.g., `gcloud compute instances list`)
  * `--` separates gcloud flags from user arguments
* **Terms:** Use `command`, `group`, `flag`, and `argument`.
* **Catchall:** *Option* works when you don't want specialized nomenclature.

### Linux commands

* **Complexity warning:** Linux syntax includes options, parameters, arguments, metacharacters (`*`, `?`), redirection (`|`, `>`, `<`), and more.
* **Terms:** Use `command`, `option` (starts with `-`), and `argument`.
* **Catchall:** *Option* is safe for general use.

### Linux signals

Use the specific verb associated with each signal:

* `SIGKILL`: **kill** (Cannot be caught/ignored. Do not use *stop* or *terminate*).
* `SIGTERM`: **terminate** (Requests termination, allows cleanup. Do not use *kill*).
* `SIGQUIT`: **quit** (Keyboard quit, can be caught).
* `SIGINT`: **interrupt** (Ctrl+C, terminates gracefully).
* `SIGPAUSE`: **pause** or **sleep** (Waits for signal).
* `SIGSUSPEND`: **suspend** (Temporarily pauses execution).
* `SIGSTOP`: **stop** (Stops for later continuation with `SIGCONT`. Cannot be caught).

## API reference code comments

* **Coverage:** Document all public classes, methods, fields, and constants.
* **Code Font:** Use code font for types, methods, and literals (`"true"`).
* **First Sentence:** Many doc generators extract the first sentence for summaries. Make it unique and avoid periods in abbreviations (use "for example" not "e.g.").
* **Tense:** Use present tense for all descriptions (*Adds*, *Returns*, not *Will add*, *Will return*).
* **Style:**
  * **Classes:** Start with a unique purpose (no "This class..."). Do not pluralize class names.
  * **Members (fields/constants):** Be brief. Link to relevant methods that use them.
  * **Methods:** Start with a third-person singular verb. Document prerequisites, dependencies (e.g., permissions), and behavior when dependencies are missing.
    * *Operations that return data:* Start with the operation verb (*Adds a bird and returns its ID*).
    * *Getters (Boolean):* "Checks whether..."
    * *Getters (Other):* "Gets the..."
    * *Setters:* "Sets the..."
    * *Updates:* "Updates the..."
    * *Deletions:* "Deletes the..."
    * *Registrations:* "Registers..."
    * *Callbacks:* "Called by..." then explain how subclasses should implement it.
  * **Parameters:** Capitalize first word. Start with "The" or "A" when describing objects.
    * *Booleans:* Explicitly state behavior for both cases. "If true, validates the certificate. If false, trusts it without validation."
    * *Defaults:* Use format "Default: value" to indicate default behavior.
  * **Return values:** "The bird..." or "True if...; false otherwise."
  * **Exceptions:** "Thrown when..." (or "If..." when the generator adds "Throws").
  * **Deprecations:** State what to use instead.

## Verb forms in reference documentation

For API/reference documentation descriptions:

* **Use third-person singular:** Describes what the method does (*Creates*, *Lists*, *Gets*).
* **Avoid imperative:** Do not use *Create*, *List*, *Get*.

## Format examples

* **Introduction:** End introductory sentence with a colon if the example follows immediately.
* **Inline:**
  * Use "for example" or "such as".
  * Use parentheses if the example is short and in the middle of a sentence.
* **Punctuation:** Use a comma or em dash before an example at the end of a sentence.

