import threading
import time
import json

class CloudServiceManager:
    """Manages cloud service lifecycle and termination"""
    
    def __init__(self, cloud_server):
        self.cloud_server = cloud_server
        self.service_status = 'running'
        self.termination_handlers = []
        
    def register_termination_handler(self, handler):
        """Register callback for graceful termination"""
        self.termination_handlers.append(handler)
    
    def terminate_service(self, node_id=None, reason="Administrative action"):
        """Terminate cloud service gracefully"""
        print(f"🛑 Initiating service termination... Reason: {reason}")
        
        # Notify all handlers
        for handler in self.termination_handlers:
            try:
                handler(node_id)
            except Exception as e:
                print(f"Warning: Termination handler failed: {e}")
        
        # Perform termination
        if node_id:
            # Specific node termination
            self.cloud_server.terminate_cloud_service(node_id)
            
            # Notify other nodes
            self.broadcast_service_termination(node_id, reason)
        else:
            # Full service termination
            self.service_status = 'terminating'
            self.broadcast_service_termination("all", reason)
            time.sleep(2)  # Give nodes time to react
            self.cloud_server.terminate_cloud_service()
            self.service_status = 'terminated'
    
    def broadcast_service_termination(self, target, reason):
        """Broadcast termination notice to nodes"""
        termination_notice = {
            'type': 'service_termination',
            'target': target,
            'reason': reason,
            'timestamp': time.time()
        }
        
        print(f"📢 Broadcasting termination notice: {target} - {reason}")
        
        # In a real implementation, send to all connected nodes
        if hasattr(self.cloud_server, 'authenticated_nodes'):
            for node_id, node_info in self.cloud_server.authenticated_nodes.items():
                if target == "all" or node_id == target:
                    try:
                        node_info['client_socket'].send(
                            json.dumps(termination_notice).encode('utf-8')
                        )
                    except:
                        pass  # Node might already be disconnected
    
    def get_service_status(self):
        """Get current service status"""
        return {
            'status': self.service_status,
            'active_nodes': len(getattr(self.cloud_server, 'authenticated_nodes', {})),
            'total_nodes': len(getattr(self.cloud_server, 'node_registry', {}))
        }

class GracefulTerminator:
    """Handles graceful termination of nodes"""
    
    @staticmethod
    def terminate_node_operations(node_id, cloud_network):
        """Gracefully terminate all operations for a node"""
        print(f"🔄 Gracefully terminating operations for node {node_id}")
        
        # Cancel ongoing transfers
        transfers_cancelled = GracefulTerminator.cancel_node_transfers(node_id, cloud_network)
        
        # Close connections
        connections_closed = GracefulTerminator.close_node_connections(node_id, cloud_network)
        
        # Cleanup resources
        GracefulTerminator.cleanup_node_resources(node_id, cloud_network)
        
        print(f"✅ Node {node_id} termination complete: "
              f"{transfers_cancelled} transfers cancelled, "
              f"{connections_closed} connections closed")
    
    @staticmethod
    def cancel_node_transfers(node_id, cloud_network):
        """Cancel all transfers involving the node"""
        cancelled = 0
        
        # Cancel transfers where node is source
        if node_id in cloud_network.transfer_operations:
            for file_id, transfer in list(cloud_network.transfer_operations[node_id].items()):
                transfer.status = 'cancelled'
                transfer.cancelled_at = time.time()
                cancelled += 1
        
        return cancelled
    
    @staticmethod
    def close_node_connections(node_id, cloud_network):
        """Close all connections for the node"""
        closed = 0
        
        # Remove connections from network
        connections_to_remove = []
        for (node1, node2) in list(cloud_network.connections.keys()):
            if node1 == node_id or node2 == node_id:
                connections_to_remove.append((node1, node2))
        
        for conn in connections_to_remove:
            del cloud_network.connections[conn]
            closed += 1
        
        # Remove from node's connection list
        if node_id in cloud_network.nodes:
            cloud_network.nodes[node_id].connections.clear()
        
        # Remove from other nodes' connection lists
        for other_node in cloud_network.nodes.values():
            if node_id in other_node.connections:
                del other_node.connections[node_id]
                closed += 1
        
        return closed
    
    @staticmethod
    def cleanup_node_resources(node_id, cloud_network):
        """Clean up node resources"""
        # Remove from discovery table
        if node_id in cloud_network.node_discovery_table:
            cloud_network.node_discovery_table[node_id]['status'] = 'terminated'
            cloud_network.node_discovery_table[node_id]['terminated_at'] = time.time()
        
        # Update network discovery
        cloud_network._update_node_discovery()