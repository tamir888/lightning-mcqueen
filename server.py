import socket
import threading
import time
import os
from colorama import init, Fore

# Server configuration
SERVER_IP = '0.0.0.0'  # Listen on all available interfaces
UDP_PORT = 12348
OFFER_PORT = 12347
TCP_PORT = 54321
MAGIC_COOKIE = b'\xAB\xCD\xDC\xBA'
OFFER_TYPE = b'\x02'
REQUEST_TYPE = b'\x03'
PAYLOAD_TYPE = b'\x04'

# Initialize colorama
init(autoreset=True)

def send_offer():
    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        while True:
            offer_message = MAGIC_COOKIE + OFFER_TYPE + UDP_PORT.to_bytes(2, 'big') + TCP_PORT.to_bytes(2, 'big')
            udp_socket.sendto(offer_message, ('<broadcast>', OFFER_PORT))  # Broadcast to all clients on the network
            time.sleep(1)  # Send offer every second
    except socket.error as e:
        print(f"{Fore.RED}Socket error in send_offer: {e}")
    finally:
        udp_socket.close()


def handle_tcp_request(client_socket, client_address):
    try:
        data = client_socket.recv(1024)

        if data[:4] == MAGIC_COOKIE and data[4:5] == REQUEST_TYPE:
            file_size = int.from_bytes(data[5:13], 'big')
            print(f"{Fore.YELLOW}Received request for {file_size} bytes from {client_address}")

            # Simulate a file (for now, a simple byte array or file)
            file_data = os.urandom(file_size)  # Generate random data as the file content

            # Create the response payload
            response = MAGIC_COOKIE + PAYLOAD_TYPE + file_data

            client_socket.sendall(response)
    except Exception as err:
        print(f"{Fore.RED}Error handling request from {client_address}: {err}")
    finally:
        # Close the connection
        client_socket.close()


def handle_udp_request(data, client_address, udp_socket):
    # Step 1: Validate the request
    if data[:4] != MAGIC_COOKIE or data[4:5] != REQUEST_TYPE:
        print(f"Invalid request from {client_address}")
        return

    file_size = int.from_bytes(data[5:13], 'big')  # Extract the file size from the request
    print(f"Received UDP request for {file_size} bytes from {client_address}")

    # Step 2: Prepare the data to send (simulate with random data for now)
    file_data = os.urandom(file_size)  # Simulating the file with random data

    # Step 3: Divide the data into segments and send them
    segment_size = 1024  # 1KB per packet, adjust as needed
    total_segments = (file_size + segment_size - 1) // segment_size  # Calculate number of segments
    print(f"Dividing the file into {total_segments} segments")

    for segment_num in range(total_segments):
        start = segment_num * segment_size
        end = min(start + segment_size, file_size)
        segment_data = file_data[start:end]

        # Construct the payload message with sequence number
        payload = MAGIC_COOKIE + PAYLOAD_TYPE
        payload += total_segments.to_bytes(8, 'big')  # Total segment count
        payload += (segment_num + 1).to_bytes(8, 'big')  # Current segment count
        payload += segment_data  # Actual data

        # Send the segment
        udp_socket.sendto(payload, client_address)

    # Indicate that the transfer is complete by closing the connection
    print(f"Completed UDP transfer to {client_address}")


def start_server():
    # Start the offer sending thread
    offer_thread = threading.Thread(target=send_offer)
    offer_thread.daemon = True
    offer_thread.start()

    # Set up the TCP server
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind((SERVER_IP, TCP_PORT))
    tcp_socket.listen(5)  # Max number of connections

    # Set up the UDP server
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((SERVER_IP, UDP_PORT))

    print(f"{Fore.CYAN}Server started, listening on IP {SERVER_IP} for TCP on port {TCP_PORT} and UDP on port {UDP_PORT}")

    def tcp_handler():
        try:
            while True:
                client_socket, client_address = tcp_socket.accept()
                print(f"{Fore.CYAN}TCP connection established with {client_address}")
                # Handle each request in a new thread
                request_thread = threading.Thread(target=handle_tcp_request, args=(client_socket, client_address))
                request_thread.daemon = True
                request_thread.start()
        except Exception as err:
            print(f"{Fore.RED}Unexpected error in TCP handler: {err}")

    def udp_handler():
        try:
            while True:
                data, client_address = udp_socket.recvfrom(4096)  # Adjust buffer size as needed
                print(f"{Fore.CYAN}UDP message received from {client_address}")
                handle_udp_request(data, client_address, udp_socket)
        except Exception as err:
            print(f"{Fore.RED}Unexpected error in UDP handler: {err}")

    # Start TCP and UDP handler threads
    tcp_thread = threading.Thread(target=tcp_handler)
    tcp_thread.daemon = True
    tcp_thread.start()

    udp_thread = threading.Thread(target=udp_handler)
    udp_thread.daemon = True
    udp_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}Shutting down server...")
    finally:
        tcp_socket.close()
        udp_socket.close()


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print(f"{Fore.BLUE}\nServer stopped manually.")
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}")
