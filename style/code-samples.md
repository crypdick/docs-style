# Code samples  

This page explains how to format code samples.

## Basic guidelines

Follow these guidelines when formatting code samples:

* **Wrap lines** at 80 characters.

  If you expect readers to have a relatively narrow browser window or to print out your
  document, consider wrapping at a smaller number of characters for readability.
* **Mark code blocks as preformatted text**. In Markdown, indent every line of the code block by four spaces.
* **Indicate omitted code by using a comment** in the syntax of the language of your code
  sample. Don't use three dots or the ellipsis character (`…`). If a code
  block contains an omission, don't format the block as click-to-copy.

Recommended:

```
apiVersion: serving.knative.dev/v1
kind: Service
# Several lines of code are omitted here.
spec:
  template:
    spec:
      containers:
      - image: IMAGE_URL
        ports:
        - name: h2c
          containerPort: 8080
```

## Introductory statements

In most cases, precede a code sample with an introductory sentence or
paragraph. The introduction can end with a colon or a period; usually a colon if it
immediately precedes the sample, usually a period if there's more material (such
as a note paragraph) between the introduction and the sample, or if the
introduction paragraph ends in a sentence that isn't directly related to the
sample.

Recommended (ending with a period): The
following code sample shows how to use the `get` method. For
information about other methods, see [link]. [sample]

Also recommended: The following code
sample shows how to use the `get` method: [sample] For information about
other methods, see [link].

Not recommended (ending with a colon): The
following code sample shows how to use the `get` method. For
information about other methods, see [link]: [sample]
