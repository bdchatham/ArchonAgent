"""AWS X-Ray tracing utilities for Archon system."""

from functools import wraps
from typing import Any, Callable, Dict, Optional
import os

# Try to import X-Ray SDK, but make it optional
try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all
    XRAY_AVAILABLE = True
except ImportError:
    XRAY_AVAILABLE = False
    xray_recorder = None


def initialize_xray() -> None:
    """
    Initialize X-Ray tracing.
    
    Patches common libraries for automatic tracing:
    - boto3/botocore (AWS SDK)
    - requests (HTTP client)
    """
    if not XRAY_AVAILABLE:
        print("X-Ray SDK not available, tracing disabled")
        return
    
    # Check if X-Ray is enabled
    if os.environ.get('XRAY_ENABLED', 'true').lower() != 'true':
        print("X-Ray tracing disabled by configuration")
        return
    
    try:
        # Patch common libraries
        patch_all()
        print("X-Ray tracing initialized")
    except Exception as e:
        print(f"Failed to initialize X-Ray: {str(e)}")


def trace_function(name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator to trace a function with X-Ray.
    
    Args:
        name: Optional subsegment name (defaults to function name)
        metadata: Optional metadata to attach to the subsegment
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not XRAY_AVAILABLE or not xray_recorder:
                # X-Ray not available, just execute function
                return func(*args, **kwargs)
            
            subsegment_name = name or func.__name__
            
            try:
                # Create subsegment
                with xray_recorder.capture(subsegment_name) as subsegment:
                    # Add metadata
                    if metadata:
                        for key, value in metadata.items():
                            subsegment.put_metadata(key, value)
                    
                    # Add function info
                    subsegment.put_metadata('function', func.__name__)
                    subsegment.put_metadata('module', func.__module__)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    return result
                    
            except Exception as e:
                # Record exception in X-Ray
                if xray_recorder:
                    try:
                        xray_recorder.current_subsegment().add_exception(e)
                    except:
                        pass
                raise
        
        return wrapper
    return decorator


def add_annotation(key: str, value: Any) -> None:
    """
    Add an annotation to the current X-Ray segment.
    
    Annotations are indexed and can be used for filtering traces.
    
    Args:
        key: Annotation key
        value: Annotation value (must be string, number, or boolean)
    """
    if not XRAY_AVAILABLE or not xray_recorder:
        return
    
    try:
        subsegment = xray_recorder.current_subsegment()
        if subsegment:
            subsegment.put_annotation(key, value)
    except Exception:
        # Silently fail if no active segment
        pass


def add_metadata(key: str, value: Any, namespace: str = 'default') -> None:
    """
    Add metadata to the current X-Ray segment.
    
    Metadata is not indexed but can contain any JSON-serializable data.
    
    Args:
        key: Metadata key
        value: Metadata value
        namespace: Metadata namespace
    """
    if not XRAY_AVAILABLE or not xray_recorder:
        return
    
    try:
        subsegment = xray_recorder.current_subsegment()
        if subsegment:
            subsegment.put_metadata(key, value, namespace)
    except Exception:
        # Silently fail if no active segment
        pass


class TracedOperation:
    """
    Context manager for tracing operations with X-Ray.
    
    Usage:
        with TracedOperation('operation_name') as op:
            op.add_annotation('key', 'value')
            # do work
    """
    
    def __init__(self, name: str):
        """
        Initialize traced operation.
        
        Args:
            name: Operation name
        """
        self.name = name
        self.subsegment = None
    
    def __enter__(self):
        """Start tracing."""
        if XRAY_AVAILABLE and xray_recorder:
            try:
                self.subsegment = xray_recorder.begin_subsegment(self.name)
            except Exception:
                pass
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracing."""
        if self.subsegment and XRAY_AVAILABLE and xray_recorder:
            try:
                if exc_type is not None:
                    # Record exception
                    self.subsegment.add_exception(exc_val)
                xray_recorder.end_subsegment()
            except Exception:
                pass
        return False
    
    def add_annotation(self, key: str, value: Any) -> None:
        """Add annotation to this operation."""
        if self.subsegment:
            try:
                self.subsegment.put_annotation(key, value)
            except Exception:
                pass
    
    def add_metadata(self, key: str, value: Any, namespace: str = 'default') -> None:
        """Add metadata to this operation."""
        if self.subsegment:
            try:
                self.subsegment.put_metadata(key, value, namespace)
            except Exception:
                pass


# Convenience functions for common operations

@trace_function(name='github_api_call')
def trace_github_call(func: Callable) -> Callable:
    """Decorator for tracing GitHub API calls."""
    return func


@trace_function(name='bedrock_invocation')
def trace_bedrock_call(func: Callable) -> Callable:
    """Decorator for tracing Bedrock API calls."""
    return func


@trace_function(name='opensearch_operation')
def trace_opensearch_call(func: Callable) -> Callable:
    """Decorator for tracing OpenSearch operations."""
    return func


@trace_function(name='dynamodb_operation')
def trace_dynamodb_call(func: Callable) -> Callable:
    """Decorator for tracing DynamoDB operations."""
    return func
