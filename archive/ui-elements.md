





# UI elements and interaction Stay organized with collections Save and categorize content based on your preferences.



## Focus on the task

When practical, state instructions in terms of what the reader
should accomplish, rather than focusing on the widgets and gestures.
By avoiding reference to UI elements, you help the reader understand
the purpose of an instruction, and it can help future-proof
procedures.

Recommended: Refresh the page.

Recommended: Expand the **Advanced options**
section.

However, know the audience and understand the context. In some cases, the point
of a procedure is to guide the reader through elements on the page. Or the UI might not be obvious,
and it's helpful to explain the gestures for completing a step. Provide the level of detail
that seems useful for the intended audience.

Recommended: Click **Refresh**.

Recommended: To expand the **Advanced
options** section, click the
arrow\_rightexpander arrow.

Not recommended: Click the zippy to expand
the **Advanced options** section.

The rest of this page focuses on scenarios where you've decided it's
useful to explicitly discuss UI elements.

For information about writing procedures, see [Procedures](/style/procedures).

## Format names of UI elements

When referring to any UI element by name, put its name in bold, using the
`b` element in HTML or `**` in Markdown. This
includes names for buttons, menus, dialogs, windows, list items, or any other
feature on the page that has a visible name. Don't use code font for UI elements,
unless it's an element that meets the [requirements for code font](/style/code-in-text).
In that case, use both code font and bold.

