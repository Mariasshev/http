from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import urllib.parse
import os
import importlib
import sys

DEV_MODE = True

def url_decode(input_str: str | None) -> str | None:
    return None if input_str is None else urllib.parse.unquote_plus(input_str)

class AccessManagerRequestHandler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if not self.parse_request():
                return
            
            self.access_manager()
            self.wfile.flush()
        except socket.timeout as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1

    def access_manager(self):
        self.send_error(501, "Method 'access_manager' not implemented")

class RequestHandler(AccessManagerRequestHandler):
    def __init__(self, *args, **kwargs):
        self.query_params = {}
        self.api = {"method": None, "service": None, "section": None}
        super().__init__(*args, **kwargs)

    def access_manager(self):
        parts = self.path.split('?', 1)
        request_path = parts[0]
        
        if self.check_static_asset(request_path):
            return

        # Разбор параметров маршрута
        self.api["method"] = self.command
        splitted_path = [url_decode(p) for p in request_path.strip("/").split("/", 1)]
        self.api["service"] = splitted_path[0] if len(splitted_path) > 0 and splitted_path[0] else "home"
        self.api["section"] = splitted_path[1] if len(splitted_path) > 1 else None

        # Разбор Query String
        query_string = parts[1] if len(parts) > 1 else ""
        if query_string:
            for item in query_string.split('&'):
                if not item: continue
                k_v = item.split('=', 1)
                key = url_decode(k_v[0])
                value = url_decode(k_v[1]) if len(k_v) > 1 else None
                
                if key in self.query_params:
                    if not isinstance(self.query_params[key], list):
                        self.query_params[key] = [self.query_params[key]]
                    self.query_params[key].append(value)
                else:
                    self.query_params[key] = value

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: sans-serif; padding: 20px; line-height: 1.5; color: #000; }}
                h1 {{ font-size: 32px; font-weight: bold; margin-bottom: 20px; }}
                h3 {{ font-size: 20px; margin: 30px 0 15px 0; }}
                .results-box {{ 
                    background: #f4f4f4; 
                    padding: 20px; 
                    font-family: 'Courier New', monospace; 
                    white-space: pre; 
                    border-radius: 2px;
                    font-size: 16px;
                    margin-bottom: 40px;
                }}
                ul {{ list-style-type: disc; padding-left: 25px; }}
                li {{ margin-bottom: 8px; }}
                a {{ color: #4B0082; text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Тестування HTTP сервера</h1>
            
            <h3>Результати:</h3>
            <div class="results-box">
self.path = {self.path}
api       = {self.api}
params    = {self.query_params}
            </div>

            <h3>Тестові сценарії:</h3>
            <ul>
                <li><a href="/">Посилання без параметрів (/)</a></li>
                <li><a href="/user">Посилання з сервісом (/user)</a></li>
                <li><a href="/user/">Посилання з сервісом (/user/)</a></li>
                <li><a href="/user/auth">Посилання з розділом (/user/auth)</a></li>
                <li><a href="/user/auth/secret">Посилання з розділами (/user/auth/secret)</a></li>
                <li><a href="/user/%D0%A3%D0%BD%D1%96%D1%84%D1%96%D0%BA%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B9&%D0%BB%D0%BE%D0%BA%D0%B0%D1%82%D0%BE%D1%80=%D1%80%D0%B5%D1%81%D1%83%D1%80%D1%81%D1%96%D0%B2&2+2=4">URL-кодовані значення (/user/Уніфікований...)</a></li>
            </ul>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

        if self.api["service"] != "home":
            module_name = f"{self.api['service'].lower()}_controller"
            class_name = f"{self.api['service'].capitalize()}Controller"
            
            if "./" not in sys.path:
                sys.path.append("./")

            try:
                controller_module = importlib.import_module(f"controllers.{module_name}")
                controller_class = getattr(controller_module, class_name)
                controller_object = controller_class(self)
                
                mname = f"do_{self.command}"
                if hasattr(controller_object, mname):
                    getattr(controller_object, mname)()
                elif hasattr(controller_object, "serve"):
                    controller_object.serve()
            except Exception:
                pass

    def check_static_asset(self, req_path):
        if self.command != "GET" or ".." in req_path:
            return False
        if not req_path.endswith('/') and '.' in req_path:
            ext = req_path[req_path.rindex('.') + 1:].lower()
            allowed_types = {'png': 'image/png', 'jpg': 'image/jpeg', 'css': 'text/css', 'js': 'text/javascript', 'ico': 'image/x-icon'}
            if ext in allowed_types:
                file_path = os.path.join(os.getcwd(), 'static', req_path.lstrip('/'))
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as f:
                            self.send_response(200)
                            self.send_header("Content-type", allowed_types[ext])
                            self.end_headers()
                            self.wfile.write(f.read())
                        return True
                    except: pass
        return False

def main():
    host, port = '127.0.0.1', 8080
    server = HTTPServer((host, port), RequestHandler)
    print(f"Server started at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    main()