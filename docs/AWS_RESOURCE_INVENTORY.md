# AWS resource inventory

Status: AWS_DEPLOYMENT_BLOCKED

Execution scope: LOCAL_ONLY. No live AWS API invocation was performed in this phase. No actual account, region, resource ID, ARN, bucket, URL or successful deployment is recorded.

| Planned resource | Actual ID / state | Ownership and cleanup |
| --- | --- | --- |
| S3 KB bucket / 13 documents + 13 metadata sidecars | NOT_CREATED / NOT_VERIFIED | Project prefix and tags; retained by cleanup |
| Managed Knowledge Base | NOT_CREATED / NOT_VERIFIED | Managed embeddings; no custom vector store |
| S3 data source / ingestion job | NOT_CREATED / NOT_VERIFIED | Exact prefix, RETAIN deletion policy |
| AgentCore MCP Gateway | NOT_CREATED / NOT_VERIFIED | AWS_IAM, project execution role |
| Native KB Retrieve target | NOT_CREATED / NOT_VERIFIED | No generation enabled |
| Policy Lambda image function / target | NOT_CREATED / NOT_VERIFIED | M3 registry adapter; ECR image prerequisite |
| IAM roles / ECR repository | NOT_PROVISIONED | Supplied by account administrator |
| AgentCore Runtime | OUT_OF_SCOPE | No implementation/deployment |

Only .aws/qingju-state.example.json is committed; it contains an empty template. Future live state/results are ignored by Git. Test-only synthetic IDs are not AWS identities or resources.
