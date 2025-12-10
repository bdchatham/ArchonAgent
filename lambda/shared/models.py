"""Data models and schemas for Archon RAG system."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import hashlib


@dataclass
class Document:
    """
    Represents a document from a repository.
    
    Attributes:
        repo_url: GitHub repository URL
        file_path: Path to file within repository
        content: Document content
        sha: Git SHA hash of the file
        last_modified: Timestamp of last modification
        document_type: Type of document (default: "kiro_doc")
        source_type: Source system (default: "github")
    """
    repo_url: str
    file_path: str
    content: str
    sha: str
    last_modified: datetime
    document_type: str = "kiro_doc"
    source_type: str = "github"
    
    def validate(self) -> bool:
        """
        Validate document fields.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.repo_url or not isinstance(self.repo_url, str):
            raise ValueError("repo_url must be a non-empty string")
        
        if not self.file_path or not isinstance(self.file_path, str):
            raise ValueError("file_path must be a non-empty string")
        
        if not isinstance(self.content, str):
            raise ValueError("content must be a string")
        
        if not self.sha or not isinstance(self.sha, str):
            raise ValueError("sha must be a non-empty string")
        
        if not isinstance(self.last_modified, datetime):
            raise ValueError("last_modified must be a datetime object")
        
        if not self.document_type or not isinstance(self.document_type, str):
            raise ValueError("document_type must be a non-empty string")
        
        if not self.source_type or not isinstance(self.source_type, str):
            raise ValueError("source_type must be a non-empty string")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert document to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        data = asdict(self)
        # Convert datetime to ISO format string
        data['last_modified'] = self.last_modified.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """
        Create Document from dictionary.
        
        Args:
            data: Dictionary with document data
            
        Returns:
            Document instance
        """
        # Parse datetime from ISO format
        if isinstance(data.get('last_modified'), str):
            data['last_modified'] = datetime.fromisoformat(
                data['last_modified'].replace('Z', '+00:00')
            )
        
        return cls(**data)
    
    def to_json(self) -> str:
        """
        Convert document to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Document':
        """
        Create Document from JSON string.
        
        Args:
            json_str: JSON string with document data
            
        Returns:
            Document instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class DocumentChunk:
    """
    Represents a chunk of a document.
    
    Attributes:
        document: Parent document
        chunk_index: Index of this chunk in the document
        text: Chunk text content
        start_char: Starting character position in original document
        end_char: Ending character position in original document
    """
    document: Document
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    
    def validate(self) -> bool:
        """
        Validate document chunk fields.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(self.document, Document):
            raise ValueError("document must be a Document instance")
        
        # Validate document
        self.document.validate()
        
        if not isinstance(self.chunk_index, int) or self.chunk_index < 0:
            raise ValueError("chunk_index must be a non-negative integer")
        
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        
        if not isinstance(self.start_char, int) or self.start_char < 0:
            raise ValueError("start_char must be a non-negative integer")
        
        if not isinstance(self.end_char, int) or self.end_char < 0:
            raise ValueError("end_char must be a non-negative integer")
        
        if self.end_char < self.start_char:
            raise ValueError("end_char must be >= start_char")
        
        return True
    
    def generate_id(self) -> str:
        """
        Generate unique ID for this chunk.
        
        Returns:
            SHA256 hash as hex string
        """
        id_string = f"{self.document.repo_url}#{self.document.file_path}#{self.chunk_index}"
        return hashlib.sha256(id_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert chunk to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'document': self.document.to_dict(),
            'chunk_index': self.chunk_index,
            'text': self.text,
            'start_char': self.start_char,
            'end_char': self.end_char
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentChunk':
        """
        Create DocumentChunk from dictionary.
        
        Args:
            data: Dictionary with chunk data
            
        Returns:
            DocumentChunk instance
        """
        document = Document.from_dict(data['document'])
        return cls(
            document=document,
            chunk_index=data['chunk_index'],
            text=data['text'],
            start_char=data['start_char'],
            end_char=data['end_char']
        )


@dataclass
class RepositoryConfig:
    """
    Configuration for a GitHub repository to monitor.
    
    Attributes:
        url: GitHub repository URL
        branch: Branch to monitor
        paths: List of paths to monitor within repository
    """
    url: str
    branch: str
    paths: List[str]
    
    def validate(self) -> bool:
        """
        Validate repository configuration.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.url or not isinstance(self.url, str):
            raise ValueError("url must be a non-empty string")
        
        if not self.branch or not isinstance(self.branch, str):
            raise ValueError("branch must be a non-empty string")
        
        if not isinstance(self.paths, list):
            raise ValueError("paths must be a list")
        
        if not self.paths:
            raise ValueError("paths must contain at least one path")
        
        for path in self.paths:
            if not isinstance(path, str):
                raise ValueError("all paths must be strings")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryConfig':
        """
        Create RepositoryConfig from dictionary.
        
        Args:
            data: Dictionary with config data
            
        Returns:
            RepositoryConfig instance
        """
        return cls(**data)


