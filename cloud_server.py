import socket
import threading
import random
import uuid
import time  # ← THIS FIXES THE ERROR
from storage_virtual_network import StorageVirtualNetwork
import json

class CloudServer:
    def __init__(self, host='localhost', port=8889):
        self.network = StorageVirtualNetwork()
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.node_registry = {}  # Track registered nodes and their addresses
        self.ip_pool = set(range(100, 255))  # Available IP addresses (192.168.1.100-254)
        
    def generate_mac_address(self):
        """Generate a random MAC address"""
        return "02:%02x:%02x:%02x:%02x:%02x" % (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
    
    def generate_ip_address(self):
        """Generate a unique IP address from the pool"""
        if not self.ip_pool:
            raise Exception("No available IP addresses in pool")
        ip_suffix = self.ip_pool.pop()
        return f"192.168.1.{ip_suffix}"
    
    def release_ip_address(self, ip_address):
        """Release IP address back to pool when node disconnects"""
        ip_suffix = int(ip_address.split('.')[-1])
        self.ip_pool.add(ip_suffix)
    
    def broadcast_node_joined(self, node_id, ip_address, mac_address):
        """Broadcast new node notification to all connected nodes"""
        notification = {
            'type': 'node_joined',
            'node_id': node_id,
            'ip_address': ip_address,
            'mac_address': mac_address,
            'timestamp': time.time()
        }
        
        # In a real implementation, you'd send this to all connected nodes
        print(f"📢 NETWORK BROADCAST: Node {node_id} joined the network")
        print(f"   📍 IP: {ip_address}, MAC: {mac_address}")
        
        # Store for new nodes to discover existing network
        self.network.node_discovery_table[node_id] = {
            'ip_address': ip_address,
            'mac_address': mac_address,
            'joined_at': time.time()
        }
    
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"🌩️ Cloud Server started on {self.host}:{self.port}")
        
        while self.running:
            client_socket, address = self.server_socket.accept()
            print(f"📡 New connection from {address}")
            client_thread = threading.Thread(
                target=self.handle_client, 
                args=(client_socket, address)
            )
            client_thread.start()
    
    def handle_client(self, client_socket, client_address):
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                response = self.process_command(json.loads(data), client_address)
                client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            # Handle node disconnection
            if hasattr(client_socket, 'node_id') and client_socket.node_id:
                node_id = client_socket.node_id
                if node_id in self.node_registry:
                    node_info = self.node_registry[node_id]
                    self.release_ip_address(node_info['ip_address'])
                    del self.node_registry[node_id]
                    print(f"📢 Node {node_id} disconnected from network")
            client_socket.close()
    
    def process_command(self, command, client_address):
        cmd_type = command.get('type')
        
        if cmd_type == 'register_node':
            return self.register_node(command, client_address)
        elif cmd_type == 'get_network_info':
            return self.get_network_info(command)
        elif cmd_type == 'connect_nodes':
            return self.connect_nodes(command)
        elif cmd_type == 'initiate_transfer':
            return self.initiate_transfer(command)
        elif cmd_type == 'process_transfer':
            return self.process_transfer(command)
        elif cmd_type == 'get_stats':
            return self.get_network_stats(command)
        else:
            return {'status': 'error', 'message': 'Unknown command'}
    
    def register_node(self, command, client_address):
        """Register a new node and assign network addresses"""
        node_id = command['node_id']
        
        if node_id in self.node_registry:
            return {
                'status': 'error', 
                'message': f'Node {node_id} already registered'
            }
        
        try:
            # Generate network addresses
            ip_address = self.generate_ip_address()
            mac_address = self.generate_mac_address()
            
            # Create node in network
            success = self.network.create_node(
                node_id=node_id,
                cpu_capacity=command.get('cpu_capacity', 4),
                memory_capacity=command.get('memory_capacity', 16),
                storage_capacity=command.get('storage_capacity', 500),
                bandwidth=command.get('bandwidth', 1000),
                ip_address=ip_address,
                mac_address=mac_address
            )
            
            if success:
                # Store node registration info
                self.node_registry[node_id] = {
                    'ip_address': ip_address,
                    'mac_address': mac_address,
                    'client_address': client_address,
                    'registered_at': time.time()
                }
                
                # Broadcast node joined notification
                self.broadcast_node_joined(node_id, ip_address, mac_address)
                
                return {
                    'status': 'success',
                    'message': f'Node {node_id} registered successfully',
                    'network_info': {
                        'ip_address': ip_address,
                        'mac_address': mac_address,
                        'cloud_server': f'{self.host}:{self.port}'
                    },
                    'existing_nodes': list(self.network.nodes.keys())
                }
            else:
                return {'status': 'error', 'message': 'Failed to create node'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'Registration failed: {str(e)}'}
    
    def get_network_info(self, command):
        """Provide network discovery information to nodes"""
        node_id = command.get('node_id')
        
        network_info = {
            'total_nodes': len(self.network.nodes),
            'node_discovery_table': getattr(self.network, 'node_discovery_table', {}),
            'cloud_timestamp': time.time()
        }
        
        return {'status': 'success', 'network_info': network_info}
    
    def connect_nodes(self, command):
        node1_id = command['node1_id']
        node2_id = command['node2_id']
        bandwidth = command['bandwidth']
        
        success = self.network.connect_nodes(node1_id, node2_id, bandwidth)
        return {'status': 'success' if success else 'error'}
    
    def initiate_transfer(self, command):
        transfer = self.network.initiate_file_transfer(
            source_node_id=command['source_node_id'],
            target_node_id=command['target_node_id'],
            file_name=command['file_name'],
            file_size=command['file_size']
        )
        
        if transfer:
            return {'status': 'success', 'file_id': transfer.file_id}
        return {'status': 'error', 'message': 'Transfer failed'}
    
    def process_transfer(self, command):
        chunks_done, completed = self.network.process_file_transfer(
            source_node_id=command['source_node_id'],
            target_node_id=command['target_node_id'],
            file_id=command['file_id'],
            chunks_per_step=command.get('chunks_per_step', 1)
        )
        
        return {
            'status': 'success',
            'chunks_done': chunks_done,
            'completed': completed
        }
    
    def get_network_stats(self, command):
        stats = self.network.get_network_stats()
        return {'status': 'success', 'stats': stats}

if __name__ == "__main__":
    server = CloudServer()
    print("🌩️ Starting Cloud Storage Network Server...")
    print("📍 Server will automatically assign IP/MAC addresses to joining nodes")
    server.start()