import socket
import json
import sys
import os
from node_client import NodeClient

class SecureNodeClient(NodeClient):
    """Node client with UTP authentication AND user accounts"""
    
    def __init__(self, node_id, server_host='localhost', server_port=8889):
        super().__init__(node_id, server_host, server_port)
        self.user_session = None
        self.user_info = None
        self.is_logged_in = False
        self.session_token = None
        self.authenticated = False
    
    def connect_to_server(self):
        """Connect to server with account options"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            
            print(f"🔐 Connecting to secure cloud server at {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))
            
            return self.show_auth_options()
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def show_auth_options(self):
        """Show authentication options"""
        while True:
            print("\n🔐 Authentication Options")
            print("1. Login with user account (Recommended)")
            print("2. Register new user account")
            print("3. Continue with UTP only (No account)")
            print("4. Exit")
            
            choice = input("Choose option (1-4): ").strip()
            
            if choice == '1':
                return self.account_login()
            elif choice == '2':
                return self.account_register()
            elif choice == '3':
                return self.utp_only_enrollment()
            elif choice == '4':
                return False
            else:
                print("❌ Invalid choice")
    
    def account_register(self):
        """Register a new user account"""
        print("\n👤 Account Registration")
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        
        register_data = {
            'type': 'register_account',
            'username': username,
            'email': email,
            'password': password
        }
        
        response = self.send_command_direct(register_data)
        
        if response.get('status') == 'success':
            print(f"✅ {response.get('message', 'Registration successful')}")
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
        
        response = self.send_command_direct(login_data)
        
        if response.get('status') == 'success':
            self.user_session = response['session_token']
            self.user_info = response['user_info']
            self.is_logged_in = True
            
            print(f"✅ {response.get('message', 'Login successful')}")
            print(f"👤 Welcome, {self.user_info['username']}!")
            print(f"💾 Storage: {self.user_info['used_storage_mb']:.1f}/{self.user_info['storage_quota_mb']} MB used")
            
            return self.account_based_enrollment()
        else:
            print(f"❌ {response.get('message', 'Login failed')}")
            return False
    
    def account_based_enrollment(self):
        """Enroll node with user account"""
        storage_mb = self.get_storage_size_from_user()
        
        enrollment_data = {
            'type': 'enrollment_request',
            'node_id': self.node_id,
            'user_email': self.user_info.get('email', 'user@example.com'),
            'user_name': self.user_info['username'],
            'session_token': self.user_session,
            'cpu_capacity': 4,
            'memory_capacity': 16,
            'storage_capacity': storage_mb / 1024,
            'bandwidth': 1000
        }
        
        response = self.send_command_direct(enrollment_data)
        
        if response.get('status') == 'enrollment_started':
            auth_token = response['auth_token']
            print("📧 Verification email sent. Check your email for the UTP code.")
            
            verification_code = input("🔢 Enter the verification code from email: ").strip()
            
            verification_data = {
                'type': 'verification_request',
                'auth_token': auth_token,
                'verification_code': verification_code
            }
            
            response = self.send_command_direct(verification_data)
            
            if response.get('status') == 'enrollment_completed':
                self.session_token = response['session_token']
                network_info = response['network_info']
                storage_gb = storage_mb / 1024
                
                self.node = self.create_authenticated_node(network_info, storage_gb)
                self.authenticated = True
                
                print(f"✅ Account-based enrollment completed!")
                if 'user_info' in response:
                    print(f"💾 Account storage updated")
                return True
            else:
                print(f"❌ Verification failed: {response.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Enrollment failed: {response.get('message', 'Unknown error')}")
            return False
    
    def utp_only_enrollment(self):
        """UTP enrollment without user account"""
        print("\n🔐 UTP-Only Enrollment")
        user_email = input("Enter your email: ").strip()
        user_name = input("Enter your name: ").strip()
        storage_mb = self.get_storage_size_from_user()
        
        enrollment_data = {
            'type': 'enrollment_request',
            'node_id': self.node_id,
            'user_email': user_email,
            'user_name': user_name,
            'cpu_capacity': 4,
            'memory_capacity': 16,
            'storage_capacity': storage_mb / 1024,
            'bandwidth': 1000
        }
        
        response = self.send_command_direct(enrollment_data)
        
        if response.get('status') == 'enrollment_started':
            auth_token = response['auth_token']
            print("📧 Verification email sent. Check your email for the UTP code.")
            
            verification_code = input("🔢 Enter the verification code from email: ").strip()
            
            verification_data = {
                'type': 'verification_request',
                'auth_token': auth_token,
                'verification_code': verification_code
            }
            
            response = self.send_command_direct(verification_data)
            
            if response.get('status') == 'enrollment_completed':
                self.session_token = response['session_token']
                network_info = response['network_info']
                storage_gb = storage_mb / 1024
                
                self.node = self.create_authenticated_node(network_info, storage_gb)
                self.authenticated = True
                
                print(f"✅ UTP enrollment completed! (No user account)")
                return True
            else:
                print(f"❌ Verification failed: {response.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Enrollment failed: {response.get('message', 'Unknown error')}")
            return False
    
    def send_command_direct(self, command):
        """Send command directly without session"""
        try:
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
        
        try:
            self.socket.send(json.dumps(command).encode('utf-8'))
            response_data = self.socket.recv(4096).decode('utf-8')
            return json.loads(response_data)
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
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
        """Get storage size from user input"""
        while True:
            try:
                size_input = input("💾 Enter storage capacity for this node (in MB, default 500MB): ").strip()
                if not size_input:
                    return 500
                
                size_mb = int(size_input)
                if size_mb > 0:
                    return size_mb
                else:
                    print("❌ Please enter a positive number")
            except ValueError:
                print("❌ Please enter a valid number")
    
    def get_user_info(self):
        """Get current user information"""
        if not self.is_logged_in:
            return {'status': 'error', 'message': 'Not logged in'}
        
        response = self.send_command({
            'type': 'get_user_info'
        })
        
        return response
    
    def list_user_nodes(self):
        """List nodes owned by current user"""
        if not self.is_logged_in:
            return {'status': 'error', 'message': 'Not logged in'}
        
        response = self.send_command({
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
                print(f"   Storage: {user_info['used_storage_mb']:.1f}/{user_info['storage_quota_mb']} MB")
                print(f"   Available: {user_info['available_storage_mb']:.1f} MB")
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
            self.is_logged_in = False
            self.user_session = None
            self.user_info = None
            print("👋 Logged out successfully")
            # Keep node connection active
        
        else:
            return False  # Command not handled here
        
        return True  # Command handled
    
    def interactive_mode(self):
        """Enhanced interactive mode with account features"""
        print(f"\n🎮 Secure Node {self.node_id} Interactive Mode")
        if self.is_logged_in:
            print(f"👤 User: {self.user_info['username']}")
            print(f"💾 Storage: {self.user_info['used_storage_mb']:.1f}/{self.user_info['storage_quota_mb']} MB")
        else:
            print("🔐 UTP Authentication Only")
        
        print("Commands:")
        if self.is_logged_in:
            print("  user_info                         - Show user account information")
            print("  my_nodes                          - List nodes owned by you")
        print("  connect <node_id>                    - Connect to another node")
        print("  transfer <node_id> <file> [size]     - Transfer virtual file")
        print("  transfer_actual <node_id> <file>     - Transfer actual file from storage")
        print("  create_file <name> <size_mb> [type]  - Create actual file")
        print("  list_files                           - List files in local storage")
        print("  delete_file <name>                   - Delete file from local storage")
        print("  stats                                - Show network statistics")
        print("  discovery                            - Show network discovery")
        print("  storage_info                         - Show node storage utilization")
        if self.is_logged_in:
            print("  logout                             - Logout from account")
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
                        self.socket.close()
                    break
                
                # Handle other commands using parent class logic
                self.interactive_mode_command(cmd)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                if self.socket:
                    self.socket.close()
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