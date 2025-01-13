import socket
import threading
import time

MAGIC_COOKIE = b'\xAB\xCD\xDC\xBA'
OFFER_TYPE = b'\x02'
REQUEST_TYPE = b'\x03'
PAYLOAD_TYPE = b'\x04'
FILE_SIZE = 1024 * 1024 * 1024


def listen_for_offer():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('0.0.0.0', 12345))  # Listen on port 12345 for UDP offers

    while True:
        data, addr = udp_socket.recvfrom(1024)
        if data[:4] == MAGIC_COOKIE and data[4:5] == OFFER_TYPE:
            server_udp_port = int.from_bytes(data[5:7], 'big')
            server_tcp_port = int.from_bytes(data[7:9], 'big')
            print(f"Received offer from {addr[0]}")
            print(f"Server UDP port: {server_udp_port}, Server TCP port: {server_tcp_port}")
            return addr[0], server_udp_port, server_tcp_port  # Return the server's IP, UDP and TCP ports


def send_tcp_request(server_ip, server_tcp_port):
    # Create a TCP socket to send the request
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((server_ip, server_tcp_port))

    # Create the request message
    request_message = MAGIC_COOKIE + REQUEST_TYPE + FILE_SIZE.to_bytes(8, 'big')

    # Log the start time
    start_time = time.time()

    # Send the request
    tcp_socket.send(request_message)
    print(f"Sent TCP request for {FILE_SIZE} bytes to {server_ip}:{server_tcp_port}")

    # Receive the response (payload)
    data = tcp_socket.recv(1024 + FILE_SIZE)  # Expecting the payload and the file data

    # Measure transfer time
    transfer_time = time.time() - start_time
    transfer_speed = (FILE_SIZE * 8) / transfer_time  # bits per second

    # Validate the magic cookie and message type
    if data[:4] == MAGIC_COOKIE and data[4:5] == PAYLOAD_TYPE:
        print(
            f"TCP transfer finished, total time: {transfer_time:.2f} seconds, total speed: {transfer_speed:.2f} bits/second")
    else:
        print("Error: Invalid response from server")

    tcp_socket.close()



def send_udp_request(server_ip, server_udp_port):
    # Create a UDP socket to send the request
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Create the request message
    request_message = MAGIC_COOKIE + REQUEST_TYPE + FILE_SIZE.to_bytes(8, 'big')

    # Log the start time
    start_time = time.time()

    # Send the request
    udp_socket.sendto(request_message, (server_ip, server_udp_port))
    print(f"Sent UDP request for {FILE_SIZE} bytes to {server_ip}:{server_udp_port}")

    # Wait for the server's response (we'll handle this part in the next steps)
    # For now, we just log the time it took
    udp_socket.close()

    # Log the elapsed time for the request
    elapsed_time = time.time() - start_time
    print(f"UDP Request sent, time taken: {elapsed_time:.2f} seconds")


def start_client():
    print("Client started, listening for offer requests...")

    # Listen for offer and get the server's IP address, UDP and TCP ports
    server_ip, server_udp_port, server_tcp_port = listen_for_offer()

    # Start the TCP and UDP request threads
    tcp_thread = threading.Thread(target=send_tcp_request, args=(server_ip, server_tcp_port))
    udp_thread = threading.Thread(target=send_udp_request, args=(server_ip, server_udp_port))

    # Start the threads
    tcp_thread.start()
    udp_thread.start()

    # Wait for both threads to finish
    tcp_thread.join()
    udp_thread.join()


if __name__ == "__main__":
    try:
        start_client()
    except KeyboardInterrupt:
        print("\nClient stopped manually.")
