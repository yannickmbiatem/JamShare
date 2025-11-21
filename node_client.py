import socket
import json
import time
import sys
from storage_virtual_node import StorageVirtualNode

class NodeClient:
    def __init__(self, node_id, server_host='localhost', server_port=8889):
        self.node_id = node_id
        self.server_host = server_host
        self.server_port = server_port
        self.node = None
        self.connected = False
        self.socket = None
        
    def connect_to_server(self):
        """Connect this node to the cloud server and register"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set timeout for connection attempt
            self.socket.settimeout(10)
            
            print(f"🔌 Connecting to cloud server at {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))
            
            # Registration code
            registration_data = {
                'type': 'register_node',
                'node_id': self.node_id,
                'cpu_capacity': 4,
                'memory_capacity': 16,
                'storage_capacity': 500,
                'bandwidth': 1000
            }
            
            response = self.send_command(registration_data)
            
            if response.get('status') == 'success':
                network_info = response['network_info']
                
                self.node = StorageVirtualNode(
                    node_id=self.node_id,
                    cpu_capacity=4,
                    memory_capacity=16,
                    storage_capacity=500,
                    bandwidth=1000,
                    ip_address=network_info['ip_address'],
                    mac_address=network_info['mac_address']
                )
                
                self.node.update_network_info(
                    ip_address=network_info['ip_address'],
                    mac_address=network_info['mac_address'],
                    cloud_server=network_info['cloud_server']
                )
                
                existing_nodes = response.get('existing_nodes', [])
                print(f"🌐 Network has {len(existing_nodes)} existing nodes: {existing_nodes}")
                
                self.connected = True
                print("✅ Node successfully joined the cloud network!")
                return True
            else:
                print(f"❌ Registration failed: {response.get('message', 'Unknown error')}")
                return False
                
        except socket.timeout:
            print(f"❌ Connection timeout: Server at {self.server_host}:{self.server_port} is not responding")
            return False
        except ConnectionRefusedError:
            print(f"❌ Connection refused: Make sure the cloud server is running on {self.server_host}:{self.server_port}")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send_command(self, command):
        """Send command to server and get response"""
        try:
            if not self.socket:
                return {'status': 'error', 'message': 'Not connected to server'}
                
            self.socket.send(json.dumps(command).encode('utf-8'))
            response_data = self.socket.recv(4096).decode('utf-8')
            return json.loads(response_data)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def create_node(self, cpu_capacity=4, memory_capacity=16, storage_capacity=500, bandwidth=1000):
        """Create this node locally and register with server"""
        # This is now handled in connect_to_server
        return True
    
    def connect_to_node(self, other_node_id, bandwidth=1000):
        """Connect to another node through the server"""
        response = self.send_command({
            'type': 'connect_nodes',
            'node1_id': self.node_id,
            'node2_id': other_node_id,
            'bandwidth': bandwidth
        })
        
        if response['status'] == 'success':
            print(f"🔗 Connected to node {other_node_id}")
            return True
        else:
            print(f"❌ Failed to connect to {other_node_id}")
            return False
    
    def initiate_transfer(self, target_node_id, file_name, file_size):
        """Initiate file transfer to another node"""
        response = self.send_command({
            'type': 'initiate_transfer',
            'source_node_id': self.node_id,
            'target_node_id': target_node_id,
            'file_name': file_name,
            'file_size': file_size
        })
        
        if response['status'] == 'success':
            print(f"📤 Transfer initiated: {response['file_id']}")
            return response['file_id']
        else:
            print(f"❌ Transfer failed: {response.get('message', 'Unknown error')}")
            return None
    
    def process_transfer(self, source_node_id, file_id, chunks_per_step=3):
        """Process ongoing transfer"""
        response = self.send_command({
            'type': 'process_transfer',
            'source_node_id': source_node_id,
            'target_node_id': self.node_id,
            'file_id': file_id,
            'chunks_per_step': chunks_per_step
        })
        
        if response['status'] == 'success':
            chunks_done = response['chunks_done']
            completed = response['completed']
            
            print(f"🔄 Transferred {chunks_done} chunks, completed: {completed}")
            
            if completed:
                print("✅ Transfer completed successfully!")
                
            return chunks_done, completed
        return 0, False
    
    def get_network_stats(self):
        """Get network statistics from server"""
        response = self.send_command({
            'type': 'get_stats'
        })
        
        if response['status'] == 'success':
            return response['stats']
        return None
    
    def get_network_discovery(self):
        """Get current network discovery information"""
        response = self.send_command({
            'type': 'get_network_info',
            'node_id': self.node_id
        })
        
        if response.get('status') == 'success':
            return response['network_info']
        return None
    
    def interactive_mode(self):
        """Interactive terminal interface for this node"""
        print(f"\n🎮 Node {self.node_id} Interactive Mode")
        print("Commands: connect <node_id>, transfer <node_id> <file> [size], stats, discovery, quit")
        
        while True:
            try:
                cmd = input(f"node_{self.node_id}> ").strip().split()
                if not cmd:
                    continue
                    
                if cmd[0] == 'connect' and len(cmd) == 2:
                    other_node = cmd[1]
                    if self.connect_to_node(other_node):
                        print(f"🔗 Connected to {other_node}")
                    else:
                        print(f"❌ Failed to connect to {other_node}")
                        
                elif cmd[0] == 'transfer' and len(cmd) >= 3:
                    target_node = cmd[1]
                    file_name = cmd[2]
                    file_size = int(cmd[3]) if len(cmd) > 3 else 100 * 1024 * 1024  # Default 100MB
                    
                    file_id = self.initiate_transfer(target_node, file_name, file_size)
                    if file_id:
                        # Process the transfer
                        while True:
                            chunks_done, completed = self.process_transfer(self.node_id, file_id)
                            if completed:
                                break
                            time.sleep(1)  # Simulate processing delay
                            
                elif cmd[0] == 'stats':
                    stats = self.get_network_stats()
                    if stats:
                        print(f"🌐 Network Stats:")
                        print(f"   Nodes: {stats['total_nodes']}")
                        print(f"   Bandwidth Usage: {stats['bandwidth_utilization']:.2f}%")
                        print(f"   Storage Usage: {stats['storage_utilization']:.2f}%")
                        print(f"   Active Transfers: {stats['active_transfers']}")
                        
                elif cmd[0] == 'discovery':
                    discovery_info = self.get_network_discovery()
                    if discovery_info:
                        print(f"🔍 Network Discovery:")
                        print(f"   Total Nodes: {discovery_info['total_nodes']}")
                        for node_id, info in discovery_info.get('node_discovery_table', {}).items():
                            status = info.get('status', 'unknown')
                            ip = info.get('ip_address', 'unknown')
                            print(f"   - {node_id}: {ip} ({status})")
                        
                elif cmd[0] == 'quit':
                    print("👋 Goodbye!")
                    if self.socket:
                        self.socket.close()
                    break
                    
                else:
                    print("❓ Unknown command. Use: connect <node>, transfer <node> <file> [size], stats, discovery, quit")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                if self.socket:
                    self.socket.close()
                break
            except Exception as e:
                print(f"💥 Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python node_client.py <node_id>")
        print("Example: python node_client.py node1")
        sys.exit(1)
    
    node_id = sys.argv[1]
    client = NodeClient(node_id)
    
    if client.connect_to_server():
        client.interactive_mode()
    else:
        print(f"❌ Node {node_id} failed to join the cloud network")
        print("💡 Make sure:")
        print("   1. The cloud server is running")
        print("   2. The server port is correct (currently 8889)")
        print("   3. No firewall is blocking the connection")