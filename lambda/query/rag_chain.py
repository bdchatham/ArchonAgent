"""RAG chain implementation using LangChain for Archon system."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_classic.chains import RetrievalQA
from langchain_classic.prompts import PromptTemplate
from langchain_core.documents import Document as LangChainDocument


@dataclass
class Document:
    """Represents a retrieved document with metadata."""
    text: str
    metadata: Dict[str, Any]
    score: float


class RAGChainError(Exception):
    """Base exception for RAG chain errors."""
    pass


class ArchonRAGChain:
    """
    RAG chain for Archon system using LangChain.
    
    Orchestrates:
    - Document retrieval from vector store
    - Context preparation for LLM
    - Response generation using AWS Bedrock
    - Source document tracking
    """
    
    # Default prompt template for Archon
    DEFAULT_PROMPT_TEMPLATE = """You are Archon, a system engineering expert assistant. Your role is to help engineers 
and agents understand product architecture by providing accurate information from 
documentation.

Context from documentation:
{context}

Question: {question}

Provide a clear, accurate answer based on the documentation. If the documentation 
doesn't contain enough information to answer fully, acknowledge this. Always cite 
the specific documents you reference.

Answer:"""
    
    def __init__(
        self,
        vector_store_manager,
        llm_model: str = "anthropic.claude-3-haiku-20240307",
        embedding_model: str = "amazon.titan-embed-text-v1",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        retrieval_k: int = 5,
        prompt_template: Optional[str] = None,
        llm: Optional[ChatBedrock] = None,
        embeddings: Optional[BedrockEmbeddings] = None
    ):
        """
        Initialize the RAG chain.
        
        Args:
            vector_store_manager: VectorStoreManager instance for retrieval
            llm_model: Name of the Bedrock LLM model
            embedding_model: Name of the Bedrock embedding model
            temperature: LLM temperature parameter
            max_tokens: Maximum tokens for LLM response
            retrieval_k: Number of documents to retrieve
            prompt_template: Optional custom prompt template
            llm: Optional pre-configured LLM (for testing)
            embeddings: Optional pre-configured embeddings (for testing)
        """
        self.vector_store_manager = vector_store_manager
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retrieval_k = retrieval_k
        
        # Initialize embeddings
        if embeddings is not None:
            self.embeddings = embeddings
        else:
            self.embeddings = BedrockEmbeddings(model_id=embedding_model)
        
        # Initialize LLM
        if llm is not None:
            self.llm = llm
        else:
            self.llm = ChatBedrock(
                model_id=llm_model,
                model_kwargs={
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
        
        # Set up prompt template
        template_text = prompt_template if prompt_template else self.DEFAULT_PROMPT_TEMPLATE
        self.prompt = PromptTemplate(
            template=template_text,
            input_variables=["context", "question"]
        )
        
        # Initialize retriever from vector store
        self._retriever = None
        self._qa_chain = None
    
    def _get_retriever(self):
        """
        Get or create the retriever from vector store.
        
        Returns:
            LangChain retriever instance
        """
        if self._retriever is None:
            langchain_store = self.vector_store_manager.get_langchain_store()
            self._retriever = langchain_store.as_retriever(
                search_kwargs={"k": self.retrieval_k}
            )
        return self._retriever
    
    def _get_qa_chain(self) -> RetrievalQA:
        """
        Get or create the RetrievalQA chain.
        
        Returns:
            Configured RetrievalQA chain
        """
        if self._qa_chain is None:
            retriever = self._get_retriever()
            self._qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": self.prompt}
            )
        return self._qa_chain
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query string
            
        Returns:
            List of Document objects with metadata and scores
            
        Raises:
            RAGChainError: If retrieval fails
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Perform similarity search
            results = self.vector_store_manager.similarity_search(
                query_vector=query_embedding,
                k=self.retrieval_k
            )
            
            # Convert to Document objects
            documents = []
            for result in results:
                documents.append(Document(
                    text=result.get('text', ''),
                    metadata=result.get('metadata', {}),
                    score=result.get('score', 0.0)
                ))
            
            return documents
            
        except Exception as e:
            raise RAGChainError(f"Failed to retrieve documents: {str(e)}") from e
    
    def generate_response(self, query: str, context: List[Document]) -> str:
        """
        Generate response using LLM with provided context.
        
        Args:
            query: Query string
            context: List of Document objects to use as context
            
        Returns:
            Generated response string
            
        Raises:
            RAGChainError: If generation fails
        """
        try:
            # Format context from documents
            context_text = "\n\n".join([
                f"Document {i+1} (from {doc.metadata.get('repo_url', 'unknown')}/{doc.metadata.get('file_path', 'unknown')}):\n{doc.text}"
                for i, doc in enumerate(context)
            ])
            
            # Format prompt
            formatted_prompt = self.prompt.format(
                context=context_text,
                question=query
            )
            
            # Generate response using LLM
            response = self.llm.invoke(formatted_prompt)
            
            # Extract text from response
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            raise RAGChainError(f"Failed to generate response: {str(e)}") from e
    
    def invoke(self, query: str) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline for a query.
        
        Args:
            query: Query string
            
        Returns:
            Dictionary containing:
                - result: Generated answer
                - source_documents: List of source documents used
                
        Raises:
            RAGChainError: If invocation fails
        """
        try:
            qa_chain = self._get_qa_chain()
            
            # Execute the chain
            result = qa_chain.invoke({"query": query})
            
            # Extract and format results
            answer = result.get("result", "")
            source_docs = result.get("source_documents", [])
            
            # Convert LangChain documents to our Document format
            formatted_sources = []
            for doc in source_docs:
                formatted_sources.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "score": doc.metadata.get("score", 0.0)
                })
            
            return {
                "result": answer,
                "source_documents": formatted_sources
            }
            
        except Exception as e:
            raise RAGChainError(f"Failed to invoke RAG chain: {str(e)}") from e
