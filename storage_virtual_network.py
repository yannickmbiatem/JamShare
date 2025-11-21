from typing import Dict, List, Optional, Tuple
import hashlib
import time
from storage_virtual_node import StorageVirtualNode, FileTransfer, TransferStatus
from collections import defaultdict

class StorageVirtualNetwork:
    def __init__(self):
        self.nodes: Dict[str, StorageVirtualNode] = {}
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        self.node_discovery_table: Dict[str, Dict] = {}  # Network-wide node registry
        
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
        
    # ... rest of existing methods ...