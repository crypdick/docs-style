# Documentation principles

## Write for the reader's task

Open each page with its purpose and what it helps the reader accomplish.
Organize instructions around tasks, and introduce information where readers
need it. Keep exhaustive option lists in reference material and product history
in release notes.

Separate usage guidance from internal design. Explain behavior, configuration,
and limitations in usage docs when readers need them to use the product.
Put implementation details for people building, debugging, or extending the
product in architecture or contributor docs. Follow the project's existing
structure rather than requiring particular directory names.

## Organize for selective reading

Give each topic one canonical explanation. Link to it from other pages instead
of maintaining duplicate explanations. Short summaries can orient readers
without repeating the details.

Use overview pages for summaries and links, group related topics, and keep
detailed instructions and reference material in focused pages. This lets humans
and agents find relevant content without reading the entire documentation set.

Keep each page focused on one coherent topic or task. Split unrelated concerns
when they obscure what readers need, but keep the steps and context needed to
complete a task together. File length alone isn't a reason to split a page.

## Describe supported extensions

For products with replaceable implementations, explain the shared concept and
contract before describing the default implementation. Distinguish guarantees
of the shared interface from capabilities of a particular implementation.

Keep implementation-specific details in clearly labeled sections, and link to
extension guidance where it helps readers customize behavior. Apply this
structure only where the product supports alternatives.

## Keep documentation accurate

Update documentation with changes to the behavior it describes. Check commands,
defaults, and constraints against their source before stating them as facts.
When code and prose repeat a value, follow the project's convention for keeping
them synchronized, such as a nearby cross-reference or a generated reference.

## Prescriptive documentation

Write prescriptive (opinionated) documentation that tells the reader what to do rather than just listing options.

### Word choice

* **Required actions:** Use *must* or imperative mood ("Do X").
* **Recommended actions:** Use "We recommend..." or "Google recommends...".
* **Optional actions:** Use *can*.
* **Possibilities:** Use *might* or *can*.
* **Outcomes:** Describe what happens ("The process returns 10 items").
* **Actual state:** When describing the state of something (e.g., a variable), use *is*, *sets*, or *must set*.
  * *Correct:* "The server sets the value to true."

## Timeless documentation

Avoid wording that depends on when the reader sees it or assumes knowledge of past or future versions. This reduces the need to update descriptions just because time has passed.

Describe how the product works. Use release notes to explain changes over time.

### Words to avoid

* **Relative timing:** *new*, *newer*, *latest*. These quickly become outdated.
  * *Avoid:* "The new subcommands..." -> *Use:* "The subcommands..." (or specify the version adding them).

### Exceptions

* **Release notes and blogs:** Time-based words (*new*, *currently*) are acceptable here as these documents are tied to a specific time.
* **Installation:** "Install the *latest* version" is a valid instruction.
* **Procedural timing:** "The VM restarts *soon* after you click..." is acceptable because it describes a sequence within the procedure, not the product roadmap.
