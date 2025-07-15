# Don’t explain technical implementation

Whenever possible, avoid over-documenting technical implementation details. Most users are not contributors.

Before documenting technical implementation details, ask yourself what the user actually needs to know to use the product or feature effectively. The audience still *does* require a reasonable amount of technical depth.

If you find yourself reasoning that “By understanding the technical implementation, the user will be better equipped to make informed decisions about using the feature,” stop. Instead, write bulleted lists that convey recommended use cases and configurations, limitations, and caveats for the reader. In most cases, those lists convey everything you hoped a detailed implementation explanation would cover.

Technical implementation details can be interesting, but they are generally not required to use a feature. Keep only the details the reader must act on and remove under-the-hood trivia:

- **Include**: infrastructure primitives that the reader must choose between or configure (for example, *“Kubernetes capacity is provided by two node pools, `cpu` and `gpu`”*).
- **Include**: error codes, metric names, and log message formats that appear in monitoring dashboards or logs.
- **Include**: command-line examples, helper scripts, and file names that the reader will run or modify.
- **Omit**: internal-only identifiers that the reader will never see (for example, exact database table names) unless they troubleshoot with them.
- **Omit**: implementation quirks that have no observable impact on latency, limits, or configuration.

A quick test: *Will the reader need this information to make a correct decision, configure something, or diagnose an issue?* If the answer is **yes**, keep the detail. If the answer is **no**, either remove it or summarize its practical impact.

Examples:
- Details about the algorithm or data structures used to compute a result.
  *Instead, summarize the result’s accuracy, performance characteristics, and any limits the user might hit.*

- In-depth architecture of the auto-scaling load balancer that fronts an API server.  
  *Instead, simply state that the service is automatically scaled and load-balanced, noting any practical impact (for example, regional failover latency).*

- A step-by-step description of which background workers pick up which jobs.  
  *Instead, describe any scheduling delays the user might notice and how to tune job priority.*

- Names of internal database tables or columns, or diagrams of the internal schema.  
  *Instead, document the data retention policy, size limits, and export formats that affect users.*

- How encryption keys are generated, rotated, and stored behind the scenes.  
  *Instead, mention the encryption standards in use (for example, AES-256 at rest) and any configuration the user controls.*

- Which microservices and RPC calls are made to assemble a response.  
  *Instead, focus on the overall latency SLA and troubleshooting steps when requests time out.*
