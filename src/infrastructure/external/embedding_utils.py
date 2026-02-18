"""
Embedding utilities for ESCO data.

This module provides utilities for generating embeddings for ESCO data
using the HuggingFace embedding provider.
"""

import os
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

class ESCOEmbedding:
    """
    Utility class for generating embeddings for ESCO data.
    Uses the HuggingFace sentence-transformers model.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1",
        device: Optional[str] = None
    ):
        """
        Initialize the embedding utility.
        
        Args:
            model_name: Name of the HuggingFace model to use
            device: Device to use for computation (cpu/cuda/mps)
        """
        if device is None:
            device = "mps" if os.getenv("TORCH_DEVICE") == "mps" else "cpu"
            
        self.model = SentenceTransformer(model_name, device=device)
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Text embedding
        """
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of text embeddings
        """
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            float: Cosine similarity score
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))) 