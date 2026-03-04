from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket 
import sys
import importlib

DEV_MODE = True


def url_decode(input: str | None) -> str | None:
  return None if input is None else urllib.parse.unquote_plus(input)


class AccessManagerRequestHandler(BaseHTTPRequestHandler):
  def handle_one_request(self):
    '''
    Базовая реализация BaseHTTPRequestHandler не позволяет внедрить
    диспетчер доступа, который, в свою очередь, является нормативным требованием,
    например https://tzi.com.ua/downloads/1.1-002-99.pdf
    '''
    # https://tedboy.github.io/python_stdlib/_modules/BaseHTTPServer.html#BaseHTTPRequestHandler.handle
    try:
      self.raw_requestline = self.rfile.readline(65537)
      if len(self.raw_requestline) > 65536:
        self.requestline = ''
        self.request_version = ''
        self.command = ''
        self.send_error(414)
        return
      if not self.raw_requestline:
        self.close_connection = 1
        return
      if not self.parse_request():
        # An error code has been sent, just exit
        return
      
      # Замена - все запросы переводятся на единственный метод access_manager
      mname = 'access_manager'
      if not hasattr(self, mname):
        self.send_error(501, "Method 'access_manager' not overriden")
        return
      # Конец замены

      method = getattr(self, mname)
      method()
      self.wfile.flush() # actually send the response if not already done.
    except socket.timeout as e:
      # a read or a write timed out.  Discard this connection
      self.log_error("Request timed out: %r", e)
      self.close_connection = 1
      return
    

  def access_manager(self):
    mname = 'do_' + self.command
    if not hasattr(self, mname):
      self.send_error(405, "Unsupported method (%r)" % self.command)
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
    parts = self.path.split('?', 1)  # /user/auth?hash=1a2d==&p=50/50&q=who?&x=10&y=20&x=30&json

    # проверка если запрос на файл, то прекращаем обработчик и отправляем файл в методе
    if self.check_static_asset(parts[0]):
      return

    # разобрать параметры маршрута API: METHOD /service/section?
    self.api["method"] = self.command
    splitted_path = [url_decode(p) for p in parts[0].strip("/").split("/", 1)]
    self.api["service"] = splitted_path[0] if len(splitted_path) > 0 and len(splitted_path[0]) > 0 else "home"
    self.api["section"] = splitted_path[1] if len(splitted_path) > 1 else None

    query_string = parts[1] if len(parts) > 1 else ""   # hash=1a2d==&p=50/50&q=who?&&x=10&y=20&x=30&json
    # розібрати параметри запиту, очікуваний рез-т: {"hash": "1a2d==", "p": "50/50", "q":"who?", x: [10, 30], y: 20, json: None}
    for key, value in (map(url_decode, (item.split('=', 1) if '=' in item else [item, None]))
      for item in query_string.split('&') if len(item) > 0):
        self.query_params[key] = value if not key in self.query_params else [
          *(self.query_params[key] if isinstance(self.query_params[key],
            (list, tuple)) else [self.query_params[key]]),
          value
        ]

    # Название файла контроллера (home_controller)
    module_name = self.api["service"].lower() + "_controller"
    # Название класса (HomeController)
    class_name = self.api["service"].capitalize() + "Controller"

    # Добавляем текущую директорию чтоб искать модули
    sys.path.append(".")

    try:
      # Ищем (подключаем) модуль с именем module_name
      controller_module = importlib.import_module(f"controllers.{module_name}")
    except Exception as ex:
      self.send_error(404, f"Controller module Not Found {module_name} {ex if DEV_MODE else ''}")
      return

    # в нем находим класс class_name, создаем с него объект
    controller_class = getattr(controller_module, class_name, None)
    if controller_class is None:
      self.send_error(404, f"Controller class not found: {controller_class}")
      return
    
    # Все данные про маршрут и запрос - в объекте self
    controller_object = controller_class(self)

    # ищем в контроллере метод-обработчик
    mname = 'serve'
    if not hasattr(controller_object, mname):
      self.send_error(500, "Non-standart controller" + (f" method 'serve' not found in '{class_name}'" if DEV_MODE else ""))
      return
    method = getattr(controller_object, mname)
    # выполняем метод, передавая управление контроллеру
    try:
      method()
    except Exception as ex:
      message = "Request processing error "
      if DEV_MODE : message += str(ex)
      self.send_error(500, message)


  def check_static_asset(self, path_file : str) -> bool:
    '''Проверяет является ли запрос на существующий файл и отправляем его'''
    if self.command != "GET": 
      return False

    if (path_file.endswith('/')
      or '../' in path_file
      or not '.' in path_file):
      return False

    path = './http/static' + path_file
    ext = path.rsplit('.', 1)[1]
    allowed_media_types = {
      "png": "image/png",
      "jpg": "image/jpeg",
      "css": "text/css",
      "js": "text/javascript"
    }
    if ext in allowed_media_types:
      try:
        with open(path, "rb") as file :
          self.send_response(200, "OK")
          self.send_header("Content-Type", allowed_media_types[ext])
          self.end_headers()
          self.wfile.write(file.read())
          return True
      except Exception as err :
        print(err)
        return
    else:
      self.send_error(415, f"Unsupported Media Type: {ext}")
      return True


def main():
  host = '127.0.0.1'
  port = 8080
  endpoint = (host, port)
  http_server = HTTPServer(endpoint, RequestHandler)
  try:
    print(f"Try start server http://{host}:{port}")
    http_server.serve_forever()
  except:
    print("Server stopped")


if __name__ == '__main__':
  main()
