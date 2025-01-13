import socket
import threading
import time
import os

# Server configuration
SERVER_IP = '0.0.0.0'  # Listen on all available interfaces
UDP_PORT = 12345
TCP_PORT = 54321
MAGIC_COOKIE = b'\xAB\xCD\xDC\xBA'
OFFER_TYPE = b'\x02'
REQUEST_TYPE = b'\x03'
PAYLOAD_TYPE = b'\x04'


def send_offer():
    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        while True:
            offer_message = MAGIC_COOKIE + OFFER_TYPE + UDP_PORT.to_bytes(2, 'big') + TCP_PORT.to_bytes(2, 'big')
            udp_socket.sendto(offer_message, ('<broadcast>', 12345))  # Broadcast to all clients on the network
            print(f"Offer sent: {offer_message.hex()}")
            time.sleep(1)  # Send offer every second
    except socket.error as e:
        print(f"Socket error in send_offer: {e}")
    finally:
        udp_socket.close()


def handle_request(client_socket, client_address):
    try:
        data = client_socket.recv(1024)

        if data[:4] == MAGIC_COOKIE and data[4:5] == REQUEST_TYPE:
            file_size = int.from_bytes(data[5:13], 'big')
            print(f"Received request for {file_size} bytes from {client_address}")

            # Simulate a file (for now, a simple byte array or file)
            # You can replace this with reading an actual file
            file_data = os.urandom(file_size)  # Generate random data as the file content

            # Create the response payload
            response = MAGIC_COOKIE + PAYLOAD_TYPE + file_data

            client_socket.sendall(response)
    except Exception as err:
        print(f"Error handling request from {client_address}: {err}")
    finally:
        # Close the connection
        client_socket.close()


def start_server():
    # Start the offer sending thread
    offer_thread = threading.Thread(target=send_offer)
    offer_thread.daemon = True
    offer_thread.start()

    # Set up the server to handle incoming requests
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        tcp_socket.bind((SERVER_IP, TCP_PORT))
        tcp_socket.listen(5)  # Max number of connections
        print(f"Server started, listening on IP {SERVER_IP}...")

        while True:
            client_socket, client_address = tcp_socket.accept()
            print(f"Connection established with {client_address}")
            # Handle each request in a new thread
            request_thread = threading.Thread(target=handle_request, args=(client_socket, client_address))
            request_thread.daemon = True
            request_thread.start()
    except socket.error as err:
        print(f"Socket error in start_server: {err}")
    except Exception as err:
        print(f"Unexpected error in start_server: {err}")
    finally:
        tcp_socket.close()


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer stopped manually.")
    except Exception as e:
        print(f"Unexpected error: {e}")
