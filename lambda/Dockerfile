# Lambda Container Image for Archon
# This provides an alternative deployment method using container images
# Useful when dependencies exceed Lambda layer size limits (250MB unzipped)

FROM public.ecr.aws/lambda/python:3.11

# Copy requirements file
COPY requirements-layer.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements-layer.txt

# Copy Lambda function code
COPY config/ ${LAMBDA_TASK_ROOT}/lambda/config/
COPY git/ ${LAMBDA_TASK_ROOT}/lambda/git/
COPY ingestion/ ${LAMBDA_TASK_ROOT}/lambda/ingestion/
COPY monitor/ ${LAMBDA_TASK_ROOT}/lambda/monitor/
COPY query/ ${LAMBDA_TASK_ROOT}/lambda/query/
COPY shared/ ${LAMBDA_TASK_ROOT}/lambda/shared/
COPY storage/ ${LAMBDA_TASK_ROOT}/lambda/storage/

# Set the CMD to your handler
# This will be overridden by the Lambda function configuration
CMD ["lambda.monitor.document_monitor.lambda_handler"]
