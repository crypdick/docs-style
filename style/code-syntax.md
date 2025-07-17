# Document command-line syntax  

## Best practices

When you write procedural or conceptual documentation for a command-line command, apply the
following best practices:

* **Provide an inline link to the command reference**. A good place for that link is in
  the text that introduces the command or a series of steps.

  Recommended:

  To connect to the instance, use the
  [`gcloud compute ssh` command](https://cloud.google.com/sdk/gcloud/reference/compute/ssh):

```shell
    gcloud compute ssh
```

* Code inside a code-fence should be indented by 4 spaces.
* Multiline shell scripts should indent the subsequent lines by 4 spaces.

  Recommended:

```shell
    python run.py --flag1 \
        --flag2 \
        --flag3
```

* Use language-specific syntax highlighting for code blocks, e.g. `python` for Python scripts.
  Use `shell` for console commands, and `bash` when you are showing an actual bash script.
  Do not change the language of the code block if one has already been specified.

* **Determine which arguments are needed to complete each task in the recommended way**.
  To minimize the number of options that you need to document in non-reference content, use as
  few optional arguments as possible. Rely on the command reference for the complete list of
  arguments.
* **Provide a click-to-copy command example that the reader doesn't need to edit after they
  copy it**. If possible, include only runnable code and placeholder variables in the
  click-to-copy example.

  Some command examples contain
  [optional arguments](#optional-arguments),
  [mutually exclusive arguments](#set-of-two-arguments), or
  [repeated arguments](#arguments-that-can-repeat)
  that are indicated by square brackets (`[]`), pipes (`|`),
  braces (`{}`), and ellipses (`...`). These characters can break
  commands if they're not first removed. For that reason, avoid using these
  arguments in click-to-copy examples.

## Format a command

To mark a block of code such as a lengthy command or a code sample, use the
following formatting:

* In HTML, use the `pre` element.
* In Markdown, use a code fence (`````).

To format a command with multiple elements, do the following:

* When a line exceeds 80 characters, you can safely add a line break before
  some characters, such as a single hyphen, double hyphen, underscore, or
  quotation marks. After the first line, indent each line by four spaces to vertically align each line
  that follows a line break.
* When you split a command line with a line break, each line except the
  last line must end with the command-continuation character. Commands that don't
  have the command-continuation character don't work.

  + Linux or Cloud Shell: A backslash typically preceded with a space
    ( `\`)
  + Windows: A caret preceded with a space ( `^`)
* Format placeholder text with placeholders.
* Follow the command line with a descriptive list of the placeholders
  used in the command line.
* When documenting a command-line option or argument, use end puctuation for complete
  sentences. Don't use end punctuation for single words or noun phrases, unless there is a mix of
  sentences and noun phrases.

## Command prompt

If your command-line instructions show multiple lines of input in one block, then start each line
of input with the prompt symbol. If you don't want users to copy the prompt symbol when they copy
the command, you might be able to turn off text selection for the symbol—for example, by using
CSS.

Don't show the current directory path before the prompt, even if
part of the instruction includes changing directories. However, if the overall
context of the command interface changes—such as from the local machine
to a remote machine—then add an additional prompt indicator, as appropriate, for
the new context.

Recommended:

Enter the following code into the terminal:

```shell
    $ adb devices
```

The output is the following:

```shell
List of devices attached
emulator-5554  device
emulator-5556  device
```

Recommended:

```shell
    $ adb shell
    shell@ $ screencap /sdcard/screen.png
    shell@ $ exit
    $ adb pull /sdcard/screen.png
```

When you're showing a one-line command, the command prompt
(the `$` symbol) is optional.

If your command-line instructions include a combination of input and output
lines, we recommend using separate code blocks for input and output.

Recommended:

```shell
    cat ~/.ssh/my-ssh-key.pub
```

The output is similar to the following:

```shell
    ssh-rsa KEY_VALUE USERNAME
```

## Optional arguments

Use square brackets around an argument to indicate that it's optional. If there's more than one
optional argument, enclose each item in its own set of square brackets.

Avoid using optional arguments in click-to-copy code examples.

In the following example, `GROUP` is required, but
`GLOBAL_FLAG` and `FILENAME` are optional:

```shell
    gcloud dns GROUP [GLOBAL_FLAG] [FILENAME]
```

## Mutually exclusive arguments

Use curly braces to indicate that the reader must choose one—and only one—of the
items inside the braces. There can be more than two mutually exclusive choices. To separate each
choice, use a pipe (`|`).

Avoid using mutually exclusive arguments in click-to-copy code examples.

In the following example, choose either `FILE_1` or `FILE_2`:

```shell
    {FILE_1|FILE_2}
```

In the following example, there are also two options:

* Left side of pipe: If the source code is deployed from a cloud
  repository, the following is required:  
  `--source=CLOUD_SOURCE --source-url=SOURCE_URL`
* Right side of pipe: If the source code is in a local directory:
  + `--bucket=BUCKET` is required.
  + `--source=LOCAL_SOURCE` is optional, as specified by the square
    brackets.

```shell
    {--source=CLOUD_SOURCE --source-url=SOURCE_URL | --bucket=BUCKET [--source=LOCAL_SOURCE]}
```

## Arguments that can repeat

Use three dots and no spaces (`...`) to indicate that the reader can specify multiple
values for the argument.

Avoid using an ellipsis in click-to-copy code examples.

In this example, the reader can specify multiple instances of the optional
parameter `GLOBAL_FLAG`:

```shell
    gcloud dns GROUP [GLOBAL_FLAG ...]
```

## Optional arguments in click-to-copy commands

[Optional arguments](#optional-arguments),
[mutually exclusive arguments](#set-of-two-arguments), and
[repeated arguments](#arguments-that-can-repeat)
contain characters (such as square brackets, curly braces, pipes, and ellipses) that can break
commands if the reader doesn't remove them. Avoid using these types of arguments in click-to-copy
commands. Instead, choose one of the following approaches:

* **Remove the optional arguments**. As a best practice,
  [use only the necessary arguments](#best-practices)
  to complete the task for the most common use case. If possible, remove optional arguments from
  the command; always provide a link to the command reference for the command, where readers can
  find the full list of options.

  Recommended:

  To get an aggregate list of all virtual machine (VM) instances in all zones for a project,
  use the
  [`gcloud compute instances list` command](https://cloud.google.com/sdk/gcloud/reference/compute/instances/list):

```shell
    gcloud compute instances list
```

  If you want to narrow the list of VMs to a specific zone, use the previous command with the
  `--zones` flag.
* **Use separate code blocks for each option**. In some cases, it might be ideal to
  provide more than one click-to-copy code block within the same section.

  Recommended:

  To create a bootable Compute Engine image, use the
  [`gcloud compute images import` command](https://cloud.google.com/sdk/gcloud/reference/compute/images/import):

```shell
    gcloud compute images import IMAGE_NAME \
        --source-file=SOURCE_FILE
```

  If you're importing an image with an existing license, specify the
  `--byol` flag:

```shell
    gcloud compute images import IMAGE_NAME \
        --source-file=SOURCE_FILE \
        --byol
```
* **Document optional arguments in separate tasks**. In some cases, it might be best to
  treat different options in separate sections.

  Recommended:

  To create a bootable or non-bootable Compute Engine image based on an existing virtual
  disk, use the
  [`gcloud compute images import` command](https://cloud.google.com/sdk/gcloud/reference/compute/images/import).

  ### Import a bootable virtual disk

  If your virtual disk has a bootable operating system installed on it, run the following
  command:

  ```
  gcloud compute images import IMAGE_NAME \
      --source-file=SOURCE_FILE
  ```

  ### Import a non-bootable virtual disk

  If your virtual disk doesn't have a bootable operating system installed on it, include the
  `--data-disk` flag:

```shell
    gcloud compute images import IMAGE_NAME \
        --source-file=SOURCE_FILE \
        --data-disk
```
* **Let the reader know that the command contains optional arguments**. If you must
  include special characters to indicate optional arguments, indicate that fact when you
  introduce the command.

  Recommended:

  To create a VM with a custom name and attach one or more existing stateful disks to that VM,
  use the
  [`gcloud compute instance-groups managed create-instance` command](https://cloud.google.com/sdk/gcloud/reference/compute/instance-groups/managed/create-instance)
  with one or multiple `--stateful-disk` flags. In the following example, you
  optionally specify the `auto-delete` subflag to keep or discard each disk when the
  VM is permanently deleted:

  ```shell
    gcloud compute instance-groups managed create-instance NAME \
        --instance=VM_NAME \
        --stateful-disk=device-name=DEVICE_NAME,source=DISK[,auto-delete=DELETE_RULE]
  ```

  For example, the following command creates a managed instance that's named
  `db-instance` and attaches the persistent disk `db-data-disk-1` as a
  stateful disk that is detached and preserved if its VM is deleted:

```shell
    gcloud compute instance-groups managed create-instance example-database-mig \
        --instance=db-instance \
        --stateful-disk=device-name=data-disk,source=projects/example-project/zones/us-east1-c/disks/db-data-disk-1,auto-delete=never
```

## Output from commands

You don't have to show output for every command. Add output only if it adds value—for
example, if the reader needs to copy a value from the output or if they need to verify a value
in the output.

If you are showing output, use one of the following introductory phrases to separate the command
from the output.

Recommended: The output is similar to the following:

Recommended: The output is the following:

If you want to explicitly call out something about the output, you can customize the introductory
phrase.

Recommended: The output is similar to the
following, in which the `IP` column shows the IP address for each resource:

To indicate that one or more lines of output are omitted from sample output, use three dots and
no spaces (`...`) on a separate line. Do not use the ellipsis character (`…`).
For example:

```
Reading file status
Upload done, resetting board...
...
Wakeup reason: 0

```