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
            
            # Точка входа для всех запросов
            self.access_manager()
            self.wfile.flush()
        except socket.timeout as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1

    def access_manager(self):
        # Базовая заглушка, будет переопределена в RequestHandler
        self.send_error(501, "Method 'access_manager' not implemented")

class RequestHandler(AccessManagerRequestHandler):
    def __init__(self, *args, **kwargs):
        self.query_params = {}
        self.api = {"method": None, "service": None, "section": None}
        super().__init__(*args, **kwargs)

    def access_manager(self):
        parts = self.path.split('?', 1)
        request_path = parts[0]
        
        # 1. Проверка статики (теперь передаем путь)
        if self.check_static_asset(request_path):
            return

        # 2. Разбор параметров маршрута
        self.api["method"] = self.command
        splitted_path = [url_decode(p) for p in request_path.strip("/").split("/", 1)]
        self.api["service"] = splitted_path[0] if len(splitted_path) > 0 and splitted_path[0] else "home"
        self.api["section"] = splitted_path[1] if len(splitted_path) > 1 else None

        # 3. Разбор Query String
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

        # 4. Динамический импорт контроллера
        module_name = f"{self.api['service'].lower()}_controller"
        class_name = f"{self.api['service'].capitalize()}Controller"

        if "./" not in sys.path:
            sys.path.append("./")

        try:
            controller_module = importlib.import_module(f"controllers.{module_name}")
            controller_class = getattr(controller_module, class_name)
            controller_object = controller_class(self) # передаем handler
            
            # Ищем метод (например, do_GET)
            mname = f"do_{self.command}"
            if hasattr(controller_object, mname):
                method = getattr(controller_object, mname)
                method()
            elif hasattr(controller_object, "serve"): # поддержка метода serve из CGI примера
                controller_object.serve()
            else:
                self.send_error(405, f"Method {self.command} not supported by {class_name}")

        except Exception as ex:
            msg = str(ex) if DEV_MODE else "Internal Server Error"
            self.send_error(404, f"Routing error: {msg}")

    def check_static_asset(self, req_path):
        """Интегрированная логика из access_manager.py"""
        if self.command != "GET":
            return False
        
        # Защита от Directory Traversal (../)
        if ".." in req_path:
            return False

        # Если путь не заканчивается на / и содержит точку — это файл
        if not req_path.endswith('/') and '.' in req_path:
            ext = req_path[req_path.rindex('.') + 1:].lower()
            allowed_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'css': 'text/css',
                'js': 'text/javascript',
                'ico': 'image/x-icon'
            }

            if ext in allowed_types:
                # Путь к папке static. Убедитесь, что она существует
                file_path = os.path.join(os.getcwd(), 'static', req_path.lstrip('/'))
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            self.send_response(200)
                            self.send_header("Content-type", allowed_types[ext])
                            self.end_headers()
                            self.wfile.write(f.read())
                        return True
                except Exception:
                    pass
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