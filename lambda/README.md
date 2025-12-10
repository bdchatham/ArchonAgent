# Archon Lambda Functions

This directory contains the Lambda function code for Archon.

## Structure

```
lambda/
├── config/              # Configuration management
│   ├── __init__.py
│   └── config_manager.py
├── git/                 # GitHub API client
│   ├── __init__.py
│   └── github_client.py
├── ingestion/           # Document ingestion pipeline
│   ├── __init__.py
│   └── ingestion_pipeline.py
├── monitor/             # Document monitor Lambda handler
│   ├── __init__.py
│   └── document_monitor.py
├── query/               # Query handler Lambda
│   ├── __init__.py
│   ├── query_handler.py
│   └── rag_chain.py
├── shared/              # Shared data models
│   ├── __init__.py
│   └── models.py
├── storage/             # Storage managers
│   ├── __init__.py
│   ├── change_tracker.py
│   └── vector_store_manager.py
├── requirements-layer.txt  # Dependencies for Lambda layer
├── Dockerfile           # Container image definition
└── .dockerignore       # Docker build exclusions
```

## Lambda Functions

### Document Monitor (`monitor/document_monitor.py`)

**Handler:** `lambda.monitor.document_monitor.lambda_handler`

**Purpose:** Monitors configured GitHub repositories for .kiro/ documentation changes

**Trigger:** EventBridge scheduled rule (cron)

**Environment Variables:**
- `DYNAMODB_TABLE` - Change tracker table name
- `OPENSEARCH_ENDPOINT` - OpenSearch collection endpoint
- `OPENSEARCH_INDEX` - Index name for documents
- `EMBEDDING_MODEL` - Bedrock embedding model ID
- `VECTOR_DIMENSIONS` - Embedding dimensions (1536)
- `CONFIG_PATH` - Path to configuration file
- `ENVIRONMENT` - Deployment environment

**IAM Permissions Required:**
- DynamoDB: Read/Write to change tracker table
- Bedrock: InvokeModel for embeddings
- OpenSearch: APIAccessAll for vector storage

### Query Handler (`query/query_handler.py`)

**Handler:** `lambda.query.query_handler.lambda_handler`

**Purpose:** Processes user queries using RAG with Bedrock and OpenSearch

**Trigger:** API Gateway (POST /v1/chat/completions)

**Environment Variables:**
- `OPENSEARCH_ENDPOINT` - OpenSearch collection endpoint
- `OPENSEARCH_INDEX` - Index name for documents
- `EMBEDDING_MODEL` - Bedrock embedding model ID
- `LLM_MODEL` - Bedrock LLM model ID
- `LLM_TEMPERATURE` - Temperature for generation
- `MAX_TOKENS` - Maximum tokens in response
- `RETRIEVAL_K` - Number of documents to retrieve
- `VECTOR_DIMENSIONS` - Embedding dimensions (1536)
- `ENVIRONMENT` - Deployment environment

**IAM Permissions Required:**
- Bedrock: InvokeModel for embeddings and LLM
- OpenSearch: APIAccessAll for vector search

## Dependencies

### Lambda Layer Dependencies

Defined in `requirements-layer.txt`:
- `pyyaml` - Configuration parsing
- `langchain` - RAG orchestration
- `langchain-aws` - AWS Bedrock integration
- `langchain-community` - Community integrations
- `opensearch-py` - Vector database client
- `PyGithub` - GitHub API client
- `requests` - HTTP client
- `urllib3` - HTTP library

### Runtime-Provided Dependencies

These are provided by the Lambda runtime and not included in the layer:
- `boto3` - AWS SDK for Python
- `botocore` - Low-level AWS SDK

## Deployment

### Using Lambda Layers (Recommended)

```bash
# 1. Build the layer
../scripts/build-lambda-layer.sh

# 2. Deploy with CDK
npm run cdk deploy ArchonKnowledgeBase
npm run cdk deploy ArchonAgent
```

### Using Container Images

```bash
# 1. Build container image
cd lambda
docker build -t archon-lambda:latest .

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag archon-lambda:latest <account>.dkr.ecr.us-east-1.amazonaws.com/archon-lambda:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/archon-lambda:latest

# 3. Update CDK to use container image
# (Modify stack to use DockerImageFunction)
```

## Local Development

### Setting Up Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-layer.txt
pip install -r ../requirements.txt  # Includes testing dependencies
```

### Running Tests

```bash
# From project root
pytest tests/

# Run specific test module
pytest tests/unit/monitor/

# Run with coverage
pytest --cov=lambda tests/
```

### Testing Lambda Handlers Locally

```python
# Example: Test monitor Lambda
from lambda.monitor.document_monitor import lambda_handler

event = {}
context = {}
result = lambda_handler(event, context)
print(result)
```

## Best Practices

1. **Imports**: Import only what you need to reduce cold start time
2. **Initialization**: Initialize clients outside handler for reuse across invocations
3. **Error Handling**: Use try/except and log errors appropriately
4. **Timeouts**: Be mindful of Lambda timeout (configured in CDK)
5. **Memory**: Monitor memory usage and adjust in CDK if needed
6. **Environment Variables**: Use environment variables for configuration
7. **Secrets**: Never hardcode credentials; use IAM roles and environment variables

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`:
1. Verify layer is attached to function
2. Check layer structure: `lambda-layer/python/<package>`
3. Rebuild layer: `../scripts/build-lambda-layer.sh`

### Timeout Errors

If Lambda times out:
1. Increase timeout in CDK stack
2. Optimize code (reduce API calls, batch operations)
3. Check CloudWatch logs for bottlenecks

### Memory Errors

If Lambda runs out of memory:
1. Increase memory in CDK stack
2. Process data in smaller chunks
3. Monitor memory usage in CloudWatch

## References

- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
