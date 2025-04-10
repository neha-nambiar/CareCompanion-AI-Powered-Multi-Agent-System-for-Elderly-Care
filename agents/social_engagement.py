"""
Social Engagement Agent for the CareCompanion system.
Monitors and promotes social interaction for elderly users.
"""

import asyncio
import json
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.logger import setup_logger
from utils.config import Config
from utils.database import db
from models.analytics import analyzer

class SocialEngagementAgent(BaseAgent):
    """
    Agent responsible for monitoring and promoting social engagement.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Social Engagement Agent.
        
        Args:
            config: Configuration object
        """
        super().__init__(name="social_engagement", config=config)
        
        # Load social engagement settings from config
        self.isolation_threshold = config.get("agents.social_engagement.isolation_threshold", 72)  # hours
        
        # Initialize user-specific data
        self.user_data = {}
        
        # Cache for social analyses
        self.social_analyses = {}
        self.analysis_timestamps = {}
        
        # Interaction types and their weights
        self.interaction_types = {
            "in_person_visit": 1.0,
            "video_call": 0.8,
            "phone_call": 0.6,
            "text_message": 0.3,
            "email": 0.3,
            "group_activity": 0.9,
            "community_event": 0.7
        }
    
    async def initialize(self) -> None:
        """
        Initialize the agent's state.
        """
        await super().initialize()
        
        # Load user data
        user_ids = analyzer.get_user_ids()
        for user_id in user_ids:
            await self._initialize_user_data(user_id)
        
        self.logger.info(f"Initialized social data for {len(user_ids)} users")
    
    async def _initialize_user_data(self, user_id: str) -> None:
        """
        Initialize data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        # Since we don't have explicit social data in our CSVs,
        # we'll create simulated data based on the other datasets
        
        self.user_data[user_id] = {
            "interaction_history": [],
            "alert_history": [],
            "last_interaction": None,
            "last_interaction_time": None,
            "social_preferences": self._get_default_social_preferences(),
            "suggested_activities": []
        }
        
        # Generate simulated social interaction history
        self._generate_simulated_interactions(user_id)
        
        # Analyze social data
        analysis = self._analyze_social_data(user_id)
        self.social_analyses[user_id] = analysis
        self.analysis_timestamps[user_id] = datetime.now()
        
        # Generate suggested activities
        suggestions = self._generate_activity_suggestions(user_id, analysis)
        self.user_data[user_id]["suggested_activities"] = suggestions
    
    def _get_default_social_preferences(self) -> Dict[str, Any]:
        """
        Get default social preferences.
        
        Returns:
            Dictionary of social preferences
        """
        return {
            "preferred_interaction_types": ["in_person_visit", "video_call", "phone_call"],
            "preferred_contacts": ["family", "friends", "caregivers"],
            "preferred_frequency": "daily",
            "privacy_level": "medium",
            "activity_interests": ["reading", "music", "television", "conversation"]
        }
    
    def _generate_simulated_interactions(self, user_id: str) -> None:
        """
        Generate simulated social interaction history.
        
        Args:
            user_id: ID of the user
        """
        now = datetime.now()
        interactions = []
        
        # Generate interactions for the past 30 days
        for days_ago in range(30, 0, -1):
            date = now - timedelta(days=days_ago)
            
            # Random number of interactions per day (0-2)
            num_interactions = random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2])[0]
            
            for _ in range(num_interactions):
                # Random interaction type
                interaction_type = random.choice(list(self.interaction_types.keys()))
                
                # Random duration (10-60 minutes)
                duration = random.randint(10, 60)
                
                # Random time of day
                hour = random.randint(9, 20)
                minute = random.choice([0, 15, 30, 45])
                interaction_time = date.replace(hour=hour, minute=minute, second=0)
                
                # Random contact type
                contact_type = random.choice(["family", "friend", "caregiver", "neighbor"])
                
                # Create interaction
                interaction = {
                    "timestamp": interaction_time.isoformat(),
                    "type": interaction_type,
                    "duration_minutes": duration,
                    "contact_type": contact_type,
                    "initiated_by_user": random.choice([True, False]),
                    "notes": f"Simulated {interaction_type} with {contact_type}"
                }
                
                interactions.append(interaction)
        
        # Sort by timestamp
        interactions.sort(key=lambda x: x["timestamp"])
        
        # Store in user data
        self.user_data[user_id]["interaction_history"] = interactions
        
        # Set last interaction
        if interactions:
            self.user_data[user_id]["last_interaction"] = interactions[-1]
            self.user_data[user_id]["last_interaction_time"] = datetime.fromisoformat(interactions[-1]["timestamp"])
    
    async def update(self) -> None:
        """
        Perform periodic social engagement update.
        """
        await super().update()
        
        # Update social analyses for all users
        for user_id in self.user_data.keys():
            # Check if analysis is older than the update interval
            if (user_id not in self.analysis_timestamps or 
                (datetime.now() - self.analysis_timestamps.get(user_id, datetime.min)).total_seconds() > self.update_interval):
                
                # Re-analyze social data
                analysis = self._analyze_social_data(user_id)
                self.social_analyses[user_id] = analysis
                self.analysis_timestamps[user_id] = datetime.now()
                
                # Check for social isolation
                isolation_alerts = self._check_social_isolation(user_id, analysis)
                
                # Store alerts
                if isolation_alerts:
                    self.user_data[user_id]["alert_history"].extend(isolation_alerts)
                    
                    # Keep only recent alerts (last 10)
                    self.user_data[user_id]["alert_history"] = self.user_data[user_id]["alert_history"][-10:]
                    
                    # Report alerts to coordination agent
                    await self._report_alerts(user_id, isolation_alerts)
                
                # Update activity suggestions
                suggestions = self._generate_activity_suggestions(user_id, analysis)
                self.user_data[user_id]["suggested_activities"] = suggestions
    
    def _check_social_isolation(self, user_id: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for social isolation based on interaction history.
        
        Args:
            user_id: ID of the user
            analysis: Social analysis results
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        now = datetime.now()
        
        # Get last interaction time
        last_interaction_time = self.user_data[user_id].get("last_interaction_time")
        
        if not last_interaction_time:
            return alerts
        
        # Calculate hours since last interaction
        hours_since_interaction = (now - last_interaction_time).total_seconds() / 3600
        
        # Check against isolation threshold
        if hours_since_interaction > self.isolation_threshold:
            level = "warning"
            if hours_since_interaction > self.isolation_threshold * 2:
                level = "urgent"
            
            alert = {
                "timestamp": now.isoformat(),
                "level": level,
                "type": "social_isolation",
                "message": f"Social isolation detected: {int(hours_since_interaction)} hours since last social interaction",
                "hours_since_interaction": int(hours_since_interaction),
                "threshold_hours": self.isolation_threshold
            }
            
            alerts.append(alert)
            
            # Store alert in database
            db.insert("alerts", {
                "user_id": user_id,
                "source": "social_engagement",
                "level": level,
                "message": alert["message"],
                "resolved": False,
                "resolution_details": ""
            })
            
            self.logger.info(f"Social isolation alert for user {user_id}: {int(hours_since_interaction)} hours")
        
        # Check interaction frequency against preferences
        weekly_interactions = analysis.get("weekly_interaction_count", 0)
        preferred_frequency = self.user_data[user_id].get("social_preferences", {}).get("preferred_frequency", "daily")
        
        expected_weekly = 7  # Default daily
        if preferred_frequency == "daily":
            expected_weekly = 7
        elif preferred_frequency == "every_other_day":
            expected_weekly = 3
        elif preferred_frequency == "weekly":
            expected_weekly = 1
        
        if weekly_interactions < expected_weekly / 2:
            alert = {
                "timestamp": now.isoformat(),
                "level": "info",
                "type": "low_interaction_frequency",
                "message": f"Low social interaction frequency: {weekly_interactions} interactions in the past week (expected: {expected_weekly})",
                "weekly_interactions": weekly_interactions,
                "expected_weekly": expected_weekly
            }
            
            alerts.append(alert)
            
            # Store alert in database
            db.insert("alerts", {
                "user_id": user_id,
                "source": "social_engagement",
                "level": "info",
                "message": alert["message"],
                "resolved": False,
                "resolution_details": ""
            })
            
            self.logger.info(f"Low interaction frequency alert for user {user_id}: {weekly_interactions} weekly")
        
        return alerts
    
    async def _report_alerts(self, user_id: str, alerts: List[Dict[str, Any]]) -> None:
        """
        Report alerts to the coordination agent.
        
        Args:
            user_id: ID of the user
            alerts: List of alert dictionaries
        """
        # This would be implemented in a full system to forward alerts
        # to the coordination agent for processing
        pass
    
    def _analyze_social_data(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze social interaction data for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Analysis results
        """
        user_data = self.user_data.get(user_id)
        
        if not user_data or "interaction_history" not in user_data:
            return {
                "status": "error",
                "message": f"No social data available for user {user_id}"
            }
        
        interaction_history = user_data["interaction_history"]
        
        if not interaction_history:
            return {
                "status": "error",
                "message": f"Empty interaction history for user {user_id}"
            }
        
        now = datetime.now()
        
        # Get interactions in the past week
        one_week_ago = now - timedelta(days=7)
        weekly_interactions = [
            interaction for interaction in interaction_history
            if datetime.fromisoformat(interaction["timestamp"]) > one_week_ago
        ]
        
        # Get interactions in the past month
        one_month_ago = now - timedelta(days=30)
        monthly_interactions = [
            interaction for interaction in interaction_history
            if datetime.fromisoformat(interaction["timestamp"]) > one_month_ago
        ]
        
        # Calculate total interaction time (weighted by type)
        weekly_interaction_minutes = 0
        monthly_interaction_minutes = 0
        
        for interaction in weekly_interactions:
            interaction_type = interaction.get("type", "phone_call")
            duration = interaction.get("duration_minutes", 0)
            weight = self.interaction_types.get(interaction_type, 0.5)
            weekly_interaction_minutes += duration * weight
        
        for interaction in monthly_interactions:
            interaction_type = interaction.get("type", "phone_call")
            duration = interaction.get("duration_minutes", 0)
            weight = self.interaction_types.get(interaction_type, 0.5)
            monthly_interaction_minutes += duration * weight
        
        # Count interaction types
        interaction_type_counts = {}
        contact_type_counts = {}
        
        for interaction in monthly_interactions:
            interaction_type = interaction.get("type", "unknown")
            contact_type = interaction.get("contact_type", "unknown")
            
            interaction_type_counts[interaction_type] = interaction_type_counts.get(interaction_type, 0) + 1
            contact_type_counts[contact_type] = contact_type_counts.get(contact_type, 0) + 1
        
        # Calculate average interaction duration
        avg_duration = 0
        if monthly_interactions:
            total_duration = sum(interaction.get("duration_minutes", 0) for interaction in monthly_interactions)
            avg_duration = total_duration / len(monthly_interactions)
        
        # Get last interaction details
        last_interaction = None
        last_interaction_time = None
        hours_since_last_interaction = None
        
        if interaction_history:
            last_interaction = interaction_history[-1]
            last_interaction_time = datetime.fromisoformat(last_interaction["timestamp"])
            hours_since_last_interaction = (now - last_interaction_time).total_seconds() / 3600
        
        # Determine overall social status
        if hours_since_last_interaction is None or hours_since_last_interaction > self.isolation_threshold:
            social_status = "alert"
        elif weekly_interactions and len(weekly_interactions) < 3:
            social_status = "attention"
        else:
            social_status = "normal"
        
        # Collect social concerns
        social_concerns = []
        
        if hours_since_last_interaction is not None and hours_since_last_interaction > self.isolation_threshold:
            social_concerns.append("Extended period without social interaction")
        
        if len(weekly_interactions) < 3:
            social_concerns.append("Low weekly interaction count")
        
        if len(interaction_type_counts) < 2:
            social_concerns.append("Limited variety of interaction types")
        
        if avg_duration < 15:
            social_concerns.append("Short average interaction duration")
        
        return {
            "status": "success",
            "timestamp": now.isoformat(),
            "weekly_interaction_count": len(weekly_interactions),
            "monthly_interaction_count": len(monthly_interactions),
            "weekly_interaction_minutes": weekly_interaction_minutes,
            "monthly_interaction_minutes": monthly_interaction_minutes,
            "interaction_type_counts": interaction_type_counts,
            "contact_type_counts": contact_type_counts,
            "average_duration": avg_duration,
            "last_interaction": last_interaction,
            "last_interaction_time": last_interaction_time.isoformat() if last_interaction_time else None,
            "hours_since_last_interaction": hours_since_last_interaction,
            "social_status": social_status,
            "social_concerns": social_concerns
        }
    
    def _generate_activity_suggestions(
        self, 
        user_id: str, 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate suggested social activities based on analysis.
        
        Args:
            user_id: ID of the user
            analysis: Social analysis results
            
        Returns:
            List of activity suggestion dictionaries
        """
        suggestions = []
        preferences = self.user_data[user_id].get("social_preferences", {})
        
        # Skip if analysis wasn't successful
        if analysis.get("status") != "success":
            return suggestions
        
        # Get preferred interaction types and interests
        preferred_types = preferences.get("preferred_interaction_types", [])
        interests = preferences.get("activity_interests", [])
        
        # Get current interaction patterns
        type_counts = analysis.get("interaction_type_counts", {})
        contact_counts = analysis.get("contact_type_counts", {})
        
        # Suggest activities based on social status
        social_status = analysis.get("social_status", "normal")
        
        if social_status == "alert":
            # Urgent suggestions for social isolation
            if "phone_call" in preferred_types:
                suggestions.append({
                    "type": "phone_call",
                    "title": "Call a family member",
                    "description": "A quick call to check in with a loved one can help reduce feelings of isolation.",
                    "priority": "high",
                    "estimated_duration": 15
                })
            
            if "video_call" in preferred_types:
                suggestions.append({
                    "type": "video_call",
                    "title": "Video call with a friend or family member",
                    "description": "Seeing a familiar face can boost your mood and reduce isolation.",
                    "priority": "high",
                    "estimated_duration": 30
                })
            
            suggestions.append({
                "type": "support_group",
                "title": "Join an online support group",
                "description": "Connect with others who share similar experiences.",
                "priority": "medium",
                "estimated_duration": 60
            })
        
        elif social_status == "attention":
            # Moderate suggestions for improving social engagement
            if "in_person_visit" in preferred_types:
                suggestions.append({
                    "type": "in_person_visit",
                    "title": "Schedule a visit with a friend or family member",
                    "description": "In-person social interaction can significantly improve well-being.",
                    "priority": "medium",
                    "estimated_duration": 60
                })
            
            if "group_activity" in preferred_types:
                activity = random.choice(interests) if interests else "conversation"
                suggestions.append({
                    "type": "group_activity",
                    "title": f"Join a {activity} group or class",
                    "description": f"Engaging in {activity} with others combines socialization with an activity you enjoy.",
                    "priority": "medium",
                    "estimated_duration": 90
                })
            
            suggestions.append({
                "type": "community_event",
                "title": "Attend a community event",
                "description": "Local events provide opportunities to meet neighbors and community members.",
                "priority": "low",
                "estimated_duration": 120
            })
        
        else:  # normal
            # General suggestions for maintaining social engagement
            if "in_person_visit" in preferred_types and "in_person_visit" not in type_counts:
                suggestions.append({
                    "type": "in_person_visit",
                    "title": "Schedule a visit with a friend or family member",
                    "description": "Regular in-person visits help maintain strong social connections.",
                    "priority": "low",
                    "estimated_duration": 60
                })
            
            if interests:
                activity = random.choice(interests)
                suggestions.append({
                    "type": "shared_activity",
                    "title": f"Share {activity} with a friend",
                    "description": f"Enjoying {activity} together can strengthen your relationship.",
                    "priority": "low",
                    "estimated_duration": 60
                })
            
            if "community_event" not in type_counts:
                suggestions.append({
                    "type": "community_event",
                    "title": "Explore local community events",
                    "description": "Community events provide opportunities to meet new people and stay connected.",
                    "priority": "low",
                    "estimated_duration": 120
                })
        
        # Add variety if interaction types are limited
        if len(type_counts) < 2:
            unused_types = [t for t in self.interaction_types.keys() if t not in type_counts]
            
            if unused_types:
                new_type = random.choice(unused_types)
                suggestions.append({
                    "type": new_type,
                    "title": f"Try a new way to connect: {new_type.replace('_', ' ')}",
                    "description": "Varying the ways you connect with others can enrich your social life.",
                    "priority": "medium",
                    "estimated_duration": 30
                })
        
        # Add contact type variety if needed
        if len(contact_counts) < 2:
            contact_types = ["family", "friend", "neighbor", "community member"]
            unused_contacts = [c for c in contact_types if c not in contact_counts]
            
            if unused_contacts:
                new_contact = random.choice(unused_contacts)
                suggestions.append({
                    "type": "expand_network",
                    "title": f"Connect with a {new_contact}",
                    "description": f"Expanding your social circle to include {new_contact}s can provide new perspectives and support.",
                    "priority": "low",
                    "estimated_duration": 30
                })
        
        # Limit to 5 suggestions
        random.shuffle(suggestions)
        return suggestions[:5]
    
    async def process_social_data(self, social_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming social interaction data.
        
        Args:
            social_data: Dictionary containing social interaction data
            
        Returns:
            Processing results
        """
        user_id = social_data.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing user_id in social data"
            }
        
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Process new interaction if provided
        new_interaction = social_data.get("interaction")
        if new_interaction:
            # Add timestamp if not provided
            if "timestamp" not in new_interaction:
                new_interaction["timestamp"] = datetime.now().isoformat()
            
            # Add to interaction history
            if "interaction_history" in self.user_data[user_id]:
                self.user_data[user_id]["interaction_history"].append(new_interaction)
                
                # Sort by timestamp
                self.user_data[user_id]["interaction_history"].sort(key=lambda x: x["timestamp"])
            
            # Update last interaction
            self.user_data[user_id]["last_interaction"] = new_interaction
            self.user_data[user_id]["last_interaction_time"] = datetime.fromisoformat(new_interaction["timestamp"])
            
            # Store in database as event
            db.insert("events", {
                "user_id": user_id,
                "event_type": "social_interaction",
                "details": new_interaction
            })
            
            self.logger.info(f"Recorded new {new_interaction.get('type', 'unknown')} interaction for user {user_id}")
        
        # Update social preferences if provided
        preferences = social_data.get("preferences")
        if preferences:
            if "social_preferences" in self.user_data[user_id]:
                self.user_data[user_id]["social_preferences"].update(preferences)
            else:
                self.user_data[user_id]["social_preferences"] = preferences
            
            self.logger.info(f"Updated social preferences for user {user_id}")
        
        # Re-analyze social data
        analysis = self._analyze_social_data(user_id)
        
        # Update analysis cache
        self.social_analyses[user_id] = analysis
        self.analysis_timestamps[user_id] = datetime.now()
        
        # Check for isolation
        alerts = self._check_social_isolation(user_id, analysis)
        
        # Add alerts to history
        if alerts:
            self.user_data[user_id]["alert_history"].extend(alerts)
            
            # Keep history manageable (last 10 entries)
            self.user_data[user_id]["alert_history"] = self.user_data[user_id]["alert_history"][-10:]
        
        # Update activity suggestions
        suggestions = self._generate_activity_suggestions(user_id, analysis)
        self.user_data[user_id]["suggested_activities"] = suggestions
        
        # Generate LLM analysis if needed
        llm_analysis = ""
        if new_interaction or preferences:
            llm_analysis = await self._generate_llm_analysis(user_id, analysis, suggestions)
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis if analysis.get("status") == "success" else None,
            "alerts": alerts,
            "suggestions": suggestions,
            "llm_analysis": llm_analysis
        }
    
    async def _generate_llm_analysis(
        self, 
        user_id: str, 
        analysis: Dict[str, Any], 
        suggestions: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an LLM analysis of social data.
        
        Args:
            user_id: ID of the user
            analysis: Social analysis results
            suggestions: List of activity suggestions
            
        Returns:
            LLM analysis string
        """
        # Skip if analysis wasn't successful
        if analysis.get("status") != "success":
            return ""
        
        # Create a detailed prompt for the LLM
        weekly_count = analysis.get("weekly_interaction_count", 0)
        monthly_count = analysis.get("monthly_interaction_count", 0)
        avg_duration = analysis.get("average_duration", 0)
        hours_since = analysis.get("hours_since_last_interaction", "unknown")
        social_status = analysis.get("social_status", "unknown")
        concerns = analysis.get("social_concerns", [])
        
        concern_text = "\n".join([f"- {concern}" for concern in concerns])
        suggestion_text = "\n".join([f"- {s['title']}: {s['description']}" for s in suggestions])
        
        prompt = f"""
        Please analyze the following social engagement data for user {user_id}:
        
        Weekly interactions: {weekly_count}
        Monthly interactions: {monthly_count}
        Average interaction duration: {avg_duration:.1f} minutes
        Hours since last interaction: {hours_since}
        Overall social status: {social_status}
        
        Social concerns:
        {concern_text if concerns else "No specific concerns."}
        
        Suggested activities:
        {suggestion_text if suggestions else "No specific suggestions."}
        
        Please provide a brief analysis of the social engagement patterns, the potential impact
        on the user's well-being, and the benefits of the suggested activities.
        """
        
        # Generate response
        return await self.generate_llm_response(
            prompt,
            max_tokens=200,
            temperature=0.7,
            response_type="status_summary"
        )
    
    async def get_social_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get the current social status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing social status
        """
        if user_id not in self.social_analyses:
            # If we don't have an analysis, generate one
            analysis = self._analyze_social_data(user_id)
            
            if analysis.get("status") == "success":
                self.social_analyses[user_id] = analysis
                self.analysis_timestamps[user_id] = datetime.now()
            else:
                return {
                    "status": "error",
                    "message": f"No social data available for user {user_id}"
                }
        
        analysis = self.social_analyses[user_id]
        
        # Get activity suggestions
        suggestions = []
        if user_id in self.user_data and "suggested_activities" in self.user_data[user_id]:
            suggestions = self.user_data[user_id]["suggested_activities"]
        
        # Get recent alerts
        recent_alerts = []
        if user_id in self.user_data and "alert_history" in self.user_data[user_id]:
            recent_alerts = self.user_data[user_id]["alert_history"][-5:]  # Last 5 alerts
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": self.analysis_timestamps.get(user_id, datetime.now()).isoformat(),
            "analysis": analysis,
            "suggestions": suggestions,
            "alerts": recent_alerts,
            "summary": self._generate_social_summary(analysis)
        }
    
    def _generate_social_summary(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of social status.
        
        Args:
            analysis: Social analysis results
            
        Returns:
            Summary string
        """
        # Generate a simple text summary
        social_status = analysis.get("social_status", "unknown")
        weekly_count = analysis.get("weekly_interaction_count", 0)
        hours_since = analysis.get("hours_since_last_interaction", "unknown")
        concerns = analysis.get("social_concerns", [])
        
        summary = f"Weekly interactions: {weekly_count}. "
        
        if hours_since != "unknown":
            summary += f"Last interaction: {int(hours_since)} hours ago. "
        
        if social_status == "normal":
            summary += "Social engagement level is healthy."
        elif social_status == "attention":
            summary += "Social engagement could be improved."
        else:  # alert
            summary += f"Social engagement needs immediate attention: {'; '.join(concerns)}"
        
        return summary
    
    async def update_social_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update social preferences for a user.
        
        Args:
            user_id: ID of the user
            preferences: Dictionary of social preferences
            
        Returns:
            Updated preferences
        """
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Update preferences
        if "social_preferences" in self.user_data[user_id]:
            self.user_data[user_id]["social_preferences"].update(preferences)
        else:
            self.user_data[user_id]["social_preferences"] = preferences
        
        self.logger.info(f"Updated social preferences for user {user_id}")
        
        # Update suggestions based on new preferences
        analysis = self.social_analyses.get(user_id)
        if analysis and analysis.get("status") == "success":
            suggestions = self._generate_activity_suggestions(user_id, analysis)
            self.user_data[user_id]["suggested_activities"] = suggestions
        
        return {
            "status": "success",
            "user_id": user_id,
            "preferences": self.user_data[user_id]["social_preferences"]
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
        
        if message_type == "social_data":
            return await self.process_social_data(message.get("data", {}))
        
        elif message_type == "get_status":
            user_id = message.get("user_id")
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in get_status request"
                }
            
            return await self.get_social_status(user_id)
        
        elif message_type == "update_preferences":
            user_id = message.get("user_id")
            preferences = message.get("preferences", {})
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in update_preferences request"
                }
            
            return await self.update_social_preferences(user_id, preferences)
        
        else:
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }