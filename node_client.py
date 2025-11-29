import socket
import json
import time
import sys
import os
from storage_virtual_node import StorageVirtualNode

class NodeClient:
    def __init__(self, node_id, server_host='localhost', server_port=8889):
        self.node_id = node_id
        self.server_host = server_host
        self.server_port = server_port
        self.node = None
        self.connected = False
        self.socket = None
        self.storage_directory = f"node_storage/{node_id}"
        self.create_storage_directory()
        
    def create_storage_directory(self):
        """Create directory for storing actual files"""
        os.makedirs(self.storage_directory, exist_ok=True)
        print(f"📁 Storage directory created: {self.storage_directory}")
    
    def set_node_storage(self, storage_mb):
        """Set node storage capacity in megabytes"""
        storage_gb = storage_mb / 1024  # Convert MB to GB for the node class
        return storage_gb
    
    def create_actual_file(self, file_name, file_size_mb, content_type="random"):
        """Create an actual file on disk with the specified size"""
        file_path = os.path.join(self.storage_directory, file_name)
        file_size_bytes = file_size_mb * 1024 * 1024
        
        if content_type == "random":
            # Create file with random data
            with open(file_path, 'wb') as f:
                f.write(os.urandom(file_size_bytes))
        elif content_type == "text":
            # Create file with text data
            with open(file_path, 'w') as f:
                # Generate repetitive text to fill the file size
                chunk = "This is a sample file content for storage simulation. "
                chunks_needed = file_size_bytes // len(chunk) + 1
                content = (chunk * chunks_needed)[:file_size_bytes]
                f.write(content)
        
        print(f"📄 Created actual file: {file_path} ({file_size_mb} MB)")
        return file_path, file_size_bytes
    
    def transfer_actual_file(self, source_file_path, target_node_id, target_file_name):
        """Transfer an actual file to another node"""
        if not os.path.exists(source_file_path):
            print(f"❌ Source file not found: {source_file_path}")
            return None
        
        file_size = os.path.getsize(source_file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"📤 Transferring actual file: {os.path.basename(source_file_path)} ({file_size_mb:.2f} MB)")
        
        # Initiate transfer through the network
        file_id = self.initiate_transfer(target_node_id, target_file_name, file_size)
        if not file_id:
            return None
        
        # Simulate transfer process
        chunks_done = 0
        while True:
            chunks_done_step, completed = self.process_transfer(self.node_id, file_id)
            chunks_done += chunks_done_step
            
            if completed:
                # Copy file to target node's storage directory (simulated)
                print(f"✅ File transfer completed! File stored in target node's storage")
                return file_id
            elif chunks_done_step == 0:
                print("❌ Transfer failed")
                return None
            
            time.sleep(0.5)  # Simulate transfer delay
    
    def connect_to_server(self):
        """Connect this node to the cloud server and register"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set timeout for connection attempt
            self.socket.settimeout(10)
            
            print(f"🔌 Connecting to cloud server at {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))
            
            # Get storage size from user
            storage_mb = self.get_storage_size_from_user()
            storage_gb = self.set_node_storage(storage_mb)
            
            # Registration code
            registration_data = {
                'type': 'register_node',
                'node_id': self.node_id,
                'cpu_capacity': 4,
                'memory_capacity': 16,
                'storage_capacity': storage_gb,
                'bandwidth': 1000
            }
            
            response = self.send_command(registration_data)
            
            if response.get('status') == 'success':
                network_info = response['network_info']
                
                self.node = StorageVirtualNode(
                    node_id=self.node_id,
                    cpu_capacity=4,
                    memory_capacity=16,
                    storage_capacity=storage_gb,
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
                print(f"✅ Node successfully joined the cloud network with {storage_mb} MB storage!")
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
    
    def list_local_files(self):
        """List all files in the node's local storage directory"""
        files = []
        if os.path.exists(self.storage_directory):
            for file_name in os.listdir(self.storage_directory):
                file_path = os.path.join(self.storage_directory, file_name)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_size_mb = file_size / (1024 * 1024)
                    files.append({
                        'name': file_name,
                        'size_bytes': file_size,
                        'size_mb': file_size_mb,
                        'path': file_path
                    })
        return files
    
    def get_node_storage_info(self):
        """Get node storage information"""
        if self.node:
            storage_info = self.node.get_storage_utilization()
            used_mb = storage_info['used_bytes'] / (1024 * 1024)
            total_mb = storage_info['total_bytes'] / (1024 * 1024)
            available_mb = storage_info['available_bytes'] / (1024 * 1024)
            
            return {
                'used_mb': used_mb,
                'total_mb': total_mb,
                'available_mb': available_mb,
                'utilization_percent': storage_info['utilization_percent']
            }
        return None
    
    def delete_local_file(self, file_name):
        """Delete a file from local storage"""
        file_path = os.path.join(self.storage_directory, file_name)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
            file_size_mb = file_size / (1024 * 1024)
            print(f"🗑️  Deleted file: {file_name} ({file_size_mb:.2f} MB)")
            return True
        else:
            print(f"❌ File not found: {file_name}")
            return False
    
    def interactive_mode_command(self, cmd):
        """Extract the command handling logic for reuse"""
        if cmd[0] == 'connect' and len(cmd) == 2:
            other_node = cmd[1]
            if self.connect_to_node(other_node):
                print(f"🔗 Connected to {other_node}")
            else:
                print(f"❌ Failed to connect to {other_node}")
                
        elif cmd[0] == 'transfer' and len(cmd) >= 3:
            target_node = cmd[1]
            file_name = cmd[2]
            file_size = int(cmd[3]) if len(cmd) > 3 else 10 * 1024 * 1024  # Default 10MB
            
            file_id = self.initiate_transfer(target_node, file_name, file_size)
            if file_id:
                # Process the transfer
                while True:
                    chunks_done, completed = self.process_transfer(self.node_id, file_id)
                    if completed:
                        break
                    time.sleep(1)  # Simulate processing delay
                    
        elif cmd[0] == 'transfer_actual' and len(cmd) >= 3:
            target_node = cmd[1]
            file_name = cmd[2]
            
            # Check if file exists locally
            file_path = os.path.join(self.storage_directory, file_name)
            if not os.path.exists(file_path):
                print(f"❌ File not found in local storage: {file_name}")
                print(f"💡 Use 'create_file' command to create a file first")
                return
            
            self.transfer_actual_file(file_path, target_node, file_name)
            
        elif cmd[0] == 'create_file' and len(cmd) >= 3:
            file_name = cmd[1]
            try:
                file_size_mb = int(cmd[2])
                content_type = cmd[3] if len(cmd) > 3 else "random"
                
                if content_type not in ["random", "text"]:
                    print("❌ Content type must be 'random' or 'text'")
                    return
                    
                self.create_actual_file(file_name, file_size_mb, content_type)
            except ValueError:
                print("❌ Invalid file size. Please enter a number.")
                
        elif cmd[0] == 'list_files':
            files = self.list_local_files()
            if files:
                print(f"📁 Files in {self.storage_directory}:")
                for file_info in files:
                    print(f"   📄 {file_info['name']} - {file_info['size_mb']:.2f} MB")
            else:
                print("📁 No files in local storage")
                
        elif cmd[0] == 'delete_file' and len(cmd) == 2:
            file_name = cmd[1]
            self.delete_local_file(file_name)
                
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
        
        elif cmd[0] == 'storage_info':
            storage_info = self.get_node_storage_info()
            if storage_info:
                print(f"💾 Node Storage Information:")
                print(f"   Used: {storage_info['used_mb']:.2f} MB")
                print(f"   Total: {storage_info['total_mb']:.2f} MB")
                print(f"   Available: {storage_info['available_mb']:.2f} MB")
                print(f"   Utilization: {storage_info['utilization_percent']:.2f}%")
    
    def interactive_mode(self):
        """Interactive terminal interface for this node"""
        print(f"\n🎮 Node {self.node_id} Interactive Mode")
        print("Commands:")
        print("  connect <node_id>                    - Connect to another node")
        print("  transfer <node_id> <file> [size]     - Transfer virtual file")
        print("  transfer_actual <node_id> <file>     - Transfer actual file from storage")
        print("  create_file <name> <size_mb> [type]  - Create actual file (types: random, text)")
        print("  list_files                           - List files in local storage")
        print("  delete_file <name>                   - Delete file from local storage")
        print("  stats                                - Show network statistics")
        print("  discovery                            - Show network discovery")
        print("  storage_info                         - Show node storage utilization")
        print("  quit                                 - Exit")
        
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
                    file_size = int(cmd[3]) if len(cmd) > 3 else 10 * 1024 * 1024  # Default 10MB
                    
                    file_id = self.initiate_transfer(target_node, file_name, file_size)
                    if file_id:
                        # Process the transfer
                        while True:
                            chunks_done, completed = self.process_transfer(self.node_id, file_id)
                            if completed:
                                break
                            time.sleep(1)  # Simulate processing delay
                            
                elif cmd[0] == 'transfer_actual' and len(cmd) >= 3:
                    target_node = cmd[1]
                    file_name = cmd[2]
                    
                    # Check if file exists locally
                    file_path = os.path.join(self.storage_directory, file_name)
                    if not os.path.exists(file_path):
                        print(f"❌ File not found in local storage: {file_name}")
                        print(f"💡 Use 'create_file' command to create a file first")
                        continue
                    
                    self.transfer_actual_file(file_path, target_node, file_name)
                    
                elif cmd[0] == 'create_file' and len(cmd) >= 3:
                    file_name = cmd[1]
                    try:
                        file_size_mb = int(cmd[2])
                        content_type = cmd[3] if len(cmd) > 3 else "random"
                        
                        if content_type not in ["random", "text"]:
                            print("❌ Content type must be 'random' or 'text'")
                            continue
                            
                        self.create_actual_file(file_name, file_size_mb, content_type)
                    except ValueError:
                        print("❌ Invalid file size. Please enter a number.")
                        
                elif cmd[0] == 'list_files':
                    files = self.list_local_files()
                    if files:
                        print(f"📁 Files in {self.storage_directory}:")
                        for file_info in files:
                            print(f"   📄 {file_info['name']} - {file_info['size_mb']:.2f} MB")
                    else:
                        print("📁 No files in local storage")
                        
                elif cmd[0] == 'delete_file' and len(cmd) == 2:
                    file_name = cmd[1]
                    self.delete_local_file(file_name)
                        
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
                
                elif cmd[0] == 'storage_info':
                    storage_info = self.get_node_storage_info()
                    if storage_info:
                        print(f"💾 Node Storage Information:")
                        print(f"   Used: {storage_info['used_mb']:.2f} MB")
                        print(f"   Total: {storage_info['total_mb']:.2f} MB")
                        print(f"   Available: {storage_info['available_mb']:.2f} MB")
                        print(f"   Utilization: {storage_info['utilization_percent']:.2f}%")
                        
                elif cmd[0] == 'quit':
                    print("👋 Goodbye!")
                    if self.socket:
                        self.socket.close()
                    break
                    
                else:
                    print("❓ Unknown command. Available commands:")
                    print("   connect, transfer, transfer_actual, create_file, list_files, delete_file, stats, discovery, storage_info, quit")
                    
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