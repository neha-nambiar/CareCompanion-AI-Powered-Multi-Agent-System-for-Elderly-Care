"""
Coordination Agent for the CareCompanion system.
Orchestrates all other agents and manages overall system state.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from agents.health_monitor import HealthMonitorAgent
from agents.safety_guardian import SafetyGuardianAgent
from agents.daily_assistant import DailyAssistantAgent
from agents.social_engagement import SocialEngagementAgent
from agents.emergency_response import EmergencyResponseAgent
from utils.logger import setup_logger
from utils.config import Config
from utils.database import db
from models.analytics import analyzer

class CoordinationAgent(BaseAgent):
    """
    Agent responsible for coordinating all other agents and managing system state.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Coordination Agent.
        
        Args:
            config: Configuration object
        """
        super().__init__(name="coordination", config=config)
        
        # References to other agents (will be set later)
        self.health_agent: Optional[HealthMonitorAgent] = None
        self.safety_agent: Optional[SafetyGuardianAgent] = None
        self.daily_agent: Optional[DailyAssistantAgent] = None
        self.social_agent: Optional[SocialEngagementAgent] = None
        self.emergency_agent: Optional[EmergencyResponseAgent] = None
        
        # User context data
        self.user_contexts = {}
        
        # System state
        self.system_state = {
            "started_at": datetime.now().isoformat(),
            "active_users": 0,
            "active_alerts": 0,
            "active_emergencies": 0
        }
        
        # Cache for expensive operations
        self.cache = {}
        self.cache_expiry = {}
    
    def set_agents(
        self, 
        health_agent: HealthMonitorAgent,
        safety_agent: SafetyGuardianAgent,
        daily_agent: DailyAssistantAgent,
        social_agent: SocialEngagementAgent,
        emergency_agent: EmergencyResponseAgent
    ) -> None:
        """
        Set references to all other agents.
        
        Args:
            health_agent: Health Monitor Agent
            safety_agent: Safety Guardian Agent
            daily_agent: Daily Assistant Agent
            social_agent: Social Engagement Agent
            emergency_agent: Emergency Response Agent
        """
        self.health_agent = health_agent
        self.safety_agent = safety_agent
        self.daily_agent = daily_agent
        self.social_agent = social_agent
        self.emergency_agent = emergency_agent
        
        self.logger.info("All agent references set")
    
    async def initialize(self) -> None:
        """
        Initialize the agent's state.
        """
        await super().initialize()
        
        # Load user data
        user_ids = analyzer.get_user_ids()
        for user_id in user_ids:
            await self._initialize_user_context(user_id)
        
        self.system_state["active_users"] = len(user_ids)
        
        self.logger.info(f"Initialized context for {len(user_ids)} users")
    
    async def _initialize_user_context(self, user_id: str) -> None:
        """
        Initialize context data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        self.user_contexts[user_id] = {
            "user_id": user_id,
            "name": f"User {user_id}",  # Default name
            "last_update": datetime.now().isoformat(),
            "health_status": "unknown",
            "safety_status": "unknown",
            "reminder_status": "unknown",
            "social_status": "unknown",
            "emergency_status": "none",
            "current_location": "unknown",
            "current_activity": "unknown",
            "alerts": [],
            "recommendations": []
        }
        
        # Get comprehensive user status from analyzer
        status = analyzer.get_comprehensive_user_status(user_id)
        
        if status:
            # Update context with status data
            if status.get("health"):
                self.user_contexts[user_id]["health_status"] = status["health"].get("health_status", "unknown")
            
            if status.get("safety"):
                self.user_contexts[user_id]["safety_status"] = status["safety"].get("safety_status", "unknown")
                self.user_contexts[user_id]["current_location"] = status["safety"].get("current_location", "unknown")
                self.user_contexts[user_id]["current_activity"] = status["safety"].get("current_activity", "unknown")
            
            if status.get("reminders"):
                self.user_contexts[user_id]["reminder_status"] = status["reminders"].get("reminder_status", "unknown")
            
            self.user_contexts[user_id]["overall_status"] = status.get("overall_status", "unknown")
    
    async def update(self) -> None:
        """
        Perform periodic coordination update.
        """
        await super().update()
        
        # Update system state
        self.system_state["active_users"] = len(self.user_contexts)
        
        # Count active alerts and emergencies
        active_alerts = 0
        active_emergencies = 0
        
        for user_id, context in self.user_contexts.items():
            active_alerts += len(context.get("alerts", []))
            if context.get("emergency_status") != "none":
                active_emergencies += 1
        
        self.system_state["active_alerts"] = active_alerts
        self.system_state["active_emergencies"] = active_emergencies
        
        # Update user contexts
        for user_id in self.user_contexts.keys():
            # Check if context update is needed (once per minute)
            last_update = datetime.fromisoformat(self.user_contexts[user_id].get("last_update", datetime.min.isoformat()))
            if (datetime.now() - last_update).total_seconds() > 60:
                await self._update_user_context(user_id)
    
    async def _update_user_context(self, user_id: str) -> None:
        """
        Update context data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        # Update health status
        if self.health_agent:
            try:
                health_status = await self.health_agent.get_health_status(user_id)
                if health_status.get("status") == "success":
                    self.user_contexts[user_id]["health_status"] = health_status["analysis"].get("health_status", "unknown")
                    
                    # Add health alerts
                    for alert in health_status.get("alerts", []):
                        if alert not in self.user_contexts[user_id]["alerts"]:
                            self.user_contexts[user_id]["alerts"].append(alert)
            except Exception as e:
                self.logger.error(f"Error updating health status for user {user_id}: {e}")
        
        # Update safety status
        if self.safety_agent:
            try:
                safety_status = await self.safety_agent.get_safety_status(user_id)
                if safety_status.get("status") == "success":
                    self.user_contexts[user_id]["safety_status"] = safety_status["analysis"].get("safety_status", "unknown")
                    self.user_contexts[user_id]["current_location"] = safety_status["analysis"].get("current_location", "unknown")
                    self.user_contexts[user_id]["current_activity"] = safety_status["analysis"].get("current_activity", "unknown")
                    
                    # Add safety alerts
                    for alert in safety_status.get("alerts", []):
                        if alert not in self.user_contexts[user_id]["alerts"]:
                            self.user_contexts[user_id]["alerts"].append(alert)
            except Exception as e:
                self.logger.error(f"Error updating safety status for user {user_id}: {e}")
        
        # Update reminder status
        if self.daily_agent:
            try:
                reminder_status = await self.daily_agent.get_reminder_status(user_id)
                if reminder_status.get("status") == "success":
                    self.user_contexts[user_id]["reminder_status"] = reminder_status["analysis"].get("reminder_status", "unknown")
                    
                    # Add recommendations
                    for rec in reminder_status.get("recommendations", []):
                        if rec not in self.user_contexts[user_id]["recommendations"]:
                            self.user_contexts[user_id]["recommendations"].append(rec)
            except Exception as e:
                self.logger.error(f"Error updating reminder status for user {user_id}: {e}")
        
        # Update social status
        if self.social_agent:
            try:
                social_status = await self.social_agent.get_social_status(user_id)
                if social_status.get("status") == "success":
                    self.user_contexts[user_id]["social_status"] = social_status["analysis"].get("social_status", "unknown")
                    
                    # Add social alerts
                    for alert in social_status.get("alerts", []):
                        if alert not in self.user_contexts[user_id]["alerts"]:
                            self.user_contexts[user_id]["alerts"].append(alert)
            except Exception as e:
                self.logger.error(f"Error updating social status for user {user_id}: {e}")
        
        # Update emergency status
        if self.emergency_agent:
            try:
                emergency_status = await self.emergency_agent.get_emergency_status(user_id)
                if emergency_status.get("status") == "success":
                    if emergency_status.get("active_emergency"):
                        self.user_contexts[user_id]["emergency_status"] = emergency_status["active_emergency"].get("type", "unknown")
                    else:
                        self.user_contexts[user_id]["emergency_status"] = "none"
            except Exception as e:
                self.logger.error(f"Error updating emergency status for user {user_id}: {e}")
        
        # Update overall status based on all components
        self.user_contexts[user_id]["overall_status"] = self._determine_overall_status(user_id)
        
        # Update timestamp
        self.user_contexts[user_id]["last_update"] = datetime.now().isoformat()
    
    def _determine_overall_status(self, user_id: str) -> str:
        """
        Determine overall status based on all component statuses.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Overall status string
        """
        context = self.user_contexts.get(user_id, {})
        
        # Check for emergency
        if context.get("emergency_status", "none") != "none":
            return "emergency"
        
        # Check component statuses
        statuses = [
            context.get("health_status", "unknown"),
            context.get("safety_status", "unknown"),
            context.get("reminder_status", "unknown"),
            context.get("social_status", "unknown")
        ]
        
        if "alert" in statuses:
            return "alert"
        elif "attention" in statuses:
            return "attention"
        elif all(status == "normal" for status in statuses if status != "unknown"):
            return "normal"
        else:
            return "unknown"
    
    async def handle_incoming_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming data from sensors or other sources.
        
        Args:
            data: Dictionary containing incoming data
            
        Returns:
            Processing results
        """
        data_type = data.get("type", "unknown")
        user_id = data.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing user_id in incoming data"
            }
        
        # Initialize user context if needed
        if user_id not in self.user_contexts:
            await self._initialize_user_context(user_id)
        
        # Process based on data type
        try:
            if data_type == "health":
                return await self._process_health_data(user_id, data)
            
            elif data_type == "safety":
                return await self._process_safety_data(user_id, data)
            
            elif data_type == "reminder":
                return await self._process_reminder_data(user_id, data)
            
            elif data_type == "social":
                return await self._process_social_data(user_id, data)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown data type: {data_type}"
                }
        
        except Exception as e:
            self.logger.error(f"Error processing {data_type} data for user {user_id}: {e}")
            return {
                "status": "error",
                "message": f"Error processing data: {str(e)}"
            }
    
    async def _process_health_data(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process health data by forwarding to Health Monitor Agent.
        
        Args:
            user_id: ID of the user
            data: Health data dictionary
            
        Returns:
            Processing results
        """
        if not self.health_agent:
            return {
                "status": "error",
                "message": "Health Monitor Agent not initialized"
            }
        
        # Forward to Health Monitor Agent
        result = await self.health_agent.process_message({
            "type": "health_data",
            "data": {
                "user_id": user_id,
                **data.get("data", {})
            }
        })
        
        # Update user context
        if result.get("status") == "success":
            # Update health status
            if "analysis" in result and "health_status" in result["analysis"]:
                self.user_contexts[user_id]["health_status"] = result["analysis"]["health_status"]
            
            # Add alerts
            for alert in result.get("alerts", []):
                if alert not in self.user_contexts[user_id]["alerts"]:
                    self.user_contexts[user_id]["alerts"].append(alert)
            
            # Check for emergencies
            urgent_alerts = [a for a in result.get("alerts", []) if a.get("level") == "urgent"]
            
            if urgent_alerts and self.emergency_agent:
                # Forward to Emergency Response Agent
                for alert in urgent_alerts:
                    await self.emergency_agent.process_message({
                        "type": "alert",
                        "user_id": user_id,
                        "alert": alert,
                        "context": self.user_contexts[user_id]
                    })
            
            # Update overall status
            self.user_contexts[user_id]["overall_status"] = self._determine_overall_status(user_id)
            self.user_contexts[user_id]["last_update"] = datetime.now().isoformat()
        
        return result
    
    async def _process_safety_data(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process safety data by forwarding to Safety Guardian Agent.
        
        Args:
            user_id: ID of the user
            data: Safety data dictionary
            
        Returns:
            Processing results
        """
        if not self.safety_agent:
            return {
                "status": "error",
                "message": "Safety Guardian Agent not initialized"
            }
        
        # Forward to Safety Guardian Agent
        result = await self.safety_agent.process_message({
            "type": "safety_data",
            "data": {
                "user_id": user_id,
                **data.get("data", {})
            }
        })
        
        # Update user context
        if result.get("status") == "success":
            # Update safety status
            if "analysis" in result and "safety_status" in result["analysis"]:
                self.user_contexts[user_id]["safety_status"] = result["analysis"]["safety_status"]
            
            # Update location and activity
            if "analysis" in result:
                if "current_location" in result["analysis"]:
                    self.user_contexts[user_id]["current_location"] = result["analysis"]["current_location"]
                
                if "current_activity" in result["analysis"]:
                    self.user_contexts[user_id]["current_activity"] = result["analysis"]["current_activity"]
            
            # Add alerts
            for alert in result.get("alerts", []):
                if alert not in self.user_contexts[user_id]["alerts"]:
                    self.user_contexts[user_id]["alerts"].append(alert)
            
            # Check for emergencies
            if result.get("emergency", False) and self.emergency_agent:
                # Forward to Emergency Response Agent
                emergency_data = {
                    "type": "fall" if data.get("data", {}).get("fall_detected", "No") == "Yes" else "safety",
                    "details": data.get("data", {}),
                    "location": data.get("data", {}).get("location", "unknown")
                }
                
                await self.emergency_agent.process_message({
                    "type": "emergency",
                    "user_id": user_id,
                    "emergency_data": emergency_data
                })
            
            # Update overall status
            self.user_contexts[user_id]["overall_status"] = self._determine_overall_status(user_id)
            self.user_contexts[user_id]["last_update"] = datetime.now().isoformat()
        
        return result
    
    async def _process_reminder_data(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process reminder data by forwarding to Daily Assistant Agent.
        
        Args:
            user_id: ID of the user
            data: Reminder data dictionary
            
        Returns:
            Processing results
        """
        if not self.daily_agent:
            return {
                "status": "error",
                "message": "Daily Assistant Agent not initialized"
            }
        
        # Forward to Daily Assistant Agent
        result = await self.daily_agent.process_message({
            "type": "reminder_data",
            "data": {
                "user_id": user_id,
                **data.get("data", {})
            }
        })
        
        # Update user context
        if result.get("status") == "success":
            # Update reminder status
            if "analysis" in result and "reminder_status" in result["analysis"]:
                self.user_contexts[user_id]["reminder_status"] = result["analysis"]["reminder_status"]
            
            # Add recommendations
            for rec in result.get("recommendations", []):
                if rec not in self.user_contexts[user_id]["recommendations"]:
                    self.user_contexts[user_id]["recommendations"].append(rec)
            
            # Update overall status
            self.user_contexts[user_id]["overall_status"] = self._determine_overall_status(user_id)
            self.user_contexts[user_id]["last_update"] = datetime.now().isoformat()
        
        return result
    
    async def _process_social_data(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process social data by forwarding to Social Engagement Agent.
        
        Args:
            user_id: ID of the user
            data: Social data dictionary
            
        Returns:
            Processing results
        """
        if not self.social_agent:
            return {
                "status": "error",
                "message": "Social Engagement Agent not initialized"
            }
        
        # Forward to Social Engagement Agent
        result = await self.social_agent.process_message({
            "type": "social_data",
            "data": {
                "user_id": user_id,
                **data.get("data", {})
            }
        })
        
        # Update user context
        if result.get("status") == "success":
            # Update social status
            if "analysis" in result and "social_status" in result["analysis"]:
                self.user_contexts[user_id]["social_status"] = result["analysis"]["social_status"]
            
            # Add alerts
            for alert in result.get("alerts", []):
                if alert not in self.user_contexts[user_id]["alerts"]:
                    self.user_contexts[user_id]["alerts"].append(alert)
            
            # Update overall status
            self.user_contexts[user_id]["overall_status"] = self._determine_overall_status(user_id)
            self.user_contexts[user_id]["last_update"] = datetime.now().isoformat()
        
        return result
    
    async def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status information for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing user status
        """
        if user_id not in self.user_contexts:
            await self._initialize_user_context(user_id)
        
        # Get the basic context
        context = self.user_contexts[user_id]
        
        # Check if context is recent enough
        last_update = datetime.fromisoformat(context.get("last_update", datetime.min.isoformat()))
        if (datetime.now() - last_update).total_seconds() > 60:
            # Update context
            await self._update_user_context(user_id)
            context = self.user_contexts[user_id]
        
        # Get detailed status from each agent
        health_status = None
        safety_status = None
        reminder_status = None
        social_status = None
        emergency_status = None
        
        if self.health_agent:
            try:
                response = await self.health_agent.get_health_status(user_id)
                if response.get("status") == "success":
                    health_status = response
            except Exception as e:
                self.logger.error(f"Error getting health status for user {user_id}: {e}")
        
        if self.safety_agent:
            try:
                response = await self.safety_agent.get_safety_status(user_id)
                if response.get("status") == "success":
                    safety_status = response
            except Exception as e:
                self.logger.error(f"Error getting safety status for user {user_id}: {e}")
        
        if self.daily_agent:
            try:
                response = await self.daily_agent.get_reminder_status(user_id)
                if response.get("status") == "success":
                    reminder_status = response
            except Exception as e:
                self.logger.error(f"Error getting reminder status for user {user_id}: {e}")
        
        if self.social_agent:
            try:
                response = await self.social_agent.get_social_status(user_id)
                if response.get("status") == "success":
                    social_status = response
            except Exception as e:
                self.logger.error(f"Error getting social status for user {user_id}: {e}")
        
        if self.emergency_agent:
            try:
                response = await self.emergency_agent.get_emergency_status(user_id)
                if response.get("status") == "success":
                    emergency_status = response
            except Exception as e:
                self.logger.error(f"Error getting emergency status for user {user_id}: {e}")
        
        # Generate comprehensive status summary
        status_summary = await self._generate_status_summary(
            user_id, 
            context, 
            health_status, 
            safety_status, 
            reminder_status, 
            social_status, 
            emergency_status
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "health": health_status,
            "safety": safety_status,
            "reminders": reminder_status,
            "social": social_status,
            "emergency": emergency_status,
            "summary": status_summary
        }
    
    async def _generate_status_summary(
        self,
        user_id: str,
        context: Dict[str, Any],
        health_status: Optional[Dict[str, Any]],
        safety_status: Optional[Dict[str, Any]],
        reminder_status: Optional[Dict[str, Any]],
        social_status: Optional[Dict[str, Any]],
        emergency_status: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate a comprehensive status summary using LLM.
        
        Args:
            user_id: ID of the user
            context: User context dictionary
            health_status: Health status data
            safety_status: Safety status data
            reminder_status: Reminder status data
            social_status: Social status data
            emergency_status: Emergency status data
            
        Returns:
            Status summary string
        """
        # Create a detailed prompt for the LLM
        health_summary = health_status.get("summary", "No health data available") if health_status else "No health data available"
        safety_summary = safety_status.get("summary", "No safety data available") if safety_status else "No safety data available"
        reminder_summary = reminder_status.get("summary", "No reminder data available") if reminder_status else "No reminder data available"
        social_summary = social_status.get("summary", "No social data available") if social_status else "No social data available"
        
        active_emergency = "None"
        if emergency_status and emergency_status.get("active_emergency"):
            active_emergency = f"Active {emergency_status['active_emergency']['type']} emergency"
        
        overall_status = context.get("overall_status", "unknown")
        
        alert_count = len(context.get("alerts", []))
        alert_text = ""
        if alert_count > 0:
            recent_alerts = context.get("alerts", [])[-3:]  # Last 3 alerts
            alert_text = "\n".join([f"- {alert.get('message', 'No message')}" for alert in recent_alerts])
        
        prompt = f"""
        Please provide a concise status summary for elderly user {user_id}.
        
        Current location: {context.get("current_location", "unknown")}
        Current activity: {context.get("current_activity", "unknown")}
        Overall status: {overall_status}
        Active emergency: {active_emergency}
        
        Component summaries:
        - Health: {health_summary}
        - Safety: {safety_summary}
        - Reminders: {reminder_summary}
        - Social: {social_summary}
        
        Recent alerts ({alert_count} total):
        {alert_text if alert_count > 0 else "No recent alerts"}
        
        Please provide a 2-3 sentence summary of the user's current status, highlighting the most important information and any areas requiring attention.
        """
        
        # Generate response
        return await self.generate_llm_response(
            prompt,
            max_tokens=200,
            temperature=0.7,
            response_type="status_summary"
        )
    
    async def resolve_alert(
        self, 
        user_id: str, 
        alert_id: str, 
        resolution_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resolve an alert for a user.
        
        Args:
            user_id: ID of the user
            alert_id: ID of the alert to resolve
            resolution_details: Optional details about the resolution
            
        Returns:
            Resolution status
        """
        if user_id not in self.user_contexts:
            return {
                "status": "error",
                "message": f"User {user_id} not found"
            }
        
        # Find the alert
        found = False
        for i, alert in enumerate(self.user_contexts[user_id].get("alerts", [])):
            if alert.get("id") == alert_id:
                # Remove from alerts list
                self.user_contexts[user_id]["alerts"].pop(i)
                found = True
                break
        
        if not found:
            return {
                "status": "error",
                "message": f"Alert {alert_id} not found for user {user_id}"
            }
        
        # Update alert in database
        db.insert("events", {
            "user_id": user_id,
            "event_type": "alert_resolved",
            "details": {
                "alert_id": alert_id,
                "resolution_time": datetime.now().isoformat(),
                "resolution_details": resolution_details or {}
            }
        })
        
        self.logger.info(f"Resolved alert {alert_id} for user {user_id}")
        
        # Update overall status
        self.user_contexts[user_id]["overall_status"] = self._determine_overall_status(user_id)
        self.user_contexts[user_id]["last_update"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": f"Alert {alert_id} resolved successfully"
        }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.
        
        Returns:
            Dictionary containing system status
        """
        # Count users by status
        status_counts = {
            "normal": 0,
            "attention": 0,
            "alert": 0,
            "emergency": 0,
            "unknown": 0
        }
        
        for user_id, context in self.user_contexts.items():
            status = context.get("overall_status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check agent status
        agents_status = {
            "health_monitor": self.health_agent is not None,
            "safety_guardian": self.safety_agent is not None,
            "daily_assistant": self.daily_agent is not None,
            "social_engagement": self.social_agent is not None,
            "emergency_response": self.emergency_agent is not None
        }
        
        # Get system uptime
        started_at = datetime.fromisoformat(self.system_state.get("started_at", datetime.now().isoformat()))
        uptime_seconds = (datetime.now() - started_at).total_seconds()
        
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "active_users": self.system_state.get("active_users", 0),
            "active_alerts": self.system_state.get("active_alerts", 0),
            "active_emergencies": self.system_state.get("active_emergencies", 0),
            "user_status_counts": status_counts,
            "agents_status": agents_status,
            "started_at": self.system_state.get("started_at"),
            "uptime": uptime
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
        
        if message_type == "data":
            return await self.handle_incoming_data(message.get("data", {}))
        
        elif message_type == "get_user_status":
            user_id = message.get("user_id")
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in get_user_status request"
                }
            
            return await self.get_user_status(user_id)
        
        elif message_type == "get_system_status":
            return await self.get_system_status()
        
        elif message_type == "resolve_alert":
            user_id = message.get("user_id")
            alert_id = message.get("alert_id")
            resolution_details = message.get("resolution_details")
            
            if not user_id or not alert_id:
                return {
                    "status": "error",
                    "message": "Missing user_id or alert_id in resolve_alert request"
                }
            
            return await self.resolve_alert(user_id, alert_id, resolution_details)
        
        else:
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }