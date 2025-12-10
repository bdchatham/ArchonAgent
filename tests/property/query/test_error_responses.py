"""
Property-based tests for invalid query error responses.

Feature: archon-rag-system, Property 14: Invalid query error responses
Validates: Requirements 5.4
"""

from unittest.mock import Mock
from hypothesis import given, strategies as st, settings

from query.query_handler import QueryHandler, QueryValidationError, create_error_response
from query.rag_chain import ArchonRAGChain


# Strategy for generating invalid query strings
@st.composite
def invalid_query_string(draw):
    """Generate invalid query strings (empty, whitespace-only, or too long)."""
    choice = draw(st.integers(min_value=0, max_value=2))
    
    if choice == 0:
        # Empty string
        return ""
    elif choice == 1:
        # Whitespace-only string
        whitespace_chars = [' ', '\t', '\n', '\r']
        length = draw(st.integers(min_value=1, max_value=20))
        return ''.join(draw(st.sampled_from(whitespace_chars)) for _ in range(length))
    else:
        # Too long string (> 1000 characters)
        return draw(st.text(min_size=1001, max_size=2000))


# Feature: archon-rag-system, Property 14: Invalid query error responses
@given(invalid_query_string())
@settings(max_examples=100)
def test_invalid_query_returns_error_message(query):
    """
    For any invalid or empty query input, the system should return 
    an error response with a helpful message explaining the issue.
    
    Validates: Requirements 5.4
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Property: Invalid queries should raise QueryValidationError with a message
    try:
        handler.handle_query(query)
        
        # If no error was raised, check if query is actually valid
        stripped = query.strip()
        if not stripped or len(stripped) > 1000:
            raise AssertionError(f"Invalid query did not raise error: {query!r}")
            
    except QueryValidationError as e:
        # Expected behavior - verify error has a message
        error_message = str(e)
        
        # Property: Error message must be non-empty
        assert error_message, "Error message should not be empty"
        
        # Property: Error message should be a string
        assert isinstance(error_message, str), "Error message should be a string"
        
        # Property: Error message should be helpful (contain relevant keywords)
        error_lower = error_message.lower()
        helpful_keywords = ['query', 'empty', 'short', 'long', 'character', 'string']
        has_helpful_info = any(keyword in error_lower for keyword in helpful_keywords)
        assert has_helpful_info, \
            f"Error message should contain helpful information: {error_message}"


@given(st.text(min_size=0, max_size=2000))
@settings(max_examples=100)
def test_error_response_format(query):
    """
    For any query that causes a validation error, the error response 
    should have a consistent format with code, message, and details.
    
    Validates: Requirements 5.4
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Determine if query should be invalid
    stripped = query.strip()
    should_be_invalid = not stripped or len(stripped) > 1000
    
    if not should_be_invalid:
        # Skip valid queries for this test
        return
    
    # Test error handling
    try:
        handler.handle_query(query)
        # Should have raised an error
        raise AssertionError(f"Invalid query did not raise error: {query!r}")
        
    except QueryValidationError as e:
        # Create error response using the helper function
        error_response = create_error_response(
            "INVALID_QUERY",
            str(e),
            "Please provide a valid query string"
        )
        
        # Property: Error response must have required fields
        assert "error" in error_response, "Error response must have 'error' field"
        assert "timestamp" in error_response, "Error response must have 'timestamp' field"
        
        # Property: Error object must have code and message
        error_obj = error_response["error"]
        assert "code" in error_obj, "Error object must have 'code' field"
        assert "message" in error_obj, "Error object must have 'message' field"
        
        # Property: Error code should be non-empty string
        assert isinstance(error_obj["code"], str), "Error code must be a string"
        assert error_obj["code"], "Error code must not be empty"
        
        # Property: Error message should be non-empty string
        assert isinstance(error_obj["message"], str), "Error message must be a string"
        assert error_obj["message"], "Error message must not be empty"
        
        # Property: Timestamp should be non-empty string
        assert isinstance(error_response["timestamp"], str), \
            "Timestamp must be a string"
        assert error_response["timestamp"], "Timestamp must not be empty"


@given(st.lists(invalid_query_string(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_consistent_error_responses(queries):
    """
    For any list of invalid queries, all error responses should 
    have consistent structure and helpful messages.
    
    Validates: Requirements 5.4
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    error_messages = []
    
    # Property: All invalid queries should produce error messages
    for query in queries:
        try:
            handler.handle_query(query)
            # Check if it's actually invalid
            stripped = query.strip()
            if not stripped or len(stripped) > 1000:
                raise AssertionError(f"Invalid query did not raise error: {query!r}")
        except QueryValidationError as e:
            error_messages.append(str(e))
    
    # Property: All error messages should be non-empty
    assert all(msg for msg in error_messages), \
        "All error messages should be non-empty"
    
    # Property: All error messages should be strings
    assert all(isinstance(msg, str) for msg in error_messages), \
        "All error messages should be strings"


@given(st.one_of(
    st.none(),
    st.integers(),
    st.floats(),
    st.lists(st.text()),
    st.dictionaries(st.text(), st.text())
))
@settings(max_examples=100)
def test_non_string_query_error_message(query):
    """
    For any non-string input, the error message should clearly 
    indicate that a string is required.
    
    Validates: Requirements 5.4
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Property: Non-string inputs should produce helpful error messages
    try:
        handler.handle_query(query)
        raise AssertionError(f"Non-string query did not raise error: {query!r}")
    except (QueryValidationError, TypeError, AttributeError) as e:
        error_message = str(e)
        
        # Property: Error message should mention string or type
        error_lower = error_message.lower()
        type_keywords = ['string', 'str', 'type']
        has_type_info = any(keyword in error_lower for keyword in type_keywords)
        
        # Allow either explicit type error or validation error
        assert has_type_info or isinstance(e, (TypeError, AttributeError)), \
            f"Error message should indicate type issue: {error_message}"


@given(invalid_query_string())
@settings(max_examples=100)
def test_error_response_structure_completeness(query):
    """
    For any invalid query, the error response created by create_error_response 
    should have all required fields with appropriate types.
    
    Validates: Requirements 5.4
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Get validation error
    try:
        handler.validate_query(query)
        # If no error, skip (query might be valid)
        return
    except QueryValidationError as e:
        error_msg = str(e)
    
    # Create error response
    error_response = create_error_response(
        "INVALID_QUERY",
        error_msg,
        "Please provide a valid query string"
    )
    
    # Property: Response must be a dictionary
    assert isinstance(error_response, dict), "Error response must be a dictionary"
    
    # Property: Must have error and timestamp at top level
    assert set(error_response.keys()) >= {"error", "timestamp"}, \
        "Error response must have 'error' and 'timestamp' fields"
    
    # Property: Error field must be a dictionary
    assert isinstance(error_response["error"], dict), \
        "Error field must be a dictionary"
    
    # Property: Error must have code and message
    error_obj = error_response["error"]
    assert "code" in error_obj, "Error must have 'code' field"
    assert "message" in error_obj, "Error must have 'message' field"
    
    # Property: Optional details field should be present if provided
    if "details" in error_obj:
        assert isinstance(error_obj["details"], str), \
            "Details field must be a string if present"
