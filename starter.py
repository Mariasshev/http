from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket 
import sys
import importlib
import os
from controllers.rest_response import RestStatus

DEV_MODE = True

def url_decode(input_str: str | None) -> str | None:
    return None if input_str is None else urllib.parse.unquote_plus(input_str)

class AccessManagerRequestHandler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.send_error(414) # Request-URI Too Long
                return
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if not self.parse_request():
                return
            
            mname = 'access_manager'
            if not hasattr(self, mname):
                status = RestStatus.NOT_IMPLEMENTED()
                self.send_error(status.code, "Method 'access_manager' not overriden")
                return

            method = getattr(self, mname)
            method()
            self.wfile.flush() 
        except socket.timeout as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    def access_manager(self):
        mname = 'do_' + self.command
        if not hasattr(self, mname):
            status = RestStatus.METHOD_NOT_ALLOWED()
            self.send_error(status.code, f"Unsupported method: {self.command}")
            return
        method = getattr(self, mname)
        method()


class RequestHandler(AccessManagerRequestHandler):
    def __init__(self, request, client_address, server):
        self.query_params = {}
        self.api = {
            "method": None,
            "service": None,
            "section": None,
        }
        super().__init__(request, client_address, server)

    def access_manager(self):
        parts = self.path.split('?', 1)
        request_path = parts[0]

        if self.check_static_asset(request_path):
            return

        self.api["method"] = self.command
        path_parts = request_path.strip("/").split("/")
        self.api["service"] = path_parts[0] if len(path_parts) > 0 and path_parts[0] else "home"
        self.api["section"] = path_parts[1] if len(path_parts) > 1 else None

        # Разбор Query String
        query_string = parts[1] if len(parts) > 1 else ""
        for item in query_string.split('&'):
            if not item: continue
            kv = item.split('=', 1)
            key = url_decode(kv[0])
            value = url_decode(kv[1]) if len(kv) > 1 else None
            
            if key in self.query_params:
                if not isinstance(self.query_params[key], list):
                    self.query_params[key] = [self.query_params[key]]
                self.query_params[key].append(value)
            else:
                self.query_params[key] = value

        module_name = self.api["service"].lower() + "_controller"
        class_name = self.api["service"].capitalize() + "Controller"

        if "." not in sys.path:
            sys.path.append(".")

        try:
            controller_module = importlib.import_module(f"controllers.{module_name}")
        except Exception as ex:
            status = RestStatus.NOT_FOUND()
            self.send_error(status.code, f"Controller module {module_name} not found. {ex if DEV_MODE else ''}")
            return

        controller_class = getattr(controller_module, class_name, None)
        if controller_class is None:
            status = RestStatus.NOT_FOUND()
            self.send_error(status.code, f"Controller class {class_name} not found")
            return
        
        controller_object = controller_class(self)

        if not hasattr(controller_object, 'serve'):
            status = RestStatus.NOT_IMPLEMENTED()
            self.send_error(status.code, f"Method 'serve' not found in {class_name}")
            return

        try:
            controller_object.serve()
        except Exception as ex:
            status = RestStatus.INTERNAL_SERVER_ERROR()
            message = str(ex) if DEV_MODE else status.phrase
            self.send_error(status.code, message)

    def check_static_asset(self, request_path: str) -> bool:
        if self.command != "GET": 
            return False

        if '../' in request_path:
            self.send_error(403, "Forbidden")
            return True

        _, ext = os.path.splitext(request_path)
        ext = ext.lower()

        if not ext:
            return False

        # Белый список типов
        allowed_media_types = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif":  "image/gif",
            ".ico":  "image/x-icon",
            ".css":  "text/css",
            ".js":   "text/javascript",
            ".html": "text/html; charset=utf-8"
        }

        if ext in allowed_media_types:
            full_path = os.path.join("static", request_path.lstrip("/"))
            try:
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    with open(full_path, "rb") as file:
                        self.send_response(200, "OK")
                        self.send_header("Content-Type", allowed_media_types[ext])
                        self.end_headers()
                        self.wfile.write(file.read())
                        return True
                else:
                    status = RestStatus.NOT_FOUND()
                    self.send_error(status.code, f"File {request_path} not found")
                    return True
            except Exception as e:
                self.send_error(500, str(e))
                return True
        else:
            status = RestStatus.UNSUPPORTED_MEDIA_TYPE()
            self.send_error(status.code, f"{status.phrase}: {ext}")
            return True


def main():
    host, port = '127.0.0.1', 8080
    try:
        http_server = HTTPServer((host, port), RequestHandler)
        print(f"Server started: http://{host}:{port}")
        http_server.serve_forever()
    except Exception as e:
        print(f"Server failed: {e}")
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    main()