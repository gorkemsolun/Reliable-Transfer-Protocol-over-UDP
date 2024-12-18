# Görkem Kadir Solun 22003214

import socket
import sys
import threading
from time import time

# Constants
PACKET_SIZE = 1024  # 1 KB
HEADER_SIZE = 2  # 2 bytes
DATA_SIZE = PACKET_SIZE - HEADER_SIZE
IP = "127.0.0.1"

print("Usage: python SR_sender.py <file_path> <receiver_port> <N> <timeout>")
print("PLEASE CORRECT THE RECEIVED FILE TYPE IF IT IS NOT A PNG")
print("Program is running...")

# Cmd args
FILE_PATH = sys.argv[1]
RECEIVER_PORT = int(sys.argv[2])
N = int(sys.argv[3])
TIMEOUT = int(sys.argv[4])  # in ms
VERBOSE = int(sys.argv[5]) if len(sys.argv) > 5 else 0

# Start time
start_time = time()

# Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect((IP, RECEIVER_PORT))

# Read file
with open(FILE_PATH, "rb") as f:
    data = f.read()

# Divide file into segments
segments = [data[i : i + DATA_SIZE] for i in range(0, len(data), DATA_SIZE)]

# Define variables
send_base = 0  # Send base
nextseqnum = 0  # Next sequence number
kill = False  # Kill flag
ack = -1  # Last ack received
# Thread dictionary {segment_no:thread}
threads = {}  # Thread dictionary {segment_no:thread}
threads_events = {}  # Thread event dictionary {segment_no:event}
# Acknowledgements received set
acks_received = set()


# Send segment function
def send_segment(i):
    # Send segment i to receiver with header i + 1 (1-indexed) in big endian
    sock.send((i + 1).to_bytes(HEADER_SIZE, byteorder="big") + segments[i])

    # Start timer
    threads[i].timer = time()

    # Wait for ack
    while True:
        # Check if timeout is reached for segment i (in ms)
        if time() - threads[i].timer > TIMEOUT / 1000:
            if threads_events[i].is_set():
                # Ack received for segment i
                # Make the thread kill itself
                kill = True
                return

            if VERBOSE:
                print(f"Timeout for segment {i}, resending segment {i}")

            # Resend segment
            sock.send((i + 1).to_bytes(HEADER_SIZE, byteorder="big") + segments[i])

            # Restart timer
            threads[i].timer = time()


# Main selective repeat loop
while True and not kill:
    # Send packet
    if nextseqnum < send_base + N and nextseqnum < len(segments):
        # Create thread
        threads[nextseqnum] = threading.Thread(target=send_segment, args=(nextseqnum,))

        # Create event
        threads_events[nextseqnum] = threading.Event()

        # Start thread
        threads[nextseqnum].start()

        if VERBOSE:
            print(f"Sending segment {nextseqnum}")

        # Increment nextseqnum
        nextseqnum += 1

    # Receive ack
    try:
        ack = int.from_bytes(sock.recv(HEADER_SIZE), byteorder="big")
        ack = ack - 1  # 1-indexed
        if VERBOSE:
            print(f"Acknowledgement {ack}")

        # Update send_base
        if ack in range(send_base, send_base + N) and ack not in acks_received:
            # Update acks_received
            acks_received.add(ack)

            # Set event for segment ack
            threads_events[ack].set()

            threads[ack].join()

            # Update send_base
            while send_base in acks_received:
                send_base += 1
    except:
        pass

    # Check if all segments are sent and all acks are received
    if send_base == len(segments) and len(acks_received) == len(segments):
        break

# Send termination signal
sock.send((0).to_bytes(HEADER_SIZE, byteorder="big"))

# Close socket
sock.close()

# End time
end_time = time()

# Print time
print(f"Time: {end_time - start_time} seconds")
