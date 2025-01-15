import socket
import threading
import time

# ANSI color codes
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"

MAGIC_COOKIE = b'\xAB\xCD\xDC\xBA'
OFFER_TYPE = b'\x02'
REQUEST_TYPE = b'\x03'
PAYLOAD_TYPE = b'\x04'
OFFER_PORT = 12347


def get_client_parameters():
    # Ask the user for file size, the number of TCP connections, and the number of UDP connections
    try:
        file_size = int(input(f"{CYAN}Enter the file size in bytes: {RESET}"))
        tcp_connections = int(input(f"{CYAN}Enter the number of TCP connections: {RESET}"))
        udp_connections = int(input(f"{CYAN}Enter the number of UDP connections: {RESET}"))

        # Validate that all inputs are positive integers
        if file_size <= 0 or tcp_connections <= 0 or udp_connections <= 0:
            raise ValueError("All inputs must be positive integers.")

        return file_size, tcp_connections, udp_connections
    except ValueError as err:
        # Handle invalid inputs and prompt the user again
        print(f"{RED}Invalid input: {err}{RESET}")
        return get_client_parameters()


def listen_for_offer():
    # Create a UDP socket to listen for server offers
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('0.0.0.0', OFFER_PORT))  # Listen for UDP offers
        print(f"{GREEN}Listening for server offers on port {OFFER_PORT}...{RESET}")

        while True:
            # Receive data from the server
            data, addr = udp_socket.recvfrom(1024)

            # Check if the received data matches the expected offer format
            if data[:4] == MAGIC_COOKIE and data[4:5] == OFFER_TYPE:
                server_udp_port = int.from_bytes(data[5:7], 'big')
                server_tcp_port = int.from_bytes(data[7:9], 'big')
                print(f"{BLUE}Received offer from {addr[0]}{RESET}")
                print(f"{YELLOW}Server UDP port: {server_udp_port}, Server TCP port: {server_tcp_port}{RESET}")
                return addr[0], server_udp_port, server_tcp_port  # Return the server's IP, UDP and TCP ports

    except socket.error as e:
        # Handle socket-related errors
        print(f"{RED}Socket error while listening for offers: {e}{RESET}")
    except Exception as e:
        # Handle any other unexpected errors
        print(f"{RED}Error while listening for offers: {e}{RESET}")
    finally:
        udp_socket.close()


def send_tcp_request(server_ip, server_tcp_port, file_size):
    # Create a TCP socket to send the request
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the server
        tcp_socket.connect((server_ip, server_tcp_port))

        # Create the request message
        request_message = MAGIC_COOKIE + REQUEST_TYPE + file_size.to_bytes(8, 'big') + b"/n"

        # Log the start time
        start_time = time.time()

        # Send the request
        tcp_socket.send(request_message)
        print(f"{CYAN}Sent TCP request for {file_size} bytes to {server_ip}:{server_tcp_port}{RESET}")

        # Receive the response (payload)
        data = tcp_socket.recv(1024 + file_size)  # Expecting the payload and the file data

        # Measure transfer time
        transfer_time = time.time() - start_time
        transfer_speed = (file_size * 8) / transfer_time  # bits per second

        # Validate the magic cookie and message type in the server's response
        if data[:4] == MAGIC_COOKIE and data[4:5] == PAYLOAD_TYPE:
            print(f"{GREEN}TCP transfer finished, total time: {transfer_time:.2f} seconds, "
                  f"total speed: {transfer_speed:.2f} bits/second{RESET}")
        else:
            print(f"{RED}Error: Invalid response from server{RESET}")
    except Exception as err:
        # Handle any exceptions during the TCP request
        print(f"{RED}Error during TCP request: {err}{RESET}")
    finally:
        tcp_socket.close()  # Ensure the socket is closed


def send_udp_request(server_ip, server_udp_port, file_size):
    # Create a UDP socket to send the request
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Step 1: Send the request
        request_message = MAGIC_COOKIE + REQUEST_TYPE + file_size.to_bytes(8, 'big')
        udp_socket.sendto(request_message, (server_ip, server_udp_port))
        print(f"{CYAN}Sent UDP request for {file_size} bytes to {server_ip}:{server_udp_port}{RESET}")

        # Step 2: Start receiving data (expect multiple segments)
        received_segments = 0
        total_segments = 0
        segment_numbers = set()
        start_time = time.time()
        data, _ = udp_socket.recvfrom(4096)
        udp_socket.settimeout(1)

        while True:

            # Step 3: Validate the response
            if data[:4] != MAGIC_COOKIE or data[4:5] != PAYLOAD_TYPE:
                print(f"{RED}Invalid payload received{RESET}")
                continue

            total_segments = int.from_bytes(data[5:13], 'big')
            current_segment = int.from_bytes(data[13:21], 'big')

            # Step 4: Check if we already received this segment
            if current_segment not in segment_numbers:
                segment_numbers.add(current_segment)
                received_segments += 1
            try:
                data, _ = udp_socket.recvfrom(4096)  # Adjust buffer size as needed
            except socket.timeout:
                print(f"{RED}No data received for more than 1 second, finishing transfer.{RESET}")
                break

        # Step 6: Calculate transfer stats
        transfer_time = time.time() - start_time
        packet_received = 100 - (100 * (total_segments - received_segments) / total_segments)
        print(f"{GREEN}UDP transfer complete in {transfer_time:.2f} seconds, "
              f"packet received: {packet_received:.2f}%{RESET}")

    except Exception as err:
        print(f"{RED}Error during UDP request: {err}{RESET}")
    finally:
        udp_socket.close()


def start_client():
    try:
        print(f"{BLUE}Client started, listening for offer requests...{RESET}")

        # Get user inputs for file size, TCP connections, and UDP connections
        file_size, tcp_connections, udp_connections = get_client_parameters()

        while True:
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
        print(f"{RED}\nClient stopped manually.{RESET}")
    except Exception as err:
        # Handle unexpected exceptions
        print(f"{RED}Error in client execution: {err}{RESET}")


if __name__ == "__main__":
    try:
        start_client()
    except KeyboardInterrupt:
        # Handle manual interruption
        print(f"{RED}\nClient stopped manually.{RESET}")
    except Exception as e:
        # Handle unexpected exceptions
        print(f"{RED}Unexpected error: {e}{RESET}")
