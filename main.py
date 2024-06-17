import http.server
import socket
import select
import base64
import requests

# Global variable to keep track of the current proxy index
proxy_index = 0

# Define your valid Base64-encoded credentials (username:password)
valid_credentials_base64 = base64.b64encode(b'kosmos:secretsauce').decode('utf-8')

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_proxy_request()

    def do_POST(self):
        self.handle_proxy_request()

    def do_CONNECT(self):
        global proxy_index
        proxies = self.read_proxies_from_file('proxies.txt')
        if not proxies:
            self.send_error(503, "Service Unavailable", "No proxies available")
            return

        # Rotate through proxies
        proxy_index = (proxy_index + 1) % len(proxies)
        proxy_url = proxies[proxy_index]
        proxy_host, proxy_port = proxy_url.split(':')

        # Establish connection to the proxy server
        try:
            proxy_sock = socket.create_connection((proxy_host, int(proxy_port)))
            self.send_response(200, 'Connection Established')
            self.end_headers()

            # Tunnel data between client and proxy
            self.client_sock = self.connection
            self.sockets = [self.client_sock, proxy_sock]
            self.proxy_sock = proxy_sock

            self.handle_tunneling()

        except Exception as e:
            self.send_error(502, "Bad Gateway", str(e))

    def handle_tunneling(self):
        try:
            while True:
                ready_socks, _, _ = select.select(self.sockets, [], [])
                if self.client_sock in ready_socks:
                    data = self.client_sock.recv(4096)
                    if not data:
                        break
                    self.proxy_sock.sendall(data)
                if self.proxy_sock in ready_socks:
                    data = self.proxy_sock.recv(4096)
                    if not data:
                        break
                    self.client_sock.sendall(data)
        finally:
            self.client_sock.close()
            self.proxy_sock.close()

    def handle_proxy_request(self):
        global proxy_index

        # Check for Basic Authentication in Authorization header
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Basic '):
            encoded_credentials = auth_header[len('Basic '):].strip()
            if encoded_credentials == valid_credentials_base64:
                # Valid credentials provided via Authorization header
                pass  # Proceed to proxy request handling
            else:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Proxy Authentication"')
                self.end_headers()
                self.wfile.write(b'Unauthorized access')
                return
        else:
            # Check for credentials in the URL (http://username:password@proxy_host:proxy_port)
            url_parts = self.path.split('@')
            if len(url_parts) > 1:
                credentials_part = url_parts[0].split('//')[1]
                username_password = credentials_part.split(':')
                if len(username_password) == 2:
                    username = username_password[0]
                    password = username_password[1]
                    if base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8') != valid_credentials_base64:
                        self.send_response(401)
                        self.send_header('WWW-Authenticate', 'Basic realm="Proxy Authentication"')
                        self.end_headers()
                        self.wfile.write(b'Unauthorized access')
                        return

        # Read proxies from file
        proxies = self.read_proxies_from_file('proxies.txt')
        if not proxies:
            self.send_error(503, "Service Unavailable", "No proxies available")
            return

        # Rotate through proxies
        proxy_index = (proxy_index + 1) % len(proxies)
        proxy_url = proxies[proxy_index]
        print(f"Using proxy: {proxy_url}")

        # Prepare headers and URL for the request
        headers = {key: val for key, val in self.headers.items()}
        request_url = self.path
        if not request_url.startswith('http'):
            request_url = f'http://{self.headers["Host"]}{self.path}'

        try:
            response = requests.request(
                method=self.command,
                url=request_url,
                headers=headers,
                data=self.rfile.read(int(self.headers.get('Content-Length', 0))) if self.command == 'POST' else None,
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=10,
            )

            # Send response back to client
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)

        except requests.RequestException as e:
            self.send_error(502, "Bad Gateway", str(e))

    def read_proxies_from_file(self, filename):
        try:
            with open(filename, 'r') as f:
                proxies = [line.strip() for line in f.readlines() if line.strip()]
                return proxies
        except IOError:
            return []

if __name__ == '__main__':
    host = 'localhost'
    port = 8080

    # Create server
    server = http.server.HTTPServer((host, port), ProxyHandler)
    print(f"Starting proxy server on http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping proxy server")
        server.server_close()
