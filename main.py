import os
import sys
import time
import socket
import webbrowser
import threading
from server import ThreadedHTTPServer, AppRequestHandler
from config import DEFAULT_HOST, DEFAULT_PORT


def find_available_port(start_port=DEFAULT_PORT, max_attempts=50):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((DEFAULT_HOST, port))
                return port
            except OSError:
                continue
    return start_port


def main():
    initial_folder = None
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if os.path.exists(candidate):
            initial_folder = os.path.abspath(candidate)

    port = find_available_port(DEFAULT_PORT)
    url = f"http://{DEFAULT_HOST}:{port}/"

    print("=" * 65)
    print("FILM PHOTO ORGANIZER & ARCHIVAL CONTACT SHEET GENERATOR")
    print("=" * 65)
    print(f"Server starting on : {url}")
    if initial_folder:
        print(f"Target folder      : {initial_folder}")
    print("Press Ctrl+C in terminal to stop the application.")
    print("=" * 65)

    server = ThreadedHTTPServer((DEFAULT_HOST, port), AppRequestHandler)

    # Launch browser after a brief pause to allow server binding
    def open_browser():
        time.sleep(0.6)
        query = f"?path={initial_folder}" if initial_folder else ""
        webbrowser.open(f"{url}{query}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Film Photo Organizer...")
        server.server_close()
        print("Done. Goodbye!")


if __name__ == "__main__":
    main()
