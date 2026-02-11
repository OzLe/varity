"""
Embedding client for external embedding services.

This module provides a client for interacting with external
embedding services, with support for different providers.
"""

from typing import Dict, Any, List, Optional
import os
from abc import ABC, abstractmethod
import numpy as np

from ...core.interfaces import ClientInterface
from ...core.entities import EmbeddingRequest, EmbeddingResponse


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    
    This class defines the interface for embedding providers,
    enabling easy substitution of different embedding services.
    """
    
    @abstractmethod
    async def get_embedding(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Get embedding for text.
        
        Args:
            text: Text to embed
            metadata: Optional embedding metadata
            
        Returns:
            List[float]: Text embedding
        """
        pass
    
    @abstractmethod
    async def batch_get_embeddings(
        self,
        texts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: Texts to embed
            metadata: Optional embedding metadata
            
        Returns:
            List[List[float]]: Text embeddings
        """
        pass


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """
    HuggingFace embedding provider.
    
    This class implements the embedding provider interface
    using HuggingFace models.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Initialize the provider.
        
        Args:
            model_name: Model name
            device: Device to use (cpu/cuda)
        """
        from sentence_transformers import SentenceTransformer
        
        self.model = SentenceTransformer(model_name, device=device)
    
    async def get_embedding(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Get embedding using HuggingFace model.
        
        Args:
            text: Text to embed
            metadata: Optional embedding metadata
            
        Returns:
            List[float]: Text embedding
        """
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    async def batch_get_embeddings(
        self,
        texts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts using HuggingFace model.
        
        Args:
            texts: Texts to embed
            metadata: Optional embedding metadata
            
        Returns:
            List[List[float]]: Text embeddings
        """
        embeddings = self.model.encode(texts)
        return embeddings.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider.
    
    This class implements the embedding provider interface
    using OpenAI's embedding API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the provider.
        
        Args:
            api_key: Optional API key
        """
        import openai
        
        self.client = openai.Client(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
    
    async def get_embedding(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Get embedding using OpenAI API.
        
        Args:
            text: Text to embed
            metadata: Optional embedding metadata
            
        Returns:
            List[float]: Text embedding
        """
        response = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    
    async def batch_get_embeddings(
        self,
        texts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts using OpenAI API.
        
        Args:
            texts: Texts to embed
            metadata: Optional embedding metadata
            
        Returns:
            List[List[float]]: Text embeddings
        """
        response = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        return [data.embedding for data in response.data]


class EmbeddingClient(ClientInterface):
    """
    Client for external embedding services.
    
    This class provides a unified interface for embedding services,
    with support for different providers.
    """
    
    def __init__(self, provider: EmbeddingProvider):
        """
        Initialize the client.
        
        Args:
            provider: Embedding provider
        """
        self.provider = provider
    
    async def get_embedding(
        self,
        request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Get embedding based on request.
        
        Args:
            request: Embedding request
            
        Returns:
            EmbeddingResponse: Embedding response
        """
        # Get embedding
        embedding = await self.provider.get_embedding(
            request.text,
            request.metadata
        )
        
        return EmbeddingResponse(
            text=request.text,
            embedding=embedding,
            metadata=request.metadata
        )
    
    async def batch_get_embeddings(
        self,
        requests: List[EmbeddingRequest]
    ) -> List[EmbeddingResponse]:
        """
        Get embeddings for multiple texts based on requests.
        
        Args:
            requests: Embedding requests
            
        Returns:
            List[EmbeddingResponse]: Embedding responses
        """
        # Extract texts
        texts = [r.text for r in requests]
        
        # Get embeddings
        embeddings = await self.provider.batch_get_embeddings(
            texts,
            requests[0].metadata  # Use metadata from first request
        )
        
        # Create responses
        return [
            EmbeddingResponse(
                text=text,
                embedding=embedding,
                metadata=request.metadata
            )
            for text, embedding, request in zip(texts, embeddings, requests)
        ]
    
    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            float: Similarity score
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Compute cosine similarity
        similarity = np.dot(vec1, vec2) / (
            np.linalg.norm(vec1) * np.linalg.norm(vec2)
        )
        
        return float(similarity) 