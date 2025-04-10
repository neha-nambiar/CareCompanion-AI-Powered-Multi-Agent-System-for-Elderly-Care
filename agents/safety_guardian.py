"""
Safety Guardian Agent for the CareCompanion system.
Monitors movement patterns, detects falls, and ensures user safety.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.logger import setup_logger
from utils.config import Config
from utils.database import db
from models.analytics import analyzer

class SafetyGuardianAgent(BaseAgent):
    """
    Agent responsible for monitoring safety and detecting falls or unusual movement patterns.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Safety Guardian Agent.
        
        Args:
            config: Configuration object
        """
        super().__init__(name="safety_guardian", config=config)
        
        # Load room settings from config
        self.room_settings = config.get("agents.safety_guardian.room_settings", {})
        
        # Initialize user-specific data
        self.user_data = {}
        
        # Cache for safety analyses
        self.safety_analyses = {}
        self.analysis_timestamps = {}
        
        # Inactivity thresholds in minutes by room
        self.inactivity_thresholds = {}
        for room, settings in self.room_settings.items():
            self.inactivity_thresholds[room] = settings.get("inactivity_threshold", 120)
    
    async def initialize(self) -> None:
        """
        Initialize the agent's state.
        """
        await super().initialize()
        
        # Load user data
        user_ids = analyzer.get_user_ids()
        for user_id in user_ids:
            await self._initialize_user_data(user_id)
        
        self.logger.info(f"Initialized safety data for {len(user_ids)} users")
    
    async def _initialize_user_data(self, user_id: str) -> None:
        """
        Initialize data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        self.user_data[user_id] = {
            "movement_history": [],
            "location_history": [],
            "fall_history": [],
            "alert_history": [],
            "last_activity": None,
            "last_location": None,
            "last_movement_time": None,
            "personalized_thresholds": self._get_default_inactivity_thresholds()
        }
        
        # Analyze safety data
        analysis = analyzer.analyze_safety_data(user_id)
        
        if analysis.get("status") == "success":
            self.safety_analyses[user_id] = analysis
            self.analysis_timestamps[user_id] = datetime.now()
            
            # Store safety history
            safety_data = analyzer.get_user_safety_data(user_id)
            if safety_data is not None:
                # Convert to list of dictionaries for internal storage
                self.user_data[user_id]["movement_history"] = safety_data.to_dict(orient="records")
                
                # Extract location history
                self.user_data[user_id]["location_history"] = [
                    {"timestamp": row["Timestamp"], "location": row["Location"]}
                    for _, row in safety_data.iterrows()
                ]
                
                # Extract fall history
                self.user_data[user_id]["fall_history"] = [
                    {
                        "timestamp": row["Timestamp"],
                        "location": row["Location"],
                        "impact_force": row["Impact Force Level"],
                        "post_fall_inactivity": row["Post-Fall Inactivity Duration (Seconds)"]
                    }
                    for _, row in safety_data.iterrows()
                    if row["Fall Detected (Yes/No)"] == "Yes"
                ]
            
            # Set last activity and location
            if "current_activity" in analysis:
                self.user_data[user_id]["last_activity"] = analysis["current_activity"]
            
            if "current_location" in analysis:
                self.user_data[user_id]["last_location"] = analysis["current_location"]
            
            self.user_data[user_id]["last_movement_time"] = datetime.now()
    
    def _get_default_inactivity_thresholds(self) -> Dict[str, int]:
        """
        Get default inactivity thresholds by room.
        
        Returns:
            Dictionary mapping room names to inactivity thresholds in minutes
        """
        thresholds = {}
        
        for room, settings in self.room_settings.items():
            thresholds[room.lower()] = settings.get("inactivity_threshold", 120)
        
        # Set default thresholds for common rooms if not in config
        if "bedroom" not in thresholds:
            thresholds["bedroom"] = 480  # 8 hours
        
        if "bathroom" not in thresholds:
            thresholds["bathroom"] = 60  # 1 hour
        
        if "living room" not in thresholds:
            thresholds["living room"] = 240  # 4 hours
        
        if "kitchen" not in thresholds:
            thresholds["kitchen"] = 120  # 2 hours
        
        return thresholds
    
    async def update(self) -> None:
        """
        Perform periodic safety monitoring update.
        """
        await super().update()
        
        # Update safety analyses for all users
        for user_id in self.user_data.keys():
            # Check if analysis is older than the update interval
            if (user_id not in self.analysis_timestamps or 
                (datetime.now() - self.analysis_timestamps.get(user_id, datetime.min)).total_seconds() > self.update_interval):
                # Re-analyze safety data
                analysis = analyzer.analyze_safety_data(user_id)
                
                if analysis.get("status") == "success":
                    # Update analysis and timestamp
                    self.safety_analyses[user_id] = analysis
                    self.analysis_timestamps[user_id] = datetime.now()
                    
                    # Check for inactivity alerts based on last known activity
                    inactivity_alerts = self._check_inactivity(user_id)
                    
                    # Store alerts
                    if inactivity_alerts:
                        self.user_data[user_id]["alert_history"].extend(inactivity_alerts)
                        
                        # Keep only recent alerts (last 20)
                        self.user_data[user_id]["alert_history"] = self.user_data[user_id]["alert_history"][-20:]
                        
                        # Report alerts to coordination agent
                        await self._report_alerts(user_id, inactivity_alerts)
    
    def _check_inactivity(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Check if the user has been inactive for too long.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of inactivity alerts if thresholds exceeded
        """
        alerts = []
        
        if user_id not in self.user_data:
            return alerts
        
        user_data = self.user_data[user_id]
        
        # Check if we have last activity time and location
        if not user_data.get("last_movement_time") or not user_data.get("last_location"):
            return alerts
        
        last_activity = user_data.get("last_activity")
        last_location = user_data.get("last_location").lower()
        last_movement_time = user_data.get("last_movement_time")
        
        # Get threshold for this location
        thresholds = user_data.get("personalized_thresholds", self._get_default_inactivity_thresholds())
        threshold_minutes = thresholds.get(last_location, 120)  # Default to 2 hours
        
        # No need to check if activity is not "No Movement"
        if last_activity != "No Movement":
            return alerts
        
        # Calculate inactive time
        now = datetime.now()
        inactive_minutes = (now - last_movement_time).total_seconds() / 60
        
        # Check if threshold exceeded
        if inactive_minutes > threshold_minutes:
            timestamp = datetime.now().isoformat()
            
            # Determine alert level based on how much the threshold is exceeded
            if inactive_minutes > threshold_minutes * 2:
                level = "urgent"
            else:
                level = "warning"
            
            alerts.append({
                "timestamp": timestamp,
                "level": level,
                "type": "excessive_inactivity",
                "message": f"User has been inactive in {last_location} for {int(inactive_minutes)} minutes (threshold: {threshold_minutes} minutes)",
                "location": last_location,
                "inactive_minutes": int(inactive_minutes),
                "threshold_minutes": threshold_minutes
            })
            
            # Store alert in database
            db.insert("alerts", {
                "user_id": user_id,
                "source": "safety_guardian",
                "level": level,
                "message": f"User has been inactive in {last_location} for {int(inactive_minutes)} minutes",
                "resolved": False,
                "resolution_details": ""
            })
            
            self.logger.info(f"Inactivity alert generated for user {user_id}: inactive for {int(inactive_minutes)} minutes in {last_location}")
        
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
    
    async def process_safety_data(self, safety_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming safety data.
        
        Args:
            safety_data: Dictionary containing safety data
            
        Returns:
            Processing results
        """
        user_id = safety_data.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing user_id in safety data"
            }
        
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Add to movement history
        if "movement_history" in self.user_data[user_id]:
            self.user_data[user_id]["movement_history"].append(safety_data)
            
            # Keep history manageable (last 100 entries)
            if len(self.user_data[user_id]["movement_history"]) > 100:
                self.user_data[user_id]["movement_history"] = self.user_data[user_id]["movement_history"][-100:]
        
        # Add to location history
        if "location_history" in self.user_data[user_id]:
            self.user_data[user_id]["location_history"].append({
                "timestamp": safety_data.get("timestamp", datetime.now().isoformat()),
                "location": safety_data.get("location")
            })
            
            # Keep history manageable (last 100 entries)
            if len(self.user_data[user_id]["location_history"]) > 100:
                self.user_data[user_id]["location_history"] = self.user_data[user_id]["location_history"][-100:]
        
        # Check for fall and add to fall history if detected
        is_fall_detected = safety_data.get("fall_detected", "No") == "Yes"
        
        if is_fall_detected and "fall_history" in self.user_data[user_id]:
            self.user_data[user_id]["fall_history"].append({
                "timestamp": safety_data.get("timestamp", datetime.now().isoformat()),
                "location": safety_data.get("location"),
                "impact_force": safety_data.get("impact_force", "-"),
                "post_fall_inactivity": safety_data.get("post_fall_inactivity", 0)
            })
        
        # Update last activity, location, and movement time
        self.user_data[user_id]["last_activity"] = safety_data.get("movement_activity")
        self.user_data[user_id]["last_location"] = safety_data.get("location")
        self.user_data[user_id]["last_movement_time"] = datetime.now()
        
        # Store in database
        db.insert("safety_data", {
            "user_id": user_id,
            "timestamp": safety_data.get("timestamp", datetime.now().isoformat()),
            "location": safety_data.get("location", "unknown"),
            "activity": safety_data.get("movement_activity", "unknown"),
            "fall_detected": is_fall_detected,
            "unusual_activity": self._is_unusual_activity(safety_data.get("movement_activity"), safety_data.get("location")),
            "inactive_too_long": False  # We'll check this in the update method
        })
        
        # Analyze safety data
        analysis = self._analyze_safety_data(user_id, safety_data)
        
        # Update analysis cache
        self.safety_analyses[user_id] = analysis
        self.analysis_timestamps[user_id] = datetime.now()
        
        # Generate alerts
        alerts = self._generate_safety_alerts(user_id, safety_data, analysis)
        
        # Add alerts to history
        if alerts:
            self.user_data[user_id]["alert_history"].extend(alerts)
            
            # Keep history manageable (last 20 entries)
            self.user_data[user_id]["alert_history"] = self.user_data[user_id]["alert_history"][-20:]
        
        # Generate LLM analysis if there are alerts or a fall
        llm_analysis = ""
        if alerts or is_fall_detected:
            llm_analysis = await self._generate_llm_analysis(user_id, safety_data, analysis, alerts)
        
        # Check for emergency conditions
        emergency = is_fall_detected or any(alert["level"] == "urgent" for alert in alerts)
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "alerts": alerts,
            "emergency": emergency,
            "llm_analysis": llm_analysis
        }
    
    def _is_unusual_activity(self, activity: Optional[str], location: Optional[str]) -> bool:
        """
        Check if an activity is unusual for a particular location.
        
        Args:
            activity: Current activity
            location: Current location
            
        Returns:
            True if activity is unusual for the location, False otherwise
        """
        if not activity or not location:
            return False
        
        location = location.lower()
        
        # Get expected activities for this location
        expected_activities = []
        
        if location in self.room_settings:
            expected_activities = self.room_settings[location].get("expected_activities", [])
        
        # If no expected activities defined, nothing is unusual
        if not expected_activities:
            return False
        
        # Check if current activity is expected
        return activity not in expected_activities
    
    def _analyze_safety_data(self, user_id: str, safety_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze safety data for a specific user.
        
        Args:
            user_id: ID of the user
            safety_data: Dictionary containing safety data
            
        Returns:
            Analysis results
        """
        # In a full implementation, this would perform real-time analysis
        # For this demo, we'll leverage our analyzer utility
        analysis = analyzer.analyze_safety_data(user_id)
        
        if analysis.get("status") != "success":
            # Create a simplified analysis based on the current data
            analysis = {
                "status": "success",
                "timestamp": safety_data.get("timestamp", datetime.now().isoformat()),
                "current_location": safety_data.get("location", "unknown"),
                "current_activity": safety_data.get("movement_activity", "unknown"),
                "fall_count": 0,
                "latest_fall": safety_data.get("fall_detected", "No") == "Yes",
                "safety_status": "normal",
                "safety_concerns": []
            }
        
        return analysis
    
    def _generate_safety_alerts(
        self, 
        user_id: str, 
        safety_data: Dict[str, Any], 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate safety alerts based on the data and analysis.
        
        Args:
            user_id: ID of the user
            safety_data: Safety data dictionary
            analysis: Analysis results
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        timestamp = datetime.now().isoformat()
        
        try:
            # Check for fall
            if safety_data.get("fall_detected", "No") == "Yes":
                alerts.append({
                    "timestamp": timestamp,
                    "level": "urgent",
                    "type": "fall_detected",
                    "message": f"Fall detected in {safety_data.get('location', 'unknown')}",
                    "location": safety_data.get("location"),
                    "impact_force": safety_data.get("impact_force", "-"),
                    "post_fall_inactivity": safety_data.get("post_fall_inactivity", 0)
                })
            
            # Check for unusual activity
            if self._is_unusual_activity(safety_data.get("movement_activity"), safety_data.get("location")):
                alerts.append({
                    "timestamp": timestamp,
                    "level": "info",
                    "type": "unusual_activity",
                    "message": f"Unusual activity detected: {safety_data.get('movement_activity')} in {safety_data.get('location')}",
                    "activity": safety_data.get("movement_activity"),
                    "location": safety_data.get("location")
                })
            
            # Check for movement pattern anomalies from analysis
            if "movement_counts" in analysis:
                movement_counts = analysis["movement_counts"]
                total_movements = sum(movement_counts.values())
                
                # Check for excessive inactivity
                if "No Movement" in movement_counts and movement_counts["No Movement"] / total_movements > 0.7:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "warning",
                        "type": "excessive_inactivity_pattern",
                        "message": "Excessive 'No Movement' activity detected in movement patterns",
                        "percentage": movement_counts["No Movement"] / total_movements * 100
                    })
                
                # Check for limited walking
                if "Walking" not in movement_counts or movement_counts.get("Walking", 0) / total_movements < 0.1:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "info",
                        "type": "limited_walking",
                        "message": "Limited walking activity detected in movement patterns",
                        "percentage": movement_counts.get("Walking", 0) / total_movements * 100 if "Walking" in movement_counts else 0
                    })
            
            # Check location changes (potential mobility issues)
            if "location_history" in self.user_data[user_id] and len(self.user_data[user_id]["location_history"]) > 10:
                # Count unique locations in last 24 hours
                unique_locations = set()
                for entry in self.user_data[user_id]["location_history"]:
                    unique_locations.add(entry["location"])
                
                if len(unique_locations) == 1:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "info",
                        "type": "limited_mobility",
                        "message": f"User has remained only in {next(iter(unique_locations))} for extended period",
                        "location": next(iter(unique_locations))
                    })
            
            # Store alerts in database
            for alert in alerts:
                db.insert("alerts", {
                    "user_id": user_id,
                    "source": "safety_guardian",
                    "level": alert["level"],
                    "message": alert["message"],
                    "resolved": False,
                    "resolution_details": ""
                })
            
            if alerts:
                self.logger.info(f"Generated {len(alerts)} safety alerts for user {user_id}")
        
        except Exception as e:
            self.logger.error(f"Error generating safety alerts: {e}")
        
        return alerts
    
    async def _generate_llm_analysis(
        self, 
        user_id: str, 
        safety_data: Dict[str, Any], 
        analysis: Dict[str, Any], 
        alerts: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an LLM analysis of safety data.
        
        Args:
            user_id: ID of the user
            safety_data: Safety data dictionary
            analysis: Safety analysis results
            alerts: List of alert dictionaries
            
        Returns:
            LLM analysis string
        """
        # Create a detailed prompt for the LLM
        alert_text = "\n".join([f"- {alert['message']}" for alert in alerts])
        
        location = safety_data.get("location", "unknown")
        activity = safety_data.get("movement_activity", "unknown")
        fall_detected = "Yes" if safety_data.get("fall_detected", "No") == "Yes" else "No"
        
        prompt = f"""
        Please analyze the following safety data for user {user_id}:
        
        Current Location: {location}
        Current Activity: {activity}
        Fall Detected: {fall_detected}
        
        Alerts detected:
        {alert_text}
        
        Please provide a brief analysis of the safety situation, potential causes for any issues,
        and recommended actions for caregivers.
        """
        
        # Generate response
        return await self.generate_llm_response(
            prompt,
            max_tokens=200,
            temperature=0.7,
            response_type="safety_analysis"
        )
    
    async def get_safety_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get the current safety status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing safety status
        """
        if user_id not in self.safety_analyses:
            # If we don't have an analysis, generate one
            analysis = analyzer.analyze_safety_data(user_id)
            
            if analysis.get("status") == "success":
                self.safety_analyses[user_id] = analysis
                self.analysis_timestamps[user_id] = datetime.now()
            else:
                return {
                    "status": "error",
                    "message": f"No safety data available for user {user_id}"
                }
        
        analysis = self.safety_analyses[user_id]
        
        # Get recent alerts
        recent_alerts = []
        if user_id in self.user_data and "alert_history" in self.user_data[user_id]:
            recent_alerts = self.user_data[user_id]["alert_history"][-5:]  # Last 5 alerts
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": self.analysis_timestamps.get(user_id, datetime.now()).isoformat(),
            "analysis": analysis,
            "alerts": recent_alerts,
            "summary": self._generate_safety_summary(analysis)
        }
    
    def _generate_safety_summary(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of safety status.
        
        Args:
            analysis: Safety analysis results
            
        Returns:
            Summary string
        """
        # Generate a simple text summary
        safety_status = analysis.get("safety_status", "unknown")
        concerns = analysis.get("safety_concerns", [])
        location = analysis.get("current_location", "unknown")
        activity = analysis.get("current_activity", "unknown")
        
        summary = f"Currently {activity} in {location}. "
        
        if safety_status == "normal":
            summary += "No safety concerns detected."
        elif safety_status == "attention":
            summary += f"Safety requires attention: {'; '.join(concerns)}"
        else:  # alert
            summary += f"ALERT: Safety requires immediate action: {'; '.join(concerns)}"
        
        return summary
    
    async def update_room_settings(self, room_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings for a specific room.
        
        Args:
            room_name: Name of the room
            settings: Settings dictionary
            
        Returns:
            Updated settings
        """
        room_name = room_name.lower()
        
        # Update room settings
        if room_name in self.room_settings:
            self.room_settings[room_name].update(settings)
        else:
            self.room_settings[room_name] = settings
        
        # Update inactivity thresholds if specified
        if "inactivity_threshold" in settings:
            self.inactivity_thresholds[room_name] = settings["inactivity_threshold"]
        
        self.logger.info(f"Updated settings for room: {room_name}")
        
        return {
            "status": "success",
            "room": room_name,
            "settings": self.room_settings[room_name]
        }
    
    async def update_inactivity_threshold(
        self, 
        user_id: str, 
        room: str, 
        threshold_minutes: int
    ) -> Dict[str, Any]:
        """
        Update inactivity threshold for a specific user and room.
        
        Args:
            user_id: ID of the user
            room: Name of the room
            threshold_minutes: Inactivity threshold in minutes
            
        Returns:
            Updated thresholds
        """
        room = room.lower()
        
        # Validate threshold
        if threshold_minutes < 5:
            return {
                "status": "error",
                "message": "Threshold too low. Minimum is 5 minutes."
            }
        
        if threshold_minutes > 720:  # 12 hours
            return {
                "status": "error",
                "message": "Threshold too high. Maximum is 720 minutes (12 hours)."
            }
        
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Update personalized threshold
        if "personalized_thresholds" not in self.user_data[user_id]:
            self.user_data[user_id]["personalized_thresholds"] = self._get_default_inactivity_thresholds()
        
        self.user_data[user_id]["personalized_thresholds"][room] = threshold_minutes
        
        self.logger.info(f"Updated inactivity threshold for user {user_id}, room {room}: {threshold_minutes} minutes")
        
        return {
            "status": "success",
            "user_id": user_id,
            "room": room,
            "threshold_minutes": threshold_minutes,
            "thresholds": self.user_data[user_id]["personalized_thresholds"]
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
        
        if message_type == "safety_data":
            return await self.process_safety_data(message.get("data", {}))
        
        elif message_type == "get_status":
            user_id = message.get("user_id")
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in get_status request"
                }
            
            return await self.get_safety_status(user_id)
        
        elif message_type == "update_room_settings":
            room_name = message.get("room_name")
            settings = message.get("settings", {})
            
            if not room_name:
                return {
                    "status": "error",
                    "message": "Missing room_name in update_room_settings request"
                }
            
            return await self.update_room_settings(room_name, settings)
        
        elif message_type == "update_inactivity_threshold":
            user_id = message.get("user_id")
            room = message.get("room")
            threshold_minutes = message.get("threshold_minutes")
            
            if not user_id or not room or not threshold_minutes:
                return {
                    "status": "error",
                    "message": "Missing parameters in update_inactivity_threshold request"
                }
            
            return await self.update_inactivity_threshold(user_id, room, threshold_minutes)
        
        else:
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }