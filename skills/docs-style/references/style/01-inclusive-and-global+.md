# Inclusive and global documentation

## Inclusive documentation

Write documentation that is respectful and accessible to everyone.

### Avoid non-inclusive language

Avoid ableist, gendered, violent, and socially charged language. Vale automation checks for specific terms.

### Handle legacy code terms

If non-inclusive terms exist in code (e.g., a configuration parameter named `master`):

* **Code font:** Always use code font for the term: `master`.
* **Context:** Use the inclusive term in prose ("The primary node...").
* **Transition:** If necessary for clarity, you can reference the legacy term in parentheses on first use: "The primary node (called `master` in the configuration) manages the cluster."
* **Do not propagate:** Use the inclusive term for all subsequent mentions.

### Diversity

* Use diverse names, locations, and scenarios in examples.
* Avoid US-centric metaphors (sports, holidays).

## Write for a global audience

Use language that non-native speakers can understand and that machine translation can handle.

### Best practices

* **Short sentences:** Easier to translate and understand.
* **Simple vocabulary:** Use *start* instead of *commence*, *use* instead of *leverage*.
* **Avoid wordy phrases:** Use *use* instead of *make use of*. Keep familiar technical phrases such as *log in*.
* **Active voice:** "System processes data" (clear subject).
* **No directional language:** Avoid *above* or *below* (layout may change).
* **Explicit helper words:** Use *that*, *of*, *then* to clarify relationships (e.g., "The rule *that* you defined").
* **Clarify antecedents:** If a pronoun (*it*, *they*) is ambiguous, replace it with the noun.
  * *Ambiguous:* "If you use the term in an ad, make sure **it** is targeted."
  * *Clear:* "If you use the term in an ad, make sure **the ad** is targeted."
* **Modifier placement:** Place modifiers like *only* immediately before the word they modify.
  * *Correct:* "Request *only* one token."
  * *Different meaning:* "*Only* request one token" can mean to request it without taking another action.
* **Noun phrases:** Rewrite strings of modifiers when it is unclear how the words relate to each other. Preserve established technical terms.
* **Repetition:** Repeat a word if it improves clarity.
  * *Better:* "IAM segmentation and network segmentation."
  * *Worse:* "IAM and network segmentation."
* **Consistency:** Use the exact same term for the same concept every time.
* **Inclusivity:** Avoid idioms (*ballpark*, *back burner*) and culturally specific references (seasons, holidays).
