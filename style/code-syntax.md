# Command-line syntax

## Formatting

* Use code blocks with language-specific syntax highlighting (`shell` for console commands, `bash` for bash scripts, `python` for Python).
* Indent code inside fences by 4 spaces.
* Break lines at 80 characters when possible. After the first line, indent continuation lines by 4 spaces.
* End each line (except the last) with the continuation character: `\` (Linux/Cloud Shell) or `^` (Windows).
* Link to the command reference when introducing a command.
* Minimize arguments to what's needed for the task. Let the reference cover all options.

## Prompts

* Use `$` for shell prompts (optional for single-line commands).
* Don't show directory paths before the prompt unless context changes (e.g., local to remote).
* Use separate code blocks for input and output.

## Syntax notation

Use these characters to document syntax, not in click-to-copy examples:

* `[optional]` — optional argument
* `{choice1|choice2}` — mutually exclusive options
* `...` — repeating argument

## Click-to-copy examples

Never use `[]`, `{}`, `|`, or `...` in copyable examples—they break if not removed. Instead:

* **Remove optional arguments** and note alternatives in prose.
* **Use separate code blocks** for each variant.
* **Document options in separate tasks** (e.g., separate sections for different flags).
* **Use placeholders** like `INSTANCE_NAME` (not `[INSTANCE_NAME]`).

## Output

* Only show output if it adds value (e.g., reader needs to verify or copy a value).
* Introduce with "The output is the following:" or "The output is similar to the following:".
* Use `...` on a separate line to indicate omitted lines.
