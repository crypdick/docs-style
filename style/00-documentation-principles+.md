# Documentation principles

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

Timeless documentation avoids words that anchor the text to a specific point in time or assume knowledge of past/future versions. It reduces maintenance and ensures accuracy even when read months or years later.

**Focus on how the product works *right now*, not how it changed or might change.**

### Words to avoid

* **Relative timing:** *new*, *newer*, *latest*. These quickly become outdated.
  * *Avoid:* "The new subcommands..." -> *Use:* "The subcommands..." (or specify the version adding them).

### Exceptions

* **Release notes & Blogs:** Time-based words (*new*, *currently*) are acceptable here as these documents are tied to a specific time.
* **Installation:** "Install the *latest* version" is a valid instruction.
* **Procedural timing:** "The VM restarts *soon* after you click..." is acceptable because it describes a sequence within the procedure, not the product roadmap.

