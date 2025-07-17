# Sentence structure  

If you want to tell the reader to do something, try to mention the circumstance, conditions, or
goal before you provide the instruction. Mentioning the circumstance first lets the reader skip
the instruction if it doesn't apply.

| Recommended | Not recommended |
| --- | --- |
| For more information, see [link to other document]. | See [link to other document] for more information. |
| To delete the entire document, click **Delete**. | Click **Delete** if you want to delete the entire document. |
| If your app is located in one of the following regions, using custom domains might add noticeable latency to responses: | Using custom domains might add noticeable latency to responses if your app is located in one of the following regions: |

This rule can result in awkward sentences. For example:
```
# Before
Don't install Ray in the environment you plan to use to build documentation. The requirements for the docs build system aren't generally compatible with the requirements you need to run Ray itself.
# After
In the environment you plan to use to build documentation, don't install Ray. The requirements for the docs build system aren't generally compatible with the requirements you need to run Ray itself.
```

In this case, instead of blindly applying the rule, rewrite the sentence to be more natural:

```
# Recommended
When building documentation, use a separate environment that doesn't have Ray installed. The documentation build system's dependencies typically conflict with those required to run Ray.
```