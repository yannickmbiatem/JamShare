# 🌩️ Cloud Storage Network Simulation

## Overview

A **distributed cloud storage network** that simulates a virtual storage infrastructure where nodes can register, connect, and transfer files in a controlled network environment. This project demonstrates core distributed system principles including **node discovery, network addressing, file transfer protocols, and resource management**.

---

## 🏗️ Architecture

The system consists of three main components:

### 1. **Cloud Server** (`cloud_server.py`)
- Central coordination server
- Manages node registration and network addressing
- Assigns unique IP/MAC addresses to joining nodes
- Handles file transfer coordination
- Maintains network discovery tables
- Manages IP address pool (192.168.1.100-254)

### 2. **Virtual Network** (`storage_virtual_network.py`)
- Manages node connections and topology
- Coordinates file transfers between nodes
- Tracks network statistics and utilization
- Handles node discovery and network updates
- Maintains bidirectional connections between nodes

### 3. **Virtual Nodes** (`storage_virtual_node.py`, `node_client.py`)
- Individual storage nodes with configurable resources (CPU, memory, storage, bandwidth)
- Handle file transfers in 1MB chunks
- Maintain local storage and network connections
- Provide performance metrics and health monitoring
- Support interactive command-line interface

---

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- No external dependencies required

### Running the System

1. **Start the Cloud Server:**
```bash
python cloud_server.py
```
```
🌩️ Cloud Server started on localhost:8889
📍 Server will automatically assign IP/MAC addresses to joining nodes
```

2. **Join Nodes to the Network:**
```bash
# In separate terminals
python node_client.py node1
python node_client.py node2
python node_client.py node3
```

3. **Use Interactive Commands:**
```
node_node1> connect node2
node_node1> transfer node2 large_file.zip 104857600  # 100MB file
node_node1> stats
node_node1> discovery
node_node1> quit
```

---

## 🔧 Core Features

### 🌐 Network Management
- **Automatic IP/MAC Address Assignment**: Server dynamically assigns network addresses from managed pool
- **Node Discovery**: Real-time discovery of network participants via central registry
- **Connection Management**: Establish bandwidth-limited bidirectional connections between nodes
- **Network Broadcasting**: Notifications when new nodes join the network

### 📁 File Transfer System
- **Chunk-based Transfers**: Files automatically split into 1MB chunks for efficient transfer
- **Progress Tracking**: Real-time transfer status and progress monitoring with completion percentages
- **Checksum Verification**: Data integrity validation through MD5 checksums for each chunk
- **Bandwidth Management**: Transfer scheduling based on available connection bandwidth
- **Transfer Resumption**: Support for partial transfers with chunk-level tracking

### 📊 Monitoring & Metrics
- **Storage Utilization**: Track used/available storage per node with percentage utilization
- **Network Statistics**: Bandwidth usage, active transfers, data volumes across entire network
- **Performance Metrics**: Transfer success rates, processing statistics, failed transfer tracking
- **Health Checks**: Comprehensive node status monitoring and availability tracking
- **Real-time Metrics**: Live updates on storage, network, and transfer metrics

### 💻 Interactive Interface
- **Command-line Interface**: Easy-to-use interactive node management console
- **Real-time Updates**: Live network discovery and status information
- **Transfer Control**: Initiate and monitor file transfers between connected nodes
- **Network Exploration**: Discover other nodes and view connection status

---

## 🎯 Use Cases

### 🔬 Distributed Systems Education
- **Network Simulation**: Study node communication patterns and network topologies
- **Resource Management**: Learn about storage and bandwidth allocation strategies
- **Fault Tolerance**: Experiment with node failures and recovery mechanisms
- **Protocol Design**: Understand chunk-based file transfer protocols

### 💾 Storage Infrastructure Testing
- **Protocol Development**: Test and develop file transfer algorithms
- **Load Testing**: Simulate multiple concurrent transfers and measure performance
- **Performance Analysis**: Measure network efficiency and identify bottlenecks
- **Scalability Testing**: Evaluate system behavior with increasing node count

### 🌐 Cloud Infrastructure Simulation
- **Network Addressing**: Study dynamic IP assignment and management
- **Node Discovery**: Implement and test discovery protocols
- **Resource Allocation**: Practice CPU, memory, and storage management
- **Monitoring Systems**: Build comprehensive metrics collection and reporting

---

## 📁 Project Structure

```
cloud-storage-simulation/
├── cloud_server.py          # Central cloud server (entry point)
├── node_client.py           # Node client implementation
├── storage_virtual_node.py  # Virtual node class definition
├── storage_virtual_network.py # Network management system
├── main.py                  # Example usage and demonstration
└── README.md               # Documentation
```

---

## 🔄 Core Processes

