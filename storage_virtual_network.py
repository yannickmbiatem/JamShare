from typing import Dict, List, Optional, Tuple
import hashlib
import time
import uuid
from storage_virtual_node import StorageVirtualNode, FileTransfer, TransferStatus, FileChunk
from collections import defaultdict

class StorageVirtualNetwork:
    def __init__(self):
        self.nodes: Dict[str, StorageVirtualNode] = {}
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        self.node_discovery_table: Dict[str, Dict] = {}  # Network-wide node registry
        self.connections: Dict[Tuple[str, str], int] = {}  # (node1, node2): bandwidth
        
    def create_node(self, node_id: str, cpu_capacity=4, memory_capacity=16, 
                   storage_capacity=500, bandwidth=1000, ip_address=None, mac_address=None):
        """Create a new node in the network with network identity"""
        if node_id in self.nodes:
            return False
            
        node = StorageVirtualNode(
            node_id=node_id,
            cpu_capacity=cpu_capacity,
            memory_capacity=memory_capacity,
            storage_capacity=storage_capacity,
            bandwidth=bandwidth,
            ip_address=ip_address,
            mac_address=mac_address
        )
        self.nodes[node_id] = node
        
        # Add to discovery table
        self.node_discovery_table[node_id] = {
            'ip_address': ip_address,
            'mac_address': mac_address,
            'joined_at': time.time(),
            'status': 'online'
        }
        
        # Update all existing nodes about new node
        self._update_node_discovery()
        
        return True
    
    def _update_node_discovery(self):
        """Update all nodes with current network discovery table"""
        for node_id, node in self.nodes.items():
            for discovered_id, discovered_info in self.node_discovery_table.items():
                if discovered_id != node_id:  # Don't add self to discovery
                    node.add_discovered_node(discovered_id, discovered_info)
    
    def add_node(self, node: StorageVirtualNode):
        """Add an existing node to the network"""
        self.nodes[node.node_id] = node
        
        # Add to discovery table if not already present
        if node.node_id not in self.node_discovery_table:
            self.node_discovery_table[node.node_id] = {
                'ip_address': node.network_info.ip_address,
                'mac_address': node.network_info.mac_address,
                'joined_at': node.network_info.joined_at,
                'status': 'online'
            }
        
        self._update_node_discovery()
    
    def remove_node(self, node_id: str):
        """Remove a node from the network"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            if node_id in self.node_discovery_table:
                self.node_discovery_table[node_id]['status'] = 'offline'
                self.node_discovery_table[node_id]['left_at'] = time.time()
            
            self._update_node_discovery()
            return True
        return False
    
    def connect_nodes(self, node1_id: str, node2_id: str, bandwidth: int = 1000) -> bool:
        """Connect two nodes with specified bandwidth"""
        if node1_id not in self.nodes or node2_id not in self.nodes:
            print(f"❌ Cannot connect: One or both nodes not found")
            return False
            
        # Create bidirectional connection
        self.connections[(node1_id, node2_id)] = bandwidth
        self.connections[(node2_id, node1_id)] = bandwidth
        
        # Update nodes about each other
        node1_info = {
            'ip_address': self.nodes[node1_id].network_info.ip_address,
            'mac_address': self.nodes[node1_id].network_info.mac_address,
            'bandwidth': bandwidth
        }
        node2_info = {
            'ip_address': self.nodes[node2_id].network_info.ip_address,
            'mac_address': self.nodes[node2_id].network_info.mac_address,
            'bandwidth': bandwidth
        }
        
        self.nodes[node1_id].connections[node2_id] = bandwidth
        self.nodes[node2_id].connections[node1_id] = bandwidth
        
        print(f"🔗 Connected {node1_id} ↔ {node2_id} with {bandwidth} Mbps")
        return True
    
    def initiate_file_transfer(self, source_node_id: str, target_node_id: str, 
                             file_name: str, file_size: int) -> Optional[FileTransfer]:
        """Initiate a file transfer between nodes"""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            print(f"❌ Transfer failed: Nodes not found")
            return None
            
        if (source_node_id, target_node_id) not in self.connections:
            print(f"❌ Transfer failed: Nodes not connected")
            return None
        
        # Create file transfer object
        file_id = str(uuid.uuid4())[:8]
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = (file_size + chunk_size - 1) // chunk_size
        
        chunks = []
        for i in range(num_chunks):
            chunk_size_actual = min(chunk_size, file_size - i * chunk_size)
            chunk_checksum = hashlib.md5(f"{file_id}_{i}".encode()).hexdigest()
            chunks.append(FileChunk(
                chunk_id=i,
                size=chunk_size_actual,
                checksum=chunk_checksum,
                status=TransferStatus.PENDING
            ))
        
        transfer = FileTransfer(
            file_id=file_id,
            file_name=file_name,
            total_size=file_size,
            chunks=chunks,
            status=TransferStatus.IN_PROGRESS
        )
        
        # Store transfer operation
        self.transfer_operations[source_node_id][file_id] = transfer
        
        print(f"📤 Transfer initiated: {file_id} ({file_name}, {file_size} bytes)")
        print(f"   From: {source_node_id} → To: {target_node_id}")
        print(f"   Chunks: {num_chunks}")
        
        return transfer
    
    def process_file_transfer(self, source_node_id: str, target_node_id: str, 
                            file_id: str, chunks_per_step: int = 3) -> Tuple[int, bool]:
        """Process file transfer in chunks"""
        if source_node_id not in self.transfer_operations:
            return 0, False
            
        if file_id not in self.transfer_operations[source_node_id]:
            return 0, False
        
        transfer = self.transfer_operations[source_node_id][file_id]
        chunks_processed = 0
        
        # Process chunks
        for chunk in transfer.chunks:
            if chunk.status == TransferStatus.PENDING and chunks_processed < chunks_per_step:
                chunk.status = TransferStatus.COMPLETED
                chunk.stored_node = target_node_id
                chunks_processed += 1
        
        # Check if transfer is complete
        all_completed = all(chunk.status == TransferStatus.COMPLETED for chunk in transfer.chunks)
        
        if all_completed:
            transfer.status = TransferStatus.COMPLETED
            transfer.completed_at = time.time()
            
            # Update target node storage
            if target_node_id in self.nodes:
                self.nodes[target_node_id].used_storage += transfer.total_size
                self.nodes[target_node_id].stored_files[file_id] = transfer
                self.nodes[target_node_id].total_data_transferred += transfer.total_size
            
            # Update source node metrics
            if source_node_id in self.nodes:
                self.nodes[source_node_id].total_data_transferred += transfer.total_size
            
            print(f"✅ Transfer {file_id} completed!")
        
        return chunks_processed, all_completed
    
    def get_network_stats(self) -> Dict:
        """Get network statistics"""
        total_storage = sum(node.total_storage for node in self.nodes.values())
        used_storage = sum(node.used_storage for node in self.nodes.values())
        total_bandwidth = sum(node.bandwidth for node in self.nodes.values())
        
        active_transfers = 0
        for node_transfers in self.transfer_operations.values():
            for transfer in node_transfers.values():
                if transfer.status == TransferStatus.IN_PROGRESS:
                    active_transfers += 1
        
        return {
            'total_nodes': len(self.nodes),
            'total_connections': len(self.connections) // 2,  # Divide by 2 for bidirectional
            'storage_utilization': (used_storage / total_storage * 100) if total_storage > 0 else 0,
            'bandwidth_utilization': 0,  # Simplified for now
            'active_transfers': active_transfers,
            'total_data_transferred': sum(node.total_data_transferred for node in self.nodes.values())
        }