# API reference code comments

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
