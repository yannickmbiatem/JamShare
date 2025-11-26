from storage_virtual_network import StorageVirtualNetwork
from storage_virtual_node import StorageVirtualNode
import os
import time

def setup_local_storage():
    """Create storage directories for all nodes"""
    base_dir = "node_storage"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        print(f"📁 Created base storage directory: {base_dir}")
    
    for node_id in ["node1", "node2"]:
        node_dir = os.path.join(base_dir, node_id)
        if not os.path.exists(node_dir):
            os.makedirs(node_dir, exist_ok=True)
            print(f"📁 Created storage directory: {node_dir}")

def create_sample_files():
    """Create sample files for demonstration"""
    sample_files = [
        ("document.pdf", 5),   # 5MB
        ("image.jpg", 2),      # 2MB
        ("data.csv", 1),       # 1MB
        ("backup.zip", 10),    # 10MB
    ]
    
    for node_id in ["node1", "node2"]:
        node_dir = f"node_storage/{node_id}"
        for file_name, size_mb in sample_files:
            file_path = os.path.join(node_dir, file_name)
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(size_mb * 1024 * 1024))
                print(f"📄 Created sample file: {file_path} ({size_mb} MB)")

def display_storage_info(network):
    """Display storage information for all nodes"""
    print(f"\n💾 Storage Information:")
    for node_id, node in network.nodes.items():
        storage_info = node.get_storage_utilization()
        used_mb = storage_info['used_bytes'] / (1024 * 1024)
        total_mb = storage_info['total_bytes'] / (1024 * 1024)
        available_mb = storage_info['available_bytes'] / (1024 * 1024)
        
        print(f"   {node_id}:")
        print(f"     Used: {used_mb:.2f} MB")
        print(f"     Total: {total_mb:.2f} MB")
        print(f"     Available: {available_mb:.2f} MB")
        print(f"     Utilization: {storage_info['utilization_percent']:.2f}%")

def list_all_files():
    """List all files in node storage directories"""
    print(f"\n📁 All Files in Storage:")
    for node_id in ["node1", "node2"]:
        node_dir = f"node_storage/{node_id}"
        if os.path.exists(node_dir):
            files = os.listdir(node_dir)
            if files:
                print(f"   {node_id}:")
                for file_name in files:
                    file_path = os.path.join(node_dir, file_name)
                    file_size = os.path.getsize(file_path)
                    file_size_mb = file_size / (1024 * 1024)
                    print(f"     📄 {file_name} - {file_size_mb:.2f} MB")
            else:
                print(f"   {node_id}: No files")

def demonstrate_file_transfer(network, source_node, target_node, file_name, file_size_mb):
    """Demonstrate a file transfer between nodes"""
    print(f"\n🚀 Demonstrating file transfer: {source_node.node_id} → {target_node.node_id}")
    print(f"   File: {file_name} ({file_size_mb} MB)")
    
    transfer = network.initiate_file_transfer(
        source_node_id=source_node.node_id,
        target_node_id=target_node.node_id,
        file_name=file_name,
        file_size=file_size_mb * 1024 * 1024  # Convert to bytes
    )

    if transfer:
        print(f"📤 Transfer initiated: {transfer.file_id}")
        
        # Process transfer in chunks
        total_chunks_transferred = 0
        while True:
            chunks_done, completed = network.process_file_transfer(
                source_node_id=source_node.node_id,
                target_node_id=target_node.node_id,
                file_id=transfer.file_id,
                chunks_per_step=2  # Process 2 chunks at a time
            )
            
            total_chunks_transferred += chunks_done
            print(f"🔄 Transferred {chunks_done} chunks (total: {total_chunks_transferred}), completed: {completed}")
            
            if completed:
                print("✅ Transfer completed successfully!")
                break
                
            # Get network stats
            stats = network.get_network_stats()
            print(f"🌐 Network Stats - Nodes: {stats['total_nodes']}, Active Transfers: {stats['active_transfers']}")
            
            # Display current storage utilization
            target_storage = target_node.get_storage_utilization()
            used_mb = target_storage['used_bytes'] / (1024 * 1024)
            total_mb = target_storage['total_bytes'] / (1024 * 1024)
            print(f"💾 Target storage: {used_mb:.1f}/{total_mb:.1f} MB ({target_storage['utilization_percent']:.2f}%)")
            
            time.sleep(1)  # Simulate transfer delay
    else:
        print("❌ Failed to initiate transfer")

def main():
    """Main demonstration function"""
    print("🌩️ Cloud Storage Network Simulation")
    print("=" * 50)
    
    # Create network
    network = StorageVirtualNetwork()

    # Setup local storage
    setup_local_storage()
    create_sample_files()

    # Create nodes with custom storage sizes
    print("\n💾 Setting up nodes with custom storage...")
    node1_storage_mb = 100  # 100MB
    node2_storage_mb = 200  # 200MB

    node1 = StorageVirtualNode("node1", 
                              cpu_capacity=4, 
                              memory_capacity=16, 
                              storage_capacity=node1_storage_mb/1024,  # Convert to GB
                              bandwidth=1000)

    node2 = StorageVirtualNode("node2", 
                              cpu_capacity=8, 
                              memory_capacity=32, 
                              storage_capacity=node2_storage_mb/1024,  # Convert to GB
                              bandwidth=2000)

    # Add nodes to network
    network.add_node(node1)
    network.add_node(node2)

    # Connect nodes with 1Gbps link
    network.connect_nodes("node1", "node2", bandwidth=1000)

    print(f"\n✅ Nodes created:")
    print(f"   Node1: {node1_storage_mb} MB storage, 1000 Mbps bandwidth")
    print(f"   Node2: {node2_storage_mb} MB storage, 2000 Mbps bandwidth")

    # Display initial state
    display_storage_info(network)
    list_all_files()

    # Demonstrate multiple file transfers
    transfers = [
        ("document.pdf", 5),   # 5MB file
        ("image.jpg", 2),      # 2MB file
        ("data.csv", 1),       # 1MB file
    ]

    for file_name, file_size_mb in transfers:
        demonstrate_file_transfer(network, node1, node2, file_name, file_size_mb)
        
        # Show updated storage after each transfer
        display_storage_info(network)
        time.sleep(1)

    # Final network statistics
    print(f"\n📊 Final Network Statistics:")
    stats = network.get_network_stats()
    print(f"   Total Nodes: {stats['total_nodes']}")
    print(f"   Total Connections: {stats['total_connections']}")
    print(f"   Storage Utilization: {stats['storage_utilization']:.2f}%")
    print(f"   Total Data Transferred: {stats['total_data_transferred'] / (1024 * 1024):.2f} MB")

    # List files after transfers
    list_all_files()

    print(f"\n🎉 Demonstration completed!")
    print(f"💡 You can now run individual nodes with: python node_client.py node1 (or node2)")
    print(f"   and use the interactive mode for more control.")

if __name__ == "__main__":
    main()