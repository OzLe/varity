"""
Model manager for handling model downloads and management.

This module provides a manager for downloading and managing
machine learning models, with support for different providers.
"""

from typing import Dict, Any, Optional, List
import os
from pathlib import Path
import hashlib
import json
import shutil
from abc import ABC, abstractmethod

import requests
from tqdm import tqdm


class ModelProvider(ABC):
    """
    Abstract base class for model providers.
    
    This class defines the interface for model providers,
    enabling easy substitution of different model sources.
    """
    
    @abstractmethod
    async def download_model(
        self,
        model_id: str,
        target_dir: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Download model from provider.
        
        Args:
            model_id: Model identifier
            target_dir: Target directory
            metadata: Optional download metadata
            
        Returns:
            str: Path to downloaded model
        """
        pass
    
    @abstractmethod
    async def get_model_info(
        self,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Get model information.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dict[str, Any]: Model information
        """
        pass


class HuggingFaceModelProvider(ModelProvider):
    """
    HuggingFace model provider.
    
    This class implements the model provider interface
    using HuggingFace's model hub.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the provider.
        
        Args:
            api_key: Optional API key
        """
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.base_url = "https://huggingface.co/api/models"
    
    async def download_model(
        self,
        model_id: str,
        target_dir: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Download model from HuggingFace.
        
        Args:
            model_id: Model identifier
            target_dir: Target directory
            metadata: Optional download metadata
            
        Returns:
            str: Path to downloaded model
        """
        from huggingface_hub import snapshot_download
        
        # Create target directory
        target_path = Path(target_dir) / model_id
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Download model
        snapshot_download(
            repo_id=model_id,
            local_dir=str(target_path),
            token=self.api_key
        )
        
        return str(target_path)
    
    async def get_model_info(
        self,
        model_id: str
    ) -> Dict[str, Any]:
        """
        Get model information from HuggingFace.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dict[str, Any]: Model information
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        response = requests.get(
            f"{self.base_url}/{model_id}",
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()


class ModelManager:
    """
    Manager for machine learning models.
    
    This class handles downloading and managing models,
    with support for different providers.
    """
    
    def __init__(
        self,
        provider: ModelProvider,
        cache_dir: str = "models"
    ):
        """
        Initialize the manager.
        
        Args:
            provider: Model provider
            cache_dir: Cache directory
        """
        self.provider = provider
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load cache index
        self.cache_index_path = self.cache_dir / "index.json"
        self.cache_index = self._load_cache_index()
    
    def _load_cache_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cache index.
        
        Returns:
            Dict[str, Dict[str, Any]]: Cache index
        """
        if self.cache_index_path.exists():
            with open(self.cache_index_path, "r") as f:
                return json.load(f)
        return {}
    
    def _save_cache_index(self) -> None:
        """Save cache index."""
        with open(self.cache_index_path, "w") as f:
            json.dump(self.cache_index, f, indent=2)
    
    def _compute_hash(self, model_id: str) -> str:
        """
        Compute hash for model ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            str: Hash value
        """
        return hashlib.sha256(model_id.encode()).hexdigest()
    
    async def download_model(
        self,
        model_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Download model.
        
        Args:
            model_id: Model identifier
            metadata: Optional download metadata
            
        Returns:
            str: Path to downloaded model
        """
        # Check if model is already downloaded
        model_hash = self._compute_hash(model_id)
        if model_hash in self.cache_index:
            return self.cache_index[model_hash]["path"]
        
        # Download model
        model_path = await self.provider.download_model(
            model_id,
            str(self.cache_dir),
            metadata
        )
        
        # Get model info
        model_info = await self.provider.get_model_info(model_id)
        
        # Update cache index
        self.cache_index[model_hash] = {
            "id": model_id,
            "path": model_path,
            "info": model_info,
            "metadata": metadata
        }
        self._save_cache_index()
        
        return model_path
    
    async def get_model_path(
        self,
        model_id: str
    ) -> Optional[str]:
        """
        Get path to downloaded model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Optional[str]: Path to model if downloaded
        """
        model_hash = self._compute_hash(model_id)
        if model_hash in self.cache_index:
            return self.cache_index[model_hash]["path"]
        return None
    
    async def get_model_info(
        self,
        model_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get model information.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Optional[Dict[str, Any]]: Model information if downloaded
        """
        model_hash = self._compute_hash(model_id)
        if model_hash in self.cache_index:
            return self.cache_index[model_hash]["info"]
        return None
    
    async def remove_model(
        self,
        model_id: str
    ) -> None:
        """
        Remove downloaded model.
        
        Args:
            model_id: Model identifier
        """
        model_hash = self._compute_hash(model_id)
        if model_hash in self.cache_index:
            # Remove model directory
            model_path = self.cache_index[model_hash]["path"]
            if os.path.exists(model_path):
                shutil.rmtree(model_path)
            
            # Remove from cache index
            del self.cache_index[model_hash]
            self._save_cache_index()
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List downloaded models.
        
        Returns:
            List[Dict[str, Any]]: List of model information
        """
        return list(self.cache_index.values()) 