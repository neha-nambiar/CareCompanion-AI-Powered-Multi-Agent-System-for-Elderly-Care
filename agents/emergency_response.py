"""
Emergency Response Agent for the CareCompanion system.
Handles emergency situations and coordinates appropriate responses.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import random

from agents.base_agent import BaseAgent
from utils.logger import setup_logger
from utils.config import Config
from utils.database import db
from models.analytics import analyzer

class EmergencyResponseAgent(BaseAgent):
    """
    Agent responsible for handling emergency situations and coordinating responses.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Emergency Response Agent.
        
        Args:
            config: Configuration object
        """
        super().__init__(name="emergency_response", config=config)
        
        # Load emergency response settings from config
        self.response_time = config.get("agents.emergency_response.response_time", 10)  # seconds
        self.escalation_levels = config.get("agents.emergency_response.escalation_levels", {
            "1": "notify_app",
            "2": "notify_caregiver",
            "3": "notify_emergency_services"
        })
        
        # Initialize emergency data
        self.active_emergencies = {}
        self.emergency_history = {}
        self.emergency_contacts = {}
        
        # Track caregiver notifications
        self.caregiver_notifications = {}
    
    async def initialize(self) -> None:
        """
        Initialize the agent's state.
        """
        await super().initialize()
        
        # Load user data
        user_ids = analyzer.get_user_ids()
        for user_id in user_ids:
            await self._initialize_user_data(user_id)
        
        self.logger.info(f"Initialized emergency data for {len(user_ids)} users")
    
    async def _initialize_user_data(self, user_id: str) -> None:
        """
        Initialize data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        self.emergency_history[user_id] = []
        self.active_emergencies[user_id] = None
        
        # Create simulated emergency contacts
        self.emergency_contacts[user_id] = self._generate_simulated_contacts()
    
    def _generate_simulated_contacts(self) -> List[Dict[str, Any]]:
        """
        Generate simulated emergency contacts.
        
        Returns:
            List of contact dictionaries
        """
        contacts = [
            {
                "name": "Jane Smith",
                "relationship": "Daughter",
                "phone": "555-1234",
                "email": "jane.smith@example.com",
                "priority": 1,
                "notify_for": ["all"]
            },
            {
                "name": "Michael Johnson",
                "relationship": "Son",
                "phone": "555-5678",
                "email": "michael.johnson@example.com",
                "priority": 2,
                "notify_for": ["health", "fall"]
            },
            {
                "name": "Dr. Robert Williams",
                "relationship": "Physician",
                "phone": "555-9101",
                "email": "dr.williams@example.com",
                "priority": 3,
                "notify_for": ["health"]
            }
        ]
        
        return contacts
    
    async def update(self) -> None:
        """
        Perform periodic emergency status update.
        """
        await super().update()
        
        # Check active emergencies for status updates
        for user_id, emergency in list(self.active_emergencies.items()):
            if emergency is None:
                continue
            
            # Check if emergency has been resolved
            if emergency.get("resolved", False):
                # Move to history
                self.emergency_history[user_id].append(emergency)
                
                # Remove from active emergencies
                self.active_emergencies[user_id] = None
                
                self.logger.info(f"Emergency resolved for user {user_id}: {emergency.get('type')}")
                
                # Limit history size
                if len(self.emergency_history[user_id]) > 20:
                    self.emergency_history[user_id] = self.emergency_history[user_id][-20:]
            else:
                # Check if emergency needs escalation
                await self._check_emergency_escalation(user_id, emergency)
    
    async def _check_emergency_escalation(self, user_id: str, emergency: Dict[str, Any]) -> None:
        """
        Check if an emergency needs escalation.
        
        Args:
            user_id: ID of the user
            emergency: Emergency dictionary
        """
        now = datetime.now()
        created_time = datetime.fromisoformat(emergency.get("created_at", now.isoformat()))
        current_level = emergency.get("escalation_level", 1)
        last_escalation = datetime.fromisoformat(emergency.get("last_escalation", created_time.isoformat()))
        
        # Calculate minutes since last escalation
        minutes_since_escalation = (now - last_escalation).total_seconds() / 60
        
        # Check if we need to escalate
        # Level 1: Initial notification
        # Level 2: After 5 minutes with no response
        # Level 3: After 10 minutes with no response
        if current_level == 1 and minutes_since_escalation >= 5:
            self._escalate_emergency(user_id, emergency, 2)
        elif current_level == 2 and minutes_since_escalation >= 5:
            self._escalate_emergency(user_id, emergency, 3)
    
    def _escalate_emergency(self, user_id: str, emergency: Dict[str, Any], new_level: int) -> None:
        """
        Escalate an emergency to a higher level.
        
        Args:
            user_id: ID of the user
            emergency: Emergency dictionary
            new_level: New escalation level
        """
        emergency["escalation_level"] = new_level
        emergency["last_escalation"] = datetime.now().isoformat()
        
        # Perform escalation action
        action = self.escalation_levels.get(str(new_level), "notify_app")
        
        if action == "notify_caregiver":
            self._notify_caregivers(user_id, emergency, urgent=True)
        elif action == "notify_emergency_services":
            self._notify_emergency_services(user_id, emergency)
        
        self.logger.info(f"Escalated emergency for user {user_id} to level {new_level}: {emergency.get('type')}")
    
    def _notify_caregivers(self, user_id: str, emergency: Dict[str, Any], urgent: bool = False) -> None:
        """
        Notify caregivers about an emergency.
        
        Args:
            user_id: ID of the user
            emergency: Emergency dictionary
            urgent: Whether this is an urgent notification
        """
        # Get emergency type to determine which caregivers to notify
        emergency_type = emergency.get("type", "unknown")
        
        # Get contacts for this user
        contacts = self.emergency_contacts.get(user_id, [])
        
        # Filter contacts by notification preferences
        if emergency_type == "fall":
            notify_contacts = [c for c in contacts if "all" in c.get("notify_for", []) or "fall" in c.get("notify_for", [])]
        elif emergency_type == "health":
            notify_contacts = [c for c in contacts if "all" in c.get("notify_for", []) or "health" in c.get("notify_for", [])]
        else:
            notify_contacts = [c for c in contacts if "all" in c.get("notify_for", [])]
        
        # Sort by priority
        notify_contacts.sort(key=lambda c: c.get("priority", 999))
        
        # Record notification
        notification_id = f"{user_id}_{emergency.get('id')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        notification = {
            "id": notification_id,
            "user_id": user_id,
            "emergency_id": emergency.get("id"),
            "timestamp": datetime.now().isoformat(),
            "contacts": [c.get("name") for c in notify_contacts],
            "urgent": urgent,
            "message": self._generate_notification_message(emergency, urgent)
        }
        
        # Store in caregiver notifications
        if user_id not in self.caregiver_notifications:
            self.caregiver_notifications[user_id] = []
        
        self.caregiver_notifications[user_id].append(notification)
        
        # Store in database
        db.insert("events", {
            "user_id": user_id,
            "event_type": "caregiver_notification",
            "details": notification
        })
        
        self.logger.info(
            f"Notified {len(notify_contacts)} caregivers for user {user_id}: "
            f"{', '.join([c.get('name') for c in notify_contacts])}"
        )
    
    def _notify_emergency_services(self, user_id: str, emergency: Dict[str, Any]) -> None:
        """
        Simulate notifying emergency services.
        
        Args:
            user_id: ID of the user
            emergency: Emergency dictionary
        """
        # Record emergency service notification
        notification = {
            "id": f"{user_id}_{emergency.get('id')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "emergency_id": emergency.get("id"),
            "timestamp": datetime.now().isoformat(),
            "service": "emergency_medical_services",
            "message": self._generate_emergency_service_message(emergency)
        }
        
        # Store in database
        db.insert("events", {
            "user_id": user_id,
            "event_type": "emergency_services_notification",
            "details": notification
        })
        
        self.logger.info(f"Notified emergency services for user {user_id}: {emergency.get('type')}")
    
    def _generate_notification_message(self, emergency: Dict[str, Any], urgent: bool = False) -> str:
        """
        Generate a notification message for caregivers.
        
        Args:
            emergency: Emergency dictionary
            urgent: Whether this is an urgent notification
            
        Returns:
            Notification message
        """
        emergency_type = emergency.get("type", "unknown")
        user_id = emergency.get("user_id", "unknown")
        timestamp = datetime.fromisoformat(emergency.get("created_at", datetime.now().isoformat()))
        
        prefix = "URGENT: " if urgent else ""
        
        if emergency_type == "fall":
            return f"{prefix}Fall detected for {user_id} at {timestamp.strftime('%H:%M')} in {emergency.get('location', 'unknown')}. Please respond immediately."
        elif emergency_type == "health":
            return f"{prefix}Health emergency for {user_id}: {emergency.get('details', 'No details')}. Please respond immediately."
        else:
            return f"{prefix}Emergency for {user_id}: {emergency.get('details', 'No details')}. Please respond immediately."
    
    def _generate_emergency_service_message(self, emergency: Dict[str, Any]) -> str:
        """
        Generate a message for emergency services.
        
        Args:
            emergency: Emergency dictionary
            
        Returns:
            Emergency service message
        """
        emergency_type = emergency.get("type", "unknown")
        user_id = emergency.get("user_id", "unknown")
        
        if emergency_type == "fall":
            return f"Fall emergency for elderly patient ID {user_id}. Location: {emergency.get('location', 'unknown')}. No response to caregiver notifications."
        elif emergency_type == "health":
            return f"Health emergency for elderly patient ID {user_id}. Issue: {emergency.get('details', 'No details')}. No response to caregiver notifications."
        else:
            return f"Emergency situation for elderly patient ID {user_id}. Issue: {emergency.get('details', 'No details')}. No response to caregiver notifications."
    
    async def handle_emergency(self, emergency_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming emergency alert.
        
        Args:
            emergency_data: Dictionary containing emergency data
            
        Returns:
            Processing results
        """
        user_id = emergency_data.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing user_id in emergency data"
            }
        
        # Initialize user data if needed
        if user_id not in self.active_emergencies:
            await self._initialize_user_data(user_id)
        
        # Create emergency record
        now = datetime.now()
        emergency_id = f"{user_id}_{emergency_data.get('type', 'unknown')}_{now.strftime('%Y%m%d%H%M%S')}"
        
        emergency = {
            "id": emergency_id,
            "user_id": user_id,
            "type": emergency_data.get("type", "unknown"),
            "details": emergency_data.get("details", {}),
            "location": emergency_data.get("location", "unknown"),
            "created_at": now.isoformat(),
            "last_escalation": now.isoformat(),
            "escalation_level": 1,
            "resolved": False,
            "resolution_details": None,
            "resolution_time": None
        }
        
        # Check if there's already an active emergency
        if self.active_emergencies[user_id] is not None:
            # If it's the same type, update it
            if self.active_emergencies[user_id]["type"] == emergency["type"]:
                # Add new information but keep escalation status
                emergency["escalation_level"] = self.active_emergencies[user_id]["escalation_level"]
                emergency["last_escalation"] = self.active_emergencies[user_id]["last_escalation"]
                
                self.active_emergencies[user_id] = emergency
                
                self.logger.info(f"Updated emergency for user {user_id}: {emergency['type']}")
            else:
                # Different type, resolve old one and create new
                old_emergency = self.active_emergencies[user_id]
                old_emergency["resolved"] = True
                old_emergency["resolution_details"] = "Superseded by new emergency"
                old_emergency["resolution_time"] = now.isoformat()
                
                self.emergency_history[user_id].append(old_emergency)
                self.active_emergencies[user_id] = emergency
                
                self.logger.info(
                    f"Superseded emergency for user {user_id}: "
                    f"{old_emergency['type']} -> {emergency['type']}"
                )
        else:
            # No active emergency, create new one
            self.active_emergencies[user_id] = emergency
            
            self.logger.info(f"Created new emergency for user {user_id}: {emergency['type']}")
        
        # Store in database
        db.insert("events", {
            "user_id": user_id,
            "event_type": "emergency_created",
            "details": emergency
        })
        
        # Perform initial response
        await self._initial_emergency_response(user_id, emergency)
        
        # Generate LLM analysis
        analysis = await self._generate_emergency_analysis(user_id, emergency)
        
        return {
            "status": "success",
            "user_id": user_id,
            "emergency": emergency,
            "analysis": analysis,
            "message": f"Emergency {emergency_id} created and initial response taken"
        }
    
    async def _initial_emergency_response(self, user_id: str, emergency: Dict[str, Any]) -> None:
        """
        Perform initial emergency response actions.
        
        Args:
            user_id: ID of the user
            emergency: Emergency dictionary
        """
        # Notify caregivers
        self._notify_caregivers(user_id, emergency)
        
        # Get additional context from other agents if available
        # In a full implementation, this would query other agents for context
        
        # For serious emergencies, escalate immediately
        emergency_type = emergency.get("type", "unknown")
        if emergency_type == "fall" and emergency.get("details", {}).get("impact_force_level", "medium") == "high":
            self._escalate_emergency(user_id, emergency, 2)
        elif emergency_type == "health" and "critical" in str(emergency.get("details", {})).lower():
            self._escalate_emergency(user_id, emergency, 2)
    
    async def _generate_emergency_analysis(self, user_id: str, emergency: Dict[str, Any]) -> str:
        """
        Generate an LLM analysis of the emergency.
        
        Args:
            user_id: ID of the user
            emergency: Emergency dictionary
            
        Returns:
            LLM analysis string
        """
        emergency_type = emergency.get("type", "unknown")
        details = json.dumps(emergency.get("details", {}))
        location = emergency.get("location", "unknown")
        
        prompt = f"""
        Please analyze the following emergency situation for user {user_id}:
        
        Emergency type: {emergency_type}
        Location: {location}
        Details: {details}
        
        Please provide:
        1. A brief assessment of the severity of the emergency
        2. Potential causes and contributing factors
        3. Recommended immediate actions
        4. Follow-up measures to prevent recurrence
        """
        
        # Generate response
        return await self.generate_llm_response(
            prompt,
            max_tokens=200,
            temperature=0.7,
            response_type="emergency_analysis"
        )
    
    async def resolve_emergency(
        self, 
        user_id: str, 
        emergency_id: Optional[str] = None, 
        resolution_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resolve an active emergency.
        
        Args:
            user_id: ID of the user
            emergency_id: Optional ID of the emergency to resolve (if None, resolves any active emergency)
            resolution_details: Optional details about the resolution
            
        Returns:
            Resolution status
        """
        if user_id not in self.active_emergencies or self.active_emergencies[user_id] is None:
            return {
                "status": "error",
                "message": f"No active emergency found for user {user_id}"
            }
        
        active_emergency = self.active_emergencies[user_id]
        
        # Check if emergency ID matches
        if emergency_id and active_emergency["id"] != emergency_id:
            return {
                "status": "error",
                "message": f"Emergency ID {emergency_id} does not match active emergency {active_emergency['id']}"
            }
        
        # Resolve emergency
        now = datetime.now()
        active_emergency["resolved"] = True
        active_emergency["resolution_time"] = now.isoformat()
        
        if resolution_details:
            active_emergency["resolution_details"] = resolution_details
        else:
            active_emergency["resolution_details"] = {"note": "Manually resolved"}
        
        # Move to history
        self.emergency_history[user_id].append(active_emergency)
        
        # Clear active emergency
        self.active_emergencies[user_id] = None
        
        # Store resolution in database
        db.insert("events", {
            "user_id": user_id,
            "event_type": "emergency_resolved",
            "details": {
                "emergency_id": active_emergency["id"],
                "resolution_time": now.isoformat(),
                "resolution_details": active_emergency["resolution_details"]
            }
        })
        
        self.logger.info(f"Resolved emergency for user {user_id}: {active_emergency['id']}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "emergency": active_emergency,
            "message": f"Emergency {active_emergency['id']} resolved successfully"
        }
    
    async def get_emergency_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get the current emergency status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing emergency status
        """
        if user_id not in self.active_emergencies:
            await self._initialize_user_data(user_id)
        
        active_emergency = self.active_emergencies[user_id]
        
        # Get recent emergency history
        recent_history = []
        if user_id in self.emergency_history:
            recent_history = self.emergency_history[user_id][-5:]  # Last 5 emergencies
        
        # Get recent notifications
        recent_notifications = []
        if user_id in self.caregiver_notifications:
            recent_notifications = self.caregiver_notifications[user_id][-5:]  # Last 5 notifications
        
        return {
            "status": "success",
            "user_id": user_id,
            "active_emergency": active_emergency,
            "recent_history": recent_history,
            "recent_notifications": recent_notifications,
            "emergency_contacts": self.emergency_contacts.get(user_id, [])
        }
    
    async def update_emergency_contacts(
        self, 
        user_id: str, 
        contacts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update emergency contacts for a user.
        
        Args:
            user_id: ID of the user
            contacts: List of contact dictionaries
            
        Returns:
            Updated contacts
        """
        if user_id not in self.emergency_contacts:
            await self._initialize_user_data(user_id)
        
        # Validate contacts
        valid_contacts = []
        for contact in contacts:
            if "name" in contact and "phone" in contact:
                # Ensure required fields
                if "priority" not in contact:
                    contact["priority"] = 999
                
                if "notify_for" not in contact:
                    contact["notify_for"] = ["all"]
                
                valid_contacts.append(contact)
        
        # Update contacts
        self.emergency_contacts[user_id] = valid_contacts
        
        # Sort by priority
        self.emergency_contacts[user_id].sort(key=lambda c: c.get("priority", 999))
        
        self.logger.info(f"Updated emergency contacts for user {user_id}: {len(valid_contacts)} contacts")
        
        return {
            "status": "success",
            "user_id": user_id,
            "contacts": self.emergency_contacts[user_id]
        }
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message received by the agent.
        
        Args:
            message: Message to process
            
        Returns:
            Response to the message
        """
        message_type = message.get("type", "unknown")
        
        if message_type == "emergency":
            user_id = message.get("user_id")
            emergency_data = message.get("emergency_data", {})
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in emergency request"
                }
            
            return await self.handle_emergency({
                "user_id": user_id,
                **emergency_data
            })
        
        elif message_type == "alert":
            user_id = message.get("user_id")
            alert = message.get("alert", {})
            context = message.get("context", {})
            
            if not user_id or not alert:
                return {
                    "status": "error",
                    "message": "Missing user_id or alert in alert request"
                }
            
            # Convert alert to emergency
            emergency_type = "unknown"
            details = {}
            
            if "type" in alert:
                if "fall" in alert["type"]:
                    emergency_type = "fall"
                    details = {
                        "location": context.get("current_location", "unknown"),
                        "impact_force_level": alert.get("impact_force", "medium"),
                        "source": alert.get("source", "unknown")
                    }
                elif any(health_term in alert["type"] for health_term in ["heart", "blood", "glucose", "oxygen"]):
                    emergency_type = "health"
                    details = {
                        "metric": alert.get("type", "unknown"),
                        "value": alert.get("value", "unknown"),
                        "threshold": alert.get("threshold", "unknown"),
                        "source": alert.get("source", "unknown")
                    }
            
            return await self.handle_emergency({
                "user_id": user_id,
                "type": emergency_type,
                "details": details,
                "location": context.get("current_location", "unknown")
            })
        
        elif message_type == "resolve_emergency":
            user_id = message.get("user_id")
            emergency_id = message.get("emergency_id")
            resolution_details = message.get("resolution_details")
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in resolve_emergency request"
                }
            
            return await self.resolve_emergency(user_id, emergency_id, resolution_details)
        
        elif message_type == "get_status":
            user_id = message.get("user_id")
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in get_status request"
                }
            
            return await self.get_emergency_status(user_id)
        
        elif message_type == "update_contacts":
            user_id = message.get("user_id")
            contacts = message.get("contacts", [])
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in update_contacts request"
                }
            
            return await self.update_emergency_contacts(user_id, contacts)
        
        else:
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }
