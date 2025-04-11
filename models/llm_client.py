"""
Ollama LLM client for the CareCompanion system.
Uses Ollama for local LLM inference.
"""

import ollama
import time
import asyncio
from typing import Dict, Any, List, Optional

from utils.logger import setup_logger
from utils.config import config

logger = setup_logger("llm_client")

class OllamaClient:
    """
    Ollama LLM client for the CareCompanion system.
    """
    
    def __init__(self, model_name: str = "mistral"):
        """
        Initialize the Ollama client.
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
        logger.info(f"Initialized OllamaClient with model: {model_name}")
    
    async def generate(self, prompt: str, max_tokens: int = 100, 
                      temperature: float = 0.7, response_type: str = "status_summary") -> str:
        """
        Generate a response using Ollama LLM.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens in the response
            temperature: Temperature parameter for generation
            response_type: Type of response (used for logging)
            
        Returns:
            Generated response
        """
        logger.debug(f"Generating {response_type} response using {self.model_name}")
        
        try:
            # Create messages list with user prompt
            messages = [{"role": "user", "content": prompt}]
            
            # Call Ollama API
            # Using run_in_executor to run the synchronous Ollama API in an async context
            loop = asyncio.get_event_loop()
            start_time = time.time()
            
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                )
            )
            
            end_time = time.time()
            
            # Extract the response text
            response_text = response["message"]["content"]
            
            logger.debug(f"Response generated in {end_time - start_time:.2f} seconds")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response with Ollama: {e}")
            # Return a simple error message that doesn't break the application flow
            return f"Error generating response: {str(e)}"
