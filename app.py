"""
Main application entry point for the CareCompanion system.
Initializes and coordinates all agents and components.
"""

import asyncio
import os
import pandas as pd
from datetime import datetime, timedelta
import argparse
import random
import time
import signal
import sys
from typing import Dict, Any, List, Optional, Tuple

from utils.config import Config
from utils.logger import setup_logger, system_logger
from utils.database import db, initialize_database
from models.analytics import analyzer
from agents.health_monitor import HealthMonitorAgent
from agents.safety_guardian import SafetyGuardianAgent
from agents.daily_assistant import DailyAssistantAgent
# Removed: from agents.social_engagement import SocialEngagementAgent
from agents.emergency_response import EmergencyResponseAgent
from agents.coordination import CoordinationAgent

# Create logger
logger = setup_logger("app")

# Global variables for clean shutdown
agents = []
running = True
sim_task = None

async def initialize_system(config: Config) -> Dict[str, Any]:
    """
    Initialize the CareCompanion system.
    
    Args:
        config: Configuration object
        
    Returns:
        Dictionary containing initialized agents
    """
    logger.info("Initializing CareCompanion system...")
    
    # Initialize database
    initialize_database()
    
    # Initialize agents
    health_agent = HealthMonitorAgent(config)
    safety_agent = SafetyGuardianAgent(config)
    daily_agent = DailyAssistantAgent(config)
    # Removed: social_agent = SocialEngagementAgent(config)
    emergency_agent = EmergencyResponseAgent(config)
    coordination_agent = CoordinationAgent(config)
    
    # Set agent references in coordination agent
    coordination_agent.set_agents(
        health_agent,
        safety_agent,
        daily_agent,
        # Removed: social_agent,
        emergency_agent
    )
    
    # Store agents in global list for clean shutdown
    global agents
    agents = [
        health_agent,
        safety_agent,
        daily_agent,
        # Removed: social_agent,
        emergency_agent,
        coordination_agent
    ]
    
    # Start all agents
    start_tasks = [agent.start() for agent in agents]
    await asyncio.gather(*start_tasks)
    
    logger.info("All agents started successfully")
    
    return {
        "health_agent": health_agent,
        "safety_agent": safety_agent,
        "daily_agent": daily_agent,
        # Removed: "social_agent": social_agent,
        "emergency_agent": emergency_agent,
        "coordination_agent": coordination_agent
    }

