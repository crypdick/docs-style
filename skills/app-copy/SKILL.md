---
name: app-copy
description: Review or edit user-facing application text in source code or localization files, including buttons, forms, errors, status, and confirmations. Use for app copy requests, rather than documentation style or general code review.
---

# Application copy

For a review, report findings. For an editing request, change the relevant
user-facing strings. Follow the product's terminology, tone, and capitalization
conventions. Use these rules when the project leaves a choice open.

Read the surrounding interface and trace the action or state behind each
message before changing it. Include accessible names and localization resources
when they describe the same control. Preserve interpolation variables, plural
forms, markup, translation keys, and program behavior.

## Describe the actual behavior

Distinguish starting an action from completing it. A queued job is not a finished
job. Accepting an order does not necessarily charge a customer. Do not promise
timing, availability, or future features without evidence from the product.

Use the same term for the same concept across related screens. Keep technical
terms that the audience needs. Explain or link unfamiliar terms where they
affect a decision. Keep help near the control it explains. Move optional detail
out of the main flow only when the interface supports it. Keep costs,
prerequisites, and consequences visible before the action.

## Name buttons and links

Use labels that describe the action and its target. Prefer **Save changes** or
**Delete project** over **Submit** or **OK** when those labels match the action.
Distinguish navigation, review, confirmation, and execution. Use **Review order**
for a review step and **Pay now** only when the action charges the customer.

Use sentence case unless the product has an established convention. Preserve
product names and acronyms. Give links meaningful destinations, such as
**View deployment logs**. Keep visible labels and accessible names consistent.

## Label forms

Use short, persistent labels. Placeholder text can show an example or expected
format. It must not replace the label or repeat it without adding information.
State required formats and constraints before submission when readers need them.
For validation errors, identify the field and explain how to correct the value.

## Explain errors and recovery

State what failed and give a recovery action when the product supports one.
Keep known causes and useful diagnostic details. Do not replace a specific
failure with a generic reassurance, blame the user, or guess the cause.

Recommend retrying only when it can resolve the failure and is safe for that
action. For example, an uncertain payment result needs a way to check payment
status before trying again. If recovery needs support, identify the contact
path and any existing error identifier that helps diagnose the problem.

## Explain status and confirmations

Report the observed state: pending, in progress, completed, or failed. After an
action, explain what happens next or where to find the result when it is not
already clear. For a queued export, use **Export queued. Check Exports for
progress.** only when that destination exists.

Use measured or documented timing when available. Otherwise describe the state
and how to check it. Do not invent a deadline or claim instant completion.

## Verify edits

Check the changed copy in context and run the project's relevant checks for
affected source or localization files. When a label changes, check selectors,
snapshots, and accessible names that depend on it. Report layout or rendered
states that you could not inspect. Vale's documentation rules do not govern
application strings.

These rules adapt selected ideas from
[SF Compute's copywriting guidelines](https://github.com/sfcompute/prompts/blob/main/copywriting.md),
with product behavior and established project conventions taking precedence.
