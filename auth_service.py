import hashlib
import secrets
import time
import json
import os
from typing import Dict, List, Any

# --- Data Persistence (Simplified) ---

STORAGE_FILE = "user_accounts.json"
ENROLLED_NODES_FILE = "enrolled_nodes.json"

def load_data(filename, default_value):
    """Load data from JSON file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Failed to decode {filename}. Starting with default data.")
            return default_value
    return default_value

def save_data(filename, data):
    """Save data to JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# --- Core Authentication Class (No Email/UTP) ---

class AuthenticationServer:
    """Authentication Server for user accounts and node association."""
    
    def __init__(self, *args, **kwargs):
        # Load data
        self.user_accounts = load_data(STORAGE_FILE, {})
        self.enrolled_nodes = load_data(ENROLLED_NODES_FILE, {})
        
        # Initial save to ensure files exist
        self.save_data_periodically()

    def save_data_periodically(self):
        """Save data to disk"""
        save_data(STORAGE_FILE, self.user_accounts)
        save_data(ENROLLED_NODES_FILE, self.enrolled_nodes)
        
    def hash_password(self, password):
        """Hash a password for secure storage."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, email, password, storage_quota_mb=1024):
        """Register a new user account."""
        if username in self.user_accounts:
            raise ValueError("Username already exists.")
        
        self.user_accounts[username] = {
            'username': username,
            'email': email,
            'password_hash': self.hash_password(password),
            'storage_quota_mb': storage_quota_mb,
            'used_storage_mb': 0,
            'nodes': [],
            'created_at': time.time()
        }
        self.save_data_periodically()

    def login_user(self, username, password):
        """Authenticate user and generate a session token."""
        user_data = self.user_accounts.get(username)
        if not user_data:
            raise ValueError("Invalid username or password.")
        
        if user_data['password_hash'] != self.hash_password(password):
            raise ValueError("Invalid username or password.")

        # Generate a new session token for the user
        session_token = secrets.token_hex(32)
        return session_token

    def get_user_info(self, username):
        """Retrieve user information (including linked nodes with metadata)."""
        user_data = self.user_accounts.get(username)
        if not user_data:
            raise ValueError("User not found.")
        
        info = user_data.copy()
        info.pop('password_hash', None)
        info['nodes_info'] = {}
        
        # Enrich node list with enrollment info
        for node_id in info['nodes']:
             info['nodes_info'][node_id] = self.enrolled_nodes.get(node_id, 
                                                                  {'storage_gb': 0, 'joined_at': 0, 'status': 'unregistered'})

        return info

    def add_node_to_user(self, username, node_id):
        """Associate an enrolled node with a user account."""
        if username not in self.user_accounts:
            raise ValueError("User not found.")
        
        if node_id not in self.user_accounts[username]['nodes']:
            self.user_accounts[username]['nodes'].append(node_id)
            self.save_data_periodically()

    def list_user_nodes(self, username):
        """List all nodes associated with a user."""
        return self.user_accounts.get(username, {}).get('nodes', [])

    def register_node(self, node_id, storage_gb):
        """Register the node's existence globally."""
        if node_id in self.enrolled_nodes:
            # Allow re-registration if it's the same storage capacity, otherwise raise error
            existing_node = self.enrolled_nodes[node_id]
            if existing_node['storage_gb'] != storage_gb:
                raise ValueError(f"Node {node_id} is already registered with different storage capacity.")
            return existing_node # Already registered, do nothing.

        self.enrolled_nodes[node_id] = {
            'storage_gb': storage_gb,
            'joined_at': time.time()
        }
        self.save_data_periodically()
        return self.enrolled_nodes[node_id]

    def get_service_stats(self) -> Dict:
        """Get authentication service statistics"""
        total_quota = 0
        total_used = 0
        total_nodes = len(self.enrolled_nodes)
        
        for user_data in self.user_accounts.values():
            total_quota += user_data['storage_quota_mb']
            total_used += user_data['used_storage_mb']
        
        return {
            'total_users': len(self.user_accounts),
            'total_nodes': total_nodes,
            'total_quota_mb': total_quota,
            'total_used_mb': total_used,
            'quota_utilization': (total_used / total_quota * 100) if total_quota > 0 else 0
        }


class EnrollmentProtocol:
    """Protocol definitions for enrollment service communication (simplified)"""
    
    @staticmethod
    def create_enrollment_request(node_id, user_session_token, storage_capacity_gb, **kwargs):
        """New, single-step enrollment request using user session token."""
        return {
            'type': 'enrollment_request',
            'node_id': node_id,
            'session_token': user_session_token, # Uses the user's session token for auth
            'storage_capacity': storage_capacity_gb,
            'timestamp': time.time(),
            **kwargs
        }
    
    @staticmethod
    def create_access_request(session_token, command_type, **kwargs):
        """General request structure for all authenticated commands"""
        return {
            'type': command_type,
            'session_token': session_token,
            'timestamp': time.time(),
            **kwargs
        }