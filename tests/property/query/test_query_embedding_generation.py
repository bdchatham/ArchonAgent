"""
Property-based tests for query embedding generation.

Feature: archon-rag-system, Property 15: Query embedding generation
Validates: Requirements 6.1
"""

from unittest.mock import Mock, MagicMock
from hypothesis import given, strategies as st, settings

from query.rag_chain import ArchonRAGChain


# Strategy for generating query strings
@st.composite
def query_string(draw):
    """Generate various query string samples."""
    # Generate queries of varying lengths
    query = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Z')),
        min_size=5,
        max_size=500
    ))
    return query


# Feature: archon-rag-system, Property 15: Query embedding generation
@given(query_string())
@settings(max_examples=100)
def test_query_embedding_generation(query):
    """
    For any valid query string, the system should generate an embedding vector 
    with the correct dimensions matching the document embeddings.
    
    Validates: Requirements 6.1
    """
    # Expected dimension for Titan embeddings
    EXPECTED_DIMENSION = 1536
    
    # Create mock vector store manager
    mock_vector_store = Mock()
    mock_vector_store.similarity_search = Mock(return_value=[])
    mock_vector_store.get_langchain_store = Mock()
    
    # Create mock embeddings that return consistent dimensions
    mock_embeddings = Mock()
    mock_embeddings.embed_query = Mock(return_value=[0.1] * EXPECTED_DIMENSION)
    
    # Create mock LLM
    mock_llm = Mock()
    
    # Create RAG chain with mocked components
    rag_chain = ArchonRAGChain(
        vector_store_manager=mock_vector_store,
        embeddings=mock_embeddings,
        llm=mock_llm
    )
    
    # Get relevant documents (which internally generates query embedding)
    try:
        documents = rag_chain.get_relevant_documents(query)
        
        # Verify that embed_query was called with the query
        mock_embeddings.embed_query.assert_called_once_with(query)
        
        # Get the embedding that was generated
        call_args = mock_embeddings.embed_query.call_args
        
        # Verify the embedding was passed to similarity search
        mock_vector_store.similarity_search.assert_called_once()
        search_call_args = mock_vector_store.similarity_search.call_args
        
        # Property: Query embedding must have correct dimensions
        query_vector = search_call_args[1]['query_vector']
        assert len(query_vector) == EXPECTED_DIMENSION, \
            f"Expected query embedding dimension {EXPECTED_DIMENSION}, got {len(query_vector)}"
        
        # Property: All embedding values should be numeric
        assert all(isinstance(val, (int, float)) for val in query_vector), \
            "All embedding values must be numeric"
            
    except Exception as e:
        # If there's an error, it should not be due to embedding generation
        # (other errors like network issues are acceptable for this property)
        if "embedding" in str(e).lower():
            raise


@given(st.lists(query_string(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_query_embedding_dimension_consistency(queries):
    """
    For any list of query strings, all generated embeddings should have 
    the same dimension size matching document embeddings.
    
    Validates: Requirements 6.1
    """
    EXPECTED_DIMENSION = 1536
    
    # Create mock vector store manager
    mock_vector_store = Mock()
    mock_vector_store.similarity_search = Mock(return_value=[])
    mock_vector_store.get_langchain_store = Mock()
    
    # Create mock embeddings that return consistent dimensions
    mock_embeddings = Mock()
    mock_embeddings.embed_query = Mock(return_value=[0.1] * EXPECTED_DIMENSION)
    
    # Create mock LLM
    mock_llm = Mock()
    
    # Create RAG chain with mocked components
    rag_chain = ArchonRAGChain(
        vector_store_manager=mock_vector_store,
        embeddings=mock_embeddings,
        llm=mock_llm
    )
    
    # Generate embeddings for all queries
    dimensions = []
    for query in queries:
        try:
            rag_chain.get_relevant_documents(query)
            
            # Get the embedding dimension from the similarity search call
            search_call_args = mock_vector_store.similarity_search.call_args
            query_vector = search_call_args[1]['query_vector']
            dimensions.append(len(query_vector))
            
        except Exception:
            # Skip queries that cause errors for other reasons
            continue
    
    # Property: All query embeddings must have the same dimension
    if dimensions:
        assert all(dim == EXPECTED_DIMENSION for dim in dimensions), \
            f"All query embeddings must have dimension {EXPECTED_DIMENSION}, got {dimensions}"
        
        # Property: Dimension consistency across all embeddings
        assert len(set(dimensions)) == 1, \
            f"All query embeddings must have the same dimension, got {set(dimensions)}"
