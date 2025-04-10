"""
Base agent class for the CareCompanion system.
Provides common functionality for all agent types.
"""

import time
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from utils.logger import setup_logger
from utils.config import Config
from models.llm_client import OllamaClient

class BaseAgent:
    """
    Base class for all agents in the CareCompanion system.
    """
    
    def __init__(self, name: str, config: Config):
        """
        Initialize the base agent.
        
        Args:
            name: Name of the agent
            config: Configuration object
        """
        self.name = name
        self.config = config
        self.logger = setup_logger(f"agent.{name}")
        
        # Get agent-specific configuration
        self.agent_config = config.get_agent_config(name)
        
        # Initialize the LLM client
        model_name = config.get_llm_model(name)
        self.llm_client = OllamaClient(model_name)
        
        # Update interval in seconds
        self.update_interval = self.agent_config.get("update_interval", 60)
        
        # Last update timestamp
        self.last_update = None
        
        # Agent state
        self.state = {}
        
        # Message queue for async communication
        self.message_queue = asyncio.Queue()
        
        # Registered callbacks
        self.callbacks = {}
        
        self.logger.info(f"Initialized {name} agent with model {model_name}")
    
    async def start(self) -> None:
        """
        Start the agent's processing loop.
        """
        self.logger.info(f"Starting {self.name} agent")
        
        # Initialize agent state
        await self.initialize()
        
        # Start the main processing loop
        asyncio.create_task(self._processing_loop())
    
    async def initialize(self) -> None:
        """
        Initialize the agent's state.
        This method should be overridden by subclasses.
        """
        self.logger.info(f"Initializing {self.name} agent")
        self.last_update = datetime.now()
    
    async def _processing_loop(self) -> None:
        """
        Main processing loop for the agent.
        Processes messages and performs periodic updates.
        """
        self.logger.info(f"Started processing loop for {self.name} agent")
        
        while True:
            try:
                # Process any pending messages
                while not self.message_queue.empty():
                    message = await self.message_queue.get()
                    response = await self.process_message(message)
                    
                    # Call callback if provided
                    callback_id = message.get("callback_id")
                    if callback_id and callback_id in self.callbacks:
                        self.callbacks[callback_id](response)
                        del self.callbacks[callback_id]
                
                # Check if update is needed
                now = datetime.now()
                if self.last_update is None or (now - self.last_update).total_seconds() >= self.update_interval:
                    await self.update()
                    self.last_update = now
                
                # Sleep to avoid busy waiting
                await asyncio.sleep(0.1)
            
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1)  # Sleep longer on error
    
    async def update(self) -> None:
        """
        Perform a periodic update.
        This method should be overridden by subclasses.
        """
        self.logger.debug(f"Update triggered for {self.name} agent")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message received by the agent.
        This method should be overridden by subclasses.
        
        Args:
            message: Message to process
            
        Returns:
            Response to the message
        """
        self.logger.debug(f"Processing message: {message.get('type', 'unknown')}")
        return {
            "status": "error",
            "message": "process_message not implemented"
        }
    
    async def send_message(
        self, 
        message: Dict[str, Any], 
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """
        Send a message to the agent.
        
        Args:
            message: Message to send
            callback: Optional callback function to call with the response
        """
        if callback:
            # Generate a callback ID
            callback_id = f"{self.name}_{int(time.time())}_{id(callback)}"
            self.callbacks[callback_id] = callback
            message["callback_id"] = callback_id
        
        # Add the message to the queue
        await self.message_queue.put(message)
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the agent's current state.
        
        Returns:
            Dictionary containing the agent's state
        """
        return self.state.copy()
    
    def update_state(self, updates: Dict[str, Any]) -> None:
        """
        Update the agent's state.
        
        Args:
            updates: Dictionary containing state updates
        """
        self.state.update(updates)
        self.logger.debug(f"Updated state: {', '.join(updates.keys())}")
    
    async def generate_llm_response(
        self, 
        prompt: str, 
        max_tokens: int = 100, 
        temperature: float = 0.7, 
        response_type: str = "status_summary"
    ) -> str:
        """
        Generate a response using the agent's LLM.
        
        Args:
            prompt: Prompt to send to the LLM
            max_tokens: Maximum number of tokens in the response
            temperature: Temperature parameter for generation
            response_type: Type of response template to use
            
        Returns:
            Generated response
        """
        return await self.llm_client.generate(
            prompt, 
            max_tokens=max_tokens, 
            temperature=temperature,
            response_type=response_type
        )