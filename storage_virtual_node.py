import time
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from enum import Enum, auto
import hashlib
import uuid

class TransferStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class NetworkInfo:
    ip_address: str
    mac_address: str
    cloud_server: str
    joined_at: float

@dataclass
class FileChunk:
    chunk_id: int
    size: int  # in bytes
    checksum: str
    status: TransferStatus = TransferStatus.PENDING
    stored_node: Optional[str] = None

@dataclass
class FileTransfer:
    file_id: str
    file_name: str
    total_size: int  # in bytes
    chunks: List[FileChunk]
    status: TransferStatus = TransferStatus.PENDING
    created_at: float = time.time()
    completed_at: Optional[float] = None

class StorageVirtualNode:
    def __init__(
        self,
        node_id: str,
        cpu_capacity: int,  # in vCPUs
        memory_capacity: int,  # in GB
        storage_capacity: int,  # in GB
        bandwidth: int,  # in Mbps
        ip_address: str = None,
        mac_address: str = None
    ):
        self.node_id = node_id
        self.cpu_capacity = cpu_capacity
        self.memory_capacity = memory_capacity
        self.total_storage = storage_capacity * 1024 * 1024 * 1024  # Convert GB to bytes
        self.bandwidth = bandwidth * 1000000  # Convert Mbps to bits per second
        
        # Network identity
        self.network_info = NetworkInfo(
            ip_address=ip_address or "0.0.0.0",
            mac_address=mac_address or "00:00:00:00:00:00",
            cloud_server="",
            joined_at=time.time()
        )
        
        # Current utilization
        self.used_storage = 0
        self.active_transfers: Dict[str, FileTransfer] = {}
        self.stored_files: Dict[str, FileTransfer] = {}
        self.network_utilization = 0  # Current bandwidth usage
        
        # Performance metrics
        self.total_requests_processed = 0
        self.total_data_transferred = 0  # in bytes
        self.failed_transfers = 0
        
        # Network connections and discovery
        self.connections: Dict[str, int] = {}  # node_id: bandwidth_available
        self.node_discovery: Dict[str, Dict] = {}  # Known nodes in network
        
        print(f"🖥️  Node {self.node_id} initialized")
        if ip_address and mac_address:
            print(f"   🌐 IP: {ip_address}, MAC: {mac_address}")

    def update_network_info(self, ip_address: str, mac_address: str, cloud_server: str):
        """Update node's network identity"""
        self.network_info.ip_address = ip_address
        self.network_info.mac_address = mac_address
        self.network_info.cloud_server = cloud_server
        self.network_info.joined_at = time.time()
        
        print(f"🔗 Node {self.node_id} network configured:")
        print(f"   📍 IP: {ip_address}")
        print(f"   🏷️  MAC: {mac_address}")
        print(f"   ☁️  Cloud: {cloud_server}")

    def add_discovered_node(self, node_id: str, node_info: Dict):
        """Add/update discovered node information"""
        self.node_discovery[node_id] = node_info
        print(f"📡 Node {self.node_id} discovered: {node_id} at {node_info.get('ip_address', 'unknown')}")

    def get_network_identity(self) -> Dict[str, str]:
        """Get node's network identity"""
        return {
            'node_id': self.node_id,
            'ip_address': self.network_info.ip_address,
            'mac_address': self.network_info.mac_address,
            'cloud_server': self.network_info.cloud_server,
            'joined_at': self.network_info.joined_at
        }

    def connect_to_node(self, other_node_id: str, bandwidth: int):
        """Connect to another node"""
        self.connections[other_node_id] = bandwidth
        print(f"🔗 Node {self.node_id} connected to {other_node_id} ({bandwidth} Mbps)")

    def disconnect_from_node(self, other_node_id: str):
        """Disconnect from another node"""
        if other_node_id in self.connections:
            del self.connections[other_node_id]
            print(f"🔌 Node {self.node_id} disconnected from {other_node_id}")

    def get_available_storage(self) -> int:
        """Get available storage in bytes"""
        return self.total_storage - self.used_storage

    def get_storage_utilization(self) -> Dict[str, float]:
        """Get storage utilization statistics"""
        utilization_percent = (self.used_storage / self.total_storage * 100) if self.total_storage > 0 else 0
        return {
            'used_bytes': self.used_storage,
            'total_bytes': self.total_storage,
            'available_bytes': self.get_available_storage(),
            'utilization_percent': utilization_percent
        }

    def can_store_file(self, file_size: int) -> bool:
        """Check if node has enough storage for a file"""
        return self.get_available_storage() >= file_size

    def initiate_file_transfer(self, target_node_id: str, file_name: str, file_size: int) -> Optional[FileTransfer]:
        """Initiate a file transfer to another node"""
        if target_node_id not in self.connections:
            print(f"❌ Cannot transfer: Not connected to {target_node_id}")
            return None

        # Create file transfer object
        file_id = str(uuid.uuid4())[:8]
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = math.ceil(file_size / chunk_size)
        
        chunks = []
        for i in range(num_chunks):
            chunk_size_actual = min(chunk_size, file_size - i * chunk_size)
            chunk_checksum = hashlib.md5(f"{file_id}_{i}_{time.time()}".encode()).hexdigest()
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
        
        self.active_transfers[file_id] = transfer
        self.total_requests_processed += 1
        
        print(f"📤 Node {self.node_id} initiated transfer: {file_id}")
        print(f"   File: {file_name} ({file_size} bytes)")
        print(f"   Target: {target_node_id}")
        print(f"   Chunks: {num_chunks}")
        
        return transfer

    def receive_file_transfer(self, file_id: str, file_name: str, file_size: int) -> bool:
        """Prepare to receive a file transfer"""
        if not self.can_store_file(file_size):
            print(f"❌ Node {self.node_id} insufficient storage for {file_name}")
            return False
        
        # Create a placeholder transfer for receiving
        transfer = FileTransfer(
            file_id=file_id,
            file_name=file_name,
            total_size=file_size,
            chunks=[],
            status=TransferStatus.PENDING
        )
        
        self.active_transfers[file_id] = transfer
        print(f"📥 Node {self.node_id} ready to receive: {file_id} ({file_name})")
        return True

    def process_chunk_transfer(self, file_id: str, chunk_data: Dict) -> bool:
        """Process an incoming chunk transfer"""
        if file_id not in self.active_transfers:
            print(f"❌ Unknown file transfer: {file_id}")
            return False
        
        transfer = self.active_transfers[file_id]
        chunk_id = chunk_data['chunk_id']
        chunk_size = chunk_data['size']
        checksum = chunk_data['checksum']
        
        # Verify we have space for this chunk
        if not self.can_store_file(chunk_size):
            print(f"❌ Insufficient storage for chunk {chunk_id} of {file_id}")
            return False
        
        # Create or update chunk
        chunk = FileChunk(
            chunk_id=chunk_id,
            size=chunk_size,
            checksum=checksum,
            status=TransferStatus.COMPLETED,
            stored_node=self.node_id
        )
        
        # Add to transfer or update existing
        if len(transfer.chunks) <= chunk_id:
            transfer.chunks.append(chunk)
        else:
            transfer.chunks[chunk_id] = chunk
        
        # Update storage usage
        self.used_storage += chunk_size
        self.total_data_transferred += chunk_size
        
        print(f"📦 Node {self.node_id} received chunk {chunk_id} of {file_id}")
        return True

    def complete_file_transfer(self, file_id: str) -> bool:
        """Mark a file transfer as completed"""
        if file_id not in self.active_transfers:
            return False
        
        transfer = self.active_transfers[file_id]
        transfer.status = TransferStatus.COMPLETED
        transfer.completed_at = time.time()
        
        # Move to stored files
        self.stored_files[file_id] = transfer
        del self.active_transfers[file_id]
        
        # Verify all chunks are present and correct
        total_size = sum(chunk.size for chunk in transfer.chunks)
        if total_size == transfer.total_size:
            print(f"✅ Node {self.node_id} completed transfer: {file_id}")
            return True
        else:
            print(f"⚠️  Node {self.node_id} completed transfer with size mismatch: {file_id}")
            transfer.status = TransferStatus.FAILED
            self.failed_transfers += 1
            return False

    def fail_file_transfer(self, file_id: str):
        """Mark a file transfer as failed"""
        if file_id in self.active_transfers:
            self.active_transfers[file_id].status = TransferStatus.FAILED
            self.failed_transfers += 1
            print(f"❌ Node {self.node_id} failed transfer: {file_id}")

    def get_transfer_status(self, file_id: str) -> Optional[Dict]:
        """Get status of a file transfer"""
        if file_id in self.active_transfers:
            transfer = self.active_transfers[file_id]
        elif file_id in self.stored_files:
            transfer = self.stored_files[file_id]
        else:
            return None
        
        completed_chunks = sum(1 for chunk in transfer.chunks if chunk.status == TransferStatus.COMPLETED)
        total_chunks = len(transfer.chunks)
        progress = (completed_chunks / total_chunks * 100) if total_chunks > 0 else 0
        
        return {
            'file_id': file_id,
            'file_name': transfer.file_name,
            'status': transfer.status.name,
            'progress_percent': progress,
            'completed_chunks': completed_chunks,
            'total_chunks': total_chunks,
            'total_size': transfer.total_size,
            'transferred_size': sum(chunk.size for chunk in transfer.chunks if chunk.status == TransferStatus.COMPLETED)
        }

    def get_active_transfers(self) -> List[Dict]:
        """Get list of active transfers"""
        return [self.get_transfer_status(file_id) for file_id in self.active_transfers.keys()]

    def get_stored_files(self) -> List[Dict]:
        """Get list of stored files"""
        files = []
        for file_id, transfer in self.stored_files.items():
            files.append({
                'file_id': file_id,
                'file_name': transfer.file_name,
                'size': transfer.total_size,
                'stored_at': transfer.completed_at,
                'chunks': len(transfer.chunks)
            })
        return files

    def delete_file(self, file_id: str) -> bool:
        """Delete a stored file"""
        if file_id in self.stored_files:
            file_size = self.stored_files[file_id].total_size
            del self.stored_files[file_id]
            self.used_storage = max(0, self.used_storage - file_size)
            print(f"🗑️  Node {self.node_id} deleted file: {file_id}")
            return True
        return False

    def get_performance_metrics(self) -> Dict:
        """Get node performance metrics"""
        storage_util = self.get_storage_utilization()
        
        return {
            'node_id': self.node_id,
            'cpu_capacity': self.cpu_capacity,
            'memory_capacity': self.memory_capacity,
            'storage_utilization': storage_util,
            'network_utilization': self.network_utilization,
            'total_requests_processed': self.total_requests_processed,
            'total_data_transferred': self.total_data_transferred,
            'failed_transfers': self.failed_transfers,
            'active_transfers_count': len(self.active_transfers),
            'stored_files_count': len(self.stored_files),
            'connected_nodes_count': len(self.connections),
            'discovered_nodes_count': len(self.node_discovery)
        }

    def get_network_info(self) -> Dict:
        """Get comprehensive network information"""
        connected_nodes = []
        for node_id, bandwidth in self.connections.items():
            node_info = self.node_discovery.get(node_id, {})
            connected_nodes.append({
                'node_id': node_id,
                'ip_address': node_info.get('ip_address', 'unknown'),
                'bandwidth': bandwidth,
                'status': node_info.get('status', 'unknown')
            })
        
        discovered_nodes = []
        for node_id, info in self.node_discovery.items():
            if node_id != self.node_id:  # Don't include self
                discovered_nodes.append({
                    'node_id': node_id,
                    'ip_address': info.get('ip_address', 'unknown'),
                    'mac_address': info.get('mac_address', 'unknown'),
                    'status': info.get('status', 'unknown'),
                    'joined_at': info.get('joined_at', 0)
                })
        
        return {
            'node_identity': self.get_network_identity(),
            'connected_nodes': connected_nodes,
            'discovered_nodes': discovered_nodes,
            'total_connections': len(self.connections),
            'total_discovered': len(discovered_nodes)
        }

    def calculate_transfer_time(self, file_size: int, target_node_id: str) -> float:
        """Calculate estimated transfer time for a file"""
        if target_node_id not in self.connections:
            return float('inf')
        
        available_bandwidth = self.connections[target_node_id] * 1000000  # Convert to bits
        # Account for network utilization (use 80% of available bandwidth)
        effective_bandwidth = available_bandwidth * 0.8
        file_size_bits = file_size * 8  # Convert bytes to bits
        
        if effective_bandwidth <= 0:
            return float('inf')
        
        transfer_time_seconds = file_size_bits / effective_bandwidth
        return transfer_time_seconds

    def health_check(self) -> Dict:
        """Perform node health check"""
        storage_health = self.get_available_storage() > 0
        network_health = len(self.connections) > 0 or len(self.node_discovery) > 0
        
        return {
            'node_id': self.node_id,
            'status': 'healthy' if storage_health and network_health else 'degraded',
            'storage_health': 'healthy' if storage_health else 'full',
            'network_health': 'healthy' if network_health else 'isolated',
            'timestamp': time.time(),
            'uptime': time.time() - self.network_info.joined_at
        }

    def reset_metrics(self):
        """Reset performance metrics"""
        self.total_requests_processed = 0
        self.total_data_transferred = 0
        self.failed_transfers = 0
        self.network_utilization = 0
        print(f"📊 Node {self.node_id} metrics reset")

    def __str__(self):
        """String representation of the node"""
        storage_util = self.get_storage_utilization()
        return (f"StorageVirtualNode(node_id={self.node_id}, "
                f"ip={self.network_info.ip_address}, "
                f"storage={storage_util['utilization_percent']:.1f}% used, "
                f"connections={len(self.connections)})")

    def __repr__(self):
        return self.__str__()