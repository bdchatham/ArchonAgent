"""
Property-based tests for query input validation.

Feature: archon-rag-system, Property 13: Query input validation
Validates: Requirements 5.2
"""

from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, assume

from query.query_handler import QueryHandler, QueryValidationError
from query.rag_chain import ArchonRAGChain


# Strategy for generating valid query strings
@st.composite
def valid_query_string(draw):
    """Generate valid query strings (non-empty, reasonable length)."""
    # Generate queries between 1 and 1000 characters
    query = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Z'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=1,
        max_size=1000
    ))
    # Ensure it's not just whitespace
    assume(query.strip())
    return query


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


# Feature: archon-rag-system, Property 13: Query input validation
@given(valid_query_string())
@settings(max_examples=100)
def test_valid_query_acceptance(query):
    """
    For any valid query string (non-empty, reasonable length), 
    the query validator should accept it without raising an error.
    
    Validates: Requirements 5.2
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Property: Valid queries should pass validation
    try:
        result = handler.validate_query(query)
        assert result is True, "Valid query should return True"
    except QueryValidationError as e:
        # If validation fails, the query must be invalid
        # Check if it's actually invalid
        stripped = query.strip()
        if stripped and 1 <= len(stripped) <= 1000:
            raise AssertionError(f"Valid query rejected: {query!r}, error: {e}")


@given(invalid_query_string())
@settings(max_examples=100)
def test_invalid_query_rejection(query):
    """
    For any invalid query string (empty, whitespace-only, or too long),
    the query validator should reject it by raising QueryValidationError.
    
    Validates: Requirements 5.2
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Property: Invalid queries should raise QueryValidationError
    try:
        handler.validate_query(query)
        
        # If no error was raised, check if query is actually valid
        stripped = query.strip()
        if not stripped or len(stripped) > 1000:
            raise AssertionError(f"Invalid query accepted: {query!r}")
            
    except QueryValidationError:
        # Expected behavior for invalid queries
        pass


@given(st.text(min_size=0, max_size=2000))
@settings(max_examples=100)
def test_query_validation_correctness(query):
    """
    For any string input, the validator should correctly identify 
    valid queries (non-empty after stripping, 1-1000 chars) and 
    reject invalid ones.
    
    Validates: Requirements 5.2
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Determine if query should be valid
    stripped = query.strip()
    should_be_valid = bool(stripped) and 1 <= len(stripped) <= 1000
    
    # Test validation
    try:
        result = handler.validate_query(query)
        
        # If validation passed, query must be valid
        assert should_be_valid, \
            f"Invalid query accepted: {query!r} (length: {len(stripped)})"
        assert result is True, "validate_query should return True for valid queries"
        
    except QueryValidationError as e:
        # If validation failed, query must be invalid
        assert not should_be_valid, \
            f"Valid query rejected: {query!r} (length: {len(stripped)}), error: {e}"


@given(st.one_of(
    st.none(),
    st.integers(),
    st.floats(),
    st.lists(st.text()),
    st.dictionaries(st.text(), st.text())
))
@settings(max_examples=100)
def test_non_string_query_rejection(query):
    """
    For any non-string input, the validator should reject it 
    by raising QueryValidationError.
    
    Validates: Requirements 5.2
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Property: Non-string inputs should be rejected
    try:
        handler.validate_query(query)
        raise AssertionError(f"Non-string query accepted: {query!r} (type: {type(query)})")
    except QueryValidationError:
        # Expected behavior
        pass
    except (TypeError, AttributeError):
        # Also acceptable if it fails with type error
        pass


@given(st.lists(valid_query_string(), min_size=1, max_size=20))
@settings(max_examples=100)
def test_validation_consistency(queries):
    """
    For any list of valid query strings, validation should 
    consistently accept all of them.
    
    Validates: Requirements 5.2
    """
    # Create mock RAG chain
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Property: All valid queries should pass validation consistently
    for query in queries:
        try:
            result = handler.validate_query(query)
            assert result is True, f"Valid query rejected: {query!r}"
        except QueryValidationError as e:
            # Check if it's actually a valid query
            stripped = query.strip()
            if stripped and 1 <= len(stripped) <= 1000:
                raise AssertionError(
                    f"Valid query rejected inconsistently: {query!r}, error: {e}"
                )
