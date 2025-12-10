"""CloudWatch custom metrics utilities for Archon system."""

import boto3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os


@dataclass
class MetricData:
    """Represents a CloudWatch metric data point."""
    name: str
    value: float
    unit: str = 'None'
    dimensions: Optional[Dict[str, str]] = None
    timestamp: Optional[datetime] = None


class MetricsPublisher:
    """
    Publisher for CloudWatch custom metrics.
    
    Provides methods to publish key operational metrics:
    - Document processing metrics
    - Query processing metrics
    - Error rates
    - Performance metrics
    """
    
    def __init__(
        self,
        namespace: str = 'Archon',
        environment: Optional[str] = None,
        cloudwatch_client=None
    ):
        """
        Initialize metrics publisher.
        
        Args:
            namespace: CloudWatch namespace for metrics
            environment: Environment name (dev, staging, prod)
            cloudwatch_client: Optional boto3 CloudWatch client (for testing)
        """
        self.namespace = namespace
        self.environment = environment or os.environ.get('ENVIRONMENT', 'dev')
        self._cloudwatch = cloudwatch_client or boto3.client('cloudwatch')
        self._batch: List[MetricData] = []
    
    def put_metric(
        self,
        name: str,
        value: float,
        unit: str = 'None',
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Add a metric to the batch.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Metric unit (Count, Seconds, Bytes, etc.)
            dimensions: Optional metric dimensions
            timestamp: Optional timestamp (defaults to now)
        """
        if dimensions is None:
            dimensions = {}
        
        # Add environment dimension
        dimensions['Environment'] = self.environment
        
        metric = MetricData(
            name=name,
            value=value,
            unit=unit,
            dimensions=dimensions,
            timestamp=timestamp or datetime.now(timezone.utc)
        )
        
        self._batch.append(metric)
        
        # Auto-flush if batch is large
        if len(self._batch) >= 20:
            self.flush()
    
    def flush(self) -> None:
        """Publish all batched metrics to CloudWatch."""
        if not self._batch:
            return
        
        try:
            # Convert to CloudWatch format
            metric_data = []
            for metric in self._batch:
                data_point = {
                    'MetricName': metric.name,
                    'Value': metric.value,
                    'Unit': metric.unit,
                    'Timestamp': metric.timestamp
                }
                
                if metric.dimensions:
                    data_point['Dimensions'] = [
                        {'Name': k, 'Value': v}
                        for k, v in metric.dimensions.items()
                    ]
                
                metric_data.append(data_point)
            
            # Publish to CloudWatch (max 20 metrics per call)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self._cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            # Clear batch
            self._batch = []
            
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Failed to publish metrics: {str(e)}")
            self._batch = []
    
    # Document monitoring metrics
    
    def record_repositories_checked(self, count: int) -> None:
        """Record number of repositories checked."""
        self.put_metric(
            name='RepositoriesChecked',
            value=count,
            unit='Count'
        )
    
    def record_documents_processed(self, count: int, repo: Optional[str] = None) -> None:
        """Record number of documents processed."""
        dimensions = {}
        if repo:
            dimensions['Repository'] = repo
        
        self.put_metric(
            name='DocumentsProcessed',
            value=count,
            unit='Count',
            dimensions=dimensions
        )
    
    def record_documents_updated(self, count: int) -> None:
        """Record number of documents updated in vector store."""
        self.put_metric(
            name='DocumentsUpdated',
            value=count,
            unit='Count'
        )
    
    def record_monitoring_errors(self, count: int, error_type: Optional[str] = None) -> None:
        """Record monitoring errors."""
        dimensions = {}
        if error_type:
            dimensions['ErrorType'] = error_type
        
        self.put_metric(
            name='MonitoringErrors',
            value=count,
            unit='Count',
            dimensions=dimensions
        )
    
    def record_monitoring_duration(self, duration_seconds: float) -> None:
        """Record monitoring execution duration."""
        self.put_metric(
            name='MonitoringDuration',
            value=duration_seconds,
            unit='Seconds'
        )
    
    # Embedding generation metrics
    
    def record_embeddings_generated(self, count: int) -> None:
        """Record number of embeddings generated."""
        self.put_metric(
            name='EmbeddingsGenerated',
            value=count,
            unit='Count'
        )
    
    def record_embedding_generation_time(self, duration_seconds: float) -> None:
        """Record embedding generation time."""
        self.put_metric(
            name='EmbeddingGenerationTime',
            value=duration_seconds,
            unit='Seconds'
        )
    
    def record_embedding_retries(self, count: int) -> None:
        """Record number of embedding generation retries."""
        self.put_metric(
            name='EmbeddingRetries',
            value=count,
            unit='Count'
        )
    
    # Query processing metrics
    
    def record_queries_processed(self, count: int = 1) -> None:
        """Record number of queries processed."""
        self.put_metric(
            name='QueriesProcessed',
            value=count,
            unit='Count'
        )
    
    def record_query_latency(self, duration_seconds: float) -> None:
        """Record query processing latency."""
        self.put_metric(
            name='QueryLatency',
            value=duration_seconds,
            unit='Seconds'
        )
    
    def record_query_errors(self, count: int = 1, error_type: Optional[str] = None) -> None:
        """Record query processing errors."""
        dimensions = {}
        if error_type:
            dimensions['ErrorType'] = error_type
        
        self.put_metric(
            name='QueryErrors',
            value=count,
            unit='Count',
            dimensions=dimensions
        )
    
    def record_documents_retrieved(self, count: int) -> None:
        """Record number of documents retrieved for a query."""
        self.put_metric(
            name='DocumentsRetrieved',
            value=count,
            unit='Count'
        )
    
    def record_llm_invocation_time(self, duration_seconds: float) -> None:
        """Record LLM invocation time."""
        self.put_metric(
            name='LLMInvocationTime',
            value=duration_seconds,
            unit='Seconds'
        )
    
    # Vector store metrics
    
    def record_vector_store_operations(self, operation: str, count: int = 1) -> None:
        """Record vector store operations."""
        self.put_metric(
            name='VectorStoreOperations',
            value=count,
            unit='Count',
            dimensions={'Operation': operation}
        )
    
    def record_vector_store_latency(self, operation: str, duration_seconds: float) -> None:
        """Record vector store operation latency."""
        self.put_metric(
            name='VectorStoreLatency',
            value=duration_seconds,
            unit='Seconds',
            dimensions={'Operation': operation}
        )
    
    # GitHub API metrics
    
    def record_github_api_calls(self, count: int = 1) -> None:
        """Record GitHub API calls."""
        self.put_metric(
            name='GitHubAPICalls',
            value=count,
            unit='Count'
        )
    
    def record_github_rate_limit_remaining(self, remaining: int) -> None:
        """Record GitHub API rate limit remaining."""
        self.put_metric(
            name='GitHubRateLimitRemaining',
            value=remaining,
            unit='Count'
        )
    
    # DynamoDB metrics
    
    def record_dynamodb_operations(self, operation: str, count: int = 1) -> None:
        """Record DynamoDB operations."""
        self.put_metric(
            name='DynamoDBOperations',
            value=count,
            unit='Count',
            dimensions={'Operation': operation}
        )
    
    def record_dynamodb_throttles(self, count: int = 1) -> None:
        """Record DynamoDB throttling events."""
        self.put_metric(
            name='DynamoDBThrottles',
            value=count,
            unit='Count'
        )


def get_metrics_publisher() -> MetricsPublisher:
    """
    Get or create a metrics publisher.
    
    Returns:
        MetricsPublisher instance
    """
    return MetricsPublisher()
