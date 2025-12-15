import socket
import threading
import json
import time
import secrets
from cloud_server import CloudServer
from auth_service import AuthenticationServer, EnrollmentProtocol

class SecureCloudServer(CloudServer):
    """Enhanced cloud server with simplified authentication and user accounts"""
    
    def __init__(self, host='localhost', port=8889, 
                 email_sender=None, email_password=None, enable_email=False):
        # NOTE: email parameters are ignored as UTP/email is removed.
        super().__init__(host, port)
        self.auth_server = AuthenticationServer() 
        self.authenticated_nodes = {}  # Track authenticated node sessions (node_id: info)
        self.user_connections = {}     # Track user sessions (session_token: username)
        self.DEFAULT_STORAGE_MB = 1024  # 1GB default storage per node
        
    def handle_client(self, client_socket, client_address):
        """
        Handles initial requests (Register/Login/Enrollment Start).
        """
        try:
            client_socket.settimeout(10)
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                client_socket.close()
                return
                
            request = json.loads(data)
            request_type = request.get('type')
            
            # --- Handle Transient Requests (Register/Login) ---
            if request_type == 'register_account':
                response = self.handle_account_registration(request)
                client_socket.send(json.dumps(response).encode('utf-8'))
                client_socket.close()
                return
            
            elif request_type == 'login_account':
                response = self.handle_account_login(request)
                client_socket.send(json.dumps(response).encode('utf-8'))
                client_socket.close()
                return

            # --- Handle Single-Step Enrollment (Initiates Persistent Connection) ---
            elif request_type == 'enrollment_request':
                response = self.handle_node_enrollment(request, client_address)
                client_socket.send(json.dumps(response).encode('utf-8'))

                if response.get('status') == 'enrollment_completed':
                    # Enrollment successful. Enter persistent mode.
                    client_socket.node_id = response.get('node_id') 
                    self.process_persistent_connection(client_socket, client_address)
                    return 
                else:
                    client_socket.close()
                    return
            
            else:
                client_socket.send(json.dumps({'status': 'error', 'message': 'Invalid initial command or not connected.'}).encode('utf-8'))
                client_socket.close()
                return

        except socket.timeout:
            print(f"🕒 Client {client_address} connection timed out during initial request.")
        except Exception as e:
            # print(f"Error handling client {client_address}: {e}")
            pass 
        finally:
            if not hasattr(client_socket, 'node_id') or not client_socket.node_id:
                 try:
                     client_socket.close()
                 except:
                     pass

    def process_persistent_connection(self, client_socket, client_address):
        """
        Handles authenticated session commands for a node.
        """
        client_socket.settimeout(600) 
        node_id = getattr(client_socket, 'node_id', 'Unknown')
        print(f"🔗 Starting persistent session for node {node_id} at {client_address}")

        while self.running:
            try:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    print(f"📣 Node {node_id} closed connection.")
                    break 

                command = json.loads(data)
                
                # All commands are handled as authenticated commands
                response = self.handle_authenticated_commands(command, client_socket, client_address)
                
                client_socket.send(json.dumps(response).encode('utf-8'))

            except socket.timeout:
                print(f"🕒 Node {node_id} connection timed out.")
                break
            except ConnectionResetError:
                print(f"❌ Node {node_id} forced close on connection.")
                break
            except Exception as e:
                print(f"💥 Error in persistent session for node {node_id}: {e}")
                break 
        
        self.handle_client_disconnect(client_socket)
        print(f"🛑 Persistent session ended for node {node_id}")


    # --- Authentication Handlers ---

    def handle_account_registration(self, request):
        """Handles user account registration"""
        username = request.get('username')
        email = request.get('email')
        password = request.get('password')
        storage_mb = request.get('storage_quota', self.DEFAULT_STORAGE_MB)
        
        try:
            self.auth_server.register_user(username, email, password, storage_quota_mb=storage_mb)
            return {'status': 'success', 'message': f'User registered successfully with {storage_mb}MB storage quota'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def handle_account_login(self, request):
        """Handles user account login"""
        username = request.get('username')
        password = request.get('password')
        
        try:
            session_token = self.auth_server.login_user(username, password)
            user_info = self.auth_server.get_user_info(username)
            
            # Track user session (CRITICAL for node enrollment validation)
            self.user_connections[session_token] = username
            
            return {
                'status': 'success', 
                'message': 'Login successful',
                'session_token': session_token,
                'user_info': user_info
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def handle_node_enrollment(self, request, client_address):
        """
        Handles the single-step node enrollment process.
        Requires a valid user_session_token for authentication.
        """
        node_id = request.get('node_id')
        user_session_token = request.get('session_token')
        storage_gb = request.get('storage_capacity', self.DEFAULT_STORAGE_MB / 1024)
        
        # 1. Validate User Session Token
        username = self.user_connections.get(user_session_token)
        if not username:
            return {'status': 'error', 'message': 'Invalid or expired user session token. Please log in first.'}

        try:
            # 2. Register Node in Auth Metadata (handles already existing nodes)
            self.auth_server.register_node(node_id, storage_gb)
            
            # 3. Network Setup
            mac_address = self.generate_mac_address()
            ip_address = self.generate_ip_address()
            
            # Create the node in the virtual network
            self.network.create_node(
                node_id=node_id,
                cpu_capacity=request.get('cpu_capacity', 4),
                memory_capacity=request.get('memory_capacity', 16),
                storage_capacity=storage_gb,
                bandwidth=request.get('bandwidth', 1000),
                ip_address=ip_address,
                mac_address=mac_address
            )
            
            # 4. Generate Node Session Token and Link Node to User
            node_session_token = secrets.token_hex(32)
            self.auth_server.add_node_to_user(username, node_id)
            
            # 5. Register the authenticated node session
            self.authenticated_nodes[node_id] = {
               'session_token': node_session_token,
               'ip_address': ip_address,
               'mac_address': mac_address,
               'user_session': user_session_token
            }
            print(f"✅ Node {node_id} enrolled by user {username} and joined network.")
            
            # 6. Package Response
            network_info = {
                'node_id': node_id,
                'ip_address': ip_address,
                'mac_address': mac_address,
                'cloud_server': f'{self.host}:{self.port}'
            }
            
            user_info = self.auth_server.get_user_info(username)
            
            return {
                'status': 'enrollment_completed',
                'message': f'Node {node_id} successfully enrolled.',
                'node_id': node_id, 
                'session_token': node_session_token, # The token for future node commands
                'network_info': network_info,
                'user_info': user_info
            }
            
        except Exception as e:
            # Clean up the IP if it was assigned before the crash
            if 'ip_address' in locals() and ip_address:
                 self.release_ip_address(ip_address)
            print(f"❌ Node Enrollment Failed: {e}")
            return {'status': 'error', 'message': str(e)}
            
    # --- Command Handling (Existing Logic) ---
    def handle_authenticated_commands(self, command, client_socket, client_address):
        """Handles commands after a node has fully enrolled OR a user is logged in."""
        session_token = command.get('session_token')
        command_type = command.get('type')
        
        # 1. Check for authenticated Node Session (for data/network commands)
        node_id = next((nid for nid, info in self.authenticated_nodes.items() 
                        if info['session_token'] == session_token), None)
        
        if node_id:
            # We have an authenticated Node Session
            if not hasattr(client_socket, 'node_id'):
                client_socket.node_id = node_id

            if command_type == 'stats':
                return self.handle_stats_command(command, node_id)
            elif command_type == 'discovery':
                return self.handle_discovery_command(command, node_id)
            elif command_type == 'connect_node':
                return self.handle_connect_node_command(command, node_id)
            elif command_type == 'transfer_file':
                return self.handle_transfer_file_command(command, node_id)
            elif command_type == 'transfer_actual_file':
                return self.handle_transfer_actual_file_command(command, node_id)
            elif command_type == 'create_actual_file':
                return self.handle_create_actual_file_command(command, node_id)
            elif command_type == 'list_files':
                return self.handle_list_files_command(command, node_id)
            elif command_type == 'delete_file':
                return self.handle_delete_file_command(command, node_id)
            elif command_type == 'storage_info':
                return self.handle_storage_info_command(command, node_id)
            else:
                return {'status': 'error', 'message': f'Unknown node command type: {command_type}'}
        
        # 2. Check for authenticated User Session (for account commands)
        username = self.user_connections.get(session_token)
        if username:
            return self.handle_user_commands(command, username)
        
        # 3. Neither authenticated
        return {'status': 'error', 'message': 'Invalid or expired session token (authentication required)'}

    def handle_user_commands(self, command, username):
        """Handles commands related to the user account (e.g., user_info, my_nodes)"""
        command_type = command.get('type')
        
        if command_type == 'get_user_info':
            try:
                user_info = self.auth_server.get_user_info(username)
                return {'status': 'success', 'user_info': user_info}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        
        elif command_type == 'list_user_nodes':
            try:
                nodes = self.auth_server.list_user_nodes(username)
                node_list = []
                for node_id in nodes:
                    status = 'active' if node_id in self.authenticated_nodes else 'inactive'
                    node_list.append({'node_id': node_id, 'status': status})
                return {'status': 'success', 'nodes': node_list}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        
        elif command_type == 'logout_account':
            session_token = command.get('session_token')
            if session_token in self.user_connections:
                del self.user_connections[session_token]
                return {'status': 'success', 'message': 'Logged out successfully'}
            else:
                return {'status': 'error', 'message': 'Session not found'}

        else:
            return {'status': 'error', 'message': f'Unknown user command type: {command_type}'}

    # --- Other command handlers (Inherited from CloudServer) ---
    def handle_stats_command(self, command, node_id):
        return {'status': 'success', 'stats': self.network.get_network_stats()}
    
    def handle_discovery_command(self, command, node_id):
        return {'status': 'success', 'discovery_table': self.network.node_discovery_table}
        
    def handle_connect_node_command(self, command, node_id):
        target_node = command.get('target_node')
        response = self.network.connect_nodes(node_id, target_node)
        if response:
            return {'status': 'success', 'message': f'Successfully connected {node_id} to {target_node}'}
        return {'status': 'error', 'message': f'Failed to connect {node_id} to {target_node}'}
        
    def handle_transfer_file_command(self, command, node_id):
        return {'status': 'success', 'message': 'Virtual transfer initiated (not fully implemented in cloud server)'}
        
    def handle_transfer_actual_file_command(self, command, node_id):
        return {'status': 'success', 'message': 'Actual file transfer initiated (requires further implementation)'}
        
    def handle_create_actual_file_command(self, command, node_id):
        return {'status': 'success', 'message': 'File created (client side operation)'}
    
    def handle_list_files_command(self, command, node_id):
        return {'status': 'success', 'files': []}
        
    def handle_delete_file_command(self, command, node_id):
        return {'status': 'success', 'message': 'File deleted (client side operation)'}
        
    def handle_storage_info_command(self, command, node_id):
        if node_id in self.network.nodes:
            node = self.network.nodes[node_id]
            return {'status': 'success', 'storage_info': {
                'total_mb': node.total_storage * 1024,
                'used_mb': node.used_storage * 1024,
                'available_mb': node.get_available_storage() * 1024,
                'utilization_percent': node.get_storage_utilization()
            }}
        return {'status': 'error', 'message': 'Node not found'}


    def handle_client_disconnect(self, client_socket):
        """Handle client disconnection with cleanup"""
        if hasattr(client_socket, 'node_id') and client_socket.node_id:
            node_id = client_socket.node_id
            if node_id in self.authenticated_nodes:
                del self.authenticated_nodes[node_id] 
            print(f"📢 Node {node_id} disconnected from secure network")
        
        super().handle_client_disconnect(client_socket)

if __name__ == "__main__":
    server = SecureCloudServer()
    print("🔐 Secure Cloud Server with Simplified Authentication and User Accounts")
    print("📍 Starting on localhost:8889")
    print("💾 Default storage per node: 1024 MB (1GB)")
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.terminate_cloud_service()