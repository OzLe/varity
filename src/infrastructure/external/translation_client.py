"""
Translation client for external translation services.

This module provides a client for interacting with external
translation services, with support for different providers.
"""

from typing import Dict, Any, List, Optional
import os
from abc import ABC, abstractmethod

from ...core.interfaces import ClientInterface
from ...core.entities import TranslationRequest, TranslationResponse


class TranslationProvider(ABC):
    """
    Abstract base class for translation providers.
    
    This class defines the interface for translation providers,
    enabling easy substitution of different translation services.
    """
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            metadata: Optional translation metadata
            
        Returns:
            str: Translated text
        """
        pass
    
    @abstractmethod
    async def batch_translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Translate multiple texts from source language to target language.
        
        Args:
            texts: Texts to translate
            source_lang: Source language code
            target_lang: Target language code
            metadata: Optional translation metadata
            
        Returns:
            List[str]: Translated texts
        """
        pass


class GoogleTranslationProvider(TranslationProvider):
    """
    Google Cloud Translation provider.
    
    This class implements the translation provider interface
    using Google Cloud Translation API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the provider.
        
        Args:
            api_key: Optional API key
        """
        from google.cloud import translate_v2 as translate
        
        self.client = translate.Client()
        self.api_key = api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate text using Google Cloud Translation.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            metadata: Optional translation metadata
            
        Returns:
            str: Translated text
        """
        result = self.client.translate(
            text,
            target_language=target_lang,
            source_language=source_lang
        )
        return result["translatedText"]
    
    async def batch_translate(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Translate multiple texts using Google Cloud Translation.
        
        Args:
            texts: Texts to translate
            source_lang: Source language code
            target_lang: Target language code
            metadata: Optional translation metadata
            
        Returns:
            List[str]: Translated texts
        """
        results = self.client.translate(
            texts,
            target_language=target_lang,
            source_language=source_lang
        )
        return [r["translatedText"] for r in results]


class TranslationClient(ClientInterface):
    """
    Client for external translation services.
    
    This class provides a unified interface for translation services,
    with support for different providers.
    """
    
    def __init__(
        self,
        provider: TranslationProvider,
        default_source_lang: str = "en",
        default_target_lang: str = "en"
    ):
        """
        Initialize the client.
        
        Args:
            provider: Translation provider
            default_source_lang: Default source language
            default_target_lang: Default target language
        """
        self.provider = provider
        self.default_source_lang = default_source_lang
        self.default_target_lang = default_target_lang
    
    async def translate(
        self,
        request: TranslationRequest
    ) -> TranslationResponse:
        """
        Translate text based on request.
        
        Args:
            request: Translation request
            
        Returns:
            TranslationResponse: Translation response
        """
        # Use request languages or defaults
        source_lang = request.source_lang or self.default_source_lang
        target_lang = request.target_lang or self.default_target_lang
        
        # Translate text
        translated_text = await self.provider.translate(
            request.text,
            source_lang,
            target_lang,
            request.metadata
        )
        
        return TranslationResponse(
            text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            metadata=request.metadata
        )
    
    async def batch_translate(
        self,
        requests: List[TranslationRequest]
    ) -> List[TranslationResponse]:
        """
        Translate multiple texts based on requests.
        
        Args:
            requests: Translation requests
            
        Returns:
            List[TranslationResponse]: Translation responses
        """
        # Group texts by language pair
        language_pairs: Dict[tuple, List[tuple]] = {}
        for i, request in enumerate(requests):
            source_lang = request.source_lang or self.default_source_lang
            target_lang = request.target_lang or self.default_target_lang
            key = (source_lang, target_lang)
            if key not in language_pairs:
                language_pairs[key] = []
            language_pairs[key].append((i, request))
        
        # Translate each group
        all_results = [None] * len(requests)
        for (source_lang, target_lang), group in language_pairs.items():
            # Extract texts and indices
            indices = [i for i, _ in group]
            texts = [r.text for _, r in group]
            
            # Translate texts
            translated_texts = await self.provider.batch_translate(
                texts,
                source_lang,
                target_lang,
                group[0][1].metadata  # Use metadata from first request
            )
            
            # Store results
            for i, text in zip(indices, translated_texts):
                all_results[i] = TranslationResponse(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    metadata=requests[i].metadata
                )
        
        return all_results 