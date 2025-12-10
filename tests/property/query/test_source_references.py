"""
Property-based tests for source reference completeness.

Feature: archon-rag-system, Property 18: Source reference completeness
Validates: Requirements 6.5
"""

from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, assume

from query.query_handler import QueryHandler, SourceReference
from query.rag_chain import ArchonRAGChain


# Strategy for generating source documents with metadata
@st.composite
def source_document(draw):
    """Generate a source document with metadata."""
    # Generate repository URL
    org = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    repo = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    repo_url = f"https://github.com/{org}/{repo}"
    
    # Generate file path
    path_parts = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=15
        ),
        min_size=1,
        max_size=5
    ))
    file_path = ".kiro/" + "/".join(path_parts) + ".md"
    
    # Generate score
    score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    # Generate text
    text = draw(st.text(min_size=10, max_size=500))
    
    return {
        "metadata": {
            "repo_url": repo_url,
            "file_path": file_path,
            "chunk_index": draw(st.integers(min_value=0, max_value=100)),
            "last_modified": "2025-12-09T10:00:00Z",
            "document_type": "kiro_doc",
            "source_type": "github"
        },
        "text": text,
        "score": score
    }


# Strategy for generating valid query strings
@st.composite
def valid_query_string(draw):
    """Generate valid query strings."""
    query = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Z'),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=5,
        max_size=200
    ))
    assume(query.strip())
    return query


