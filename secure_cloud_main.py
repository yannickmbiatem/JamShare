from cloud_server_auth import SecureCloudServer
from service_manager import CloudServiceManager, GracefulTerminator
import threading
import time
import signal
import sys

class SecureCloudStorageNetwork:
    """Main integrated secure cloud storage network"""
    
    def __init__(self, email_sender=None, email_password=None, enable_email=True):
        self.cloud_server = SecureCloudServer(
            email_sender=email_sender,
            email_password=email_password,
            enable_email=enable_email
        )
        self.service_manager = CloudServiceManager(self.cloud_server)
        self.setup_termination_handlers()
    
    def setup_termination_handlers(self):
        """Setup graceful termination handlers"""
        # Register termination handler for the cloud server
        self.service_manager.register_termination_handler(
            lambda node_id: GracefulTerminator.terminate_node_operations(
                node_id, self.cloud_server.network
            )
        )
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)
    
    def graceful_shutdown(self, signum, frame):
        """Handle graceful shutdown on signals"""
        print(f"\n🛑 Received shutdown signal {signum}")
        self.service_manager.terminate_service(
            reason=f"Signal {signum} received"
        )
        sys.exit(0)
    
    def start_network(self):
        """Start the secure cloud storage network"""
        print("🌩️🔐 Starting Secure Cloud Storage Network")
        print("=" * 50)
        print("Features:")
        print("  ✅ UTP Email Authentication")
        print("  ✅ Secure Node Enrollment")  
        print("  ✅ Service Termination Protocol")
        print("  ✅ Integrated with Storage Project")
        print("=" * 50)
        
        # Start the cloud server in a separate thread
        server_thread = threading.Thread(target=self.cloud_server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # Monitor service status
        try:
            while True:
                status = self.service_manager.get_service_status()
                print(f"📊 Service Status: {status['status']} | "
                      f"Active Nodes: {status['active_nodes']} | "
                      f"Total Nodes: {status['total_nodes']}")
                time.sleep(30)  # Report every 30 seconds
                
        except KeyboardInterrupt:
            self.graceful_shutdown(signal.SIGINT, None)

def main():
    """Main entry point for the secure cloud storage network"""
    # Configure these values for your email service
    EMAIL_SENDER = None      # Set to your email, e.g., "your_email@gmail.com"
    EMAIL_PASSWORD = None    # Set to your app password
    ENABLE_EMAIL = False     # Set to True if you configured email
    
    secure_network = SecureCloudStorageNetwork(
        email_sender=EMAIL_SENDER,
        email_password=EMAIL_PASSWORD,
        enable_email=ENABLE_EMAIL
    )
    secure_network.start_network()

if __name__ == "__main__":
    main()