"""
Health Monitor Agent for the CareCompanion system.
Monitors health metrics and detects anomalies.
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

class HealthMonitorAgent(BaseAgent):
    """
    Agent responsible for monitoring health metrics and detecting anomalies.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Health Monitor Agent.
        
        Args:
            config: Configuration object
        """
        super().__init__(name="health_monitor", config=config)
        
        # Load health thresholds from config
        self.thresholds = config.get("agents.health_monitor.thresholds", {})
        
        # Initialize user-specific data
        self.user_data = {}
        
        # Cache for health analyses
        self.health_analyses = {}
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
        
        self.logger.info(f"Initialized health data for {len(user_ids)} users")
    
    async def _initialize_user_data(self, user_id: str) -> None:
        """
        Initialize data for a specific user.
        
        Args:
            user_id: ID of the user
        """
        self.user_data[user_id] = {
            "health_history": [],
            "alert_history": [],
            "personalized_thresholds": self._get_default_thresholds()
        }
        
        # Analyze health data
        analysis = analyzer.analyze_health_metrics(user_id)
        
        if analysis.get("status") == "success":
            self.health_analyses[user_id] = analysis
            self.analysis_timestamps[user_id] = datetime.now()
            
            # Store health history
            health_data = analyzer.get_user_health_data(user_id)
            if health_data is not None:
                # Convert to list of dictionaries for internal storage
                self.user_data[user_id]["health_history"] = health_data.to_dict(orient="records")
            
            # Calculate personalized thresholds based on historical data
            personalized_thresholds = self._calculate_personalized_thresholds(user_id, analysis)
            self.user_data[user_id]["personalized_thresholds"] = personalized_thresholds
    
    def _get_default_thresholds(self) -> Dict[str, Dict[str, int]]:
        """
        Get default health thresholds from configuration.
        
        Returns:
            Dictionary containing default thresholds
        """
        return {
            "heart_rate": {
                "min": self.thresholds.get("heart_rate", {}).get("min", 60),
                "max": self.thresholds.get("heart_rate", {}).get("max", 100)
            },
            "blood_pressure_systolic": {
                "min": self.thresholds.get("blood_pressure_systolic", {}).get("min", 90),
                "max": self.thresholds.get("blood_pressure_systolic", {}).get("max", 140)
            },
            "blood_pressure_diastolic": {
                "min": self.thresholds.get("blood_pressure_diastolic", {}).get("min", 60),
                "max": self.thresholds.get("blood_pressure_diastolic", {}).get("max", 90)
            },
            "glucose": {
                "min": self.thresholds.get("glucose", {}).get("min", 70),
                "max": self.thresholds.get("glucose", {}).get("max", 140)
            },
            "oxygen": {
                "min": self.thresholds.get("oxygen", {}).get("min", 95),
                "max": self.thresholds.get("oxygen", {}).get("max", 100)
            }
        }
    
    def _calculate_personalized_thresholds(
        self, 
        user_id: str, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Dict[str, int]]:
        """
        Calculate personalized thresholds based on historical data.
        
        Args:
            user_id: ID of the user
            analysis: Health analysis results
            
        Returns:
            Dictionary containing personalized thresholds
        """
        personalized = self._get_default_thresholds()
        
        # Only personalize if we have sufficient health history
        if user_id in self.user_data and len(self.user_data[user_id]["health_history"]) >= 5:
            try:
                # Heart rate thresholds
                if "heart_rate" in analysis:
                    hr_stats = analysis["heart_rate"]
                    # Set thresholds based on historical data with some margin
                    personalized["heart_rate"]["min"] = max(int(hr_stats["mean"] - 15), 50)
                    personalized["heart_rate"]["max"] = min(int(hr_stats["mean"] + 15), 150)
                
                # Blood pressure thresholds
                if "blood_pressure" in analysis:
                    bp_stats = analysis["blood_pressure"]
                    if "mean_systolic" in bp_stats and bp_stats["mean_systolic"]:
                        personalized["blood_pressure_systolic"]["min"] = max(int(bp_stats["mean_systolic"] - 15), 85)
                        personalized["blood_pressure_systolic"]["max"] = min(int(bp_stats["mean_systolic"] + 15), 160)
                    
                    if "mean_diastolic" in bp_stats and bp_stats["mean_diastolic"]:
                        personalized["blood_pressure_diastolic"]["min"] = max(int(bp_stats["mean_diastolic"] - 10), 50)
                        personalized["blood_pressure_diastolic"]["max"] = min(int(bp_stats["mean_diastolic"] + 10), 100)
                
                # Glucose thresholds
                if "glucose" in analysis:
                    glucose_stats = analysis["glucose"]
                    personalized["glucose"]["min"] = max(int(glucose_stats["mean"] - 20), 65)
                    personalized["glucose"]["max"] = min(int(glucose_stats["mean"] + 20), 180)
                
                # Oxygen thresholds (less personalization for safety)
                if "oxygen" in analysis:
                    oxygen_stats = analysis["oxygen"]
                    personalized["oxygen"]["min"] = max(int(oxygen_stats["mean"] - 3), 90)
                    personalized["oxygen"]["max"] = 100  # Always 100% max
                
                self.logger.info(f"Generated personalized thresholds for user {user_id}")
            
            except Exception as e:
                self.logger.error(f"Error calculating personalized thresholds: {e}")
        
        return personalized
    
    async def update(self) -> None:
        """
        Perform periodic health monitoring update.
        """
        await super().update()
        
        # Update health analyses for all users
        for user_id in self.user_data.keys():
            # Check if analysis is older than the update interval
            if (user_id not in self.analysis_timestamps or 
                (datetime.now() - self.analysis_timestamps.get(user_id, datetime.min)).total_seconds() > self.update_interval):
                # Re-analyze health data
                analysis = analyzer.analyze_health_metrics(user_id)
                
                if analysis.get("status") == "success":
                    # Update analysis and timestamp
                    self.health_analyses[user_id] = analysis
                    self.analysis_timestamps[user_id] = datetime.now()
                    
                    # Check for alerts
                    alerts = self._generate_health_alerts(user_id, analysis)
                    
                    # Store alerts
                    if alerts:
                        self.user_data[user_id]["alert_history"].extend(alerts)
                        
                        # Keep only recent alerts (last 20)
                        self.user_data[user_id]["alert_history"] = self.user_data[user_id]["alert_history"][-20:]
                        
                        # Report alerts to coordination agent
                        await self._report_alerts(user_id, alerts)
    
    def _generate_health_alerts(self, user_id: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate health alerts based on analysis results.
        
        Args:
            user_id: ID of the user
            analysis: Health analysis results
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        timestamp = datetime.now().isoformat()
        
        try:
            # Get personalized thresholds
            thresholds = self.user_data.get(user_id, {}).get("personalized_thresholds", self._get_default_thresholds())
            
            # Check heart rate
            if "heart_rate" in analysis:
                hr = analysis["heart_rate"]
                hr_value = hr.get("current")
                
                if hr_value < thresholds["heart_rate"]["min"]:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "warning",
                        "type": "heart_rate_low",
                        "message": f"Heart rate below threshold: {hr_value} bpm (min: {thresholds['heart_rate']['min']})",
                        "value": hr_value,
                        "threshold": thresholds["heart_rate"]["min"],
                        "comparison": "below"
                    })
                elif hr_value > thresholds["heart_rate"]["max"]:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "warning",
                        "type": "heart_rate_high",
                        "message": f"Heart rate above threshold: {hr_value} bpm (max: {thresholds['heart_rate']['max']})",
                        "value": hr_value,
                        "threshold": thresholds["heart_rate"]["max"],
                        "comparison": "above"
                    })
            
            # Check blood pressure
            if "blood_pressure" in analysis:
                bp = analysis["blood_pressure"]
                systolic = bp.get("current_systolic")
                diastolic = bp.get("current_diastolic")
                
                if systolic and diastolic:
                    # Check systolic
                    if systolic < thresholds["blood_pressure_systolic"]["min"]:
                        alerts.append({
                            "timestamp": timestamp,
                            "level": "warning",
                            "type": "blood_pressure_systolic_low",
                            "message": f"Systolic blood pressure below threshold: {systolic} mmHg (min: {thresholds['blood_pressure_systolic']['min']})",
                            "value": systolic,
                            "threshold": thresholds["blood_pressure_systolic"]["min"],
                            "comparison": "below"
                        })
                    elif systolic > thresholds["blood_pressure_systolic"]["max"]:
                        alerts.append({
                            "timestamp": timestamp,
                            "level": "warning" if systolic < 160 else "urgent",
                            "type": "blood_pressure_systolic_high",
                            "message": f"Systolic blood pressure above threshold: {systolic} mmHg (max: {thresholds['blood_pressure_systolic']['max']})",
                            "value": systolic,
                            "threshold": thresholds["blood_pressure_systolic"]["max"],
                            "comparison": "above"
                        })
                    
                    # Check diastolic
                    if diastolic < thresholds["blood_pressure_diastolic"]["min"]:
                        alerts.append({
                            "timestamp": timestamp,
                            "level": "warning",
                            "type": "blood_pressure_diastolic_low",
                            "message": f"Diastolic blood pressure below threshold: {diastolic} mmHg (min: {thresholds['blood_pressure_diastolic']['min']})",
                            "value": diastolic,
                            "threshold": thresholds["blood_pressure_diastolic"]["min"],
                            "comparison": "below"
                        })
                    elif diastolic > thresholds["blood_pressure_diastolic"]["max"]:
                        alerts.append({
                            "timestamp": timestamp,
                            "level": "warning" if diastolic < 100 else "urgent",
                            "type": "blood_pressure_diastolic_high",
                            "message": f"Diastolic blood pressure above threshold: {diastolic} mmHg (max: {thresholds['blood_pressure_diastolic']['max']})",
                            "value": diastolic,
                            "threshold": thresholds["blood_pressure_diastolic"]["max"],
                            "comparison": "above"
                        })
            
            # Check glucose
            if "glucose" in analysis:
                glucose = analysis["glucose"]
                glucose_value = glucose.get("current")
                
                if glucose_value < thresholds["glucose"]["min"]:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "warning" if glucose_value > 60 else "urgent",
                        "type": "glucose_low",
                        "message": f"Glucose level below threshold: {glucose_value} mg/dL (min: {thresholds['glucose']['min']})",
                        "value": glucose_value,
                        "threshold": thresholds["glucose"]["min"],
                        "comparison": "below"
                    })
                elif glucose_value > thresholds["glucose"]["max"]:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "warning" if glucose_value < 180 else "urgent",
                        "type": "glucose_high",
                        "message": f"Glucose level above threshold: {glucose_value} mg/dL (max: {thresholds['glucose']['max']})",
                        "value": glucose_value,
                        "threshold": thresholds["glucose"]["max"],
                        "comparison": "above"
                    })
            
            # Check oxygen
            if "oxygen" in analysis:
                oxygen = analysis["oxygen"]
                oxygen_value = oxygen.get("current")
                
                if oxygen_value < thresholds["oxygen"]["min"]:
                    alerts.append({
                        "timestamp": timestamp,
                        "level": "warning" if oxygen_value > 92 else "urgent",
                        "type": "oxygen_low",
                        "message": f"Oxygen saturation below threshold: {oxygen_value}% (min: {thresholds['oxygen']['min']})",
                        "value": oxygen_value,
                        "threshold": thresholds["oxygen"]["min"],
                        "comparison": "below"
                    })
            
            # Store alerts in database
            for alert in alerts:
                db.insert("alerts", {
                    "user_id": user_id,
                    "source": "health_monitor",
                    "level": alert["level"],
                    "message": alert["message"],
                    "resolved": False,
                    "resolution_details": ""
                })
            
            if alerts:
                self.logger.info(f"Generated {len(alerts)} health alerts for user {user_id}")
        
        except Exception as e:
            self.logger.error(f"Error generating health alerts: {e}")
        
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
    
    async def process_health_data(self, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming health data.
        
        Args:
            health_data: Dictionary containing health data
            
        Returns:
            Processing results
        """
        user_id = health_data.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing user_id in health data"
            }
        
        # Initialize user data if needed
        if user_id not in self.user_data:
            await self._initialize_user_data(user_id)
        
        # Add to health history
        if "health_history" in self.user_data[user_id]:
            self.user_data[user_id]["health_history"].append(health_data)
            
            # Keep history manageable (last 100 entries)
            if len(self.user_data[user_id]["health_history"]) > 100:
                self.user_data[user_id]["health_history"] = self.user_data[user_id]["health_history"][-100:]
        
        # Store in database
        db.insert("health_data", {
            "user_id": user_id,
            "timestamp": health_data.get("timestamp", datetime.now().isoformat()),
            "heart_rate": health_data.get("heart_rate"),
            "blood_pressure": health_data.get("blood_pressure"),
            "glucose": health_data.get("glucose"),
            "oxygen": health_data.get("oxygen")
        })
        
        # Analyze new data
        analysis = self._analyze_health_data(user_id, health_data)
        
        # Update analysis cache
        self.health_analyses[user_id] = analysis
        self.analysis_timestamps[user_id] = datetime.now()
        
        # Generate alerts
        alerts = self._generate_health_alerts(user_id, analysis)
        
        # Add alerts to history
        if alerts:
            self.user_data[user_id]["alert_history"].extend(alerts)
            
            # Keep history manageable (last 20 entries)
            self.user_data[user_id]["alert_history"] = self.user_data[user_id]["alert_history"][-20:]
        
        # Generate LLM analysis if there are alerts
        llm_analysis = ""
        if alerts:
            llm_analysis = await self._generate_llm_analysis(user_id, analysis, alerts)
        
        return {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "alerts": alerts,
            "llm_analysis": llm_analysis
        }
    
    def _analyze_health_data(self, user_id: str, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze health data for a specific user.
        
        Args:
            user_id: ID of the user
            health_data: Dictionary containing health data
            
        Returns:
            Analysis results
        """
        # In a full implementation, this would perform real-time analysis
        # For this demo, we'll leverage our analyzer utility
        analysis = analyzer.analyze_health_metrics(user_id)
        
        if analysis.get("status") != "success":
            # Create a simplified analysis based on the current data
            analysis = {
                "status": "success",
                "timestamp": health_data.get("timestamp", datetime.now().isoformat()),
                "heart_rate": {
                    "current": health_data.get("heart_rate"),
                    "above_threshold": False
                },
                "blood_pressure": {
                    "current": health_data.get("blood_pressure"),
                    "above_threshold": False
                },
                "glucose": {
                    "current": health_data.get("glucose"),
                    "above_threshold": False
                },
                "oxygen": {
                    "current": health_data.get("oxygen"),
                    "below_threshold": False
                },
                "health_status": "normal",
                "health_concerns": []
            }
        
        return analysis
    
    async def _generate_llm_analysis(
        self, 
        user_id: str, 
        analysis: Dict[str, Any], 
        alerts: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an LLM analysis of health data.
        
        Args:
            user_id: ID of the user
            analysis: Health analysis results
            alerts: List of alert dictionaries
            
        Returns:
            LLM analysis string
        """
        # Create a detailed prompt for the LLM
        alert_text = "\n".join([f"- {alert['message']}" for alert in alerts])
        
        prompt = f"""
        Please analyze the following health data for user {user_id}:
        
        Heart Rate: {analysis.get('heart_rate', {}).get('current', 'N/A')} bpm
        Blood Pressure: {analysis.get('blood_pressure', {}).get('current', 'N/A')}
        Glucose: {analysis.get('glucose', {}).get('current', 'N/A')} mg/dL
        Oxygen Saturation: {analysis.get('oxygen', {}).get('current', 'N/A')}%
        
        Alerts detected:
        {alert_text}
        
        Please provide a brief analysis of the health status, potential causes for the alerts,
        and recommended actions for caregivers.
        """
        
        # Generate response
        return await self.generate_llm_response(
            prompt,
            max_tokens=200,
            temperature=0.7,
            response_type="health_analysis"
        )
    
    async def get_health_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get the current health status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing health status
        """
        if user_id not in self.health_analyses:
            # If we don't have an analysis, generate one
            analysis = analyzer.analyze_health_metrics(user_id)
            
            if analysis.get("status") == "success":
                self.health_analyses[user_id] = analysis
                self.analysis_timestamps[user_id] = datetime.now()
            else:
                return {
                    "status": "error",
                    "message": f"No health data available for user {user_id}"
                }
        
        analysis = self.health_analyses[user_id]
        
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
            "summary": self._generate_health_summary(analysis)
        }
    
    def _generate_health_summary(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of health status.
        
        Args:
            analysis: Health analysis results
            
        Returns:
            Summary string
        """
        # Generate a simple text summary
        health_status = analysis.get("health_status", "unknown")
        concerns = analysis.get("health_concerns", [])
        
        if health_status == "normal":
            summary = "Vital signs are within normal ranges. No immediate health concerns."
        elif health_status == "attention":
            summary = f"Health requires attention: {'; '.join(concerns)}"
        else:  # alert
            summary = f"ALERT: Health requires immediate attention: {'; '.join(concerns)}"
        
        return summary
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message received by the agent.
        
        Args:
            message: Message to process
            
        Returns:
            Response to the message
        """
        message_type = message.get("type", "unknown")
        
        if message_type == "health_data":
            return await self.process_health_data(message.get("data", {}))
        
        elif message_type == "get_status":
            user_id = message.get("user_id")
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in get_status request"
                }
            
            return await self.get_health_status(user_id)
        
        elif message_type == "update_thresholds":
            user_id = message.get("user_id")
            thresholds = message.get("thresholds", {})
            
            if not user_id:
                return {
                    "status": "error",
                    "message": "Missing user_id in update_thresholds request"
                }
            
            # Update thresholds
            if user_id in self.user_data:
                if "personalized_thresholds" in self.user_data[user_id]:
                    self.user_data[user_id]["personalized_thresholds"].update(thresholds)
                else:
                    self.user_data[user_id]["personalized_thresholds"] = thresholds
                
                return {
                    "status": "success",
                    "message": f"Updated thresholds for user {user_id}",
                    "thresholds": self.user_data[user_id]["personalized_thresholds"]
                }
            else:
                return {
                    "status": "error",
                    "message": f"User {user_id} not found"
                }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown message type: {message_type}"
            }
