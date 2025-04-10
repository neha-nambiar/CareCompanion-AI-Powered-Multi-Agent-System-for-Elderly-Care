"""
Daily Assistant Agent for the CareCompanion system.
Manages reminders and daily activities for elderly users.
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

class DailyAssistantAgent(BaseAgent):
    """
    Agent responsible for managing reminders and daily activities.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Daily Assistant Agent.
        
        Args:
            config: Configuration object
        """
        super().__init__(name="daily_assistant", config=config)
        
        # Load reminder settings from config
        self.reminder_types = config.get("agents.daily_assistant.reminder_types", {})
        
        # Initialize user-specific data
        self.user_data = {}
        
        # Cache for reminder analyses
        self.reminder_analyses = {}
        self.analysis_timestamps = {}
    
    async def initialize(self) -> None:
        """
        Initialize the agent's state.
        """
        await super().initialize()
        
        # Load user data
        user_ids = analyzer.get_user_ids()
        for user_id in user_ids:
            await self._initialize_user_data(user_id)
        
        self.logger.info(f"Initialized reminder data for {len(user_ids)} users")
    
    async def _initialize_user_data(self, user_id: str) -> None:
        """
        Initialize data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        self.user_data[user_id] = {
            "reminder_history": [],
            "upcoming_reminders": [],
            "alert_history": [],
            "reminder_preferences": self._get_default_reminder_preferences(),
            "last_reminder": None,
            "last_reminder_time": None
        }
        
        # Analyze reminder data
        analysis = analyzer.analyze_reminder_data(user_id)
        
        if analysis.get("status") == "success":
            self.reminder_analyses[user_id] = analysis
            self.analysis_timestamps[user_id] = datetime.now()
            
            # Store reminder history
            reminder_data = analyzer.get_user_reminder_data(user_id)
            if reminder_data is not None:
                # Convert to list of dictionaries for internal storage
                self.user_data[user_id]["reminder_history"] = reminder_data.to_dict(orient="records")
                
                # Generate upcoming reminders based on history
                self.user_data[user_id]["upcoming_reminders"] = self._generate_upcoming_reminders(user_id, reminder_data)
    
    def _get_default_reminder_preferences(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default reminder preferences.
        
        Returns:
            Dictionary of reminder preferences
        """
        preferences = {}
        
        for reminder_type, settings in self.reminder_types.items():
            preferences[reminder_type] = {
                "enabled": True,
                "priority": settings.get("priority", "medium"),
                "max_delay": settings.get("max_delay", 60),  # minutes
                "preferred_times": []
            }
        
        # Add default preferred times if not in config
        if "medication" in preferences and not preferences["medication"]["preferred_times"]:
            preferences["medication"]["preferred_times"] = ["08:00", "12:00", "18:00"]
        
        if "hydration" in preferences and not preferences["hydration"]["preferred_times"]:
            preferences["hydration"]["preferred_times"] = ["09:00", "12:00", "15:00", "18:00"]
        
        if "exercise" in preferences and not preferences["exercise"]["preferred_times"]:
            preferences["exercise"]["preferred_times"] = ["10:00", "16:00"]
        
        return preferences
    
    def _generate_upcoming_reminders(self, user_id: str, reminder_data) -> List[Dict[str, Any]]:
        """
        Generate upcoming reminders based on historical data.
        
        Args:
            user_id: ID of the user
            reminder_data: DataFrame with reminder data
            
        Returns:
            List of upcoming reminder dictionaries
        """
        upcoming = []
        
        # Get reminder types and their frequencies from historical data
        reminder_types = reminder_data["Reminder Type"].unique()
        
        # Generate realistic upcoming reminders
        now = datetime.now()
        
        for reminder_type in reminder_types:
            # Filter data for this type
            type_data = reminder_data[reminder_data["Reminder Type"] == reminder_type]
            
            # Get scheduled times for this type
            scheduled_times = type_data["Scheduled Time"].unique()
            
            for time_str in scheduled_times:
                # Parse time
                try:
                    hour, minute, second = map(int, time_str.split(":"))
                    scheduled_time = now.replace(hour=hour, minute=minute, second=0)
                    
                    # If time has passed, schedule for tomorrow
                    if scheduled_time < now:
                        scheduled_time = scheduled_time + timedelta(days=1)
                    
                    # Create upcoming reminder
                    upcoming.append({
                        "user_id": user_id,
                        "reminder_type": reminder_type,
                        "content": self._generate_reminder_content(reminder_type),
                        "scheduled_time": scheduled_time.isoformat(),
                        "created_at": now.isoformat(),
                        "sent": False,
                        "acknowledged": False
                    })
                except:
                    self.logger.warning(f"Could not parse scheduled time: {time_str}")
        
        # Sort by scheduled time
        upcoming.sort(key=lambda x: x["scheduled_time"])
        
        return upcoming
    
    def _generate_reminder_content(self, reminder_type: str) -> str:
        """
        Generate content for a reminder based on its type.
        
        Args:
            reminder_type: Type of reminder
            
        Returns:
            Reminder content string
        """
        if reminder_type.lower() == "medication":
            return random.choice([
                "Take your blood pressure medication",
                "Time for your heart medication",
                "Don't forget your daily vitamin",
                "Take your arthritis medication"
            ])
        elif reminder_type.lower() == "hydration":
            return random.choice([
                "Drink a glass of water",
                "Stay hydrated - have some water",
                "Time to have some water",
                "Remember to drink fluids regularly"
            ])
        elif reminder_type.lower() == "exercise":
            return random.choice([
                "Time for your gentle stretching routine",
                "Do your daily walking exercise",
                "Remember to do your physical therapy exercises",
                "Time for some light movement activities"
            ])
        elif reminder_type.lower() == "appointment":
            return random.choice([
                "Doctor's appointment tomorrow at 10:00 AM",
                "Reminder: Physical therapy session at 2:00 PM",
                "You have a telehealth call scheduled",
                "Don't forget your check-up appointment"
            ])
        else:
            return f"Reminder for your {reminder_type}"
    
    async def update(self) -> None:
        """
        Perform periodic reminder update.
        """
        await super().update()
        
        # Update reminders for all users
        now = datetime.now()
        
        for user_id, user_data in self.user_data.items():
            # Check for reminders that need to be sent
            if "upcoming_reminders" in user_data:
                sent_reminders = []
                remaining_reminders = []
                
                for reminder in user_data["upcoming_reminders"]:
                    # Parse scheduled time
                    scheduled_time = datetime.fromisoformat(reminder["scheduled_time"])
                    
                    # Check if it's time to send the reminder
                    if scheduled_time <= now and not reminder["sent"]:
                        # Mark as sent
                        reminder["sent"] = True
                        reminder["sent_at"] = now.isoformat()
                        
                        # Add to sent list
                        sent_reminders.append(reminder)
                        
                        # Store in database
                        db.insert("reminders", {
                            "user_id": user_id,
                            "timestamp": now.isoformat(),
                            "type": reminder["reminder_type"],
                            "content": reminder["content"],
                            "scheduled_time": reminder["scheduled_time"],
                            "sent": True,
                            "acknowledged": False
                        })
                        
                        # Record last reminder
                        user_data["last_reminder"] = reminder
                        user_data["last_reminder_time"] = now
                    
                    remaining_reminders.append(reminder)
                
                # Update upcoming reminders
                user_data["upcoming_reminders"] = remaining_reminders
                
                # Send notifications for sent reminders
                if sent_reminders:
                    await self._notify_reminders(user_id, sent_reminders)
                    
                    # Re-analyze reminder data if we've sent reminders
                    analysis = analyzer.analyze_reminder_data(user_id)
                    
                    if analysis.get("status") == "success":
                        self.reminder_analyses[user_id] = analysis
                        self.analysis_timestamps[user_id] = now
            
            # Generate new reminders if we're running low
            if len(user_data["upcoming_reminders"]) < 5:
                self._generate_additional_reminders(user_id)
            
            # Check for overdue reminders
            overdue_alerts = self._check_overdue_reminders(user_id)
            
            # Store alerts
            if overdue_alerts:
                user_data["alert_history"].extend(overdue_alerts)
                
                # Keep only recent alerts (last 20)
                user_data["alert_history"] = user_data["alert_history"][-20:]
                
                # Report alerts to coordination agent
                await self._report_alerts(user_id, overdue_alerts)
    
    async def _notify_reminders(self, user_id: str, reminders: List[Dict[str, Any]]) -> None:
        """
        Notify the user about reminders.
        
        Args:
            user_id: ID of the user
            reminders: List of reminder dictionaries
        """
        # In a full system, this would send notifications to the user's device
        # For this demo, we'll just log the reminders
        for reminder in reminders:
            self.logger.info(
                f"Sending reminder to user {user_id}: "
                f"{reminder['reminder_type']} - {reminder['content']}"
            )
    
    def _generate_additional_reminders(self, user_id: str) -> None:
        """
        Generate additional upcoming reminders.
        
        Args:
            user_id: ID of the user
        """
        user_data = self.user_data.get(user_id)
        if not user_data:
            return
        
        preferences = user_data.get("reminder_preferences", self._get_default_reminder_preferences())
        upcoming = user_data.get("upcoming_reminders", [])
        
        # Get existing scheduled times to avoid duplicates
        scheduled_times = set()
        for reminder in upcoming:
            scheduled_times.add(reminder["scheduled_time"])
        
        # Generate new reminders
        now = datetime.now()
        new_reminders = []
        
        for reminder_type, settings in preferences.items():
            if not settings.get("enabled", True):
                continue
            
            # Get preferred times
            preferred_times = settings.get("preferred_times", [])
            
            # If no preferred times, use reasonable defaults
            if not preferred_times:
                if reminder_type == "medication":
                    preferred_times = ["08:00", "12:00", "18:00"]
                elif reminder_type == "hydration":
                    preferred_times = ["09:00", "12:00", "15:00", "18:00"]
                elif reminder_type == "exercise":
                    preferred_times = ["10:00", "16:00"]
                elif reminder_type == "appointment":
                    preferred_times = ["09:00"]  # Usually one appointment
            
            for time_str in preferred_times:
                # Parse time
                try:
                    hour, minute = map(int, time_str.split(":"))
                    scheduled_time = now.replace(hour=hour, minute=minute, second=0)
                    
                    # If time has passed, schedule for tomorrow
                    if scheduled_time < now:
                        scheduled_time = scheduled_time + timedelta(days=1)
                    
                    # Skip if we already have this scheduled time
                    if scheduled_time.isoformat() in scheduled_times:
                        continue
                    
                    # Create new reminder
                    new_reminders.append({
                        "user_id": user_id,
                        "reminder_type": reminder_type,
                        "content": self._generate_reminder_content(reminder_type),
                        "scheduled_time": scheduled_time.isoformat(),
                        "created_at": now.isoformat(),
                        "sent": False,
                        "acknowledged": False
                    })
                    
                    # Add to scheduled times set
                    scheduled_times.add(scheduled_time.isoformat())
                except:
                    self.logger.warning(f"Could not parse preferred time: {time_str}")
        
        # Add new reminders to upcoming list
        user_data["upcoming_reminders"].extend(new_reminders)
        
        # Sort by scheduled time
        user_data["upcoming_reminders"].sort(key=lambda x: x["scheduled_time"])
        
        if new_reminders:
            self.logger.info(f"Generated {len(new_reminders)} new reminders for user {user_id}")
    
    def _check_overdue_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Check for overdue reminders that haven't been acknowledged.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of alert dictionaries for overdue reminders
        """
        alerts = []
        now = datetime.now()
        
        user_data = self.user_data.get(user_id)
        if not user_data:
            return alerts
        
        preferences = user_data.get("reminder_preferences", self._get_default_reminder_preferences())
        reminder_history = user_data.get("reminder_history", [])
        
        # Get sent reminders that haven't been acknowledged
        for idx, reminder in enumerate(reminder_history):
            # Skip if not sent or already acknowledged
            if reminder.get("Reminder Sent (Yes/No)") != "Yes":
                continue
            
            if reminder.get("Acknowledged (Yes/No)") == "Yes":
                continue
            
            reminder_type = reminder.get("Reminder Type", "").lower()
            
            # Get max delay for this reminder type
            max_delay = 60  # Default 60 minutes
            if reminder_type in preferences:
                max_delay = preferences[reminder_type].get("max_delay", 60)
            
            # Check if reminder is overdue
            sent_time = datetime.now()  # In a real system, we'd use the actual sent time
            if (now - sent_time).total_seconds() / 60 > max_delay:
                # Determine alert level based on reminder priority
                priority = "medium"
                if reminder_type in preferences:
                    priority = preferences[reminder_type].get("priority", "medium")
                
                level = "info"
                if priority == "high":
                    level = "warning"
                
                # Create alert
                timestamp = now.isoformat()
                alert = {
                    "timestamp": timestamp,
                    "level": level,
                    "type": "reminder_overdue",
                    "message": f"Overdue {reminder_type} reminder: {reminder.get('content', 'No content')}",
                    "reminder_type": reminder_type,
                    "reminder_id": idx,
                    "delay_minutes": int((now - sent_time).total_seconds() / 60)
                }
                
                alerts.append(alert)
                
                # Store alert in database
                db.insert("alerts", {
                    "user_id": user_id,
                    "source": "daily_assistant",
                    "level": level,
                    "message": alert["message"],
                    "resolved": False,
                    "resolution_details": ""
                })
        
        if alerts:
            self.logger.info(f"Generated {len(alerts)} overdue reminder alerts for user {user_id}")
        
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
    
    async def process_reminder_data(self, reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming reminder data.
        
        Args:
            reminder_data: Dictionary containing reminder data
            
        Returns:
            Processing results
        """
        user_id = reminder_data.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing user_id in reminder data"
            }
        
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Process acknowledgment
        acknowledgment = reminder_data.get("acknowledgment", False)
        reminder_id = reminder_data.get("reminder_id")
        
        if acknowledgment and reminder_id is not None:
            # Find the reminder in history
            found = False
            if "reminder_history" in self.user_data[user_id]:
                for idx, reminder in enumerate(self.user_data[user_id]["reminder_history"]):
                    if idx == reminder_id:
                        # Mark as acknowledged
                        reminder["Acknowledged (Yes/No)"] = "Yes"
                        found = True
                        break
            
            # Update database
            if found:
                # In a real system, we'd update the specific reminder in the database
                db.insert("events", {
                    "user_id": user_id,
                    "event_type": "reminder_acknowledged",
                    "details": {
                        "reminder_id": reminder_id,
                        "timestamp": datetime.now().isoformat()
                    }
                })
                
                self.logger.info(f"User {user_id} acknowledged reminder {reminder_id}")
        
        # Add new reminder if provided
        new_reminder = reminder_data.get("new_reminder")
        if new_reminder:
            # Add to upcoming reminders
            if "upcoming_reminders" in self.user_data[user_id]:
                now = datetime.now()
                
                # Create reminder structure
                reminder = {
                    "user_id": user_id,
                    "reminder_type": new_reminder.get("type", "custom"),
                    "content": new_reminder.get("content", "Custom reminder"),
                    "scheduled_time": new_reminder.get("scheduled_time", (now + timedelta(hours=1)).isoformat()),
                    "created_at": now.isoformat(),
                    "sent": False,
                    "acknowledged": False
                }
                
                self.user_data[user_id]["upcoming_reminders"].append(reminder)
                
                # Sort by scheduled time
                self.user_data[user_id]["upcoming_reminders"].sort(key=lambda x: x["scheduled_time"])
                
                self.logger.info(f"Added new {reminder['reminder_type']} reminder for user {user_id}")
        
        # Update reminder preferences if provided
        preferences = reminder_data.get("preferences")
        if preferences:
            if "reminder_preferences" in self.user_data[user_id]:
                self.user_data[user_id]["reminder_preferences"].update(preferences)
            else:
                self.user_data[user_id]["reminder_preferences"] = preferences
            
            self.logger.info(f"Updated reminder preferences for user {user_id}")
        
        # Re-analyze reminder data
        analysis = analyzer.analyze_reminder_data(user_id)
        
        if analysis.get("status") == "success":
            self.reminder_analyses[user_id] = analysis
            self.analysis_timestamps[user_id] = datetime.now()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(user_id, analysis)
        
        # Generate LLM analysis if needed
        llm_analysis = ""
        if acknowledgment or new_reminder or preferences:
            llm_analysis = await self._generate_llm_analysis(user_id, analysis, recommendations)
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis if analysis.get("status") == "success" else None,
            "upcoming_reminders": self.user_data[user_id].get("upcoming_reminders", [])[:5],  # Next 5 reminders
            "recommendations": recommendations,
            "llm_analysis": llm_analysis
        }
    
    def _generate_recommendations(
        self, 
        user_id: str, 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on reminder analysis.
        
        Args:
            user_id: ID of the user
            analysis: Reminder analysis results
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        if analysis.get("status") != "success":
            return recommendations
        
        # Check acknowledgment rate
        acknowledgment_rate = analysis.get("acknowledgment_rate", 0)
        
        if acknowledgment_rate < 50:
            recommendations.append({
                "type": "reminder_method",
                "message": "Consider changing reminder delivery method to improve acknowledgment rate",
                "action": "adjust_settings",
                "priority": "high"
            })
        
        # Check acknowledgment by type
        by_type = analysis.get("acknowledgment_by_type", {})
        
        for reminder_type, stats in by_type.items():
            if stats.get("rate", 0) < 50 and stats.get("sent", 0) > 3:
                recommendations.append({
                    "type": "reminder_timing",
                    "message": f"Adjust timing for {reminder_type} reminders to improve acknowledgment rate",
                    "action": "adjust_timing",
                    "reminder_type": reminder_type,
                    "priority": "medium"
                })
        
        # Check if additional reminders might be needed
        reminder_counts = analysis.get("reminder_counts", {})
        
        # Hard-coded recommendations for demo purposes
        if "Hydration" not in reminder_counts or reminder_counts.get("Hydration", 0) < 3:
            recommendations.append({
                "type": "add_reminder",
                "message": "Consider adding more hydration reminders throughout the day",
                "action": "add_reminders",
                "reminder_type": "Hydration",
                "priority": "medium"
            })
        
        if "Exercise" not in reminder_counts or reminder_counts.get("Exercise", 0) < 1:
            recommendations.append({
                "type": "add_reminder",
                "message": "Add exercise reminders to promote physical activity",
                "action": "add_reminders",
                "reminder_type": "Exercise",
                "priority": "medium"
            })
        
        return recommendations
    
    async def _generate_llm_analysis(
        self, 
        user_id: str, 
        analysis: Dict[str, Any], 
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an LLM analysis of reminder data.
        
        Args:
            user_id: ID of the user
            analysis: Reminder analysis results
            recommendations: List of recommendation dictionaries
            
        Returns:
            LLM analysis string
        """
        # Skip if analysis wasn't successful
        if analysis.get("status") != "success":
            return ""
        
        # Create a detailed prompt for the LLM
        ack_rate = analysis.get("acknowledgment_rate", 0)
        reminder_counts = analysis.get("reminder_counts", {})
        recommendation_text = "\n".join([f"- {rec['message']}" for rec in recommendations])
        
        prompt = f"""
        Please analyze the following reminder data for user {user_id}:
        
        Overall acknowledgment rate: {ack_rate:.1f}%
        
        Reminder types and counts:
        {', '.join([f"{type}: {count}" for type, count in reminder_counts.items()])}
        
        Recommendations:
        {recommendation_text if recommendations else "No specific recommendations."}
        
        Please provide a brief analysis of the reminder patterns, suggestions for improving
        adherence, and any other insights that would help optimize the reminder system.
        """
        
        # Generate response
        return await self.generate_llm_response(
            prompt,
            max_tokens=200,
            temperature=0.7,
            response_type="reminder_analysis"
        )
    
    async def get_reminder_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get the current reminder status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing reminder status
        """
        if user_id not in self.reminder_analyses:
            # If we don't have an analysis, generate one
            analysis = analyzer.analyze_reminder_data(user_id)
            
            if analysis.get("status") == "success":
                self.reminder_analyses[user_id] = analysis
                self.analysis_timestamps[user_id] = datetime.now()
            else:
                return {
                    "status": "error",
                    "message": f"No reminder data available for user {user_id}"
                }
        
        analysis = self.reminder_analyses[user_id]
        
        # Get upcoming reminders
        upcoming_reminders = []
        if user_id in self.user_data and "upcoming_reminders" in self.user_data[user_id]:
            upcoming_reminders = self.user_data[user_id]["upcoming_reminders"][:5]  # Next 5 reminders
        
        # Get recent alerts
        recent_alerts = []
        if user_id in self.user_data and "alert_history" in self.user_data[user_id]:
            recent_alerts = self.user_data[user_id]["alert_history"][-5:]  # Last 5 alerts
        
        # Generate recommendations
        recommendations = self._generate_recommendations(user_id, analysis)
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": self.analysis_timestamps.get(user_id, datetime.now()).isoformat(),
            "analysis": analysis,
            "upcoming_reminders": upcoming_reminders,
            "alerts": recent_alerts,
            "recommendations": recommendations,
            "summary": self._generate_reminder_summary(analysis, upcoming_reminders)
        }
    
    def _generate_reminder_summary(
        self, 
        analysis: Dict[str, Any], 
        upcoming_reminders: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a human-readable summary of reminder status.
        
        Args:
            analysis: Reminder analysis results
            upcoming_reminders: List of upcoming reminder dictionaries
            
        Returns:
            Summary string
        """
        # Generate a simple text summary
        ack_rate = analysis.get("acknowledgment_rate", 0)
        reminder_status = analysis.get("reminder_status", "unknown")
        
        summary = f"Reminder acknowledgment rate: {ack_rate:.1f}%. "
        
        if upcoming_reminders:
            next_reminder = upcoming_reminders[0]
            scheduled_time = datetime.fromisoformat(next_reminder["scheduled_time"])
            reminder_type = next_reminder["reminder_type"]
            
            summary += f"Next reminder: {reminder_type} at {scheduled_time.strftime('%H:%M')}. "
        
        if reminder_status == "normal":
            summary += "Reminder adherence is good."
        elif reminder_status == "attention":
            summary += "Reminder adherence needs some attention."
        else:  # alert
            summary += "Reminder adherence requires immediate intervention."
        
        return summary
    
    async def update_reminder_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update reminder preferences for a user.
        
        Args:
            user_id: ID of the user
            preferences: Dictionary of reminder preferences
            
        Returns:
            Updated preferences
        """
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Update preferences
        if "reminder_preferences" in self.user_data[user_id]:
            self.user_data[user_id]["reminder_preferences"].update(preferences)
        else:
            self.user_data[user_id]["reminder_preferences"] = preferences
        
        self.logger.info(f"Updated reminder preferences for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "preferences": self.user_data[user_id]["reminder_preferences"]
        }
    
    async def add_reminder(
        self, 
        user_id: str, 
        reminder_type: str, 
        content: str, 
        scheduled_time: str
    ) -> Dict[str, Any]:
        """
        Add a new reminder for a user.
        
        Args:
            user_id: ID of the user
            reminder_type: Type of reminder
            content: Reminder content
            scheduled_time: Scheduled time for the reminder (ISO format)
            
        Returns:
            Added reminder
        """
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Validate scheduled time
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_time)
        except:
            return {
                "status": "error",
                "message": "Invalid scheduled_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."
            }
        
        now = datetime.now()
        
        # Create reminder
        reminder = {
            "user_id": user_id,
            "reminder_type": reminder_type,
            "content": content,
            "scheduled_time": scheduled_time,
            "created_at": now.isoformat(),
            "sent": False,
            "acknowledged": False
        }
        
        # Add to upcoming reminders
        if "upcoming_reminders" in self.user_data[user_id]:
            self.user_data[user_id]["upcoming_reminders"].append(reminder)
            
            # Sort by scheduled time
            self.user_data[user_id]["upcoming_reminders"].sort(key=lambda x: x["scheduled_time"])
        
        self.logger.info(f"Added new {reminder_type} reminder for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "reminder": reminder
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
        
        if message_type == "reminder_data":
            return await self.process_reminder_data(message.get("data", {}))
        
        elif message_type == "get_status":
            user_id = message.get("user_id")
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in get_status request"
                }
            
            return await self.get_reminder_status(user_id)
        
        elif message_type == "update_preferences":
            user_id = message.get("user_id")
            preferences = message.get("preferences", {})
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in update_preferences request"
                }
            
            return await self.update_reminder_preferences(user_id, preferences)
        
        elif message_type == "add_reminder":
            user_id = message.get("user_id")
            reminder_type = message.get("reminder_type")
            content = message.get("content")
            scheduled_time = message.get("scheduled_time")
            
            if not user_id or not reminder_type or not content or not scheduled_time:
                return {
                    "status": "error",
                    "message": "Missing parameters in add_reminder request"
                }
            
            return await self.add_reminder(user_id, reminder_type, content, scheduled_time)
        
        else:
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }