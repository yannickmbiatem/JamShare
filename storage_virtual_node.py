import time
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from enum import Enum, auto
import hashlib

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

    # ... rest of existing methods remain the same ...