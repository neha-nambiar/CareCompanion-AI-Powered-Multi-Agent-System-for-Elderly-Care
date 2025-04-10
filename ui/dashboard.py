"""
Streamlit dashboard for the CareCompanion system.
Provides visualizations and interfaces for monitoring elderly users.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import time as time_module
from datetime import datetime, timedelta
import random
from typing import Dict, Any, List, Optional

# Set page title and icon
st.set_page_config(
    page_title="CareCompanion Dashboard",
    page_icon="❤️",
    layout="wide"
)

# Initialize session state for storing data between reruns
if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

if "active_alerts" not in st.session_state:
    st.session_state.active_alerts = []

if "system_status" not in st.session_state:
    st.session_state.system_status = {
        "active_users": 0,
        "active_alerts": 0,
        "active_emergencies": 0,
        "user_status_counts": {
            "normal": 0,
            "attention": 0,
            "alert": 0,
            "emergency": 0,
            "unknown": 0
        },
        "agents_status": {
            "health_monitor": True,
            "safety_guardian": True,
            "daily_assistant": True,
            "social_engagement": True,
            "emergency_response": True
        },
        "started_at": datetime.now().isoformat(),
        "uptime": "0h 0m 0s"
    }

# Functions to simulate API calls to the backend
def fetch_system_status():
    """
    Fetch system status from backend.
    In this demo, we'll simulate the response.
    """
    # Load data files to get user counts
    try:
        safety_data = pd.read_csv("data/safety_monitoring.csv")
        user_ids = safety_data["Device-ID/User-ID"].unique()
        
        # Generate simulated system status
        now = datetime.now()
        started_at = datetime.now() - timedelta(hours=random.randint(1, 24))
        uptime_seconds = (now - started_at).total_seconds()
        
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        # Generate random count for each status
        total_users = len(user_ids)
        
        # Distribution by status (mostly normal, some attention, few alerts/emergencies)
        status_counts = {
            "normal": int(total_users * 0.6),
            "attention": int(total_users * 0.25),
            "alert": int(total_users * 0.1),
            "emergency": int(total_users * 0.02),
            "unknown": total_users - int(total_users * 0.97)  # Remainder
        }
        
        # Simulate active alerts (1-2 per user not in normal state)
        active_alerts = sum(status_counts.values()) - status_counts["normal"]
        active_emergencies = status_counts["emergency"]
        
        # All agents are running in this simulation
        agents_status = {
            "health_monitor": True,
            "safety_guardian": True,
            "daily_assistant": True,
            "social_engagement": True,
            "emergency_response": True
        }
        
        return {
            "status": "success",
            "timestamp": now.isoformat(),
            "active_users": total_users,
            "active_alerts": active_alerts,
            "active_emergencies": active_emergencies,
            "user_status_counts": status_counts,
            "agents_status": agents_status,
            "started_at": started_at.isoformat(),
            "uptime": uptime
        }
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return st.session_state.system_status

def fetch_user_list():
    """
    Fetch list of users from backend.
    In this demo, we'll get the list from data files.
    """
    try:
        # Load data files to get unique user IDs
        safety_data = pd.read_csv("data/safety_monitoring.csv")
        health_data = pd.read_csv("data/health_monitoring.csv")
        reminder_data = pd.read_csv("data/daily_reminder.csv")
        
        # Combine user IDs from all data sources
        user_ids = set(safety_data["Device-ID/User-ID"].unique())
        user_ids.update(health_data["Device-ID/User-ID"].unique())
        user_ids.update(reminder_data["Device-ID/User-ID"].unique())
        
        user_list = []
        
        for user_id in user_ids:
            # Assign a random status for demo purposes
            status = random.choice(["normal", "attention", "alert", "emergency", "normal", "normal"])
            
            # Create simulated user info
            user_list.append({
                "user_id": user_id,
                "name": f"User {user_id}",
                "status": status,
                "location": random.choice(["Bedroom", "Living Room", "Kitchen", "Bathroom"]),
                "activity": random.choice(["Sitting", "Walking", "No Movement", "Lying"]),
                "last_update": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat()
            })
        
        return user_list
    
    except Exception as e:
        st.error(f"Error loading user list: {e}")
        return []

def fetch_user_details(user_id):
    """
    Fetch detailed user information.
    In this demo, we'll generate simulated data.
    """
    try:
        # Load data files to get actual data for this user
        safety_data = pd.read_csv("data/safety_monitoring.csv")
        health_data = pd.read_csv("data/health_monitoring.csv")
        reminder_data = pd.read_csv("data/daily_reminder.csv")
        
        # Filter data for this user
        user_safety = safety_data[safety_data["Device-ID/User-ID"] == user_id]
        user_health = health_data[health_data["Device-ID/User-ID"] == user_id]
        user_reminder = reminder_data[reminder_data["Device-ID/User-ID"] == user_id]
        
        # Generate health status
        health_status = {}
        if len(user_health) > 0:
            latest_health = user_health.iloc[-1]
            health_status = {
                "heart_rate": int(latest_health["Heart Rate"]),
                "blood_pressure": latest_health["Blood Pressure"],
                "glucose": int(latest_health["Glucose Levels"]),
                "oxygen": int(latest_health["Oxygen Saturation (SpO₂%)"]),
                "alerts": [],
                "status": "normal" if latest_health["Alert Triggered (Yes/No)"] == "No" else "alert"
            }
            
            # Add simulated alerts if any triggered
            if latest_health["Alert Triggered (Yes/No)"] == "Yes":
                # Check which metrics triggered the alert
                alerts = []
                if latest_health["Heart Rate Below/Above Threshold (Yes/No)"] == "Yes":
                    alerts.append({
                        "level": "warning",
                        "type": "heart_rate",
                        "message": f"Heart rate outside normal range: {health_status['heart_rate']} bpm",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if latest_health["Blood Pressure Below/Above Threshold (Yes/No)"] == "Yes":
                    alerts.append({
                        "level": "warning",
                        "type": "blood_pressure",
                        "message": f"Blood pressure outside normal range: {health_status['blood_pressure']} mmHg",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if latest_health["Glucose Levels Below/Above Threshold (Yes/No)"] == "Yes":
                    alerts.append({
                        "level": "warning",
                        "type": "glucose",
                        "message": f"Glucose level outside normal range: {health_status['glucose']} mg/dL",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if latest_health["SpO₂ Below Threshold (Yes/No)"] == "Yes":
                    alerts.append({
                        "level": "warning",
                        "type": "oxygen",
                        "message": f"Oxygen Saturation (SpO₂%) below threshold: {health_status['oxygen']}%",
                        "timestamp": datetime.now().isoformat()
                    })
                
                health_status["alerts"] = alerts
        
        # Generate safety status
        safety_status = {}
        if len(user_safety) > 0:
            latest_safety = user_safety.iloc[-1]
            safety_status = {
                "location": latest_safety["Location"],
                "activity": latest_safety["Movement Activity"],
                "fall_detected": latest_safety["Fall Detected (Yes/No)"] == "Yes",
                "alerts": [],
                "status": "normal"
            }
            
            # Add simulated alerts
            alerts = []
            if latest_safety["Fall Detected (Yes/No)"] == "Yes":
                alerts.append({
                    "level": "urgent",
                    "type": "fall",
                    "message": f"Fall detected in {safety_status['location']}",
                    "timestamp": datetime.now().isoformat()
                })
                safety_status["status"] = "emergency"
            
            elif latest_safety["Alert Triggered (Yes/No)"] == "Yes":
                if latest_safety["Movement Activity"] == "No Movement":
                    alerts.append({
                        "level": "warning",
                        "type": "inactivity",
                        "message": f"Extended inactivity detected in {safety_status['location']}",
                        "timestamp": datetime.now().isoformat()
                    })
                    safety_status["status"] = "attention"
            
            safety_status["alerts"] = alerts
        
        # Generate reminder status
        reminder_status = {}
        if len(user_reminder) > 0:
            latest_reminder = user_reminder.iloc[-1]
            
            # Get upcoming reminders (next 3)
            upcoming = []
            for _, row in user_reminder.iterrows():
                if row["Reminder Sent (Yes/No)"] == "No":
                    upcoming.append({
                        "type": row["Reminder Type"],
                        "scheduled_time": row["Scheduled Time"],
                        "sent": False,
                        "acknowledged": False
                    })
                    if len(upcoming) >= 3:
                        break
            
            # Get recently sent reminders
            recent = []
            for _, row in user_reminder.iterrows():
                if row["Reminder Sent (Yes/No)"] == "Yes":
                    recent.append({
                        "type": row["Reminder Type"],
                        "scheduled_time": row["Scheduled Time"],
                        "sent": True,
                        "acknowledged": row["Acknowledged (Yes/No)"] == "Yes"
                    })
                    if len(recent) >= 3:
                        break
            
            # Calculate acknowledgment rate
            sent_count = len(user_reminder[user_reminder["Reminder Sent (Yes/No)"] == "Yes"])
            ack_count = len(user_reminder[(user_reminder["Reminder Sent (Yes/No)"] == "Yes") & 
                                          (user_reminder["Acknowledged (Yes/No)"] == "Yes")])
            
            ack_rate = (ack_count / sent_count * 100) if sent_count > 0 else 0
            
            reminder_status = {
                "upcoming_reminders": upcoming,
                "recent_reminders": recent,
                "acknowledgment_rate": ack_rate,
                "alerts": [],
                "status": "normal" if ack_rate >= 70 else "attention"
            }
            
            # Add alerts for low acknowledgment rate
            if ack_rate < 50:
                reminder_status["alerts"].append({
                    "level": "warning",
                    "type": "low_acknowledgment",
                    "message": f"Low reminder acknowledgment rate: {ack_rate:.1f}%",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Generate social status (simulated since we don't have social data)
        social_status = {
            "weekly_interactions": random.randint(3, 15),
            "last_interaction": {
                "type": random.choice(["video_call", "phone_call", "in_person_visit"]),
                "contact": random.choice(["Family member", "Friend", "Caregiver"]),
                "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat()
            },
            "suggestions": [
                {
                    "type": "video_call",
                    "title": "Schedule a video call with family",
                    "description": "Regular video calls help maintain social connections.",
                    "priority": "medium"
                },
                {
                    "type": "community_event",
                    "title": "Attend local community event",
                    "description": "Community events provide opportunities to meet new people.",
                    "priority": "low"
                }
            ],
            "alerts": [],
            "status": "normal"
        }
        
        # Generate alert if last interaction was more than 48 hours ago
        last_interaction_time = datetime.fromisoformat(social_status["last_interaction"]["timestamp"])
        hours_since = (datetime.now() - last_interaction_time).total_seconds() / 3600
        
        if hours_since > 72:
            social_status["alerts"].append({
                "level": "warning",
                "type": "social_isolation",
                "message": f"Limited social interaction: {int(hours_since)} hours since last contact",
                "timestamp": datetime.now().isoformat()
            })
            social_status["status"] = "attention"
        
        # Combine all alerts
        all_alerts = (
            health_status.get("alerts", []) + 
            safety_status.get("alerts", []) + 
            reminder_status.get("alerts", []) + 
            social_status.get("alerts", [])
        )
        
        # Determine overall status
        statuses = [
            health_status.get("status", "unknown"),
            safety_status.get("status", "unknown"),
            reminder_status.get("status", "unknown"),
            social_status.get("status", "unknown")
        ]
        
        if "emergency" in statuses:
            overall_status = "emergency"
        elif "alert" in statuses:
            overall_status = "alert"
        elif "attention" in statuses:
            overall_status = "attention"
        elif all(status == "normal" for status in statuses if status != "unknown"):
            overall_status = "normal"
        else:
            overall_status = "unknown"
        
        # Generate status summary
        summary = "User is currently "
        if safety_status:
            summary += f"{safety_status.get('activity', 'unknown activity').lower()} in the {safety_status.get('location', 'unknown location').lower()}. "
        
        if overall_status == "normal":
            summary += "All monitored parameters are within normal ranges."
        elif overall_status == "attention":
            summary += f"Some parameters require attention. {len(all_alerts)} active alerts."
        elif overall_status == "alert":
            summary += f"Critical situation detected. {len(all_alerts)} active alerts."
        elif overall_status == "emergency":
            summary += "EMERGENCY SITUATION DETECTED. Immediate response required."
        
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "health": health_status,
            "safety": safety_status,
            "reminders": reminder_status,
            "social": social_status,
            "overall_status": overall_status,
            "summary": summary,
            "alerts": all_alerts
        }
    
    except Exception as e:
        st.error(f"Error fetching user details: {e}")
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "overall_status": "unknown",
            "summary": "Error fetching user details",
            "alerts": []
        }

def update_data():
    """
    Update data in session state.
    """
    # Update system status
    st.session_state.system_status = fetch_system_status()
    
    # Update selected user if one is selected
    if st.session_state.selected_user:
        user_details = fetch_user_details(st.session_state.selected_user)
        st.session_state.user_details = user_details
        st.session_state.active_alerts = user_details.get("alerts", [])

def resolve_alert(alert):
    """
    Resolve an alert (simulated).
    """
    # In a real application, this would call an API endpoint
    if alert in st.session_state.active_alerts:
        st.session_state.active_alerts.remove(alert)
        
        # Show success message
        st.success(f"Alert resolved: {alert.get('message', 'No message')}")
        
        # Refresh data
        time_module.sleep(0.5)  # Simulate API call delay
        update_data()

def handle_user_selection():
    """
    Handle user selection change.
    """
    # Get user details for selected user
    user_details = fetch_user_details(st.session_state.selected_user)
    st.session_state.user_details = user_details
    st.session_state.active_alerts = user_details.get("alerts", [])

# Define color scheme for status levels
status_colors = {
    "normal": "green",
    "attention": "orange",
    "alert": "red",
    "emergency": "darkred",
    "unknown": "gray"
}

# Main dashboard
st.title("CareCompanion Dashboard")
st.markdown("### Elderly Care Monitoring System")

# Refresh button
if st.button("Refresh Data"):
    update_data()
    st.success("Data refreshed successfully!")

# Create two columns for the layout
col1, col2 = st.columns([1, 3])

# Sidebar with user list
with col1:
    st.subheader("System Status")
    
    # Display system metrics
    system_status = st.session_state.system_status
    
    # Create metrics row
    metric1, metric2, metric3 = st.columns(3)
    
    with metric1:
        st.metric("Active Users", system_status["active_users"])
    
    with metric2:
        st.metric("Active Alerts", system_status["active_alerts"])
    
    with metric3:
        st.metric("Emergencies", system_status["active_emergencies"])
    
    # Display agent status
    st.subheader("Agent Status")
    agent_status = system_status["agents_status"]
    
    for agent, status in agent_status.items():
        status_icon = "✅" if status else "❌"
        st.markdown(f"**{agent.replace('_', ' ').title()}**: {status_icon}")
    
    # Display status distribution
    st.subheader("User Status Distribution")
    status_counts = system_status["user_status_counts"]
    
    # Prepare data for chart
    labels = list(status_counts.keys())
    sizes = list(status_counts.values())

    # Filter out NaN values and zeros
    valid_indices = []
    for i, size in enumerate(sizes):
        if not (pd.isna(size) or size == 0):
            valid_indices.append(i)

    filtered_labels = [labels[i] for i in valid_indices]
    filtered_sizes = [sizes[i] for i in valid_indices]
    filtered_colors = [status_colors[status] for status in filtered_labels]

    # Only create pie chart if we have valid data
    if filtered_sizes:
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.warning("No valid status data available")
    
    # Uptime information
    st.markdown(f"**System Uptime**: {system_status['uptime']}")
    
    # User list
    st.subheader("User List")
    
    user_list = fetch_user_list()
    
    # Create selectbox for user selection
    user_options = [f"{user['name']} ({user['status']})" for user in user_list]
    user_dict = {f"{user['name']} ({user['status']})": user["user_id"] for user in user_list}
    
    selected_option = st.selectbox(
        "Select a user to view details:",
        options=user_options,
        index=0 if user_options else None,
        key="user_selector",
        on_change=handle_user_selection
    )
    
    if selected_option:
        st.session_state.selected_user = user_dict[selected_option]
    
    # Create styled user list
    for user in user_list:
        status_color = status_colors.get(user["status"], "gray")
        status_emoji = "🟢" if user["status"] == "normal" else "🟠" if user["status"] == "attention" else "🔴" if user["status"] == "alert" else "⚠️" if user["status"] == "emergency" else "⚪"
        
        st.markdown(
            f"""
            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; border-left: 5px solid {status_color}; background-color: #f0f2f6;">
                <div style="font-weight: bold;">{status_emoji} {user["name"]}</div>
                <div style="font-size: 0.8em;">Location: {user["location"]}</div>
                <div style="font-size: 0.8em;">Activity: {user["activity"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Main content area
with col2:
    # User details section
    if st.session_state.selected_user:
        # Fetch user details if not already in session state
        if "user_details" not in st.session_state:
            user_details = fetch_user_details(st.session_state.selected_user)
            st.session_state.user_details = user_details
            st.session_state.active_alerts = user_details.get("alerts", [])
        else:
            user_details = st.session_state.user_details
        
        # User header with status
        user_name = user_details.get("name", f"User {st.session_state.selected_user}")
        status = user_details.get("overall_status", "unknown")
        status_color = status_colors.get(status, "gray")
        
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <div style="font-size: 24px; font-weight: bold; margin-right: 10px;">{user_name}</div>
                <div style="background-color: {status_color}; color: white; padding: 5px 10px; border-radius: 15px; font-size: 14px;">
                    {status.upper()}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Summary
        st.markdown(f"**Summary**: {user_details.get('summary', 'No summary available')}")
        
        # Create tabs for different categories
        tabs = st.tabs(["Overview", "Health", "Safety", "Reminders", "Social", "Alerts"])
        
        # Overview tab
        with tabs[0]:
            st.subheader("Current Status")
            
            # Create metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                health_status = user_details.get("health", {}).get("status", "unknown")
                health_color = status_colors.get(health_status, "gray")
                st.markdown(f"Health: <span style='color: {health_color};'>{health_status.title()}</span>", unsafe_allow_html=True)
            
            with col2:
                safety_status = user_details.get("safety", {}).get("status", "unknown")
                safety_color = status_colors.get(safety_status, "gray")
                st.markdown(f"Safety: <span style='color: {safety_color};'>{safety_status.title()}</span>", unsafe_allow_html=True)
            
            with col3:
                reminder_status = user_details.get("reminders", {}).get("status", "unknown")
                reminder_color = status_colors.get(reminder_status, "gray")
                st.markdown(f"Reminders: <span style='color: {reminder_color};'>{reminder_status.title()}</span>", unsafe_allow_html=True)
            
            with col4:
                social_status = user_details.get("social", {}).get("status", "unknown")
                social_color = status_colors.get(social_status, "gray")
                st.markdown(f"Social: <span style='color: {social_color};'>{social_status.title()}</span>", unsafe_allow_html=True)
            
            # Current location and activity
            st.subheader("Current Activity")
            location = user_details.get("safety", {}).get("location", "Unknown")
            activity = user_details.get("safety", {}).get("activity", "Unknown")
            
            st.markdown(f"Location: **{location}**")
            st.markdown(f"Activity: **{activity}**")
            
            # Recent alerts
            st.subheader("Recent Alerts")
            active_alerts = user_details.get("alerts", [])
            
            if active_alerts:
                for alert in active_alerts:
                    level = alert.get("level", "info")
                    message = alert.get("message", "No message")
                    source = alert.get("type", "unknown")
                    
                    alert_color = "blue" if level == "info" else "orange" if level == "warning" else "red"
                    
                    st.markdown(
                        f"""
                        <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba({', '.join(['255, 0, 0, 0.1'] if level == 'urgent' else ['255, 165, 0, 0.1'] if level == 'warning' else ['0, 0, 255, 0.1'])});">
                            <div style="font-weight: bold; color: {alert_color};">{level.upper()}: {message}</div>
                            <div style="font-size: 0.8em;">Source: {source}</div>
                            <button style="background-color: #f0f2f6; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-top: 5px;" onclick="alert('Resolve button clicked')">Resolve</button>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Add a resolve button (since we can't use the HTML button)
                    if st.button(f"Resolve {source.title()} Alert", key=f"resolve_{source}_{alert.get('timestamp', '')}"):
                        resolve_alert(alert)
            else:
                st.info("No active alerts")
        
        # Health tab
        with tabs[1]:
            health_data = user_details.get("health", {})
            
            if health_data:
                # Display vital signs
                st.subheader("Current Vital Signs")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Heart rate
                    heart_rate = health_data.get("heart_rate", "N/A")
                    st.metric("Heart Rate", f"{heart_rate} bpm")
                    
                    # Blood pressure
                    blood_pressure = health_data.get("blood_pressure", "N/A")
                    st.metric("Blood Pressure", blood_pressure)
                
                with col2:
                    # Glucose
                    glucose = health_data.get("glucose", "N/A")
                    st.metric("Glucose", f"{glucose} mg/dL")
                    
                    # Oxygen
                    oxygen = health_data.get("oxygen", "N/A")
                    st.metric("Oxygen Saturation (SpO₂%)", f"{oxygen}%")
                
                # Mock health trend visualization
                st.subheader("Health Trends (Last 7 Days)")
                
                # Generate random data for demo
                dates = [datetime.now() - timedelta(days=i) for i in range(7, 0, -1)]
                date_labels = [date.strftime("%m/%d") for date in dates]
                
                # Heart rate trend (simulated)
                heart_rates = [random.randint(60, 100) for _ in range(7)]
                
                # Create figure
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(date_labels, heart_rates, marker='o', linestyle='-', color='red')
                ax.set_title('Heart Rate Trend')
                ax.set_ylabel('BPM')
                ax.grid(True, linestyle='--', alpha=0.7)
                st.pyplot(fig)
                
                # Health alerts
                st.subheader("Health Alerts")
                health_alerts = health_data.get("alerts", [])
                
                if health_alerts:
                    for alert in health_alerts:
                        level = alert.get("level", "info")
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        alert_color = "blue" if level == "info" else "orange" if level == "warning" else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba({', '.join(['255, 0, 0, 0.1'] if level == 'urgent' else ['255, 165, 0, 0.1'] if level == 'warning' else ['0, 0, 255, 0.1'])});">
                                <div style="font-weight: bold; color: {alert_color};">{level.upper()}: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve {alert_type.title()} Alert", key=f"resolve_health_{alert_type}"):
                            resolve_alert(alert)
                else:
                    st.info("No active health alerts")
            else:
                st.warning("No health data available")
        
        # Safety tab
        with tabs[2]:
            safety_data = user_details.get("safety", {})
            
            if safety_data:
                # Display safety status
                st.subheader("Current Safety Status")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Location
                    location = safety_data.get("location", "Unknown")
                    st.markdown(f"**Current Location**: {location}")
                    
                    # Activity
                    activity = safety_data.get("activity", "Unknown")
                    st.markdown(f"**Current Activity**: {activity}")
                
                with col2:
                    # Fall detection
                    fall_detected = safety_data.get("fall_detected", False)
                    fall_status = "❌ No Falls Detected" if not fall_detected else "⚠️ FALL DETECTED"
                    fall_color = "green" if not fall_detected else "red"
                    st.markdown(f"**Fall Status**: <span style='color: {fall_color};'>{fall_status}</span>", unsafe_allow_html=True)
                    
                    # Safety status
                    status = safety_data.get("status", "unknown")
                    status_color = status_colors.get(status, "gray")
                    st.markdown(f"**Overall Safety**: <span style='color: {status_color};'>{status.title()}</span>", unsafe_allow_html=True)
                
                # Mock location visualization (simple placeholder)
                st.subheader("Home Location Map")
                
                # Create a simple home layout visualization
                fig, ax = plt.subplots(figsize=(8, 6))
                
                # Define rooms as rectangles
                rooms = {
                    "Living Room": [0.1, 0.1, 0.5, 0.5],
                    "Kitchen": [0.6, 0.1, 0.3, 0.3],
                    "Bedroom": [0.1, 0.6, 0.4, 0.3],
                    "Bathroom": [0.6, 0.4, 0.3, 0.2]
                }
                
                # Plot rooms
                for room_name, dims in rooms.items():
                    color = "lightblue"
                    if room_name == location:
                        color = "lightgreen"  # Highlight current location
                    
                    rect = plt.Rectangle((dims[0], dims[1]), dims[2], dims[3], facecolor=color, edgecolor='black', alpha=0.7)
                    ax.add_patch(rect)
                    ax.text(dims[0] + dims[2]/2, dims[1] + dims[3]/2, room_name, ha='center', va='center')
                
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.set_xticks([])
                ax.set_yticks([])
                ax.set_title('Home Layout')
                st.pyplot(fig)
                
                # Safety alerts
                st.subheader("Safety Alerts")
                safety_alerts = safety_data.get("alerts", [])
                
                if safety_alerts:
                    for alert in safety_alerts:
                        level = alert.get("level", "info")
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        alert_color = "blue" if level == "info" else "orange" if level == "warning" else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba({', '.join(['255, 0, 0, 0.1'] if level == 'urgent' else ['255, 165, 0, 0.1'] if level == 'warning' else ['0, 0, 255, 0.1'])});">
                                <div style="font-weight: bold; color: {alert_color};">{level.upper()}: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve {alert_type.title()} Alert", key=f"resolve_safety_{alert_type}"):
                            resolve_alert(alert)
                else:
                    st.info("No active safety alerts")
            else:
                st.warning("No safety data available")
        
        # Reminders tab
        with tabs[3]:
            reminder_data = user_details.get("reminders", {})
            
            if reminder_data:
                # Display reminder status
                st.subheader("Reminder Status")
                
                # Acknowledgment rate
                ack_rate = reminder_data.get("acknowledgment_rate", 0)
                ack_color = "green" if ack_rate >= 80 else "orange" if ack_rate >= 50 else "red"
                
                st.markdown(f"**Acknowledgment Rate**: <span style='color: {ack_color};'>{ack_rate:.1f}%</span>", unsafe_allow_html=True)
                
                # Progress bar
                st.progress(ack_rate / 100)
                
                # Upcoming reminders
                st.subheader("Upcoming Reminders")
                upcoming = reminder_data.get("upcoming_reminders", [])
                
                if upcoming:
                    for reminder in upcoming:
                        reminder_type = reminder.get("type", "Unknown")
                        time = reminder.get("scheduled_time", "Unknown")
                        
                        type_icon = "💊" if reminder_type == "Medication" else "💧" if reminder_type == "Hydration" else "📅" if reminder_type == "Appointment" else "🏃" if reminder_type == "Exercise" else "⏰"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: #f0f2f6;">
                                <div style="font-weight: bold;">{type_icon} {reminder_type}</div>
                                <div style="font-size: 0.8em;">Scheduled: {time}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No upcoming reminders")
                
                # Recent reminders
                st.subheader("Recent Reminders")
                recent = reminder_data.get("recent_reminders", [])
                
                if recent:
                    for reminder in recent:
                        reminder_type = reminder.get("type", "Unknown")
                        time = reminder.get("scheduled_time", "Unknown")
                        acknowledged = reminder.get("acknowledged", False)
                        
                        type_icon = "💊" if reminder_type == "Medication" else "💧" if reminder_type == "Hydration" else "📅" if reminder_type == "Appointment" else "🏃" if reminder_type == "Exercise" else "⏰"
                        status_icon = "✅" if acknowledged else "⏳"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: #f0f2f6;">
                                <div style="font-weight: bold;">{type_icon} {reminder_type} {status_icon}</div>
                                <div style="font-size: 0.8em;">Scheduled: {time}</div>
                                <div style="font-size: 0.8em;">Status: {("Acknowledged" if acknowledged else "Sent, waiting for acknowledgment")}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No recent reminders")
                
                # Reminder alerts
                st.subheader("Reminder Alerts")
                reminder_alerts = reminder_data.get("alerts", [])
                
                if reminder_alerts:
                    for alert in reminder_alerts:
                        level = alert.get("level", "info")
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        alert_color = "blue" if level == "info" else "orange" if level == "warning" else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba({', '.join(['255, 0, 0, 0.1'] if level == 'urgent' else ['255, 165, 0, 0.1'] if level == 'warning' else ['0, 0, 255, 0.1'])});">
                                <div style="font-weight: bold; color: {alert_color};">{level.upper()}: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve {alert_type.title()} Alert", key=f"resolve_reminder_{alert_type}"):
                            resolve_alert(alert)
                else:
                    st.info("No active reminder alerts")
            else:
                st.warning("No reminder data available")
        
        # Social tab
        with tabs[4]:
            social_data = user_details.get("social", {})
            
            if social_data:
                # Display social status
                st.subheader("Social Engagement Status")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Weekly interactions
                    weekly = social_data.get("weekly_interactions", 0)
                    st.metric("Weekly Interactions", weekly)
                
                with col2:
                    # Last interaction
                    last_interaction = social_data.get("last_interaction", {})
                    last_type = last_interaction.get("type", "unknown")
                    last_contact = last_interaction.get("contact", "unknown")
                    last_time = datetime.fromisoformat(last_interaction.get("timestamp", datetime.now().isoformat()))
                    
                    hours_ago = int((datetime.now() - last_time).total_seconds() / 3600)
                    
                    st.markdown(f"**Last Interaction**: {last_type.replace('_', ' ').title()} with {last_contact}")
                    st.markdown(f"**Time Since**: {hours_ago} hours ago")
                
                # Social engagement visualization
                st.subheader("Social Engagement (Last 30 Days)")
                
                # Generate random data for demo
                dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
                date_labels = [date.strftime("%m/%d") for date in dates]
                
                # Interaction counts (simulated)
                interactions = [random.randint(0, 3) for _ in range(30)]
                
                # Create figure
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.bar(date_labels, interactions, color='purple', alpha=0.7)
                ax.set_title('Social Interactions')
                ax.set_ylabel('Count')
                ax.set_xticks(date_labels[::5])  # Show every 5th date
                ax.grid(True, linestyle='--', alpha=0.7, axis='y')
                st.pyplot(fig)
                
                # Suggested activities
                st.subheader("Suggested Activities")
                suggestions = social_data.get("suggestions", [])
                
                if suggestions:
                    for suggestion in suggestions:
                        suggestion_type = suggestion.get("type", "unknown")
                        title = suggestion.get("title", "No title")
                        description = suggestion.get("description", "No description")
                        priority = suggestion.get("priority", "low")
                        
                        priority_color = "green" if priority == "low" else "orange" if priority == "medium" else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; border-left: 5px solid {priority_color}; background-color: #f0f2f6;">
                                <div style="font-weight: bold;">{title}</div>
                                <div style="font-size: 0.9em;">{description}</div>
                                <div style="font-size: 0.8em; color: {priority_color};">Priority: {priority.title()}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No activity suggestions")
                
                # Social alerts
                st.subheader("Social Alerts")
                social_alerts = social_data.get("alerts", [])
                
                if social_alerts:
                    for alert in social_alerts:
                        level = alert.get("level", "info")
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        alert_color = "blue" if level == "info" else "orange" if level == "warning" else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba({', '.join(['255, 0, 0, 0.1'] if level == 'urgent' else ['255, 165, 0, 0.1'] if level == 'warning' else ['0, 0, 255, 0.1'])});">
                                <div style="font-weight: bold; color: {alert_color};">{level.upper()}: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve {alert_type.title()} Alert", key=f"resolve_social_{alert_type}"):
                            resolve_alert(alert)
                else:
                    st.info("No active social alerts")
            else:
                st.warning("No social data available")
        
        # Alerts tab
        with tabs[5]:
            st.subheader("All Active Alerts")
            
            alerts = user_details.get("alerts", [])
            
            if alerts:
                # Group alerts by level
                urgent_alerts = [a for a in alerts if a.get("level") == "urgent"]
                warning_alerts = [a for a in alerts if a.get("level") == "warning"]
                info_alerts = [a for a in alerts if a.get("level") == "info"]
                
                # Display urgent alerts first
                if urgent_alerts:
                    st.markdown("#### Urgent Alerts")
                    for alert in urgent_alerts:
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba(255, 0, 0, 0.1);">
                                <div style="font-weight: bold; color: red;">URGENT: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve Urgent {alert_type.title()} Alert", key=f"resolve_urgent_{alert_type}"):
                            resolve_alert(alert)
                
                # Display warning alerts
                if warning_alerts:
                    st.markdown("#### Warning Alerts")
                    for alert in warning_alerts:
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba(255, 165, 0, 0.1);">
                                <div style="font-weight: bold; color: orange;">WARNING: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve Warning {alert_type.title()} Alert", key=f"resolve_warning_{alert_type}"):
                            resolve_alert(alert)
                
                # Display info alerts
                if info_alerts:
                    st.markdown("#### Information Alerts")
                    for alert in info_alerts:
                        message = alert.get("message", "No message")
                        alert_type = alert.get("type", "unknown")
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: rgba(0, 0, 255, 0.1);">
                                <div style="font-weight: bold; color: blue;">INFO: {message}</div>
                                <div style="font-size: 0.8em;">Type: {alert_type}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        if st.button(f"Resolve Info {alert_type.title()} Alert", key=f"resolve_info_{alert_type}"):
                            resolve_alert(alert)
                
                # Add resolve all button
                if st.button("Resolve All Alerts"):
                    st.session_state.active_alerts = []
                    st.success("All alerts resolved")
                    time_module.sleep(0.5)  # Simulate API call delay
                    update_data()
            else:
                st.info("No active alerts")
    else:
        st.info("Select a user from the list to view details")

# Initialize data on first run
if "initialized" not in st.session_state:
    update_data()
    st.session_state.initialized = True

# Periodically refresh data (every 60 seconds)
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time_module.time()
elif time_module.time() - st.session_state.last_refresh > 60:
    update_data()
    st.session_state.last_refresh = time_module.time()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888;">
        CareCompanion Dashboard | Elderly Care Multi-Agent System
    </div>
    """,
    unsafe_allow_html=True
)