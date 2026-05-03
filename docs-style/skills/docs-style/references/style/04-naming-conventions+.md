# Naming conventions

## Filenames and file types

**Important:** Do not apply these naming rules to existing links or URLs (this will break them).

### Guidelines for names

* **Format:** Use lowercase with hyphens (`query-data.html`).
  * **Why?** Search engines interpret hyphens as spaces (good for SEO). Underscores are often treated as joining characters.
* **Consistency Exception:** If a directory already uses underscores (e.g. `lesson_1.md`), match the existing pattern (`lesson_2.md`) rather than mixing styles.
* **Characters:** Use only ASCII alphanumeric characters.
* **Clarity:** Avoid generic names (`document1.html`).

### Referencing

* **Files:** Use code font and add "file" (e.g., "the `build.sh` file").
* **Types:** Use formal names (PNG file), not extensions (`.png` file), unless discussing the extension itself.
* **Verbs:** Do not use file types as verbs (e.g., "Extract the zip file", not "Unzip").

## Placeholders

### Format

* **Style:** Uppercase with underscores (`PROJECT_ID`).
* **No possessives:** Do not use possessive adjectives (`YOUR_PROJECT_ID`).
* **Inline:** Mark with code font (`PROJECT_ID`).

### Explaining Placeholders

Explain placeholders on their first use.

* **Single placeholder:** "Replace `PLACEHOLDER` with..."
* **Multiple placeholders:** Use a list introduced by "Replace the following:"
  * `PLACEHOLDER`: description

### Output

If example output contains placeholders, explain them: "This output includes the following values:"

