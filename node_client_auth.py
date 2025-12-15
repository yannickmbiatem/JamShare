import socket
import json
import sys
import os
import time
import re
from node_client import NodeClient

class SecureNodeClient(NodeClient):
    """Node client with user account authentication"""
    
    def __init__(self, node_id, server_host='localhost', server_port=8889):
        super().__init__(node_id, server_host, server_port)
        self.user_session = None
        self.user_info = None
        self.is_logged_in = False
        self.session_token = None
        self.authenticated = False
        self.DEFAULT_STORAGE_MB = 1024  # 1GB default storage
        self.MAX_RETRIES = 3
    
    def connect_to_server(self):
        """Establish single persistent connection for entire session"""
        try:
            print(f"🔐 Connecting to secure cloud server at {self.server_host}:{self.server_port}...")
            
            # Create the main connection for the session
            if not self.create_connection():
                return False
            
            # Use this single connection for all operations
            return self.show_auth_options()
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def show_auth_options(self):
        """Show authentication options and handle the chosen flow"""
        while True:
            print("\n🔐 Authentication Options")
            print("1. Login with user account (Recommended)")
            print("2. Register new user account")
            print("3. Continue with node-only enrollment (No account)")
            print("4. Exit")
            
            choice = input("Choose option (1-4): ").strip()
            
            if choice == '1':
                return self.account_login()
            elif choice == '2':
                return self.account_register()
            elif choice == '3':
                return self.node_only_enrollment()
            elif choice == '4':
                self.close_connection()
                return False
            else:
                print("❌ Invalid choice")
    
    def create_connection(self):
        """Create a new connection to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✅ Connected to server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to create connection: {e}")
            return False
    
    def close_connection(self):
        """Close the current connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def account_register(self):
        """Register a new user account"""
        print("\n👤 Account Registration")
        
        while True:
            username = input("Username: ").strip()
            if not self.validate_username(username):
                print("❌ Username must be 3-20 characters (letters, numbers, underscore, hyphen)")
                continue
            break
        
        email = input("Email: ").strip()
        
        while True:
            password = input("Password: ").strip()
            if not self.validate_password(password):
                print("❌ Password must be at least 6 characters")
                continue
            break
        
        register_data = {
            'type': 'register_account',
            'username': username,
            'email': email,
            'password': password
        }
        
        response = self.send_command_with_retry(register_data)
        
        if response.get('status') == 'success':
            print(f"✅ {response.get('message', 'Registration successful')}")
            # Now login with the new account
            return self.account_login()
        else:
            print(f"❌ {response.get('message', 'Registration failed')}")
            return False
    
    def account_login(self):
        """Login with user account"""
        print("\n🔐 Account Login")
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        login_data = {
            'type': 'login_account',
            'username': username,
            'password': password
        }
        
        response = self.send_command_with_retry(login_data)
        
        if response.get('status') == 'success':
            self.user_session = response['session_token']
            self.user_info = self.safe_get_user_info(response)
            self.is_logged_in = True
            
            print(f"✅ {response.get('message', 'Login successful')}")
            print(f"👤 Welcome, {self.user_info.get('username', 'User')}!")
            print(f"💾 Storage Quota: {self.user_info.get('storage_quota_mb', 1024)} MB")
            print(f"💾 Used Storage: {self.user_info.get('used_storage_mb', 0):.1f} MB")
            print(f"💾 Available Storage: {self.user_info.get('available_storage_mb', 1024):.1f} MB")
            
            return self.account_based_enrollment()
        else:
            print(f"❌ {response.get('message', 'Login failed')}")
            return False
    
    def safe_get_user_info(self, response):
        """Safely extract user info from response with default values"""
        user_info = response.get('user_info', {})
        
        # Ensure all required fields exist with defaults
        safe_info = {
            'username': user_info.get('username', 'Unknown'),
            'email': user_info.get('email', 'unknown@example.com'),
            'storage_quota_mb': float(user_info.get('storage_quota_mb', 1024)),
            'used_storage_mb': float(user_info.get('used_storage_mb', 0)),
            'available_storage_mb': float(user_info.get('available_storage_mb', 1024)),
            'owned_nodes': user_info.get('owned_nodes', []),
            'nodes_info': user_info.get('nodes_info', {})
        }
        
        # Calculate available storage if not provided
        if 'available_storage_mb' not in user_info:
            quota = safe_info['storage_quota_mb']
            used = safe_info['used_storage_mb']
            safe_info['available_storage_mb'] = max(0, quota - used)
        
        return safe_info
    
    def account_based_enrollment(self):
        """Enroll node with user account - storage is automatically allocated"""
        storage_mb = self.DEFAULT_STORAGE_MB
        
        enrollment_data = {
            'type': 'enrollment_request',
            'node_id': self.node_id,
            'user_email': self.user_info.get('email', 'user@example.com'),
            'user_name': self.user_info.get('username', 'User'),
            'session_token': self.user_session,
            'cpu_capacity': 4,
            'memory_capacity': 16,
            'storage_capacity': storage_mb / 1024,  # Convert MB to GB
            'bandwidth': 1000
        }
        
        print(f"\n💾 Automatic storage allocation: {storage_mb} MB (1GB)")
        
        response = self.send_command_with_retry(enrollment_data)
        
        if response.get('status') == 'enrollment_completed':
            self.session_token = response['session_token']
            network_info = response['network_info']
            storage_gb = storage_mb / 1024
            
            self.node = self.create_authenticated_node(network_info, storage_gb)
            self.authenticated = True
            
            print(f"\n✅ Account-based enrollment completed!")
            print(f"💾 Automatically allocated {storage_mb} MB storage")
            
            # Update user info if returned
            if 'user_info' in response:
                self.user_info = self.safe_get_user_info(response)
                print(f"👤 User account linked successfully")
            return True
        else:
            print(f"❌ Enrollment failed: {response.get('message', 'Unknown error')}")
            return False
    
    def node_only_enrollment(self):
        """Node enrollment without user account - automatic 1GB storage"""
        print("\n🔐 Node-Only Enrollment")
        
        while True:
            user_email = input("Enter your email: ").strip()
            if not self.validate_email(user_email):
                print("❌ Please enter a valid email address")
                continue
            break
        
        user_name = input("Enter your name: ").strip()
        
        # Fixed 1GB storage for node-only users
        storage_mb = self.DEFAULT_STORAGE_MB
        
        enrollment_data = {
            'type': 'enrollment_request',
            'node_id': self.node_id,
            'user_email': user_email,
            'user_name': user_name,
            'cpu_capacity': 4,
            'memory_capacity': 16,
            'storage_capacity': storage_mb / 1024,  # Convert MB to GB
            'bandwidth': 1000
        }
        
        print(f"\n💾 Automatic storage allocation: {storage_mb} MB (1GB)")
        
        response = self.send_command_with_retry(enrollment_data)
        
        if response.get('status') == 'enrollment_completed':
            self.session_token = response['session_token']
            network_info = response['network_info']
            storage_gb = storage_mb / 1024
            
            self.node = self.create_authenticated_node(network_info, storage_gb)
            self.authenticated = True
            
            print(f"\n✅ Node enrollment completed!")
            print(f"💾 Automatically allocated {storage_mb} MB storage")
            return True
        else:
            print(f"❌ Enrollment failed: {response.get('message', 'Unknown error')}")
            return False
    
    def send_command_with_retry(self, command, max_retries=None):
        """Send command with retry logic"""
        if max_retries is None:
            max_retries = self.MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                return self.send_command_direct(command)
            except (ConnectionError, socket.timeout) as e:
                if attempt == max_retries - 1:
                    raise
                print(f"🔄 Retry {attempt + 1}/{max_retries}...")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {'status': 'error', 'message': 'Max retries exceeded'}
    
    def send_command_direct(self, command):
        """Send command directly through the persistent connection"""
        try:
            if not self.socket:
                return {'status': 'error', 'message': 'Not connected to server'}
                
            self.socket.send(json.dumps(command).encode('utf-8'))
            response_data = self.socket.recv(4096).decode('utf-8')
            return json.loads(response_data)
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def send_command(self, command):
        """Enhanced send command with session"""
        if self.is_logged_in and self.user_session:
            command['session_token'] = self.user_session
        elif self.session_token:
            command['session_token'] = self.session_token
        
        return self.send_command_direct(command)
    
    def create_authenticated_node(self, network_info, storage_gb):
        """Create node after authentication"""
        from storage_virtual_node import StorageVirtualNode
        
        node = StorageVirtualNode(
            node_id=self.node_id,
            cpu_capacity=4,
            memory_capacity=16,
            storage_capacity=storage_gb,
            bandwidth=1000,
            ip_address=network_info['ip_address'],
            mac_address=network_info['mac_address']
        )
        
        node.update_network_info(
            ip_address=network_info['ip_address'],
            mac_address=network_info['mac_address'],
            cloud_server=network_info['cloud_server']
        )
        
        return node
    
    def get_storage_size_from_user(self):
        """Returns fixed 1GB storage - no user input needed"""
        return self.DEFAULT_STORAGE_MB
    
    def validate_username(self, username):
        """Validate username format"""
        pattern = r'^[a-zA-Z0-9_-]{3,20}$'
        return bool(re.match(pattern, username))
    
    def validate_password(self, password):
        """Validate password strength"""
        return len(password) >= 6
    
    def validate_email(self, email):
        """Basic email validation"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_node_id(self, node_id):
        """Validate node ID format"""
        pattern = r'^[a-zA-Z0-9_-]{3,20}$'
        return bool(re.match(pattern, node_id))
    
    def validate_storage_size(self, size_mb):
        """Validate storage allocation"""
        return 100 <= size_mb <= 10240  # 100MB to 10GB
    
    def get_user_info(self):
        """Get current user information"""
        if not self.is_logged_in:
            return {'status': 'error', 'message': 'Not logged in'}
        
        response = self.send_command_with_retry({
            'type': 'get_user_info'
        })
        
        if response.get('status') == 'success':
            response['user_info'] = self.safe_get_user_info(response)
        
        return response
    
    def list_user_nodes(self):
        """List nodes owned by current user"""
        if not self.is_logged_in:
            return {'status': 'error', 'message': 'Not logged in'}
        
        response = self.send_command_with_retry({
            'type': 'list_user_nodes'
        })
        
        return response
    
    def handle_account_commands(self, cmd):
        """Handle account-specific commands"""
        if cmd[0] == 'user_info' and self.is_logged_in:
            response = self.get_user_info()
            if response.get('status') == 'success':
                user_info = response['user_info']
                print(f"👤 User Information:")
                print(f"   Username: {user_info['username']}")
                print(f"   Email: {user_info['email']}")
                print(f"   Storage Quota: {user_info['storage_quota_mb']} MB")
                print(f"   Used Storage: {user_info['used_storage_mb']:.1f} MB")
                print(f"   Available Storage: {user_info['available_storage_mb']:.1f} MB")
                print(f"   Nodes: {', '.join(user_info['owned_nodes']) if user_info['owned_nodes'] else 'None'}")
            else:
                print(f"❌ {response.get('message', 'Failed to get user info')}")
        
        elif cmd[0] == 'my_nodes' and self.is_logged_in:
            response = self.list_user_nodes()
            if response.get('status') == 'success':
                nodes = response.get('nodes', [])
                print(f"🖥️  Your Nodes: {', '.join(nodes) if nodes else 'None'}")
            else:
                print(f"❌ {response.get('message', 'Failed to get nodes')}")
        
        elif cmd[0] == 'logout' and self.is_logged_in:
            response = self.send_command_with_retry({
                'type': 'logout_account',
                'session_token': self.user_session
            })
            
            if response.get('status') == 'success':
                self.is_logged_in = False
                self.user_session = None
                self.user_info = None
                print("👋 Logged out successfully")
            else:
                print(f"❌ Logout failed: {response.get('message', 'Unknown error')}")
        
        elif cmd[0] == 'debug' and self.is_logged_in:
            response = self.send_command_with_retry({
                'type': 'debug_state'
            })
            if response.get('status') == 'success':
                print("🔍 Server Debug State:")
                print(json.dumps(response.get('debug_info', {}), indent=2))
            else:
                print(f"❌ {response.get('message', 'Debug failed')}")
        
        else:
            return False  # Command not handled here
        
        return True  # Command handled
    
    def interactive_mode(self):
        """Enhanced interactive mode with account features"""
        if not self.authenticated:
            print(f"❌ Node {self.node_id} is not authenticated")
            return False
            
        print(f"\n🎮 Secure Node {self.node_id} Interactive Mode")
        if self.is_logged_in:
            print(f"👤 User: {self.user_info.get('username', 'Unknown')}")
            print(f"💾 Quota: {self.user_info.get('storage_quota_mb', 1024)} MB")
            print(f"💾 Used: {self.user_info.get('used_storage_mb', 0):.1f} MB")
            print(f"💾 Available: {self.user_info.get('available_storage_mb', 1024):.1f} MB")
        else:
            print("🔐 Node Authentication Only")
        
        print("\nCommands:")
        if self.is_logged_in:
            print("  user_info                         - Show user account information")
            print("  my_nodes                          - List nodes owned by you")
            print("  debug                             - Show server debug state")
            print("  logout                            - Logout from account")
        print("  connect <node_id>                    - Connect to another node")
        print("  transfer <node_id> <file> <size_mb>  - Transfer virtual file")
        print("  transfer_actual <node_id> <file>     - Transfer actual file from storage")
        print("  create_file <name> <size_mb> [type]  - Create actual file")
        print("  list_files                           - List files in local storage")
        print("  delete_file <name>                   - Delete file from local storage")
        print("  stats                                - Show network statistics")
        print("  discovery                            - Show network discovery")
        print("  storage_info                         - Show node storage utilization")
        print("  quit                                 - Exit")
        
        while True:
            try:
                cmd = input(f"secure_node_{self.node_id}> ").strip().split()
                if not cmd:
                    continue
                
                # Handle account commands first
                if self.handle_account_commands(cmd):
                    continue
                
                # Handle quit command
                if cmd[0] == 'quit':
                    print("👋 Goodbye!")
                    if self.socket:
                        self.close_connection()
                    break
                
                # Handle other commands using parent class logic
                self.interactive_mode_command(cmd)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                if self.socket:
                    self.close_connection()
                break
            except Exception as e:
                print(f"💥 Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python node_client_auth.py <node_id>")
        print("Example: python node_client_auth.py node1")
        sys.exit(1)
    
    node_id = sys.argv[1]
    client = SecureNodeClient(node_id)
    
    if client.connect_to_server():
        client.interactive_mode()
    else:
        print(f"❌ Node {node_id} failed to join the secure cloud network")