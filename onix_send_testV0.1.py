import os
import socket
import time

# Socket configuration
ONIX_IP = '10.129.47.225'  # Replace with the receiver's IP
ONIX_PORT = 60000        # Replace with the receiver's port

# File to send
FILE_PATH = 'FM-1-2025-03-04-11-08-17-jsonALLConnections.json'  # Replace with the path to the file you want to send

def send_file(file_path, onix_ip, onix_port):
    """
    Sends a file over UDP to the specified IP and port.
    """
    chunk_size = 1024  # Chunk size for sending data
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(5)  # Set a timeout for socket operations

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    try:
        # Send the file name and size first
        udp_socket.sendto(f"{file_name}:{file_size}".encode(), (onix_ip, onix_port))
        print(f"Sent file info: {file_name} ({file_size} bytes)")

        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                udp_socket.sendto(chunk, (onix_ip, onix_port))
                #print(f"Sent chunk of size {len(chunk)} bytes")
        
        time.sleep(0.1)

        # Send an end-of-file marker
        udp_socket.sendto(b"EOF", (onix_ip, onix_port))
        print(f"File {file_name} sent successfully to {onix_ip}:{onix_port}")
    except socket.error as e:
        print(f"Socket error while sending file {file_name}: {str(e)}")
    finally:
        udp_socket.close()

if __name__ == "__main__":
    # Ensure the file exists
    if not os.path.exists(FILE_PATH):
        print(f"Error: File {FILE_PATH} does not exist.")
        exit(1)

    print(f"Starting UDP file sender...")
    print(f"Sending file: {FILE_PATH} to {ONIX_IP}:{ONIX_PORT}")

    # Send the file
    send_file(FILE_PATH, ONIX_IP, ONIX_PORT)

    print("File sending process completed.")