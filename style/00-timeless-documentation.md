# Timeless documentation

Timeless documentation avoids words that anchor the text to a specific point in time or assume knowledge of past/future versions. It reduces maintenance and ensures accuracy even when read months or years later.

**Focus on how the product works *right now*, not how it changed or might change.**

## Words to avoid

* **Implied context:** *currently*, *now*, *at present*, *as of this writing*. The documentation is assumed to be current for the version being read.
  * *Avoid:* "The emulator currently supports X." -> *Use:* "The emulator supports X."
* **Relative timing:** *new*, *newer*, *latest*. These quickly become outdated.
  * *Avoid:* "The new subcommands..." -> *Use:* "The subcommands..." (or specify the version adding them).
* **Promises/Speculation:** *soon*, *eventually*, *future*. Do not promise features that don't exist yet.

## Exceptions

* **Release notes & Blogs:** Time-based words (*new*, *currently*) are acceptable here as these documents are tied to a specific time.
* **Installation:** "Install the *latest* version" is a valid instruction.
* **Procedural timing:** "The VM restarts *soon* after you click..." is acceptable because it describes a sequence within the procedure, not the product roadmap.
