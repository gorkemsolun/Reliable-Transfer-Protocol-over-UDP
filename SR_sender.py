# Görkem Kadir Solun 22003214

import socket
import sys
import threading
import time

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
start_time = time.time()

# Read file
with open(FILE_PATH, "rb") as f:
    data = f.read()

# Divide file into segments
segments = [data[i : i + DATA_SIZE] for i in range(0, len(data), DATA_SIZE)]


class SR_Sender:
    def __init__(self):
        self.send_base = 0
        self.next_seq_num = 0
        self.acks_received = set()
        self.lock = threading.Lock()
        # Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((IP, RECEIVER_PORT))

    # Send segment function
    def send_segment(self, i):
        # Send segment i to receiver with header i + 1 (1-indexed) in big endian
        self.sock.send((i + 1).to_bytes(HEADER_SIZE, byteorder="big") + segments[i])

        # Wait for ack
        while i not in self.acks_received:
            time.sleep(TIMEOUT / 1000)
            with self.lock:
                if VERBOSE:
                    print(f"Timeout for segment {i}, resending segment")

                # Resend segment
                self.sock.send(
                    (i + 1).to_bytes(HEADER_SIZE, byteorder="big") + segments[i]
                )

    # Receive ack function
    def receive_ack(self):
        while True:
            try:
                last_ack = int.from_bytes(self.sock.recv(HEADER_SIZE), byteorder="big")
                last_ack = last_ack - 1  # 1-indexed
                if VERBOSE:
                    print(f"Acknowledgement {last_ack}")

                # Update send_base
                with self.lock:
                    if (
                        last_ack in range(self.send_base, self.send_base + N)
                        and last_ack not in self.acks_received
                    ):
                        # Update acks_received
                        self.acks_received.add(last_ack)

                        # Update send_base
                        while self.send_base in self.acks_received:
                            self.send_base += 1
            except:
                pass

    def main(self):
        # Start receive ack thread
        ack_thread = threading.Thread(target=self.receive_ack, daemon=True)
        ack_thread.start()

        # Main selective repeat loop
        while True:
            # Send packet
            with self.lock:
                # Check if nextseqnum is within window and not exceeding segments
                if self.next_seq_num < self.send_base + N and self.next_seq_num < len(
                    segments
                ):
                    # Create thread
                    send_thread = threading.Thread(
                        target=self.send_segment, args=(self.next_seq_num,), daemon=True
                    )

                    # Start thread
                    send_thread.start()

                    if VERBOSE:
                        print(f"Sending segment {self.next_seq_num}")

                    # Increment nextseqnum
                    self.next_seq_num += 1

                # Check if all segments are sent and all acks are received
                if len(self.acks_received) == len(segments):
                    break

        # Send termination signal
        self.sock.send((0).to_bytes(HEADER_SIZE, byteorder="big"))

        # Close socket
        self.sock.close()


if __name__ == "__main__":
    # Create sender object
    sender = SR_Sender()

    # Run sender
    sender.main()

    # End time
    end_time = time.time()

    # Print time
    print(f"Time: {end_time - start_time} seconds")
