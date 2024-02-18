"""
Author: Konano
Description: A HTTP Server based on socket and multi-threading
"""

import argparse
import socket
import threading
from base64 import b64encode

from utils.log import logger


class WSGIServer(object):
    def __init__(self, server_address):
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind(server_address)
        self.listen_socket.listen(128)

    def serve_forever(self):
        while True:
            client_socket, client_address = self.listen_socket.accept()
            new_process = threading.Thread(
                target=self.handleRequest,
                args=(
                    client_socket,
                    client_address,
                ),
            )
            new_process.start()

    def handleRequest(self, client_socket, client_address):
        try:
            recv_data = client_socket.recv(PACKET_MAXSIZE)
        except ConnectionResetError:
            client_socket.close()
            logger.warning("ConnectionResetError")
            return
        if len(recv_data) == 0:
            client_socket.close()
            return
        if VERBOSE:
            logger.debug(client_address)
            print(f"{b64encode(recv_data) = }")
        content = b64encode(recv_data)
        # content = b64encode(recv_data) + b'_' + str(time.time()).encode()
        response_header = "HTTP/1.1 200 OK\r\n"
        response_header += "Content-Type: application/javascript\r\n"
        response_header += f"Content-Length: {len(content)}\r\n"
        response_header += f"ReqsMiner: {content.decode()}\r\n"
        response_header += "\r\n"
        response_body = content
        client_socket.send(response_header.encode())
        client_socket.send(response_body)
        client_socket.close()


def get_args():
    parser = argparse.ArgumentParser(description="ReqsMiner Server")
    parser.add_argument(
        "--host", type=str, default="localhost", help="listening host (default: localhost)"
    )
    parser.add_argument("--port", type=int, default=8080, help="listening port (default: 8080)")
    parser.add_argument(
        "--packet-maxsize", type=int, default=2048, help="packet maxsize (default: 2048)"
    )
    parser.add_argument(
        "--verbose", action="store_true", default=False, help="verbose mode (default: False)"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = get_args()

    SERVER_ADDR = (HOST, PORT) = args.host, args.port
    PACKET_MAXSIZE = args.packet_maxsize
    VERBOSE = args.verbose

    try:
        httpd = WSGIServer(SERVER_ADDR)
        logger.info(f"Web Server: Serving HTTP on port {PORT} ...")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()  # print a newline after ^C
        logger.info("Web Server: Shutting down server ...")
        httpd.listen_socket.close()
