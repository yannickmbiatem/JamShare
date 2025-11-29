import socket
import threading
import json
import time
from cloud_server import CloudServer
from auth_service import AuthenticationServer, EnrollmentProtocol

class SecureCloudServer(CloudServer):
    """Enhanced cloud server with UTP authentication"""
    
    def __init__(self, host='localhost', port=8889, 
                 email_sender=None, email_password=None, enable_email=True):
        super().__init__(host, port)
        self.auth_server = AuthenticationServer(
            email_sender=email_sender,
            email_password=email_password,
            enable_email=enable_email
        )
        self.authenticated_nodes = {}  # Track authenticated node sessions
        
    def handle_client(self, client_socket, client_address):
        """Enhanced client handler with authentication"""
        try:
            # Initial handshake for authentication
            auth_data = client_socket.recv(1024).decode('utf-8')
            if not auth_data:
                return
                
            initial_msg = json.loads(auth_data)
            
            # Check if this is an enrollment request
            if initial_msg.get('type') == 'enrollment_request':
                self.handle_enrollment(client_socket, initial_msg)
                return
                
            # Check if this is a regular command with authentication
            if not self.authenticate_client(initial_msg, client_socket):
                return
                
            # Process authenticated commands
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                response = self.process_authenticated_command(json.loads(data), client_socket)
                client_socket.send(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            self.handle_client_disconnect(client_socket)
    
    def handle_enrollment(self, client_socket, enrollment_msg):
        """Handle UTP enrollment process"""
        try:
            node_id = enrollment_msg['node_id']
            user_email = enrollment_msg['user_email']
            user_name = enrollment_msg.get('user_name', 'User')
            
            print(f"🔐 Starting UTP enrollment for node {node_id}")
            
            # Start enrollment process
            auth_token = self.auth_server.start_enrollment(node_id, user_email, user_name)
            
            if auth_token:
                response = {
                    'status': 'enrollment_started',
                    'auth_token': auth_token,
                    'message': 'Verification email sent'
                }
            else:
                response = {
                    'status': 'error',
                    'message': 'Failed to start enrollment'
                }
                
            client_socket.send(json.dumps(response).encode('utf-8'))
            
            # Wait for verification
            verification_data = client_socket.recv(1024).decode('utf-8')
            verification_msg = json.loads(verification_data)
            
            if verification_msg.get('type') == 'verification_request':
                success, result = self.auth_server.complete_enrollment(
                    verification_msg['auth_token'],
                    verification_msg['verification_code']
                )
                
                if success:
                    session_token = result
                    self.authenticated_nodes[node_id] = {
                        'session_token': session_token,
                        'client_socket': client_socket,
                        'authenticated_at': time.time()
                    }
                    
                    # Complete node registration with superclass
                    registration_success = self.complete_node_registration(node_id, enrollment_msg)
                    
                    response = {
                        'status': 'enrollment_completed',
                        'session_token': session_token,
                        'network_info': registration_success
                    }
                else:
                    response = {
                        'status': 'error',
                        'message': result
                    }
                    
                client_socket.send(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"Enrollment error: {e}")
            client_socket.close()
    
    def complete_node_registration(self, node_id, enrollment_msg):
        """Complete node registration after successful authentication"""
        # Generate network addresses
        ip_address = self.generate_ip_address()
        mac_address = self.generate_mac_address()
        
        # Create node in network
        success = self.network.create_node(
            node_id=node_id,
            cpu_capacity=enrollment_msg.get('cpu_capacity', 4),
            memory_capacity=enrollment_msg.get('memory_capacity', 16),
            storage_capacity=enrollment_msg.get('storage_capacity', 500),
            bandwidth=enrollment_msg.get('bandwidth', 1000),
            ip_address=ip_address,
            mac_address=mac_address
        )
        
        if success:
            # Store node registration info
            self.node_registry[node_id] = {
                'ip_address': ip_address,
                'mac_address': mac_address,
                'registered_at': time.time(),
                'authenticated': True
            }
            
            # Broadcast node joined notification
            self.broadcast_node_joined(node_id, ip_address, mac_address)
            
            return {
                'ip_address': ip_address,
                'mac_address': mac_address,
                'cloud_server': f'{self.host}:{self.port}'
            }
        
        return None
    
    def authenticate_client(self, message, client_socket):
        """Authenticate client using session token"""
        node_id = message.get('node_id')
        session_token = message.get('session_token')
        
        if not node_id or not session_token:
            response = {'status': 'error', 'message': 'Authentication required'}
            client_socket.send(json.dumps(response).encode('utf-8'))
            return False
        
        # Validate access
        valid, message = self.auth_server.validate_node_access(node_id, session_token)
        if not valid:
            response = {'status': 'error', 'message': message}
            client_socket.send(json.dumps(response).encode('utf-8'))
            return False
        
        # Store authenticated connection
        self.authenticated_nodes[node_id] = {
            'session_token': session_token,
            'client_socket': client_socket,
            'authenticated_at': time.time()
        }
        
        client_socket.node_id = node_id
        return True
    
    def process_authenticated_command(self, command, client_socket):
        """Process commands from authenticated clients"""
        # Validate session for each command
        node_id = client_socket.node_id
        session_token = self.authenticated_nodes.get(node_id, {}).get('session_token')
        
        if not session_token:
            return {'status': 'error', 'message': 'Session expired'}
        
        valid, message = self.auth_server.validate_node_access(node_id, session_token)
        if not valid:
            return {'status': 'error', 'message': message}
        
        # Process the command using parent class logic
        return self.process_command(command, client_socket.getpeername())
    
    def terminate_cloud_service(self, node_id=None):
        """Terminate cloud services for specific node or all nodes"""
        if node_id:
            # Terminate service for specific node
            if node_id in self.authenticated_nodes:
                socket_info = self.authenticated_nodes[node_id]
                try:
                    socket_info['client_socket'].close()
                except:
                    pass
                del self.authenticated_nodes[node_id]
            
            if node_id in self.node_registry:
                # Release IP address
                ip_address = self.node_registry[node_id]['ip_address']
                self.release_ip_address(ip_address)
                del self.node_registry[node_id]
            
            # Remove from network
            self.network.remove_node(node_id)
            print(f"🔴 Terminated cloud service for node {node_id}")
            
        else:
            # Terminate all services
            print("🔴 Terminating all cloud services...")
            for node_id in list(self.authenticated_nodes.keys()):
                self.terminate_cloud_service(node_id)
            
            self.running = False
            self.server_socket.close()
            print("🛑 Cloud service terminated")
    
    def handle_client_disconnect(self, client_socket):
        """Handle client disconnection with cleanup"""
        if hasattr(client_socket, 'node_id') and client_socket.node_id:
            node_id = client_socket.node_id
            if node_id in self.authenticated_nodes:
                del self.authenticated_nodes[node_id]
        
        super().handle_client_disconnect(client_socket)

if __name__ == "__main__":
    server = SecureCloudServer()
    print("🔐 Secure Cloud Server with UTP Authentication")
    print("📍 Starting on localhost:8889")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
        server.terminate_cloud_service()