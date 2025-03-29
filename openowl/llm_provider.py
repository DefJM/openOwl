"""LLM Provider abstraction to support multiple LLM backends."""

import os
import abc
import json
import requests
from typing import Dict, List, Optional, Union, Any

import anthropic
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""
    
    @abc.abstractmethod
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 700, 
                     temperature: float = 0, 
                     stream: bool = False) -> str:
        """Generate text from the LLM provider.
        
        Args:
            prompt: The prompt to send to the LLM.
            max_tokens: Maximum number of tokens to generate.
            temperature: Temperature for generation (0-1).
            stream: Whether to stream the response.
            
        Returns:
            Generated text response.
        """
        pass
    
    @classmethod
    def create(cls, provider: str, model: str, **kwargs) -> 'LLMProvider':
        """Factory method to create an LLM provider.
        
        Args:
            provider: Provider name ('claude' or 'ollama').
            model: Model name to use.
            **kwargs: Additional provider-specific arguments.
            
        Returns:
            An instance of the specified LLM provider.
        """
        if provider.lower() == 'claude':
            return ClaudeProvider(model, **kwargs)
        elif provider.lower() == 'ollama':
            return OllamaProvider(model, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")


class ClaudeProvider(LLMProvider):
    """Provider for Claude API."""
    
    def __init__(self, model: str, api_key: Optional[str] = None):
        """Initialize Claude provider.
        
        Args:
            model: Claude model to use.
            api_key: API key for Claude. If None, uses CLAUDE_API_KEY from env.
        """
        self.model = model
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 700, 
                     temperature: float = 0, 
                     stream: bool = False) -> str:
        """Generate text using Claude API.
        
        Args:
            prompt: The prompt to send to Claude.
            max_tokens: Maximum number of tokens to generate.
            temperature: Temperature for generation (0-1).
            stream: Whether to stream the response.
            
        Returns:
            Generated text response.
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
        )
        
        return message.content[0].text


class OllamaProvider(LLMProvider):
    """Provider for Ollama API."""
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        """Initialize Ollama provider.
        
        Args:
            model: Ollama model to use.
            base_url: Base URL for Ollama API. Default is localhost:11434.
        """
        self.model = model
        self.base_url = base_url
        self.api_endpoint = f"{self.base_url}/api/generate"
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 700, 
                     temperature: float = 0, 
                     stream: bool = False) -> str:
        """Generate text using Ollama API.
        
        Args:
            prompt: The prompt to send to Ollama.
            max_tokens: Maximum number of tokens to generate.
            temperature: Temperature for generation (0-1).
            stream: Whether to stream the response.
            
        Returns:
            Generated text response.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        response = requests.post(self.api_endpoint, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Return the generated text
        return result['response'] 