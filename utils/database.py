"""
Database utilities for the CareCompanion system.
This is a simple in-memory simulation of a database.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from utils.logger import setup_logger
from utils.config import config

logger = setup_logger("database")

class DatabaseSimulator:
    """
    Simple in-memory database simulator for the CareCompanion system.
    Simulates basic database operations for development and testing.
    """
    
    def __init__(self):
        """
        Initialize the database simulator.
        """
        self.tables = {}
        self.id_counters = {}
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """
        Create a new table in the database.
        
        Args:
            table_name: Name of the table to create
            schema: Dictionary mapping column names to types
            
        Returns:
            True if table was created, False if it already exists
        """
        if table_name in self.tables:
            logger.warning(f"Table '{table_name}' already exists")
            return False
        
        self.tables[table_name] = {
            'schema': schema,
            'data': []
        }
        self.id_counters[table_name] = 0
        
        logger.info(f"Created table '{table_name}'")
        return True
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert a record into a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary containing column-value pairs
            
        Returns:
            ID of the inserted record
        """
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' does not exist")
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Generate an ID for the record
        record_id = self.id_counters[table_name] + 1
        self.id_counters[table_name] = record_id
        
        # Add ID and timestamp to the record
        record = {
            'id': record_id,
            'created_at': datetime.now().isoformat(),
            **data
        }
        
        # Add the record to the table
        self.tables[table_name]['data'].append(record)
        
        logger.debug(f"Inserted record into '{table_name}' with ID {record_id}")
        return record_id
    
    def update(self, table_name: str, record_id: int, data: Dict[str, Any]) -> bool:
        """
        Update a record in a table.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to update
            data: Dictionary containing column-value pairs to update
            
        Returns:
            True if record was updated, False if not found
        """
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' does not exist")
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Find the record
        for i, record in enumerate(self.tables[table_name]['data']):
            if record['id'] == record_id:
                # Update the record
                self.tables[table_name]['data'][i].update(data)
                self.tables[table_name]['data'][i]['updated_at'] = datetime.now().isoformat()
                
                logger.debug(f"Updated record in '{table_name}' with ID {record_id}")
                return True
        
        logger.warning(f"Record with ID {record_id} not found in '{table_name}'")
        return False
    
    def delete(self, table_name: str, record_id: int) -> bool:
        """
        Delete a record from a table.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to delete
            
        Returns:
            True if record was deleted, False if not found
        """
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' does not exist")
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Find and delete the record
        for i, record in enumerate(self.tables[table_name]['data']):
            if record['id'] == record_id:
                del self.tables[table_name]['data'][i]
                
                logger.debug(f"Deleted record from '{table_name}' with ID {record_id}")
                return True
        
        logger.warning(f"Record with ID {record_id} not found in '{table_name}'")
        return False
    
    def query(self, table_name: str, conditions: Optional[Dict[str, Any]] = None, 
              order_by: Optional[str] = None, desc: bool = False, 
              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query records from a table.
        
        Args:
            table_name: Name of the table
            conditions: Optional dictionary of column-value pairs to filter by
            order_by: Optional column name to order by
            desc: Whether to order in descending order
            limit: Optional maximum number of records to return
            
        Returns:
            List of matching records
        """
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' does not exist")
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Start with all records
        results = self.tables[table_name]['data'].copy()
        
        # Apply conditions
        if conditions:
            filtered_results = []
            for record in results:
                matches = True
                for column, value in conditions.items():
                    if column not in record or record[column] != value:
                        matches = False
                        break
                
                if matches:
                    filtered_results.append(record)
            
            results = filtered_results
        
        # Apply ordering
        if order_by:
            if order_by in self.tables[table_name]['schema']:
                results.sort(key=lambda r: r.get(order_by), reverse=desc)
            else:
                logger.warning(f"Column '{order_by}' not found in table '{table_name}'")
        
        # Apply limit
        if limit and limit > 0:
            results = results[:limit]
        
        return results
    
    def get_by_id(self, table_name: str, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a record by its ID.
        
        Args:
            table_name: Name of the table
            record_id: ID of the record to retrieve
            
        Returns:
            Record dict if found, None otherwise
        """
        if table_name not in self.tables:
            logger.error(f"Table '{table_name}' does not exist")
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Find the record
        for record in self.tables[table_name]['data']:
            if record['id'] == record_id:
                return record
        
        logger.debug(f"Record with ID {record_id} not found in '{table_name}'")
        return None
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save the database to a JSON file.
        
        Args:
            file_path: Path to save the database to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    'tables': self.tables,
                    'id_counters': self.id_counters
                }, f, indent=2)
            
            logger.info(f"Database saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving database to {file_path}: {e}")
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load the database from a JSON file.
        
        Args:
            file_path: Path to load the database from
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"Database file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.tables = data['tables']
                self.id_counters = data['id_counters']
            
            logger.info(f"Database loaded from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading database from {file_path}: {e}")
            return False


# Create global database instance
db = DatabaseSimulator()

# Initialize common tables
def initialize_database():
    """
    Initialize the database with common tables.
    """
    # Users table
    db.create_table('users', {
        'user_id': 'str',
        'name': 'str',
        'age': 'int',
        'preferences': 'dict'
    })
    
    # Health data table
    db.create_table('health_data', {
        'user_id': 'str',
        'timestamp': 'str',
        'heart_rate': 'int',
        'blood_pressure': 'str',
        'glucose': 'int',
        'oxygen': 'int'
    })
    
    # Safety data table
    db.create_table('safety_data', {
        'user_id': 'str',
        'timestamp': 'str',
        'location': 'str',
        'activity': 'str',
        'fall_detected': 'bool',
        'unusual_activity': 'bool',
        'inactive_too_long': 'bool'
    })
    
    # Reminder data table
    db.create_table('reminders', {
        'user_id': 'str',
        'timestamp': 'str',
        'type': 'str',
        'content': 'str',
        'scheduled_time': 'str',
        'sent': 'bool',
        'acknowledged': 'bool'
    })
    
    # Alert table
    db.create_table('alerts', {
        'user_id': 'str',
        'source': 'str',
        'level': 'str',
        'message': 'str',
        'resolved': 'bool',
        'resolution_details': 'str'
    })
    
    # Event table
    db.create_table('events', {
        'user_id': 'str',
        'event_type': 'str',
        'details': 'dict'
    })
    
    # Add a default user
    db.insert('users', {
        'user_id': 'U1000',
        'name': 'John Doe',
        'age': 75,
        'preferences': {
            'remind_hydration': True,
            'remind_medication': True,
            'health_check_frequency': 'high',
            'privacy_level': 'medium'
        }
    })
    
    logger.info("Database initialized with common tables")