**Note**: The reason for using the [`b`
element](https://html.spec.whatwg.org/multipage/semantics.html#the-b-element) is that in modern HTML, `b` connotes text to which
you want to draw visual attention, whereas the [`strong`
element](https://html.spec.whatwg.org/multipage/semantics.html#the-strong-element) indicates strong importance.

Don't make an official feature name or product name bold, except when it
directly refers to an element on the page that uses the name (such as a window
title or button name).

Recommended:
In the **New project** window, select the **New activity**
checkbox, and then click **Next**.

Not recommended:
In the New Project window, select "New Activity", and then click the
"Next" button.

## Use appropriate capitalization

In most cases, follow the capitalization as it appears on the page. However,
if labels are inconsistent or they're all uppercase, use sentence case.

| Guidance | Recommended | Not recommended |
| --- | --- | --- |
| When a label is all uppercase, use sentence case. | Click refresh **Refresh**. | Click **REFRESH**. |
| When referring to multiple labels that are inconsistently cased, use sentence case for all of the labels. | Click **New project**, and then click **New activity**. | Click **NEW PROJECT**, and then click **New Activity**. |

## Refer to UI elements

Don't use UI elements as if they were English verbs or nouns.

| Recommended | Not recommended |
| --- | --- |
| In the **Name** field, enter an account name. | **Name** the account. |
| To save the settings, click **Save**. | **Save** the settings. |
| In the **Service account ID** field, enter a name.  For **Service account ID**, enter a name. | Specify a **Service account ID**. |

## Terminology and usage

A user interface can contain a variety of UI elements. In general, focus on
the feature and its functionality, not the UI element. If you think it adds
clarity for the reader, add the name of the UI element. For example, both of the
following sentences are valid:

Recommended:
Go to **File > Tools**.

Recommended:
In the **File** menu, click **Tools**.

Following are some definitions of the terms to use when referring to UI
elements.

For prepositions to use with these elements, see the
[Prepositions](#prepositions) table.

### Windows, pages, dialogs, and panes

Most often, a *window* is the entire application window in a desktop
environment. However, it can also refer to modular application elements that you
can open and close. For example, in Android Studio, several windows are
available in the **View > Tool Windows** menu.

Recommended:
In the **MyApp** window, click **Edit**.

Not recommended:
In the **MyApp** page, click **Edit**.

*Page* is the preferred term when referring to a web page in general, and to a sub-page
of a console in particular. For more information, see
[console](/style/word-list#console).

Recommended:
In the Google Cloud console, go to the **Deployments** page.

Not recommended:
In the Google Cloud console, go to the **Deployments** window.

A *dialog* is a smaller window that is usually detached from the
main application window and appears in front of the window.

Recommended:
In the **Welcome** dialog, click **OK**.

Not recommended:
In the **Welcome** pop-up window, click **OK**.

A *pane* is similar to a window inside the application—it's a
distinct rectangular region of a window. However, a pane is tightly coupled to
the other UI regions around it and usually cannot be hidden on its own, whereas
a window is distinctly separate and can be hidden. Do not use terms such as
*panel*, *section*, *area*, or *column* to
refer to a pane.

Recommended:
In the **Create service account** pane, click **New**.

Not recommended:
In the **Create service account** panel, click **New**.

### Menus and menu bars

In a desktop application, the *menu bar* appears at the top of the
window or at the top of the screen; it's a set of *menus* (such as
**File** or **Edit**), each of which is a set of related
*commands* and/or nested submenus.

To refer to an item in a menu, use the term *command*, not *choice*, *menu item*,
or *option*. Exception: if you're documenting how to build an interface,
you can use *menu item*.

To refer to a menu, use the form *the **LABEL\_NAME** menu.*

To tell the reader where to find a command in a menu or submenu, use a phrase like
*In the **File** menu, select **Open**.*

Don't use *drop-down* as a synonym for *menu*. See
[drop-down](/style/word-list#drop-down).

#### Use angle brackets

Another option is to use angle brackets (>). If you use angle brackets, follow these
guidelines:

* Put a nonbreaking space (`&nbsp;`) before each angle bracket.
* Don't bold each menu name separately; instead, enclose the entire sequence in a single bold
  tag (`<b>...</b>` or `**...**`).
* Wrap the angle bracket with a span tag and add an `aria-label` attribute with
  *and then* text
  (for example, `<span aria-label="and then">></span>`).
  Otherwise, some screen readers might read `>` as "greater than."

In the following example, the text renders as *Select **View >
Tools > Developer Tools***. A screen reader
interprets this as *Select View and then Tools and then Developer Tools*.

### HTML

```
Select <b>View&ampnbsp<span aria-label="and then">></span> Tools&ampnbsp<span aria-label="and then">></span> Developer Tools</b>.
```

### Markdown

```
Select **View&ampnbsp<span aria-label="and then">></span> Tools <span aria-label="and then">></span> Developer Tools**.
```

This notation is useful for abbreviating a longer phrase like *In the
**File** menu, select **Open**.* However, this notation applies only to
menu items. Don't use it to describe a combination of different UI elements.

Recommended: Select
**MyApp > Preferences**, and then select the
**Languages** preference pane.

Not recommended:
Select **MyApp** > **Preferences** > **Languages** >
**+** > **CSS**.

### Navigation menu

A *navigation menu* is a control—usually a pane or window—that contains a list of items
that the user can click to go to pages in an application or website. Don't use the terms
*navigation bar*, *navigation pane*, *navigation panel*, or
*navigation window* for such a control.

### Toolbar

A *toolbar* is a set of buttons for common user actions. A toolbar
button that includes a menu is called a *menu button*. Refer to the
toolbar by name if you think that the user needs help finding a button.

Recommended: On the **Dashboard**
toolbar, click **Edit**.

Recommended: Click **Edit**.

### Buttons and icons

A *button* initiates an action when clicked (or tapped, in the case
of a touchscreen). To refer to a button, use the button's label.

Recommended: Click **OK**.

Not recommended: Click the "OK"
button.

An icon is a symbol or image that represents an object or a function. An icon
can be a button as well. If the button includes an icon, write the name of the
button as shown in the tooltip, and add the button icon before the
name. If you need to use a space between the icon and the name for readability,
use a nonbreaking space.

Recommended: Click
more\_vert **Settings and utilities**.

Not recommended: Click
more\_vert.

If the icon tooltip is identical to the name of the icon, use an
[empty `alt` attribute](/style/images#alt-text).

If you're unsure of the name of the icon, inspect the element using browser
tools. In many cases, a visual element like an icon has an ARIA attribute
that provides a textual description of the element for use by screen readers.
To inspect an element, right-click the element and select
**Inspect** or **Inspect element**, depending on your browser. Look for one of the following
types of labels: `aria-labelledby`, `aria-label`,
`aria-describedby`, `label`, `placeholder`, or `title`.
For more information, see
[Using aria-label](https://www.w3.org/TR/WCAG20-TECHS/ARIA14.html)
and
[Accessible Name and Description calculation](https://www.w3.org/TR/html-aapi/#accessible-name-and-description-calculation).

If a button with an icon doesn't include a tooltip, submit a bug report
requesting that a tooltip be added. Tooltips are crucial for accessibility, and
for documentation and discoverability in general.

Recommended: Click ![](/static/style/images/icon-add.png) **Add**.

Not recommended: Click the ![hammer icon](/static/style/images/icon-add.png) icon.

If a UI element name ends with an ellipsis (...), leave out the ellipsis.

Recommended: Click **Browse**.

Not recommended: Click
**Browse ...**.

Don't use directional language to orient the reader, such as *above*,
*below*, or *right-hand side*. Phrases like those don't work well for
accessibility or for localization. If a UI element is hard to find, provide a
screenshot.

Recommended: Click menu **Menu**.

Not recommended: In the left-side panel,
click the button with three lines.

### Tab

A *tab* is a navigation element that looks like a file tab. To refer
to a tab, use the form *the **LABEL\_NAME** tab*.

Recommended: Select
**Tools > Options**, and then click the **Edit** tab.

### Text box

A *text box* is a box that the user can type in. Use
*box* and the form *the **LABEL\_NAME** box*. Format the text
that the user types by using the `code` element in HTML, or by using code
formatting (monospace) in other markup.

Recommended: In the **Owner** box,
enter your name.

Recommended: In the **Name** box,
enter `wsfc-1`.

In Google Cloud, use
*field* instead of *box*.

In Google Workspace documentation, use
*field* instead of *box*.

Recommended: In the **Instance** field,
specify a value less than 64 characters long.

### List box, combo box, and spin box

A *list box* is a box that offers the user a list of items. To refer to a list box, use
the form *the **LABEL\_NAME** list* or
*the **LABEL\_NAME** box*, whichever is clearer.

Recommended: In the **Item** list, select
**Desktop**.

A *combo box* is a combination of a text box and a list box. To
refer to a combo box, use the form *the **LABEL\_NAME** box*. To refer to
entering a value into a combo box, use the verbs *type or select* or *enter*.

Recommended: In the **Font** box, type
or select the font that you want to use.

A *spin box* is a box that lets the user choose a value by clicking
arrows or by typing. To refer to a spin box, use the form *the
**LABEL\_NAME** box*. To refer to entering a value into a spin
box, use the verb *enter*.

Recommended: In the **Font Size** box,
enter a font size.

### Checkbox

A *checkbox* is a small box that indicates whether an option is
on or off. To refer to a checkbox, use the form *the
**LABEL\_NAME** checkbox*.

Be wary of using the verbs *check* and *uncheck*, which can be ambiguous; it's often
best to use *select* and *clear* instead.

Recommended: Select the **Automatically
check for updates** checkbox.

Recommended: Clear the
**Bookmarks** checkbox.

If you need to refer to the state of the checkbox, it's often best to refer to it as
*selected* or *not selected*.

Recommended: Make sure that the
**Bookmarks** checkbox is selected.

Recommended: Make sure that the
**Bookmarks** checkbox isn't selected.

### Radio button

A *radio button* is a small button used to choose one item from a
group of mutually exclusive options. To refer to a radio button, use the radio
button's label, or refer to the group of buttons by its label.

Recommended: Select **Do not remember
passwords**.

Recommended: For **Startup mode**,
select an option.

### Expander arrow

An *expander arrow* is the UI element used to expand or collapse a section of
navigation or content. Avoid referring to these explicitly in documentation, but when you do, use
the terms *expander arrow* and *expandable section* rather than terms like
*expando* or *zippy*.

Recommended: To expand the
**Advanced options** section, click the
arrow\_rightexpander arrow.

Not recommended: To expand
the **Advanced options** section, click the zippy.

### Toggle

A *toggle* is the UI element that switches back and forth between on and off
states. Don't use the word *toggle* as a verb. Describe the action that you want the
user to take.

Recommended: To turn on the setting, click
the **Wi-Fi** toggle.

In some cases, you might not know what state the toggle is in before the user interacts with it
so be clear what position the toggle should be in.

Recommended: In **Settings**, click
the **Magic mode** toggle to the on position.

## Press and type keyboard keys

To indicate that the user should press a given keyboard key or
combination, use the `kbd` element.

The following is an example of a `<kbd>` tag:

Recommended:
`Press <kbd>Control+C</kbd>.`

When rendered, the text appears as follows:

Recommended: Press `Control+C`.

If you're working with non-HTML markup, use monospace formatting, which is how the
`kbd` element renders.

To refer to a letter key, use uppercase instead of lowercase.

Recommended: To save, press
`Control+S`.

Not recommended: To save, press
`Control+s`.

To refer to a key that the user types to enter that key's value as text input,
use the `code` element, not the `kbd` element.
For more information, see [Code font](/style/text-formatting#code-font).

To refer to a keyboard key, use the key's name. If that's ambiguous, use the
form *the `KEY_NAME` key*.

Recommended: Press `Esc`.

Recommended: Press the `Esc` key.

Spell out the names of modifier keys such as Command, Control, Option, and
Shift. Don't use symbols for those keys. To refer to a key combination, use the
form *`MODIFIER+KEY_NAME`*.

Recommended: Press
`Control+V`.

When you provide shortcuts for multiple operating systems, put the macOS shortcut in
parentheses after the Windows and Linux shortcut.

Recommended: To copy, press
`Control+C` (or `Command+C` on macOS).

Not recommended: To copy, press
`Ctrl+C` (`⌘+C`).

To refer to a key or combination that uses the Shift key, use the form
*`MODIFIER+Shift+KEY_NAME`*.

Recommended: Press
`Control+Shift+?`.

Spell out the names of characters that could be confusing in a keyboard
shortcut, such as comma, hyphen, period, and plus.

To refer to a keyboard shortcut, use either *keyboard shortcut* or *key
combination*.

To refer to pressing a key or combination to cause an action to occur, use
the verb *press*. To refer to typing a key or combination as part of text, use
the verbs *enter* or *type*.

## Prepositions

When documenting the UI, use the following prepositions.

| Preposition | UI element | Recommended |
| --- | --- | --- |
| in | dialogs  fields  lists  menus  panes  windows | In the **Alert** dialog, click **OK**.  In the **Name** field, enter `wsfc-1`.  In the **Item** list, select **Desktop**.  In the **File** menu, click **Tools**.  In the **Metrics** pane, click **New**.  In the **Task** window, click **Start**. |
| on | pages  tabs  toolbars | On the **Create an instance** page, click **Add**.  On the **Edit** tab, click **Save**.  On the **Dashboard** toolbar, click **Edit**. |

## Verbs in procedures

To describe an action on the page, use the following verbs. For more
information about each verb, see its corresponding entry on the
[word list](/style/word-list).

* [Click](/style/word-list#click)
* [Choose](/style/word-list#choose)
* [Drag](/style/word-list#drag)
* [Enable](/style/word-list#enable)
* [Enter, type](/style/word-list#enter)
* Go to (see [scroll](/style/word-list#scroll))
* [Hold the pointer over](/style/word-list#hold-the-pointer-over)
* [Press](/style/word-list#press)
* [Select](/style/word-list#select)
* [Tap](/style/word-list#tap)
* [Turn on, turn off](/style/word-list#turn-on)

For information about writing procedures, see [Procedures](/style/procedures).