async def data_simulation(coordination_agent: CoordinationAgent) -> None:
    """
    Run a simulation of incoming data for testing.
    
    Args:
        coordination_agent: Coordination Agent for handling data
    """
    logger.info("Starting data simulation...")
    
    # Load and preprocess data
    try:
        safety_data = pd.read_csv("data/safety_monitoring.csv")
        health_data = pd.read_csv("data/health_monitoring.csv")
        reminder_data = pd.read_csv("data/daily_reminder.csv")
        
        logger.info(f"Loaded data files: {len(safety_data)} safety records, {len(health_data)} health records, {len(reminder_data)} reminder records")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return
    
    # Get unique user IDs
    user_ids = set(safety_data["Device-ID/User-ID"].unique())
    user_ids.update(health_data["Device-ID/User-ID"].unique())
    user_ids.update(reminder_data["Device-ID/User-ID"].unique())
    
    user_ids = sorted(list(user_ids))
    logger.info(f"Found {len(user_ids)} unique users in data")
    
    # Simulation loop
    global running
    while running:
        try:
            # Select random user
            user_id = random.choice(user_ids)
            
            # Select random data type (removed social)
            data_type = random.choice(["health", "safety", "reminder"])
            
            if data_type == "health":
                # Get random health record for this user
                user_health = health_data[health_data["Device-ID/User-ID"] == user_id]
                if len(user_health) > 0:
                    record = user_health.sample(1).iloc[0].to_dict()
                    
                    # Send to coordination agent
                    await coordination_agent.process_message({
                        "type": "data",
                        "data": {
                            "type": "health",
                            "user_id": user_id,
                            "data": {
                                "timestamp": datetime.now().isoformat(),
                                "heart_rate": record["Heart Rate"],
                                "blood_pressure": record["Blood Pressure"],
                                "glucose": record["Glucose Levels"],
                                "oxygen": record["Oxygen Saturation (SpO₂%)"]
                            }
                        } 
                    })
                    
                    logger.info(f"Sent health data for user {user_id}")
            
            elif data_type == "safety":
                # Get random safety record for this user
                user_safety = safety_data[safety_data["Device-ID/User-ID"] == user_id]
                if len(user_safety) > 0:
                    record = user_safety.sample(1).iloc[0].to_dict()
                    
                    # Send to coordination agent
                    await coordination_agent.process_message({
                        "type": "data",
                        "data": {
                            "type": "safety",
                            "user_id": user_id,
                            "data": {
                                "timestamp": datetime.now().isoformat(),
                                "location": record["Location"],
                                "movement_activity": record["Movement Activity"],
                                "fall_detected": record["Fall Detected (Yes/No)"],
                                "impact_force": record["Impact Force Level"],
                                "post_fall_inactivity": record["Post-Fall Inactivity Duration (Seconds)"]
                            }
                        }
                    })
                    
                    logger.info(f"Sent safety data for user {user_id}")
            
            elif data_type == "reminder":
                # Get random reminder record for this user
                user_reminder = reminder_data[reminder_data["Device-ID/User-ID"] == user_id]
                if len(user_reminder) > 0:
                    record = user_reminder.sample(1).iloc[0].to_dict()
                    
                    # Randomly decide if acknowledged
                    acknowledged = random.choice([True, False])
                    
                    # Send to coordination agent
                    await coordination_agent.process_message({
                        "type": "data",
                        "data": {
                            "type": "reminder",
                            "user_id": user_id,
                            "data": {
                                "timestamp": datetime.now().isoformat(),
                                "reminder_type": record["Reminder Type"],
                                "scheduled_time": record["Scheduled Time"],
                                "acknowledgment": acknowledged
                            }
                        }
                    })
                    
                    logger.info(f"Sent reminder data for user {user_id} (acknowledged: {acknowledged})")
            
            # Random delay between 2-5 seconds
            await asyncio.sleep(random.uniform(2, 5))
        
        except Exception as e:
            logger.error(f"Error in simulation: {e}")
            await asyncio.sleep(1)

def handle_exit(signum, frame):
    """
    Handle exit signals for clean shutdown.
    """
    logger.info("Received exit signal, shutting down...")
    global running
    running = False

async def shutdown_system():
    """
    Shutdown the system gracefully.
    """
    global sim_task
    
    # Cancel simulation task if running
    if sim_task and not sim_task.done():
        sim_task.cancel()
        try:
            await sim_task
        except asyncio.CancelledError:
            pass
    
    # Allow agents to perform cleanup
    logger.info("Shutting down agents...")
    
    # In a more complete implementation, each agent would have a shutdown method
    
    # Save database state
    db_path = "data/carecompanion.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db.save_to_file(db_path)
    logger.info(f"Database state saved to {db_path}")
    
    logger.info("Shutdown complete")

async def main():
    """
    Main application entry point.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CareCompanion Multi-Agent System")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--simulate", action="store_true", help="Run data simulation")
    args = parser.parse_args()
    
    # Load configuration
    config = Config(args.config)
    
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Initialize system
        system = await initialize_system(config)
        coordination_agent = system["coordination_agent"]
        
        logger.info("CareCompanion system initialized successfully")
        
        # Start data simulation if requested
        if args.simulate:
            global sim_task
            sim_task = asyncio.create_task(data_simulation(coordination_agent))
        
        # Main application loop
        global running
        while running:
            # In a real application, this would handle UI events, API requests, etc.
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main application: {e}")
    finally:
        await shutdown_system()

if __name__ == "__main__":
    asyncio.run(main())