# Feature: archon-rag-system, Property 18: Source reference completeness
@given(valid_query_string(), st.lists(source_document(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_source_reference_has_repo_and_path(query, source_docs):
    """
    For any query response, each source reference should include 
    both repository URL and file path.
    
    Validates: Requirements 6.5
    """
    # Create mock RAG chain that returns the source documents
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    mock_rag_chain.invoke = Mock(return_value={
        "result": "This is a test answer.",
        "source_documents": source_docs
    })
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Handle query
    response = handler.handle_query(query)
    
    # Property: Response should have sources
    assert hasattr(response, 'sources'), "Response must have 'sources' attribute"
    assert isinstance(response.sources, list), "Sources must be a list"
    
    # Property: Each source reference must have repo and file_path
    for source_ref in response.sources:
        assert isinstance(source_ref, SourceReference), \
            "Each source must be a SourceReference object"
        
        # Property: Must have repo field
        assert hasattr(source_ref, 'repo'), "Source reference must have 'repo' field"
        assert source_ref.repo is not None, "Source reference repo must not be None"
        assert isinstance(source_ref.repo, str), "Source reference repo must be a string"
        
        # Property: Must have file_path field
        assert hasattr(source_ref, 'file_path'), \
            "Source reference must have 'file_path' field"
        assert source_ref.file_path is not None, \
            "Source reference file_path must not be None"
        assert isinstance(source_ref.file_path, str), \
            "Source reference file_path must be a string"


@given(valid_query_string(), st.lists(source_document(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_source_reference_preserves_metadata(query, source_docs):
    """
    For any query response, source references should preserve the 
    repository URL and file path from the original document metadata.
    
    Validates: Requirements 6.5
    """
    # Create mock RAG chain that returns the source documents
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    mock_rag_chain.invoke = Mock(return_value={
        "result": "This is a test answer.",
        "source_documents": source_docs
    })
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Handle query
    response = handler.handle_query(query)
    
    # Property: Source references should match original metadata
    assert len(response.sources) <= len(source_docs), \
        "Number of source references should not exceed source documents"
    
    for i, source_ref in enumerate(response.sources):
        if i < len(source_docs):
            original_metadata = source_docs[i]["metadata"]
            
            # Property: Repo URL should match original
            assert source_ref.repo == original_metadata["repo_url"], \
                f"Source reference repo should match original: {source_ref.repo} != {original_metadata['repo_url']}"
            
            # Property: File path should match original
            assert source_ref.file_path == original_metadata["file_path"], \
                f"Source reference file_path should match original: {source_ref.file_path} != {original_metadata['file_path']}"


@given(valid_query_string(), st.lists(source_document(), min_size=0, max_size=10))
@settings(max_examples=100)
def test_all_sources_have_complete_references(query, source_docs):
    """
    For any query response with sources, all source references 
    should be complete with non-empty repo and file_path.
    
    Validates: Requirements 6.5
    """
    # Create mock RAG chain that returns the source documents
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    mock_rag_chain.invoke = Mock(return_value={
        "result": "This is a test answer.",
        "source_documents": source_docs
    })
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Handle query
    response = handler.handle_query(query)
    
    # Property: All source references must be complete
    for source_ref in response.sources:
        # Property: Repo must be non-empty
        assert source_ref.repo, \
            f"Source reference repo must be non-empty, got: {source_ref.repo!r}"
        
        # Property: File path must be non-empty
        assert source_ref.file_path, \
            f"Source reference file_path must be non-empty, got: {source_ref.file_path!r}"
        
        # Property: Both should be strings
        assert isinstance(source_ref.repo, str), \
            f"Source reference repo must be string, got: {type(source_ref.repo)}"
        assert isinstance(source_ref.file_path, str), \
            f"Source reference file_path must be string, got: {type(source_ref.file_path)}"


@given(valid_query_string(), st.lists(source_document(), min_size=1, max_size=10))
@settings(max_examples=100)
def test_source_reference_has_relevance_score(query, source_docs):
    """
    For any query response, each source reference should include 
    a relevance score.
    
    Validates: Requirements 6.5
    """
    # Create mock RAG chain that returns the source documents
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    mock_rag_chain.invoke = Mock(return_value={
        "result": "This is a test answer.",
        "source_documents": source_docs
    })
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Handle query
    response = handler.handle_query(query)
    
    # Property: Each source reference must have relevance_score
    for source_ref in response.sources:
        assert hasattr(source_ref, 'relevance_score'), \
            "Source reference must have 'relevance_score' field"
        
        # Property: Relevance score should be numeric
        assert isinstance(source_ref.relevance_score, (int, float)), \
            f"Relevance score must be numeric, got: {type(source_ref.relevance_score)}"


@given(
    valid_query_string(),
    st.lists(source_document(), min_size=1, max_size=10),
    st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100)
def test_source_references_respect_max_results(query, source_docs, max_results):
    """
    For any query with max_results parameter, the number of source 
    references should not exceed max_results.
    
    Validates: Requirements 6.5
    """
    # Create mock RAG chain that returns the source documents
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    mock_rag_chain.invoke = Mock(return_value={
        "result": "This is a test answer.",
        "source_documents": source_docs
    })
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain, max_results=max_results)
    
    # Handle query
    response = handler.handle_query(query)
    
    # Property: Number of sources should not exceed max_results
    assert len(response.sources) <= max_results, \
        f"Number of sources ({len(response.sources)}) should not exceed max_results ({max_results})"
    
    # Property: All returned sources should still be complete
    for source_ref in response.sources:
        assert source_ref.repo, "Source repo must be non-empty"
        assert source_ref.file_path, "Source file_path must be non-empty"


@given(valid_query_string())
@settings(max_examples=100)
def test_empty_sources_handled_correctly(query):
    """
    For any query that returns no source documents, the response 
    should have an empty sources list (not None or error).
    
    Validates: Requirements 6.5
    """
    # Create mock RAG chain that returns no sources
    mock_rag_chain = Mock(spec=ArchonRAGChain)
    mock_rag_chain.invoke = Mock(return_value={
        "result": "No relevant documentation found.",
        "source_documents": []
    })
    
    # Create query handler
    handler = QueryHandler(rag_chain=mock_rag_chain)
    
    # Handle query
    response = handler.handle_query(query)
    
    # Property: Sources should be an empty list, not None
    assert response.sources is not None, "Sources should not be None"
    assert isinstance(response.sources, list), "Sources should be a list"
    assert len(response.sources) == 0, "Sources should be empty"
