import socket
import threading
import time

MAGIC_COOKIE = b'\xAB\xCD\xDC\xBA'
OFFER_TYPE = b'\x02'
REQUEST_TYPE = b'\x03'
PAYLOAD_TYPE = b'\x04'


def get_client_parameters():
    # Ask the user for file size, the number of TCP connections, and the number of UDP connections
    try:
        file_size = int(input("Enter the file size in bytes: "))
        tcp_connections = int(input("Enter the number of TCP connections: "))
        udp_connections = int(input("Enter the number of UDP connections: "))

        # Validate that all inputs are positive integers
        if file_size <= 0 or tcp_connections <= 0 or udp_connections <= 0:
            raise ValueError("All inputs must be positive integers.")

        return file_size, tcp_connections, udp_connections
    except ValueError as err:
        # Handle invalid inputs and prompt the user again
        print(f"Invalid input: {err}")
        return get_client_parameters()


def listen_for_offer():
    # Create a UDP socket to listen for server offers
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('0.0.0.0', 12345))  # Listen on port 12345 for UDP offers

        while True:
            # Receive data from the server
            data, addr = udp_socket.recvfrom(1024)

            # Check if the received data matches the expected offer format
            if data[:4] == MAGIC_COOKIE and data[4:5] == OFFER_TYPE:
                server_udp_port = int.from_bytes(data[5:7], 'big')
                server_tcp_port = int.from_bytes(data[7:9], 'big')
                print(f"Received offer from {addr[0]}")
                print(f"Server UDP port: {server_udp_port}, Server TCP port: {server_tcp_port}")
                return addr[0], server_udp_port, server_tcp_port  # Return the server's IP, UDP and TCP ports

    except socket.error as e:
        # Handle socket-related errors
        print(f"Socket error while listening for offers: {e}")
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Error while listening for offers: {e}")
    finally:
        udp_socket.close()


def send_tcp_request(server_ip, server_tcp_port, file_size):
    # Create a TCP socket to send the request
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the server
        tcp_socket.connect((server_ip, server_tcp_port))

        # Create the request message
        request_message = MAGIC_COOKIE + REQUEST_TYPE + file_size.to_bytes(8, 'big')

        # Log the start time
        start_time = time.time()

        # Send the request
        tcp_socket.send(request_message)
        print(f"Sent TCP request for {file_size} bytes to {server_ip}:{server_tcp_port}")

        # Receive the response (payload)
        data = tcp_socket.recv(1024 + file_size)  # Expecting the payload and the file data

        # Measure transfer time
        transfer_time = time.time() - start_time
        transfer_speed = (file_size * 8) / transfer_time  # bits per second

        # Validate the magic cookie and message type in the server's response
        if data[:4] == MAGIC_COOKIE and data[4:5] == PAYLOAD_TYPE:
            print(
                f"TCP transfer finished, total time: {transfer_time:.2f} seconds, total speed: {transfer_speed:.2f} bits/second")
        else:
            print("Error: Invalid response from server")
    except Exception as err:
        # Handle any exceptions during the TCP request
        print(f"Error during TCP request: {err}")
    finally:
        tcp_socket.close()  # Ensure the socket is closed


def send_udp_request(server_ip, server_udp_port, file_size):
    # Create a UDP socket to send the request
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Create the request message
        request_message = MAGIC_COOKIE + REQUEST_TYPE + file_size.to_bytes(8, 'big')

        # Log the start time
        start_time = time.time()

        # Send the request
        udp_socket.sendto(request_message, (server_ip, server_udp_port))
        print(f"Sent UDP request for {file_size} bytes to {server_ip}:{server_udp_port}")

        # Log the elapsed time for the request
        elapsed_time = time.time() - start_time
        print(f"UDP Request sent, time taken: {elapsed_time:.2f} seconds")
    except Exception as err:
        # Handle any exceptions during the UDP request
        print(f"Error during UDP request: {err}")
    finally:
        udp_socket.close()  # Ensure the socket is closed


def start_client():
    try:
        print("Client started, listening for offer requests...")

        # Get user inputs for file size, TCP connections, and UDP connections
        file_size, tcp_connections, udp_connections = get_client_parameters()

        # Listen for offer and get the server's IP address, UDP, and TCP ports
        server_ip, server_udp_port, server_tcp_port = listen_for_offer()

        # Start the requested number of TCP and UDP request threads
        tcp_threads = [
            threading.Thread(target=send_tcp_request, args=(server_ip, server_tcp_port, file_size))
            for _ in range(tcp_connections)
        ]
        udp_threads = [
            threading.Thread(target=send_udp_request, args=(server_ip, server_udp_port, file_size))
            for _ in range(udp_connections)
        ]

        # Start all threads
        for thread in tcp_threads + udp_threads:
            thread.start()

        # Wait for all threads to finish
        for thread in tcp_threads + udp_threads:
            thread.join()

    except KeyboardInterrupt:
        # Handle manual interruption
        print("\nClient stopped manually.")
    except Exception as err:
        # Handle unexpected exceptions
        print(f"Error in client execution: {err}")


if __name__ == "__main__":
    try:
        start_client()
    except KeyboardInterrupt:
        # Handle manual interruption
        print("\nClient stopped manually.")
    except Exception as e:
        # Handle unexpected exceptions
        print(f"Unexpected error: {e}")
