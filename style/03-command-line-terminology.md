# Command-line terminology

## General guidance

* **Prefer explaining what the command does** rather than naming each element, especially for complex Linux commands.
* **Ask whether readers need terminology** or just need to understand the command's behavior.

## gcloud CLI

* **Structure:** `gcloud GROUP COMMAND --flag=VALUE ARGUMENT`
  * Groups can be nested (e.g., `gcloud compute instances list`)
  * `--` separates gcloud flags from user arguments
* **Terms:** Use `command`, `group`, `flag`, and `argument`.
* **Catchall:** *Option* works when you don't want specialized nomenclature.

## Linux commands

* **Complexity warning:** Linux syntax includes options, parameters, arguments, metacharacters (`*`, `?`), redirection (`|`, `>`, `<`), and more.
* **Terms:** Use `command`, `option` (starts with `-`), and `argument`.
* **Catchall:** *Option* is safe for general use.

## Linux signals

Use the specific verb associated with each signal:

* `SIGKILL`: **kill** (Cannot be caught/ignored. Do not use *stop* or *terminate*).
* `SIGTERM`: **terminate** (Requests termination, allows cleanup. Do not use *kill*).
* `SIGQUIT`: **quit** (Keyboard quit, can be caught).
* `SIGINT`: **interrupt** (Ctrl+C, terminates gracefully).
* `SIGPAUSE`: **pause** or **sleep** (Waits for signal).
* `SIGSUSPEND`: **suspend** (Temporarily pauses execution).
* `SIGSTOP`: **stop** (Stops for later continuation with `SIGCONT`. Cannot be caught).
