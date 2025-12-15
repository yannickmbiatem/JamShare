from typing import Dict, List, Optional, Tuple
import hashlib
import time
import uuid
import json
from storage_virtual_node import StorageVirtualNode, FileTransfer, TransferStatus, FileChunk
from collections import defaultdict
import os

class StorageVirtualNetwork:
    def __init__(self):
        self.nodes: Dict[str, StorageVirtualNode] = {}
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        self.node_discovery_table: Dict[str, Dict] = {}  # Network-wide node registry
        self.connections: Dict[Tuple[str, str], int] = {}  # (node1, node2): bandwidth
        self.file_content_storage: Dict[str, bytes] = {}  # Store file content for transfers
        self.network_log: List[Dict] = []  # Network event log
        self.max_retries = 3
        
    def log_event(self, event_type: str, message: str, node_id: str = None, data: Dict = None):
        """Log network events"""
        log_entry = {
            'timestamp': time.time(),
            'type': event_type,
            'message': message,
            'node_id': node_id,
            'data': data or {}
        }
        self.network_log.append(log_entry)
        
        # Keep only last 1000 events
        if len(self.network_log) > 1000:
            self.network_log = self.network_log[-1000:]
        
        print(f"📝 [{event_type}] {message}" + (f" (Node: {node_id})" if node_id else ""))

    def create_node(self, node_id: str, cpu_capacity=4, memory_capacity=16, 
                   storage_capacity=500, bandwidth=1000, ip_address=None, mac_address=None):
        """Create a new node in the network with network identity"""
        if node_id in self.nodes:
            self.log_event('WARNING', f'Node {node_id} already exists', node_id)
            return False
            
        try:
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
            
            self.log_event('NODE_CREATED', f'Node {node_id} created successfully', node_id, {
                'ip': ip_address,
                'mac': mac_address,
                'storage_gb': storage_capacity
            })
            
            return True
            
        except Exception as e:
            self.log_event('ERROR', f'Failed to create node {node_id}: {str(e)}', node_id)
            return False
    
    def _update_node_discovery(self):
        """Update all nodes with current network discovery table"""
        for node_id, node in self.nodes.items():
            try:
                for discovered_id, discovered_info in self.node_discovery_table.items():
                    if discovered_id != node_id:  # Don't add self to discovery
                        node.add_discovered_node(discovered_id, discovered_info)
            except Exception as e:
                self.log_event('ERROR', f'Failed to update discovery for node {node_id}: {str(e)}', node_id)
    
    def add_node(self, node: StorageVirtualNode):
        """Add an existing node to the network"""
        try:
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
            self.log_event('NODE_ADDED', f'Node {node.node_id} added to network', node.node_id)
            return True
            
        except Exception as e:
            self.log_event('ERROR', f'Failed to add node {node.node_id}: {str(e)}', node.node_id)
            return False
    
    def remove_node(self, node_id: str):
        """Remove a node from the network"""
        try:
            if node_id in self.nodes:
                del self.nodes[node_id]
                if node_id in self.node_discovery_table:
                    self.node_discovery_table[node_id]['status'] = 'offline'
                    self.node_discovery_table[node_id]['left_at'] = time.time()
                
                self._update_node_discovery()
                
                # Clean up connections involving this node
                connections_to_remove = []
                for (node1, node2) in list(self.connections.keys()):
                    if node1 == node_id or node2 == node_id:
                        connections_to_remove.append((node1, node2))
                
                for conn in connections_to_remove:
                    del self.connections[conn]
                
                self.log_event('NODE_REMOVED', f'Node {node_id} removed from network', node_id)
                return True
                
            self.log_event('WARNING', f'Node {node_id} not found for removal', node_id)
            return False
            
        except Exception as e:
            self.log_event('ERROR', f'Failed to remove node {node_id}: {str(e)}', node_id)
            return False
    
    def connect_nodes(self, node1_id: str, node2_id: str, bandwidth: int = 1000) -> bool:
        """Connect two nodes with specified bandwidth"""
        if node1_id not in self.nodes or node2_id not in self.nodes:
            self.log_event('ERROR', f'Cannot connect: One or both nodes not found')
            return False
            
        if node1_id == node2_id:
            self.log_event('ERROR', f'Cannot connect node to itself: {node1_id}')
            return False
            
        try:
            # Validate bandwidth
            if bandwidth <= 0:
                self.log_event('ERROR', f'Invalid bandwidth: {bandwidth}')
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
            
            self.log_event('NODES_CONNECTED', f'Connected {node1_id} ↔ {node2_id} with {bandwidth} Mbps', 
                          None, {'node1': node1_id, 'node2': node2_id, 'bandwidth': bandwidth})
            return True
            
        except Exception as e:
            self.log_event('ERROR', f'Failed to connect nodes {node1_id} and {node2_id}: {str(e)}')
            return False
    
    def initiate_file_transfer(self, source_node_id: str, target_node_id: str, 
                             file_name: str, file_size: int) -> Optional[FileTransfer]:
        """Initiate a file transfer between nodes with retry logic"""
        for attempt in range(self.max_retries):
            try:
                return self._initiate_file_transfer_attempt(source_node_id, target_node_id, file_name, file_size, attempt)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.log_event('ERROR', f'Transfer failed after {self.max_retries} attempts: {str(e)}', 
                                  source_node_id, {'target': target_node_id, 'file': file_name})
                    return None
                
                self.log_event('WARNING', f'Transfer attempt {attempt + 1} failed, retrying...', 
                              source_node_id, {'error': str(e)})
                time.sleep(1)  # Wait before retry
        
        return None

    def _initiate_file_transfer_attempt(self, source_node_id: str, target_node_id: str, 
                                      file_name: str, file_size: int, attempt: int) -> Optional[FileTransfer]:
        """Single attempt to initiate file transfer"""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            raise ValueError(f"Nodes not found: {source_node_id} or {target_node_id}")
            
        if (source_node_id, target_node_id) not in self.connections:
            raise ValueError(f"Nodes not connected: {source_node_id} and {target_node_id}")
        
        # Validate file size
        if file_size <= 0:
            raise ValueError(f"Invalid file size: {file_size}")
        
        # Check target storage availability
        target_node = self.nodes[target_node_id]
        if not target_node.can_store_file(file_size):
            raise ValueError(f"Target node {target_node_id} insufficient storage")
        
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
        
        # Notify target node
        target_node.receive_file_transfer(file_id, file_name, file_size)
        
        self.log_event('TRANSFER_INITIATED', f'Transfer {file_id} initiated: {file_name} ({file_size} bytes)', 
                      source_node_id, {
                          'target': target_node_id,
                          'file_id': file_id,
                          'file_name': file_name,
                          'file_size': file_size,
                          'chunks': num_chunks,
                          'attempt': attempt + 1
                      })
        
        return transfer

    def initiate_file_transfer_with_content(self, source_node_id: str, target_node_id: str, 
                                          file_name: str, file_size: int, file_content_hex: str) -> Optional[FileTransfer]:
        """Initiate a file transfer with actual file content"""
        try:
            # Convert hex string back to bytes
            file_content = bytes.fromhex(file_content_hex)
            
            # Validate content size matches declared size
            if len(file_content) != file_size:
                self.log_event('ERROR', f'File content size mismatch: declared {file_size}, actual {len(file_content)}', 
                              source_node_id)
                return None
            
            # Create transfer
            transfer = self.initiate_file_transfer(source_node_id, target_node_id, file_name, file_size)
            
            if transfer:
                # Store file content
                self.file_content_storage[transfer.file_id] = file_content
                self.log_event('TRANSFER_WITH_CONTENT', f'Stored file content for transfer {transfer.file_id}', 
                              source_node_id, {'file_id': transfer.file_id})
            
            return transfer
            
        except ValueError as e:
            self.log_event('ERROR', f'Invalid file content format: {str(e)}', source_node_id)
            return None
        except Exception as e:
            self.log_event('ERROR', f'Failed to initiate transfer with content: {str(e)}', source_node_id)
            return None
    
    def process_file_transfer(self, source_node_id: str, target_node_id: str, 
                            file_id: str, chunks_per_step: int = 3) -> Tuple[int, bool]:
        """Process file transfer in chunks with error handling"""
        try:
            return self._process_file_transfer_safe(source_node_id, target_node_id, file_id, chunks_per_step)
        except Exception as e:
            self.log_event('ERROR', f'Error processing transfer {file_id}: {str(e)}', source_node_id)
            return 0, False

    def _process_file_transfer_safe(self, source_node_id: str, target_node_id: str, 
                                  file_id: str, chunks_per_step: int) -> Tuple[int, bool]:
        """Safe processing of file transfer"""
        if source_node_id not in self.transfer_operations:
            return 0, False
            
        if file_id not in self.transfer_operations[source_node_id]:
            return 0, False
        
        transfer = self.transfer_operations[source_node_id][file_id]
        chunks_processed = 0
        
        # Process chunks
        for chunk in transfer.chunks:
            if chunk.status == TransferStatus.PENDING and chunks_processed < chunks_per_step:
                try:
                    # Simulate chunk transfer
                    chunk_data = {
                        'chunk_id': chunk.chunk_id,
                        'size': chunk.size,
                        'checksum': chunk.checksum
                    }
                    
                    # Process on target node
                    if target_node_id in self.nodes:
                        success = self.nodes[target_node_id].process_chunk_transfer(file_id, chunk_data)
                        if success:
                            chunk.status = TransferStatus.COMPLETED
                            chunk.stored_node = target_node_id
                            chunks_processed += 1
                            
                            self.log_event('CHUNK_TRANSFERRED', f'Chunk {chunk.chunk_id} transferred for {file_id}', 
                                          source_node_id, {
                                              'file_id': file_id,
                                              'chunk_id': chunk.chunk_id,
                                              'size': chunk.size
                                          })
                except Exception as e:
                    self.log_event('ERROR', f'Failed to process chunk {chunk.chunk_id}: {str(e)}', source_node_id)
                    continue
        
        # Check if transfer is complete
        all_completed = all(chunk.status == TransferStatus.COMPLETED for chunk in transfer.chunks)
        
        if all_completed:
            try:
                transfer.status = TransferStatus.COMPLETED
                transfer.completed_at = time.time()
                
                # Update target node storage
                if target_node_id in self.nodes:
                    self.nodes[target_node_id].used_storage += transfer.total_size
                    self.nodes[target_node_id].stored_files[file_id] = transfer
                    self.nodes[target_node_id].total_data_transferred += transfer.total_size
                    
                    # Store actual file on target node if content is available
                    if file_id in self.file_content_storage:
                        success = self._store_actual_file_on_node(target_node_id, transfer.file_name, 
                                                                self.file_content_storage[file_id], transfer.total_size)
                        if success:
                            # Clean up stored content
                            del self.file_content_storage[file_id]
                        else:
                            self.log_event('WARNING', f'Failed to store actual file for transfer {file_id}', target_node_id)
                
                # Update source node metrics
                if source_node_id in self.nodes:
                    self.nodes[source_node_id].total_data_transferred += transfer.total_size
                
                # Clean up transfer operation
                if file_id in self.transfer_operations[source_node_id]:
                    del self.transfer_operations[source_node_id][file_id]
                
                self.log_event('TRANSFER_COMPLETED', f'Transfer {file_id} completed successfully!', 
                              source_node_id, {
                                  'file_id': file_id,
                                  'file_name': transfer.file_name,
                                  'total_size': transfer.total_size,
                                  'duration': transfer.completed_at - transfer.created_at
                              })
                
            except Exception as e:
                self.log_event('ERROR', f'Failed to complete transfer {file_id}: {str(e)}', source_node_id)
                transfer.status = TransferStatus.FAILED
        
        return chunks_processed, all_completed

    def _store_actual_file_on_node(self, node_id: str, file_name: str, file_content: bytes, file_size: int):
        """Store actual file content on node's local storage"""
        try:
            # Create node storage directory
            storage_dir = f"node_storage/{node_id}"
            os.makedirs(storage_dir, exist_ok=True)
            
            # Write file content
            file_path = os.path.join(storage_dir, file_name)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            file_size_mb = file_size / (1024 * 1024)
            self.log_event('FILE_STORED', f'Stored actual file: {file_path} ({file_size_mb:.2f} MB)', node_id)
            return True
        except Exception as e:
            self.log_event('ERROR', f'Failed to store file on {node_id}: {str(e)}', node_id)
            return False
    
    def get_network_stats(self) -> Dict:
        """Get network statistics"""
        try:
            total_storage = sum(node.total_storage for node in self.nodes.values())
            used_storage = sum(node.used_storage for node in self.nodes.values())
            
            active_transfers = 0
            total_transfer_size = 0
            for node_transfers in self.transfer_operations.values():
                for transfer in node_transfers.values():
                    if transfer.status == TransferStatus.IN_PROGRESS:
                        active_transfers += 1
                        total_transfer_size += transfer.total_size
            
            # Calculate network health
            online_nodes = sum(1 for node_info in self.node_discovery_table.values() 
                              if node_info.get('status') == 'online')
            
            total_connections = len(self.connections) // 2  # Divide by 2 for bidirectional
            
            return {
                'total_nodes': len(self.nodes),
                'online_nodes': online_nodes,
                'total_connections': total_connections,
                'storage_utilization': (used_storage / total_storage * 100) if total_storage > 0 else 0,
                'active_transfers': active_transfers,
                'total_transfer_size': total_transfer_size,
                'total_data_transferred': sum(node.total_data_transferred for node in self.nodes.values()),
                'network_health': 'healthy' if online_nodes > 0 and total_connections > 0 else 'degraded',
                'event_log_count': len(self.network_log)
            }
        except Exception as e:
            self.log_event('ERROR', f'Failed to get network stats: {str(e)}')
            return {
                'total_nodes': 0,
                'online_nodes': 0,
                'total_connections': 0,
                'storage_utilization': 0,
                'active_transfers': 0,
                'total_transfer_size': 0,
                'total_data_transferred': 0,
                'network_health': 'error',
                'event_log_count': len(self.network_log)
            }
    
    def get_event_log(self, limit: int = 50) -> List[Dict]:
        """Get recent network events"""
        return self.network_log[-limit:] if self.network_log else []
    
    def save_network_state(self, filename: str = "network_state.json"):
        """Save network state to file"""
        try:
            state = {
                'nodes': {},
                'connections': list(self.connections.keys()),
                'node_discovery': self.node_discovery_table,
                'timestamp': time.time()
            }
            
            for node_id, node in self.nodes.items():
                state['nodes'][node_id] = {
                    'cpu': node.cpu_capacity,
                    'memory': node.memory_capacity,
                    'storage': node.total_storage,
                    'bandwidth': node.bandwidth,
                    'ip': node.network_info.ip_address,
                    'mac': node.network_info.mac_address
                }
            
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.log_event('STATE_SAVED', f'Network state saved to {filename}')
            return True
        except Exception as e:
            self.log_event('ERROR', f'Failed to save network state: {str(e)}')
            return False