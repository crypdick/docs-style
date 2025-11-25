# Procedures

A procedure is a sequence of numbered steps to accomplish a task.

## Best Practices

* **One way only:** Document the best/easiest way to do a task. Do not document multiple methods (e.g., console vs CLI) unless necessary.
* **No repetition:** Link to existing procedures instead of repeating steps.
* **Keyboard shortcuts:** Do not use them (they vary by OS/locale).
* **Politeness:** Do not use "please".
* **Introduction:** Provide context. End with a colon if steps follow immediately, or a period if there is intervening text.

## Step Structure

1. **Imperative verb:** Start with the action ("Click", "Enter").
2. **Location first:** State where to act before the action ("In the console, click **Save**").
3. **Goal first:** If the step has a specific goal, state it first ("To save changes, click **Save**").
4. **Code/Commands:** Focus on what the command does, not the act of running it.
    * **Recommended:** "Deploy the app:"
    * **Not recommended:** "Run the following command to deploy the app:"

## Formatting

* **Single step:** Use a bullet, not a number.
* **Sub-steps:** Use lowercase letters (a, b).
* **Optional steps:** Start with "Optional:" (no parentheses).
* **Results:** Place the result of an action in the same paragraph as the step.
* **Menu paths:** Use `>` to combine short menu selections.
  * *Recommended:* "Click **File > New > Document**."
