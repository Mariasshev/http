from http.server import BaseHTTPRequestHandler
import json
from controllers.rest_response import RestResponse, RestStatus

# С целью избегания адреса /rest меняем правило именования для класса
class ControllerRest : 
  def __init__(self, handler: BaseHTTPRequestHandler):
    self.handler = handler
    self.rest_response = RestResponse()

  def before_execution(self):
      pass
  
  def after_execution(self): 
      pass


  # Основной метод запуска контроллера, который обеспечивает жизненный цикл запроса
  def serve(self):
    mname = 'do_' + self.handler.command
    if not hasattr(self, mname):
      self.rest_response.status = RestStatus(
          isOk=False,
          code=405,
          phrase="Unsupported method (%r) in '%r'" % (self.handler.command, self.__class__.__name__)
        )
      
    else:
      method = getattr(self, mname)
      # выполняем метод, передавая управление контроллеру
      try:
        self.before_execution()
        method()
        self.after_execution()
      except Exception as ex:
        self.rest_response.status = RestStatus(
          isOk=False,
          code=500,
          phrase="Request processing error " + str(ex)
        )
      
    self.send_rest_response()



  def send_rest_response(self):
    self.handler.send_response(200, "OK")
    self.handler.send_header("Content-Type", "application/json; charset=utf-8")
    self.handler.end_headers()
    self.handler.wfile.write(
      json.dumps(
          self.rest_response,
          ensure_ascii=False,
          default=lambda x: x.__json__() if hasattr(x, '__json__') else str(x)
      ).encode()
    )
