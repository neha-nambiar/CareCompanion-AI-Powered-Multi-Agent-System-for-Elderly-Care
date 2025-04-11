"""
Analytics utilities for the CareCompanion system.
Provides functions for data analysis and processing.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta

from utils.logger import setup_logger
from utils.config import config

logger = setup_logger("analytics")

class DataAnalyzer:
    """
    Data analysis utilities for the CareCompanion system.
    """
    
    def __init__(self):
        """
        Initialize the DataAnalyzer.
        """
        self.data_path = config.get_data_path()
        self.health_data = None
        self.safety_data = None
        self.reminder_data = None
        
        # Load data if available
        self._load_data()
    
    def _load_data(self) -> None:
        """
        Load data from CSV files.
        """
        try:
            # Health monitoring data
            health_path = os.path.join(self.data_path, "health_monitoring.csv")
            if os.path.exists(health_path):
                self.health_data = pd.read_csv(health_path)
                logger.info(f"Loaded health data: {len(self.health_data)} records")
            else:
                logger.warning(f"Health data file not found at {health_path}")
            
            # Safety monitoring data
            safety_path = os.path.join(self.data_path, "safety_monitoring.csv")
            if os.path.exists(safety_path):
                self.safety_data = pd.read_csv(safety_path)
                logger.info(f"Loaded safety data: {len(self.safety_data)} records")
            else:
                logger.warning(f"Safety data file not found at {safety_path}")
            
            # Reminder data
            reminder_path = os.path.join(self.data_path, "daily_reminder.csv")
            if os.path.exists(reminder_path):
                self.reminder_data = pd.read_csv(reminder_path)
                logger.info(f"Loaded reminder data: {len(self.reminder_data)} records")
            else:
                logger.warning(f"Reminder data file not found at {reminder_path}")
        
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def get_user_ids(self) -> List[str]:
        """
        Get a list of unique user IDs across all datasets.
        
        Returns:
            List of unique user IDs
        """
        user_ids = set()
        
        if self.health_data is not None:
            user_ids.update(self.health_data["Device-ID/User-ID"].unique())
        
        if self.safety_data is not None:
            user_ids.update(self.safety_data["Device-ID/User-ID"].unique())
        
        if self.reminder_data is not None:
            user_ids.update(self.reminder_data["Device-ID/User-ID"].unique())
        
        return sorted(list(user_ids))
    
    def get_user_health_data(self, user_id: str) -> Optional[pd.DataFrame]:
        """
        Get health data for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            DataFrame with user's health data or None if not found
        """
        if self.health_data is None:
            logger.warning("Health data not loaded")
            return None
        
        user_data = self.health_data[self.health_data["Device-ID/User-ID"] == user_id]
        
        if len(user_data) == 0:
            logger.warning(f"No health data found for user {user_id}")
            return None
        
        return user_data
    
    def get_user_safety_data(self, user_id: str) -> Optional[pd.DataFrame]:
        """
        Get safety data for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            DataFrame with user's safety data or None if not found
        """
        if self.safety_data is None:
            logger.warning("Safety data not loaded")
            return None
        
        user_data = self.safety_data[self.safety_data["Device-ID/User-ID"] == user_id]
        
        if len(user_data) == 0:
            logger.warning(f"No safety data found for user {user_id}")
            return None
        
        return user_data
    
    def get_user_reminder_data(self, user_id: str) -> Optional[pd.DataFrame]:
        """
        Get reminder data for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            DataFrame with user's reminder data or None if not found
        """
        if self.reminder_data is None:
            logger.warning("Reminder data not loaded")
            return None
        
        user_data = self.reminder_data[self.reminder_data["Device-ID/User-ID"] == user_id]
        
        if len(user_data) == 0:
            logger.warning(f"No reminder data found for user {user_id}")
            return None
        
        return user_data
    
    def analyze_health_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze health metrics for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with analysis results
        """
        user_data = self.get_user_health_data(user_id)
        
        if user_data is None or len(user_data) == 0:
            return {
                "status": "error",
                "message": f"No health data available for user {user_id}"
            }
        
        try:
            # Convert timestamp to datetime for sorting
            user_data = user_data.copy()
            user_data["Timestamp"] = pd.to_datetime(user_data["Timestamp"])
            
            # Sort by timestamp
            user_data = user_data.sort_values("Timestamp")
            
            # Get the most recent reading
            latest = user_data.iloc[-1]
            
            # Calculate statistics for heart rate
            hr_stats = {
                "current": int(latest["Heart Rate"]),
                "mean": float(user_data["Heart Rate"].mean()),
                "min": int(user_data["Heart Rate"].min()),
                "max": int(user_data["Heart Rate"].max()),
                "above_threshold": latest["Heart Rate Below/Above Threshold (Yes/No)"] == "Yes"
            }
            
            # Process blood pressure
            bp_values = []
            bp_systolic = []
            bp_diastolic = []
            
            for bp in user_data["Blood Pressure"]:
                try:
                    parts = bp.split("/")
                    systolic = int(parts[0].strip())
                    diastolic = int(parts[1].split(" ")[0].strip())
                    bp_systolic.append(systolic)
                    bp_diastolic.append(diastolic)
                    bp_values.append((systolic, diastolic))
                except:
                    pass
            
            latest_bp = latest["Blood Pressure"]
            latest_bp_parts = latest_bp.split("/")
            latest_systolic = int(latest_bp_parts[0].strip())
            latest_diastolic = int(latest_bp_parts[1].split(" ")[0].strip())
            
            bp_stats = {
                "current": latest_bp,
                "current_systolic": latest_systolic,
                "current_diastolic": latest_diastolic,
                "mean_systolic": float(np.mean(bp_systolic)) if bp_systolic else None,
                "mean_diastolic": float(np.mean(bp_diastolic)) if bp_diastolic else None,
                "min_systolic": int(min(bp_systolic)) if bp_systolic else None,
                "max_systolic": int(max(bp_systolic)) if bp_systolic else None,
                "min_diastolic": int(min(bp_diastolic)) if bp_diastolic else None,
                "max_diastolic": int(max(bp_diastolic)) if bp_diastolic else None,
                "above_threshold": latest["Blood Pressure Below/Above Threshold (Yes/No)"] == "Yes"
            }
            
            # Calculate statistics for glucose
            glucose_stats = {
                "current": int(latest["Glucose Levels"]),
                "mean": float(user_data["Glucose Levels"].mean()),
                "min": int(user_data["Glucose Levels"].min()),
                "max": int(user_data["Glucose Levels"].max()),
                "above_threshold": latest["Glucose Levels Below/Above Threshold (Yes/No)"] == "Yes"
            }
            
            # Calculate statistics for oxygen
            oxygen_stats = {
                "current": int(latest["Oxygen Saturation (SpO₂%)"]),
                "mean": float(user_data["Oxygen Saturation (SpO₂%)"].mean()),
                "min": int(user_data["Oxygen Saturation (SpO₂%)"].min()),
                "max": int(user_data["Oxygen Saturation (SpO₂%)"].max()),
                "below_threshold": latest["SpO₂ Below Threshold (Yes/No)"] == "Yes"
            }
            
            # Count alerts
            alert_count = len(user_data[user_data["Alert Triggered (Yes/No)"] == "Yes"])
            
            # Check latest alerts
            latest_alert = latest["Alert Triggered (Yes/No)"] == "Yes"
            latest_caregiver_notified = latest["Caregiver Notified (Yes/No)"] == "Yes"
            
            # Determine overall health status
            health_concerns = []
            
            if hr_stats["above_threshold"]:
                health_concerns.append("Heart rate outside normal range")
            
            if bp_stats["above_threshold"]:
                health_concerns.append("Blood pressure outside normal range")
            
            if glucose_stats["above_threshold"]:
                health_concerns.append("Glucose levels outside normal range")
            
            if oxygen_stats["below_threshold"]:
                health_concerns.append("Oxygen Saturation (SpO₂%) below threshold")
            
            if len(health_concerns) == 0:
                status = "normal"
            elif len(health_concerns) == 1:
                status = "attention"
            else:
                status = "alert"
            
            return {
                "status": "success",
                "timestamp": latest["Timestamp"],
                "heart_rate": hr_stats,
                "blood_pressure": bp_stats,
                "glucose": glucose_stats,
                "oxygen": oxygen_stats,
                "alert_count": alert_count,
                "latest_alert": latest_alert,
                "latest_caregiver_notified": latest_caregiver_notified,
                "health_status": status,
                "health_concerns": health_concerns
            }
        
        except Exception as e:
            logger.error(f"Error analyzing health metrics: {e}")
            return {
                "status": "error",
                "message": f"Error analyzing health metrics: {str(e)}"
            }
    
    def analyze_safety_data(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze safety data for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with analysis results
        """
        user_data = self.get_user_safety_data(user_id)
        
        if user_data is None or len(user_data) == 0:
            return {
                "status": "error",
                "message": f"No safety data available for user {user_id}"
            }
        
        try:
            # Convert timestamp to datetime for sorting
            user_data = user_data.copy()
            user_data["Timestamp"] = pd.to_datetime(user_data["Timestamp"])
            
            # Sort by timestamp
            user_data = user_data.sort_values("Timestamp")
            
            # Get the most recent reading
            latest = user_data.iloc[-1]
            
            # Analyze movement activity
            movement_counts = user_data["Movement Activity"].value_counts().to_dict()
            most_common_activity = user_data["Movement Activity"].value_counts().idxmax()
            
            # Analyze location
            location_counts = user_data["Location"].value_counts().to_dict()
            most_common_location = user_data["Location"].value_counts().idxmax()
            
            # Analyze falls
            fall_count = len(user_data[user_data["Fall Detected (Yes/No)"] == "Yes"])
            has_falls = fall_count > 0
            
            latest_fall = latest["Fall Detected (Yes/No)"] == "Yes"
            latest_location = latest["Location"]
            latest_activity = latest["Movement Activity"]
            latest_alert = latest["Alert Triggered (Yes/No)"] == "Yes"
            latest_caregiver_notified = latest["Caregiver Notified (Yes/No)"] == "Yes"
            
            # Calculate inactivity patterns
            inactivity_count = len(user_data[user_data["Movement Activity"] == "No Movement"])
            inactivity_percentage = (inactivity_count / len(user_data)) * 100
            
            # Determine post-fall inactivity statistics
            post_fall_times = user_data["Post-Fall Inactivity Duration (Seconds)"]
            post_fall_stats = {
                "mean": float(post_fall_times.mean()),
                "max": int(post_fall_times.max()),
                "current": int(latest["Post-Fall Inactivity Duration (Seconds)"])
            }
            
            # Analyze time spent in each location
            location_times = {}
            for location in location_counts.keys():
                location_data = user_data[user_data["Location"] == location]
                location_times[location] = len(location_data)
            
            # Determine overall safety status
            safety_concerns = []
            
            if latest_fall:
                safety_concerns.append("Recent fall detected")
            
            if has_falls:
                safety_concerns.append("History of falls")
            
            if inactivity_percentage > 50:
                safety_concerns.append("High levels of inactivity")
            
            if latest_activity == "No Movement" and latest["Post-Fall Inactivity Duration (Seconds)"] > 300:
                safety_concerns.append("Extended period of no movement")
            
            if len(safety_concerns) == 0:
                status = "normal"
            elif len(safety_concerns) == 1:
                status = "attention"
            else:
                status = "alert"
            
            return {
                "status": "success",
                "timestamp": latest["Timestamp"],
                "current_location": latest_location,
                "current_activity": latest_activity,
                "movement_counts": movement_counts,
                "most_common_activity": most_common_activity,
                "location_counts": location_counts,
                "most_common_location": most_common_location,
                "fall_count": fall_count,
                "latest_fall": latest_fall,
                "latest_alert": latest_alert,
                "latest_caregiver_notified": latest_caregiver_notified,
                "inactivity_percentage": inactivity_percentage,
                "post_fall_stats": post_fall_stats,
                "location_times": location_times,
                "safety_status": status,
                "safety_concerns": safety_concerns
            }
        
        except Exception as e:
            logger.error(f"Error analyzing safety data: {e}")
            return {
                "status": "error",
                "message": f"Error analyzing safety data: {str(e)}"
            }
    
    def analyze_reminder_data(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze reminder data for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with analysis results
        """
        user_data = self.get_user_reminder_data(user_id)
        
        if user_data is None or len(user_data) == 0:
            return {
                "status": "error",
                "message": f"No reminder data available for user {user_id}"
            }
        
        try:
            # Convert timestamp to datetime for sorting
            user_data = user_data.copy()
            user_data["Timestamp"] = pd.to_datetime(user_data["Timestamp"])
            
            # Sort by timestamp
            user_data = user_data.sort_values("Timestamp")
            
            # Get the most recent reading
            latest = user_data.iloc[-1]
            
            # Analyze reminder types
            reminder_counts = user_data["Reminder Type"].value_counts().to_dict()
            most_common_reminder = user_data["Reminder Type"].value_counts().idxmax()
            
            # Calculate reminder response rates
            sent_reminders = user_data[user_data["Reminder Sent (Yes/No)"] == "Yes"]
            acknowledged_reminders = sent_reminders[sent_reminders["Acknowledged (Yes/No)"] == "Yes"]
            
            sent_count = len(sent_reminders)
            acknowledged_count = len(acknowledged_reminders)
            
            if sent_count > 0:
                acknowledgment_rate = (acknowledged_count / sent_count) * 100
            else:
                acknowledgment_rate = 0
            
            # Calculate acknowledgment rates by type
            acknowledgment_by_type = {}
            for reminder_type in reminder_counts.keys():
                type_sent = sent_reminders[sent_reminders["Reminder Type"] == reminder_type]
                type_acknowledged = type_sent[type_sent["Acknowledged (Yes/No)"] == "Yes"]
                
                if len(type_sent) > 0:
                    rate = (len(type_acknowledged) / len(type_sent)) * 100
                else:
                    rate = 0
                
                acknowledgment_by_type[reminder_type] = {
                    "sent": len(type_sent),
                    "acknowledged": len(type_acknowledged),
                    "rate": rate
                }
            
            # Get upcoming reminders (we'll simulate this since there's no real-time data)
            upcoming_reminders = []
            for _, row in user_data.iterrows():
                if row["Reminder Sent (Yes/No)"] == "No":
                    upcoming_reminders.append({
                        "type": row["Reminder Type"],
                        "scheduled_time": row["Scheduled Time"],
                        "timestamp": row["Timestamp"]
                    })
            
            # Limit to next 5 upcoming reminders
            upcoming_reminders = upcoming_reminders[:5]
            
            # Determine overall reminder status
            reminder_concerns = []
            
            if acknowledgment_rate < 50:
                reminder_concerns.append("Low overall reminder acknowledgment rate")
            
            for reminder_type, stats in acknowledgment_by_type.items():
                if stats["rate"] < 50 and stats["sent"] > 3:
                    reminder_concerns.append(f"Low acknowledgment rate for {reminder_type} reminders")
            
            if len(reminder_concerns) == 0:
                status = "normal"
            elif len(reminder_concerns) == 1:
                status = "attention"
            else:
                status = "alert"
            
            return {
                "status": "success",
                "timestamp": latest["Timestamp"],
                "reminder_counts": reminder_counts,
                "most_common_reminder": most_common_reminder,
                "sent_count": sent_count,
                "acknowledged_count": acknowledged_count,
                "acknowledgment_rate": acknowledgment_rate,
                "acknowledgment_by_type": acknowledgment_by_type,
                "upcoming_reminders": upcoming_reminders,
                "reminder_status": status,
                "reminder_concerns": reminder_concerns
            }
        
        except Exception as e:
            logger.error(f"Error analyzing reminder data: {e}")
            return {
                "status": "error",
                "message": f"Error analyzing reminder data: {str(e)}"
            }
    
    def get_comprehensive_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive status report for a user combining all data sources.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with comprehensive status information
        """
        health_analysis = self.analyze_health_metrics(user_id)
        safety_analysis = self.analyze_safety_data(user_id)
        reminder_analysis = self.analyze_reminder_data(user_id)
        
        # Determine overall well-being status
        overall_concerns = []
        
        if health_analysis.get("status") == "success":
            overall_concerns.extend(health_analysis.get("health_concerns", []))
        
        if safety_analysis.get("status") == "success":
            overall_concerns.extend(safety_analysis.get("safety_concerns", []))
        
        if reminder_analysis.get("status") == "success":
            overall_concerns.extend(reminder_analysis.get("reminder_concerns", []))
        
        if len(overall_concerns) == 0:
            overall_status = "normal"
        elif len(overall_concerns) <= 2:
            overall_status = "attention"
        else:
            overall_status = "alert"
        
        # Create a detailed status message
        status_message = self._generate_status_message(
            overall_status, 
            health_analysis, 
            safety_analysis, 
            reminder_analysis
        )
        
        # Determine if emergency response is needed
        emergency_response_needed = False
        emergency_type = None
        
        if health_analysis.get("status") == "success":
            if health_analysis.get("health_status") == "alert" and health_analysis.get("latest_alert", False):
                emergency_response_needed = True
                emergency_type = "health"
        
        if safety_analysis.get("status") == "success":
            if safety_analysis.get("latest_fall", False):
                emergency_response_needed = True
                emergency_type = "fall"
        
        return {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "health": health_analysis if health_analysis.get("status") == "success" else None,
            "safety": safety_analysis if safety_analysis.get("status") == "success" else None,
            "reminders": reminder_analysis if reminder_analysis.get("status") == "success" else None,
            "overall_status": overall_status,
            "overall_concerns": overall_concerns,
            "status_message": status_message,
            "emergency_response_needed": emergency_response_needed,
            "emergency_type": emergency_type
        }
    
    def _generate_status_message(
        self, 
        overall_status: str, 
        health_analysis: Dict[str, Any], 
        safety_analysis: Dict[str, Any], 
        reminder_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate a human-readable status message.
        
        Args:
            overall_status: Overall status level
            health_analysis: Health analysis results
            safety_analysis: Safety analysis results
            reminder_analysis: Reminder analysis results
            
        Returns:
            Status message string
        """
        if overall_status == "normal":
            message = "All systems normal. "
            
            if health_analysis.get("status") == "success":
                message += "Vital signs are within expected ranges. "
            
            if safety_analysis.get("status") == "success":
                location = safety_analysis.get("current_location", "unknown location")
                activity = safety_analysis.get("current_activity", "unknown activity")
                message += f"Currently {activity} in the {location}. "
            
            if reminder_analysis.get("status") == "success":
                ack_rate = reminder_analysis.get("acknowledgment_rate", 0)
                message += f"Reminder acknowledgment rate is {ack_rate:.1f}%. "
            
            message += "No immediate concerns detected."
        
        elif overall_status == "attention":
            message = "Some issues require attention. "
            
            # Add specific concerns
            concerns = []
            
            if health_analysis.get("status") == "success":
                concerns.extend(health_analysis.get("health_concerns", []))
            
            if safety_analysis.get("status") == "success":
                concerns.extend(safety_analysis.get("safety_concerns", []))
            
            if reminder_analysis.get("status") == "success":
                concerns.extend(reminder_analysis.get("reminder_concerns", []))
            
            if concerns:
                message += "Concerns: " + "; ".join(concerns) + ". "
            
            message += "Please monitor these issues closely."
        
        else:  # alert
            message = "ALERT: Immediate attention required. "
            
            # Add specific concerns
            concerns = []
            
            if health_analysis.get("status") == "success":
                concerns.extend(health_analysis.get("health_concerns", []))
            
            if safety_analysis.get("status") == "success":
                concerns.extend(safety_analysis.get("safety_concerns", []))
            
            if reminder_analysis.get("status") == "success":
                concerns.extend(reminder_analysis.get("reminder_concerns", []))
            
            if concerns:
                message += "Critical issues: " + "; ".join(concerns) + ". "
            
            message += "Immediate action recommended."
        
        return message


# Create a global analyzer instance
analyzer = DataAnalyzer()
