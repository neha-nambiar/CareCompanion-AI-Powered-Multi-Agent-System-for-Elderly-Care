"""
Simulated LLM client for the CareCompanion system.
Since we don't have actual access to Ollama models, this simulates responses.
"""

import time
import random
from typing import Dict, Any, List, Optional

from utils.logger import setup_logger
from utils.config import config

logger = setup_logger("llm_client")

class OllamaClient:
    """
    Simulated Ollama LLM client for the CareCompanion system.
    """
    
    def __init__(self, model_name: str = "Gemma-2B"):
        """
        Initialize the Ollama client.
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
        logger.info(f"Initialized OllamaClient with model: {model_name}")
        
        # Templates for different types of responses
        self.response_templates = {
            # Health analysis templates
            "health_analysis": [
                "Based on the vital signs, the user's health status appears {condition}. {specific_insight}",
                "Analysis of health metrics indicates {condition} status. {specific_insight}",
                "Health metrics evaluation shows {condition} patterns. {specific_insight}"
            ],
            
            # Safety analysis templates
            "safety_analysis": [
                "The user's movement patterns are {condition}. {specific_insight}",
                "Safety assessment indicates {condition} situation. {specific_insight}",
                "Activity analysis shows {condition} behavior. {specific_insight}"
            ],
            
            # Reminder analysis templates
            "reminder_analysis": [
                "The user's reminder compliance is {condition}. {specific_insight}",
                "Reminder adherence analysis indicates {condition} patterns. {specific_insight}",
                "Assessment of reminder responses shows {condition} trends. {specific_insight}"
            ],
            
            # Emergency analysis templates
            "emergency_analysis": [
                "Emergency situation detected: {specific_insight} Recommended action: {action}",
                "URGENT: {specific_insight} Immediate response required. {action}",
                "Critical alert: {specific_insight} Please take immediate action: {action}"
            ],
            
            # General status templates
            "status_summary": [
                "Overall user status is {condition}. {specific_insight}",
                "User well-being assessment: {condition}. {specific_insight}",
                "Current status evaluation: {condition}. {specific_insight}"
            ]
        }
    
    async def generate(self, prompt: str, max_tokens: int = 100, 
                      temperature: float = 0.7, response_type: str = "status_summary") -> str:
        """
        Generate a response using the simulated LLM.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens in the response
            temperature: Temperature parameter for generation
            response_type: Type of response template to use
            
        Returns:
            Generated response
        """
        logger.debug(f"Generating response for prompt: {prompt[:50]}...")
        
        # Simulate processing time based on model size and prompt length
        process_time = 0.1 + (len(prompt) * 0.001) + random.uniform(0.1, 0.5)
        time.sleep(process_time)
        
        # Extract keywords from prompt to use in response
        keywords = self._extract_keywords(prompt)
        
        # Generate a simulated response based on the prompt and keywords
        response = self._generate_simulated_response(keywords, response_type)
        
        # Truncate to max tokens (approximated by characters)
        max_chars = max_tokens * 4  # Rough approximation
        if len(response) > max_chars:
            response = response[:max_chars] + "..."
        
        logger.debug(f"Generated response: {response[:50]}...")
        return response
    
    def _extract_keywords(self, prompt: str) -> Dict[str, Any]:
        """
        Extract relevant keywords from the prompt.
        This is a simplified simulation.
        
        Args:
            prompt: The prompt to analyze
            
        Returns:
            Dictionary of extracted keywords/values
        """
        keywords = {
            "condition": "normal",
            "specific_insight": "",
            "action": ""
        }
        
        # Extract condition based on keywords in the prompt
        if "emergency" in prompt.lower() or "urgent" in prompt.lower() or "critical" in prompt.lower():
            keywords["condition"] = "critical"
        elif "warning" in prompt.lower() or "concerning" in prompt.lower():
            keywords["condition"] = "concerning"
        elif "good" in prompt.lower() or "normal" in prompt.lower() or "stable" in prompt.lower():
            keywords["condition"] = "normal"
        else:
            keywords["condition"] = random.choice(["normal", "stable", "good", "concerning", "irregular"])
        
        # Generate specific insights based on prompt content
        if "heart rate" in prompt.lower() or "pulse" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Heart rate is significantly elevated and requires immediate attention."
                keywords["action"] = "Contact healthcare provider immediately."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Heart rate shows irregular patterns that should be monitored closely."
                keywords["action"] = "Schedule a check-up within the next few days."
            else:
                keywords["specific_insight"] = "Heart rate is within normal range for the user's profile."
                keywords["action"] = "Continue routine monitoring."
        
        elif "blood pressure" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Blood pressure is dangerously high, indicating possible hypertensive crisis."
                keywords["action"] = "Seek emergency medical attention."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Blood pressure is elevated above the user's normal range."
                keywords["action"] = "Ensure medication compliance and reduce sodium intake."
            else:
                keywords["specific_insight"] = "Blood pressure readings are consistent with the user's baseline."
                keywords["action"] = "Maintain current management plan."
        
        elif "glucose" in prompt.lower() or "sugar" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Glucose levels indicate possible hypoglycemia or hyperglycemia."
                keywords["action"] = "Check glucose again and follow emergency protocol if confirmed."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Glucose readings show fluctuations outside the target range."
                keywords["action"] = "Review insulin dosing and meal schedule."
            else:
                keywords["specific_insight"] = "Glucose levels are well-controlled."
                keywords["action"] = "Continue current management approach."
        
        elif "fall" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "A serious fall has been detected with possible injury."
                keywords["action"] = "Initiate emergency response protocol immediately."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "A minor fall occurred but the user appears to have recovered."
                keywords["action"] = "Check in with the user to assess any potential injuries."
            else:
                keywords["specific_insight"] = "No falls detected in the monitoring period."
                keywords["action"] = "Continue fall prevention measures."
        
        elif "movement" in prompt.lower() or "activity" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Prolonged inactivity detected in an unusual location."
                keywords["action"] = "Perform a wellness check immediately."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Movement patterns show decreased mobility compared to baseline."
                keywords["action"] = "Encourage light physical activity and monitor for improvement."
            else:
                keywords["specific_insight"] = "Activity levels are consistent with the user's normal routine."
                keywords["action"] = "Maintain current activity recommendations."
        
        elif "reminder" in prompt.lower() or "medication" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Critical medication doses have been missed repeatedly."
                keywords["action"] = "Contact caregiver to ensure medication compliance."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Occasional missed medication doses observed."
                keywords["action"] = "Adjust reminder timing or method to improve adherence."
            else:
                keywords["specific_insight"] = "Medication adherence is excellent with consistent acknowledgment."
                keywords["action"] = "Continue current reminder schedule."
        
        elif "social" in prompt.lower() or "isolation" in prompt.lower():
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Severe social isolation detected with minimal interaction over an extended period."
                keywords["action"] = "Schedule a social visit and assess mental health status."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Declining social engagement compared to previous patterns."
                keywords["action"] = "Suggest video calls with family or community activities."
            else:
                keywords["specific_insight"] = "Social interaction frequency is healthy and regular."
                keywords["action"] = "Continue encouraging social engagement activities."
        
        else:
            # Default insights for general status
            if keywords["condition"] == "critical":
                keywords["specific_insight"] = "Multiple health and safety concerns require immediate attention."
                keywords["action"] = "Contact primary caregiver and healthcare provider."
            elif keywords["condition"] == "concerning":
                keywords["specific_insight"] = "Some parameters are outside normal ranges and should be monitored."
                keywords["action"] = "Increase monitoring frequency and reassess in 24 hours."
            else:
                keywords["specific_insight"] = "All monitoring parameters are within acceptable ranges."
                keywords["action"] = "Continue routine monitoring protocol."
        
        return keywords
    
    def _generate_simulated_response(self, keywords: Dict[str, Any], response_type: str) -> str:
        """
        Generate a simulated response using templates and extracted keywords.
        
        Args:
            keywords: Dictionary of keywords to include in the response
            response_type: Type of response template to use
            
        Returns:
            Generated response string
        """
        # Get templates for the specified response type
        templates = self.response_templates.get(
            response_type, 
            self.response_templates["status_summary"]
        )
        
        # Select a random template
        template = random.choice(templates)
        
        # Fill in the template with keywords
        response = template.format(**keywords)
        
        # Add more context based on condition
        if keywords["condition"] in ["critical", "concerning"]:
            response += f" {keywords['action']}"
        
        return response