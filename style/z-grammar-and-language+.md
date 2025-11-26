# Grammar and language mechanics

## Numbers

* **Spell out:**
  * Numbers 0-9.
  * Any number at the start of a sentence.
  * Indefinite numbers (*millions*).
* **Use Numerals:**
  * 10 and greater.
  * Technical quantities/measurements (even < 10): *5 MB*, *version 3*, *64-bit*.
  * Decimals, percentages (*5%*), negative numbers.
  * Dimensions (*192x192* - use lowercase x).
* **Formatting:**
  * **Commas:** Use for 4+ digits (1,000).
  * **Ranges:** Use a hyphen (10-20).
  * **Currency:** US style (`$10.00`).
  * **Fractions:** Express as decimal numbers when possible (*0.75* instead of *three-quarters*).

## Abbreviations

Use standard abbreviations to save time, but spell them out if they might be unfamiliar. If the reader has to pause to decipher an abbreviation, it slows down comprehension.

* **First reference:** Spell out the term followed by the abbreviation in parentheses: *Border Gateway Protocol* (*BGP*).
* **Exceptions:** Don't spell out widely known terms (AI, API, URL, PDF, JSON, USB).
* **Plurals:** Add *s* or *es* (APIs, OSes). Do not use an apostrophe.
* **Verbs:** Do not use abbreviations as verbs (e.g., "Use SSH to log in", not "ssh into").
* **Periods:** Use periods for shortened words (Dr., etc.).

### Indefinite articles

Choose *a* or *an* based on the pronunciation of the abbreviation.

* "an API" (pronounced "ay-pee-eye" - starts with vowel sound).
* "a URL" (pronounced "yu-are-el" - starts with consonant sound).

## Plurals

### Single letters

Italicize the letter and add *'s* (e.g., "Mind your *p*'s and *q*'s"). When capitalization is irrelevant, use uppercase (e.g., "Mind your *P's* and *Q's*").

## Possessives

### Form

* **Singular nouns (including ending in s):** Add *'s* (e.g., *vector's*, *class's*).
* **Plural nouns ending in s:** Add apostrophe only (e.g., *models'*).
* **Plural nouns not ending in s:** Add *'s* (e.g., *people's*).

### Restrictions

* **Products/Trademarks:** Do not form possessives of product names or trademarks.
  * **Recommended:** "Performance of Google Search"
  * **Not recommended:** "Google Search's performance"
