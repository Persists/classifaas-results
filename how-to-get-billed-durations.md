To obtain execution time and billing information across providers, we query the respective managed logging services for each platform.

**AWS Lambda (CloudWatch Logs Insights)**  
We extract the billed duration and related metrics from CloudWatch Logs Insights:

```sql
-- Run against the log group of the target Lambda function(s)
filter @message like "Billed Duration"
| fields @timestamp,
         @requestId,
         @duration,
         @billedDuration,
         @maxMemoryUsed,
         @memorySize,
         @initDuration
| limit 10000
```

**Azure Functions (Application Insights / KQL)**  
For Azure Functions, we read the `duration` (corresponding to `DurationMs`) from the `requests` table in Application Insights:

```kql
union
    app("<FUNCTION_APP_1>").requests,
    app("<FUNCTION_APP_2>").requests,
    app("<FUNCTION_APP_3>").requests
| project timestamp,
          cloud_RoleName,
          name,
          id,
          url,
          customDimensions.InvocationId,
          duration
| order by timestamp desc
```

In practice, we include one `app("<FUNCTION_APP_NAME>").requests` entry per function and memory configuration.

**Alibaba Cloud Function Compute (Log Service)**  
On Alibaba Cloud, we use Log Service advanced queries and filter on the `FCRequestMetrics` topic for the relevant function and memory settings:

```sql
__topic__: "FCRequestMetrics:/<FUNCTION_NAME>-<MEMORY_CONFIG_1>"
 OR __topic__: "FCRequestMetrics:/<FUNCTION_NAME>-<MEMORY_CONFIG_2>"
 OR __topic__: "FCRequestMetrics:/<FUNCTION_NAME>-<MEMORY_CONFIG_3>"
```

**Google Cloud Functions (Cloud Logging)**  
On Google Cloud, we use the Logs Explorer to filter by function name and select successful invocations. We then parse the duration from the log message:

```sql
resource.labels.function_name = "<FUNCTION_NAME>-<REGION>-<MEMORY_CONFIG>"
SEARCH("Function execution took")
SEARCH("finished with status code: 200")
```

Here, `<FUNCTION_NAME>`, `<REGION>`, and `<MEMORY_CONFIG>` are placeholders for the concrete function, deployment region, and memory configuration used in our experiments.