### Node Registration Process
1. **Connection**: Node client connects to cloud server on port 8889
2. **Registration**: Node sends registration request with capacity specifications
3. **Address Assignment**: Server assigns unique IP and MAC addresses
4. **Network Join**: Node added to network discovery table
5. **Notification**: Existing nodes notified of new participant via broadcast

### File Transfer Process
1. **Initiation**: Source node requests transfer to target node with file details
2. **Validation**: System checks connection status and target storage capacity
3. **Chunking**: File split into 1MB chunks with individual MD5 checksums
4. **Transfer**: Chunks transmitted sequentially with progress tracking
5. **Verification**: Each chunk validated using checksum on receipt
6. **Storage**: Chunks stored on target node with status tracking
7. **Completion**: File marked complete when all chunks successfully transferred

### Network Discovery Process
- Centralized discovery table maintained by cloud server
- Nodes receive automatic updates when new nodes join network
- Connection information shared for peer-to-peer transfers
- Health status tracking for all network participants

---

## 📈 Performance Metrics Tracked

### Node-level Metrics
- **Storage Utilization**: Used/total storage with percentage
- **Transfer Statistics**: Successful vs failed transfers count
- **Data Volume**: Total bytes transferred
- **Network Connections**: Active connection count and bandwidth
- **Uptime**: Node availability and health status

### Network-level Metrics
- **Total Nodes**: Number of active nodes in network
- **Active Transfers**: Concurrent file transfers in progress
- **Bandwidth Utilization**: Overall network capacity usage
- **Storage Distribution**: Aggregate storage across all nodes
- **Connection Topology**: Network connectivity graph

---

## 🛠️ Technical Implementation

### Key Classes

**StorageVirtualNode**: Represents individual storage nodes
- Manages local storage and transfers
- Tracks performance metrics
- Handles network connections

**StorageVirtualNetwork**: Manages network topology
- Coordinates inter-node communication
- Tracks network-wide statistics
- Manages node discovery

**CloudServer**: Central coordination
- Handles node registration
- Manages IP address allocation
- Coordinates network broadcasts

### Data Structures
- **FileChunk**: Individual file segments with checksums
- **FileTransfer**: Complete transfer operations with status tracking
- **NetworkInfo**: Node network identity and addressing
- **TransferStatus**: Enumeration of transfer states

---

## 💡 Example Usage

```python
# Create network and nodes
network = StorageVirtualNetwork()
node1 = StorageVirtualNode("node1", storage_capacity=500, bandwidth=1000)
node2 = StorageVirtualNode("node2", storage_capacity=1000, bandwidth=2000)

# Add to network and connect
network.add_node(node1)
network.add_node(node2)
network.connect_nodes("node1", "node2", bandwidth=1000)

# Transfer file
transfer = network.initiate_file_transfer(
    source_node_id="node1",
    target_node_id="node2", 
    file_name="data.zip",
    file_size=100 * 1024 * 1024  # 100MB
)

# Process transfer in chunks
chunks_done, completed = network.process_file_transfer(
    source_node_id="node1",
    target_node_id="node2",
    file_id=transfer.file_id,
    chunks_per_step=3
)
```

---

## 🐛 Troubleshooting

### Common Issues

**Connection Refused:**
- Ensure cloud server is running before starting nodes
- Verify port 8889 is available and not blocked
- Check firewall settings for local connections

**Transfer Failures:**
- Confirm nodes are connected before initiating transfers
- Verify adequate storage capacity on target node
- Monitor available bandwidth for large transfers
- Check chunk checksum validation logs

**Node Discovery Issues:**
- Restart cloud server to refresh discovery table
- Ensure unique node IDs across the network
- Verify network broadcast functionality

**Resource Exhaustion:**
- Monitor IP address pool availability
- Track individual node storage utilization
- Manage concurrent transfer limits

---

## 🔮 Extension Possibilities

### Potential Enhancements
- **Multiple Transfer Protocols**: Add UDP, TCP variants
- **Security Features**: Encryption, authentication
- **Load Balancing**: Dynamic resource allocation
- **Fault Tolerance**: Node failure recovery mechanisms
- **Web Interface**: Graphical monitoring dashboard
- **API Endpoints**: RESTful interface for automation
- **Containerization**: Docker support for easy deployment

---

## 📚 Learning Outcomes

This simulation demonstrates:

- **Distributed System Design**: Centralized coordination with decentralized execution
- **Network Protocols**: Custom implementation of node communication
- **Resource Management**: Dynamic allocation of storage and bandwidth
- **Fault Tolerance**: Handling node disconnections and transfer failures
- **Monitoring Systems**: Real-time performance tracking and metrics collection
- **Protocol Design**: Chunk-based file transfer with integrity verification

This project provides practical experience in building and managing distributed storage systems, making it ideal for educational purposes and infrastructure prototyping.