* **Companies:** Possessives are allowed (*Google's office*) unless the name is used as a trademark.
* **Code:** Do not form possessives of code items.
  * **Recommended:** "Value of `wordCount`"
  * **Not recommended:** "`wordCount`'s value"

### Awkward possessives

If a possessive phrase sounds clunky or confusing, rewrite it using *of* or by rearranging the sentence.

* **Recommended:** "The rule that the FTC issued."
* **Not recommended:** "The FTC's rule."

## Prepositions

* **End of sentence:** It is acceptable to end a sentence with a preposition if it sounds more natural (e.g., "...the language you're interacting with").
* **Clarity:** Use prepositions to increase clarity, but omit unnecessary ones.

## Sentence structure

* **Conditions first:** Place circumstances/conditions before instructions so readers know if it applies to them.
  * **Recommended:** "If you want to delete the file, click **Delete**."
  * **Not recommended:** "Click **Delete** if you want to delete the file."
* **Natural order:** If putting the condition first creates a convoluted sentence, rewrite it for natural flow.
  * *Awkward condition-first:* "In the environment you plan to use to build documentation, don't install Ray."
  * *Better:* "When building documentation, use a separate environment that doesn't have Ray installed."
* **Closeness:** Keep the subject and verb close together.

## Punctuation

### Colons

* **Introduction:** Preceding text must be a complete sentence.

### Semicolons

Avoid semicolons. Use them only for:

* Joining closely related independent clauses (especially with adverbs like *however*, *therefore*).
* Separating complex list items that contain internal commas.

### Periods

* **Usage:**
  * **Lists:** End items with a period if they are complete sentences.
  * **URLs:** Avoid ending a sentence with a URL. If unavoidable, do not put a space between the URL and the period.
  * **Numbers:** Use periods for decimals.

### Commas

* **Introductory phrases:** Place a comma after introductory phrases ("Finally, ...").
* **Independent clauses:**
  * Use a comma before coordinating conjunctions (*and, but, or*) that join two independent clauses ("The library creates feeds, and it ensures validity").
  * *Exception:* You can omit the comma if both clauses are very short.
* **Dependent clauses:**
  * Generally **no comma** if the dependent clause follows the independent one ("Flags are variables and can be read directly").
  * Use a comma *only* if the sentence is confusing without it.
* **Nonrestrictive clauses:** Use commas to set off clauses that add extra info ("The group, *which is large*, ...").
* **Conjunctive adverbs:** Comma after *however*, *therefore*, etc.

### Ellipses

* **Quotes:** Use to indicate omitted text in quotes (4 dots if crossing sentence boundary).
* **UI:** Use if the UI element contains them (`Save ...`).
* **Formatting:** Space before and after (` ... `).
* **Code samples:** Use comments (e.g., `# Code omitted`) instead of ellipses (`...`).

### Parentheses

Avoid parentheses for important information; assume readers might skip them. Use commas, dashes, or separate sentences instead.

* **Usage:** Keep parenthetical content short.
* **Punctuation:**
  * **Inside:** If the parentheses contain a complete standalone sentence, place the period *inside* the closing parenthesis.
  * **Outside:** If the parentheses are part of a larger sentence, place the period *outside* the closing parenthesis.

### Quotation marks

* **Type:** Use straight double quotes (`"`). Use single quotes (`'`) only for nested quotations or specific code syntax.
* **Usage:**
  * **Titles:** Use for titles of short works (articles).
  * **Metaphors:** Use if introducing an unfamiliar metaphorical term (e.g., This configuration forms an "island" in the network).
  * **Emphasis:** Do not use quotation marks for emphasis.
* **Punctuation:**
  * **Exception:** Place punctuation *outside* if the quote is a literal string or code entity (e.g., If you enter "escape", the program crashes.).

### Slashes

* **Avoid:** Do not use slashes for "or" (use the word *or*) or for abbreviations (*care of*, not *c/o*).
* **And/or:** Avoid *and/or* (usually *and* suffices).
* **Dates/Fractions:** Do not use slashes.
* **Allowed:** File paths and URLs.
* **Line breaks:** If a long URL must be broken across lines, break it immediately after a slash. Do not add a hyphen.

### Dashes

* **Em dash (—):** Use for interruptions or breaks in thought.
* **En dash (–):** Do not use. Use a hyphen or "to" for ranges (e.g., 10-20 or 10 to 20).
* **Lists:** Use a colon (not a dash) to separate items from descriptions in lists.

### Hyphens

Use hyphens for clarity and to combine terms.

#### General usage

* **No spaces:** Never place a space around a hyphen (except for suspended hyphens).

#### Compounds

* **Modifiers:** Hyphenate compound modifiers before a noun (*well-designed app*).
  * **Exception:** Do not hyphenate adverbs ending in *-ly* (*publicly available*).
* **Predicate:** Do not hyphenate compound modifiers after the noun (*app is well designed*).
* **Nouns:** Generally closed (one word) if standard (*webpage*, *workaround*).

#### Prefixes

* **General rule:** No hyphen (*metadata*, *subsystem*).
* **Exceptions (use hyphen):**
  * *self-*, *cross-*, *all-*, *ex-*
  * Proper nouns (*non-Google*)
  * Numbers (*post-2000*)
  * Clarity (*re-sign* vs *resign*)

#### Numbers

* **Ranges:** Use a hyphen (10-20), NOT an en dash.
* **Units:** Do not hyphenate number + unit (*200 GB disk*), except for modifiers where the unit implies multiplication (*vCPU-hours*, *person-hours*).
* **Suspended:** Use for shared base (*one- or two-hour intervals*).

