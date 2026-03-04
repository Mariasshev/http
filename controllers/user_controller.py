from http.server import BaseHTTPRequestHandler
from controllers.controller_rest import ControllerRest

class UserController(ControllerRest):
    def __init__(self, handler: BaseHTTPRequestHandler):
        super().__init__(handler)

    def do_GET(self):
        self.rest_response.data = {
            "result": {
                "x": 10,
                "y": 20,
                "w": 30,
                "t": "Вітання!!"
            },
      
            "query_params": getattr(self.handler, 'query_params', {}),
            
            "api_params": getattr(self.handler, 'api', {}),
            
            "raw_query_string": self.handler.path.split('?', 1)[1] if '?' in self.handler.path else ""
        }