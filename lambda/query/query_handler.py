"""Query handler Lambda function for Archon RAG system."""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from .rag_chain import ArchonRAGChain, RAGChainError


@dataclass
class SourceReference:
    """Reference to a source document."""
    repo: str
    file_path: str
    relevance_score: float
    chunk_text: Optional[str] = None


@dataclass
class QueryResponse:
    """Response to a query request."""
    answer: str
    sources: List[SourceReference]
    timestamp: str
    query: str


class QueryValidationError(Exception):
    """Raised when query validation fails."""
    pass


class QueryHandler:
    """
    Handler for processing user queries using RAG pipeline.
    
    Orchestrates:
    - Query validation
    - RAG chain invocation
    - Response formatting with source references
    - Error handling
    """
    
    # Query validation constraints
    MIN_QUERY_LENGTH = 1
    MAX_QUERY_LENGTH = 1000
    
    def __init__(self, rag_chain: ArchonRAGChain, max_results: int = 5):
        """
        Initialize the query handler.
        
        Args:
            rag_chain: Configured ArchonRAGChain instance
            max_results: Maximum number of source documents to return
        """
        self.rag_chain = rag_chain
        self.max_results = max_results
    
    def validate_query(self, query: str) -> bool:
        """
        Validate query input.
        
        Args:
            query: Query string to validate
            
        Returns:
            True if valid
            
        Raises:
            QueryValidationError: If query is invalid
        """
        # Check if query is a string
        if not isinstance(query, str):
            raise QueryValidationError("Query must be a string")
        
        # Check if query is empty or only whitespace
        if not query or not query.strip():
            raise QueryValidationError("Query cannot be empty")
        
        # Check query length
        query_length = len(query.strip())
        if query_length < self.MIN_QUERY_LENGTH:
            raise QueryValidationError(
                f"Query is too short (minimum {self.MIN_QUERY_LENGTH} characters)"
            )
        
        if query_length > self.MAX_QUERY_LENGTH:
            raise QueryValidationError(
                f"Query is too long (maximum {self.MAX_QUERY_LENGTH} characters)"
            )
        
        return True
    
    def handle_query(self, query: str, max_results: Optional[int] = None) -> QueryResponse:
        """
        Process a user query through the RAG pipeline.
        
        Args:
            query: User query string
            max_results: Optional override for maximum results
            
        Returns:
            QueryResponse with answer and sources
            
        Raises:
            QueryValidationError: If query is invalid
            RAGChainError: If RAG processing fails
        """
        # Validate query
        self.validate_query(query)
        
        # Use provided max_results or default
        k = max_results if max_results is not None else self.max_results
        
        # Invoke RAG chain
        try:
            result = self.rag_chain.invoke(query)
        except RAGChainError:
            raise
        except Exception as e:
            raise RAGChainError(f"Failed to process query: {str(e)}") from e
        
        # Extract answer and sources
        answer = result.get("result", "")
        source_documents = result.get("source_documents", [])
        
        # Format response
        response = self.format_response(
            llm_response=answer,
            sources=source_documents[:k],
            query=query
        )
        
        return response
    
    def format_response(
        self,
        llm_response: str,
        sources: List[Dict[str, Any]],
        query: str
    ) -> QueryResponse:
        """
        Format the response with source references.
        
        Args:
            llm_response: Generated answer from LLM
            sources: List of source documents with metadata
            query: Original query string
            
        Returns:
            Formatted QueryResponse object
        """
        # Convert source documents to SourceReference objects
        source_refs = []
        for source in sources:
            metadata = source.get("metadata", {})
            
            # Extract required fields
            repo = metadata.get("repo_url", "")
            file_path = metadata.get("file_path", "")
            score = source.get("score", 0.0)
            chunk_text = source.get("text", None)
            
            source_refs.append(SourceReference(
                repo=repo,
                file_path=file_path,
                relevance_score=score,
                chunk_text=chunk_text
            ))
        
        # Create response with timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        return QueryResponse(
            answer=llm_response,
            sources=source_refs,
            timestamp=timestamp,
            query=query
        )


def create_error_response(error_code: str, message: str, details: str = "") -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_code: Error code identifier
        message: Error message
        details: Additional error details
        
    Returns:
        Error response dictionary
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    response = {
        "error": {
            "code": error_code,
            "message": message
        },
        "timestamp": timestamp
    }
    
    if details:
        response["error"]["details"] = details
    
    return response


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for query processing.
    
    Args:
        event: API Gateway event with query request
        context: Lambda context
        
    Returns:
        API Gateway response with query result or error
    """
    try:
        # Parse request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})
        
        query = body.get("query", "")
        max_results = body.get("max_results", None)
        
        # Initialize components (in production, these would be initialized once)
        # For now, we'll need environment variables for configuration
        opensearch_endpoint = os.environ.get("OPENSEARCH_ENDPOINT")
        index_name = os.environ.get("INDEX_NAME", "archon-docs")
        embedding_model = os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v1")
        llm_model = os.environ.get("LLM_MODEL", "anthropic.claude-3-haiku-20240307")
        retrieval_k = int(os.environ.get("RETRIEVAL_K", "5"))
        
        if not opensearch_endpoint:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(create_error_response(
                    "CONFIGURATION_ERROR",
                    "OpenSearch endpoint not configured",
                    "OPENSEARCH_ENDPOINT environment variable is required"
                ))
            }
        
        # Import here to avoid circular dependencies
        from storage.vector_store_manager import VectorStoreManager
        
        # Initialize vector store manager
        vector_store = VectorStoreManager(
            opensearch_endpoint=opensearch_endpoint,
            index_name=index_name,
            embedding_model=embedding_model
        )
        
        # Initialize RAG chain
        rag_chain = ArchonRAGChain(
            vector_store_manager=vector_store,
            llm_model=llm_model,
            embedding_model=embedding_model,
            retrieval_k=retrieval_k
        )
        
        # Initialize query handler
        handler = QueryHandler(rag_chain=rag_chain, max_results=retrieval_k)
        
        # Process query
        response = handler.handle_query(query, max_results)
        
        # Convert response to dictionary
        response_dict = asdict(response)
        
        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response_dict)
        }
        
    except QueryValidationError as e:
        # Invalid query error
        error_response = create_error_response(
            "INVALID_QUERY",
            str(e),
            "Please provide a valid query string"
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(error_response)
        }
        
    except RAGChainError as e:
        # RAG processing error
        error_response = create_error_response(
            "PROCESSING_ERROR",
            "Failed to process query",
            str(e)
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(error_response)
        }
        
    except json.JSONDecodeError as e:
        # Invalid JSON in request
        error_response = create_error_response(
            "INVALID_REQUEST",
            "Invalid JSON in request body",
            str(e)
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(error_response)
        }
        
    except Exception as e:
        # Unexpected error
        error_response = create_error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            str(e)
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(error_response)
        }
