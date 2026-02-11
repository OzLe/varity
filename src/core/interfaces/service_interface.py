"""
Service interface definitions for ESCO business logic.

This module defines the abstract interfaces that all service implementations
must follow to ensure consistent business logic patterns across the application.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic, Callable
from datetime import datetime

from ..entities import (
    IngestionState,
    IngestionDecision,
    IngestionProgress,
    IngestionResult,
    ValidationResult,
    IngestionConfig,
    SearchQuery,
    SearchResult,
    SearchResponse
)

T = TypeVar('T')

class IngestionServiceInterface(ABC):
    """Interface for ingestion service operations."""
    
    @abstractmethod
    def get_current_state(self) -> IngestionState:
        """
        Get the current ingestion state.
        
        Returns:
            IngestionState: Current state of the ingestion system
        """
        pass
    
    @abstractmethod
    def should_run_ingestion(self, force_reingest: bool = False) -> IngestionDecision:
        """
        Determine whether ingestion should run.
        
        Args:
            force_reingest: Whether to force re-ingestion regardless of current state
            
        Returns:
            IngestionDecision: Decision object with reasoning and state information
        """
        pass
    
    @abstractmethod
    def validate_prerequisites(self) -> ValidationResult:
        """
        Validate all prerequisites for ingestion.
        
        Returns:
            ValidationResult: Validation status and details
        """
        pass
    
    @abstractmethod
    def run_ingestion(self, progress_callback: Optional[Callable[[IngestionProgress], None]] = None) -> IngestionResult:
        """
        Run the ingestion process.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            IngestionResult: Result of the ingestion process
        """
        pass
    
    @abstractmethod
    def verify_completion(self) -> ValidationResult:
        """
        Verify that ingestion completed successfully.
        
        Returns:
            ValidationResult: Validation status and details
        """
        pass
    
    @abstractmethod
    def get_ingestion_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the ingestion process.
        
        Returns:
            Dict[str, Any]: Dictionary of metrics
        """
        pass


class SearchServiceInterface(ABC):
    """Interface for search service operations."""
    
    @abstractmethod
    def search(self, query: SearchQuery) -> SearchResponse:
        """
        Perform a search operation.
        
        Args:
            query: Search query parameters
            
        Returns:
            SearchResponse: Search results and metadata
        """
        pass
    
    @abstractmethod
    def get_by_uri(self, uri: str) -> Optional[SearchResult]:
        """
        Get a single result by URI.
        
        Args:
            uri: URI of the result to retrieve
            
        Returns:
            Optional[SearchResult]: The result if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_related(self, uri: str, limit: int = 10) -> List[SearchResult]:
        """
        Get related results for a given URI.
        
        Args:
            uri: URI to find related results for
            limit: Maximum number of results to return
            
        Returns:
            List[SearchResult]: List of related results
        """
        pass


class TranslationServiceInterface(ABC):
    """Interface for translation service operations."""
    
    @abstractmethod
    def translate_text(self, text: str, target_language: str) -> str:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            str: Translated text
        """
        pass
    
    @abstractmethod
    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        """
        Translate multiple texts to target language.
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            
        Returns:
            List[str]: List of translated texts
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported target languages.
        
        Returns:
            List[str]: List of supported language codes
        """
        pass 