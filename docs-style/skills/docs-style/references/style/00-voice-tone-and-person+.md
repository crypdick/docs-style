# Voice, tone, tense, and person

## Voice and tone

**Voice:** Conversational, friendly, respectful, and knowledgeable. Aim to sound like a helpful colleague.
**Tone:** Casual but professional. Accessible to a global audience.

### Guidelines

* **Be conversational but not colloquial:** Use natural language, but avoid slang ("dude", "awesome") or text-speak.
* **Be direct but polite:** Use the imperative mood ("Click Save") without excessive politeness ("Please click Save").
  * *Exception:* "Please" is acceptable in FAQs or when asking for user feedback/help.
* **Avoid fillers:** Remove phrases like "Please note," "At this time," or "It is important to note that."
* **No "Let's":** Avoid "Let's do X." Use "Do X."
* **No pop-culture references:** They age poorly and may not translate across cultures.

### Techniques for checking tone

* **Read it aloud:** If a sentence sounds awkward or robotic when spoken, rewrite it to be more conversational.
* **Check transitions:** Use transitions (*though*, *however*, *this way*) to make text flow smoother, but avoid overusing formal transitions like *nonetheless* or *herein*.

### Anthropomorphism

Don't attribute human qualities (seeing, telling, thinking, wanting) to software or hardware.

**Why?** Anthropomorphism is figurative language, which is imprecise and difficult to translate.

* **Recommended:** "The system detects a new device." / "The object specifies the split point."
* **Not recommended:** "The system sees a new device." / "The object tells the splitter..."

### Excessive claims

* **Avoid hype:** Don't use *best*, *fastest*, *guaranteed* unless verifiable.
* **Future-proof:** Ensure claims will remain true over time. Avoid absolute statements that might be invalidated by future releases or competitor updates.
* **Security:** Don't claim a product is "secure" (implies invulnerability). Say it "helps with security" or "is designed for security".
* **Comparisons:** Be factual, specific, and cite sources.

## Active voice

Use active voice. The grammatical subject should perform the action.

**Why?** Passive voice often obscures the actor, making it hard for the reader to know *who* or *what* is responsible (the user? the system? a background process?).

* **Active:** "The client queries the server." (Clear: Client -> Server)
* **Passive:** "The server is queried." (Unclear: By whom?)
* **Clumsy Passive:** "The server is queried by the client." (Wordy. Just use active.)

### Exceptions (When passive is okay)

Passive voice is acceptable when the actor is unknown, irrelevant, or you want to emphasize the object.

* **Emphasis on object:** "The file is saved." (The saving is more important than who clicked the button).
* **De-emphasizing the subject:** "Over 50 conflicts were found." (Better than "You created over 50 conflicts").
* **Unknown actor:** "The database was purged." (It doesn't matter which specific process did it).

## Present tense

Use present tense for statements that describe general behavior that is not associated with a particular time.

### Future tense

Use future tense (*will*) only to distinguish an action that will occur in the future, distinct from the immediate action being described.

* **Correct:** "Add the filename to the backup list. The file **will be archived** the next time the backup process runs." (The archiving happens later).
* **Incorrect:** "A message is sent that **will notify** subscribers." (If the notification is part of the sending process, use present: "that *notifies* subscribers").

**Do not use future tense for:**

* Product behavior that happens immediately or asynchronously (unless strictly a future event).
* Describing how a feature *will* work after a future update (document the current version).

### Hypotheticals

Avoid the hypothetical future *would*. It often implies uncertainty.

* **Recommended:** "If you send an unsubscribe message, the server **removes** you from the mailing list."
* **Not recommended:** "You can send an unsubscribe message. The server **would then remove** you from the mailing list."

## Person and pronouns

### Second and first person

* **Address the reader as *you*:** Use second person (*you/your*) for the reader. Use imperative verbs for instructions ("Click Submit").
* **Software/Users as third person:** Use third person for the software or other users ("The system processes...", "The user account is created...").
* **Organization as *we*:** Use *we* only to refer to the organization ("We recommend...", "Contact us").
* **Audience consistency:** Identify who *you* is (developer? sysadmin?) and be consistent. Do not switch expected personas mid-document.

### Pronoun clarity

Ensure pronouns clearly refer to their antecedent.

#### Ambiguous references

* **Clarify 'it/this/that':** Follow demonstrative pronouns with a noun.
  * **Recommended:** "Set *this value* to true."
  * **Not recommended:** "Set *this* to true."
* **Vague antecedents:** Rewrite if the pronoun's target is unclear.
  * **Ambiguous:** "If you type text in the field, it doesn't change." (Does "it" refer to the text or the field?)
  * **Clear:** "If you type text in the field, the text doesn't change."

#### Gender-neutral pronouns

* Use singular *they*.

#### Personal pronouns

* **Second person:** Use *you* whenever possible.
* **First person:** Avoid *I*, *we*, *us* except in FAQs or when referring to the organization (e.g., "We recommend...").

#### Relative pronouns

* **That vs. Which:**
  * Use *that* for restrictive clauses (no comma): "The echidna *that has a long snout* is furry." (Specifies which one).
  * Use *which* for non-restrictive clauses (comma): "The echidna, *which has a long snout*, is furry." (Adds extra info).
* **Who:** Use *who* for people.
* **Optional pronouns:** Use *that* and *which* to prevent ambiguity (e.g., "The link *that* you want to open").

