# Inclusive documentation

Write documentation that is respectful and accessible to everyone.

## Avoid non-inclusive language

* **Ableist:** Avoid *sanity check*, *cripple*, *crazy*, *blind eye*. Use *final check*, *slow down*, *baffling*, *ignore*.
* **Gendered:** Avoid *man-hours*, *mankind*. Use *person-hours*, *humanity*.
* **Violent:** Avoid *kill*, *hang*. Use *stop*, *unresponsive*.
* **Socially charged:**
  * Avoid *blacklist/whitelist*, *master/slave*. Use *blocklist/allowlist*, *primary/replica*, *controller/agent*.
  * Avoid *first-class citizen*. Use *core feature*, *built-in*, or *top-level*.

## Handling legacy code terms

If non-inclusive terms exist in code (e.g., a config parameter named `master`):

* **Code font:** Always use code font for the term: `master`.
* **Context:** Use the inclusive term in prose ("The primary node...").
* **Transition:** If necessary for clarity, you can reference the legacy term in parentheses on first use: "The primary node (called `master` in the configuration) manages the cluster."
* **Do not propagate:** Use the inclusive term for all subsequent mentions.

## Diversity

* Use diverse names, locations, and scenarios in examples.
* Avoid US-centric metaphors (sports, holidays).