@dataclass
class SourceReference:
    """
    Reference to a source document.
    
    Attributes:
        repo: Repository URL
        file_path: Path to file within repository
        relevance_score: Relevance score from similarity search
        chunk_text: Optional text of the relevant chunk
    """
    repo: str
    file_path: str
    relevance_score: float
    chunk_text: Optional[str] = None
    
    def validate(self) -> bool:
        """
        Validate source reference fields.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.repo or not isinstance(self.repo, str):
            raise ValueError("repo must be a non-empty string")
        
        if not self.file_path or not isinstance(self.file_path, str):
            raise ValueError("file_path must be a non-empty string")
        
        if not isinstance(self.relevance_score, (int, float)):
            raise ValueError("relevance_score must be a number")
        
        if self.relevance_score < 0:
            raise ValueError("relevance_score must be non-negative")
        
        if self.chunk_text is not None and not isinstance(self.chunk_text, str):
            raise ValueError("chunk_text must be a string or None")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceReference':
        """
        Create SourceReference from dictionary.
        
        Args:
            data: Dictionary with source reference data
            
        Returns:
            SourceReference instance
        """
        return cls(**data)


@dataclass
class QueryResponse:
    """
    Response to a query request.
    
    Attributes:
        answer: Generated answer from LLM
        sources: List of source references
        timestamp: ISO format timestamp of response
        query: Original query string
    """
    answer: str
    sources: List[SourceReference]
    timestamp: str
    query: str
    
    def validate(self) -> bool:
        """
        Validate query response fields.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(self.answer, str):
            raise ValueError("answer must be a string")
        
        if not isinstance(self.sources, list):
            raise ValueError("sources must be a list")
        
        for source in self.sources:
            if not isinstance(source, SourceReference):
                raise ValueError("all sources must be SourceReference instances")
            source.validate()
        
        if not self.timestamp or not isinstance(self.timestamp, str):
            raise ValueError("timestamp must be a non-empty string")
        
        if not isinstance(self.query, str):
            raise ValueError("query must be a string")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'answer': self.answer,
            'sources': [source.to_dict() for source in self.sources],
            'timestamp': self.timestamp,
            'query': self.query
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryResponse':
        """
        Create QueryResponse from dictionary.
        
        Args:
            data: Dictionary with response data
            
        Returns:
            QueryResponse instance
        """
        sources = [SourceReference.from_dict(s) for s in data['sources']]
        return cls(
            answer=data['answer'],
            sources=sources,
            timestamp=data['timestamp'],
            query=data['query']
        )
    
    def to_json(self) -> str:
        """
        Convert to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'QueryResponse':
        """
        Create QueryResponse from JSON string.
        
        Args:
            json_str: JSON string with response data
            
        Returns:
            QueryResponse instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class MonitoringResult:
    """
    Results from a monitoring execution.
    
    Attributes:
        repositories_checked: Number of repositories successfully checked
        documents_processed: Number of documents processed
        documents_updated: Number of documents updated in vector store
        errors: List of error messages encountered
        execution_time: Total execution time in seconds
    """
    repositories_checked: int
    documents_processed: int
    documents_updated: int
    errors: List[str]
    execution_time: float
    
    def validate(self) -> bool:
        """
        Validate monitoring result fields.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(self.repositories_checked, int) or self.repositories_checked < 0:
            raise ValueError("repositories_checked must be a non-negative integer")
        
        if not isinstance(self.documents_processed, int) or self.documents_processed < 0:
            raise ValueError("documents_processed must be a non-negative integer")
        
        if not isinstance(self.documents_updated, int) or self.documents_updated < 0:
            raise ValueError("documents_updated must be a non-negative integer")
        
        if not isinstance(self.errors, list):
            raise ValueError("errors must be a list")
        
        for error in self.errors:
            if not isinstance(error, str):
                raise ValueError("all errors must be strings")
        
        if not isinstance(self.execution_time, (int, float)) or self.execution_time < 0:
            raise ValueError("execution_time must be a non-negative number")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoringResult':
        """
        Create MonitoringResult from dictionary.
        
        Args:
            data: Dictionary with result data
            
        Returns:
            MonitoringResult instance
        """
        return cls(**data)
    
    def to_json(self) -> str:
        """
        Convert to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MonitoringResult':
        """
        Create MonitoringResult from JSON string.
        
        Args:
            json_str: JSON string with result data
            
        Returns:
            MonitoringResult instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class VectorDocument:
    """
    Represents a document with embeddings for vector storage.
    
    Attributes:
        id: Unique identifier for the document
        vector: Embedding vector
        metadata: Document metadata
        text: Document text content
    """
    id: str
    vector: List[float]
    metadata: Dict[str, Any]
    text: str
    
    def validate(self) -> bool:
        """
        Validate vector document fields.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.id or not isinstance(self.id, str):
            raise ValueError("id must be a non-empty string")
        
        if not isinstance(self.vector, list):
            raise ValueError("vector must be a list")
        
        if not self.vector:
            raise ValueError("vector must not be empty")
        
        for val in self.vector:
            if not isinstance(val, (int, float)):
                raise ValueError("all vector values must be numbers")
        
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")
        
        # Validate required metadata fields
        required_fields = ['repo_url', 'file_path']
        for field in required_fields:
            if field not in self.metadata:
                raise ValueError(f"metadata must contain '{field}' field")
        
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorDocument':
        """
        Create VectorDocument from dictionary.
        
        Args:
            data: Dictionary with vector document data
            
        Returns:
            VectorDocument instance
        """
        return cls(**data)
