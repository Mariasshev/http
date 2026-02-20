from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import urllib.parse

def url_decode(input:str|None) -> str|None :
    return None if input is None else urllib.parse.unquote_plus(input)


class AccessManagerRequestHandler(BaseHTTPRequestHandler) :
    def handle_one_request(self) :
        '''Базова реалызація BaseHTTPRequestHandler не дозволяє впровадити
        диспетчер доступу, який, у свою чергу, є вимогою нормативних
        документів, зокрема https://tzi.com.ua/downloads/1.1-002-99.pdf
        '''

        #https://tedboy.github.io/python_stdlib/_modules/BaseHTTPServer.html#BaseHTTPRequestHandler.handle
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
            # заміна - усі запити переводяться на єдиний метод access_manager
            mname = 'access_manager' 
            if not hasattr(self, mname):
                self.send_error(501, "Method access_manager not overriden ")
                return
            # кінець заміни
            method = getattr(self, mname)
            method()

            self.wfile.flush() #actually send the response if not already done.
        except socket.timeout as e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    def access_manager(self) :
        mname = 'do_' + self.command
        if not hasattr(self, mname):
            self.send_error(405, "Unsupported method (%r)" % self.command)
            return
        method = getattr(self, mname)
        method()



class RequestHandler(AccessManagerRequestHandler) :
    def __init__(self, request, client_address, server) :
        self.query_params = {}
        self.api = {
            "method" : None,
            "service" : None,
            "section" : None,

        }
        super().__init__(request, client_address, server)
       


    def access_manager(self):
        parts = self.path.split('?', 1)
        path = parts[0] # /user/auth
        # розібрати параметри маршруту API: METHOD /service/section?
        self.api["method"] = self.command
        splitted_path = [url_decode(p) for p in parts[0].strip("/").split("/", 1)]
        self.api["service"] = splitted_path[0] if len(splitted_path) > 0 and len(splitted_path[0]) else "home"
        self.api["section"] = splitted_path[1] if len(splitted_path) > 1 and len(splitted_path[1]) else None
        query_string = parts[1] if len(parts) > 1 else "" # hash=1a2d==&p=50/50&q=who?&&x=10&y=20&x=30&json
        # розібрати параметри запиту, очікуваний рез-т: {"hash": "1a2d==", "p": "50/50", "q":"who?", x: [10, 30], y: 20, json: None}
        for key, value in (map(url_decode, (item.split('=', 1) if '=' in item else [item, None]))
            for item in query_string.split('&') if len(item) > 0) :
                self.query_params[key] = value if not key in self.query_params else [
                    *(self.query_params[key] if isinstance(self.query_params[key], (list, tuple)) else [self.query_params[key]]),
                    value
                ]
        return super().access_manager()

    def do_GET(self) :
            print(f"Запит отримано: {self.path}")
            
            # =список тестових посилань
            test_links = [
                ("/user/auth", "Без параметрів"),
                ("/user/auth?", "Без параметрів, але з '?'"),
                ("/user/auth?hash=1a2d==&p=50/50&q=who?&x=10&y=20&x=30&json", "Повтори ключів та прапорці"),
                ("/user/auth?hash=1a2d==&p=50/50&q=who?&&x=10&y=20&x=30&json&url=%D0%A3%D0%BD%D1%96%D1%84%D1%96%D0%BA%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B9&%D0%BB%D0%BE%D0%BA%D0%B0%D1%82%D0%BE%D1%80=%D1%80%D0%B5%D1%81%D1%83%D1%80%D1%81%D1%96%D0%B2&2+2=4", "URL-кодовані ключі та значення")
            ]

            links_html = "".join([f'<li><a href="{href}">{label}</a></li>' for href, label in test_links])

            self.send_response(200, "OK")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            response_body = f"""
            <html>
                <head><title>HTTP Server Test</title></head>
                <body>
                    <h1>Тестування HTTP сервера</h1>
                    <h3>Результати:</h3>
                    <pre style="background: #f4f4f4; padding: 10px; border-radius: 5px;">
                    self.path = {self.path}
                    api       = {self.api}
                    params    = {self.query_params}
                    </pre>
                    
                    <hr/>
                    
                    <h3>Тестові сценарії:</h3>
                    <ul>
                        {links_html}
                    </ul>
                    
                    <hr/>
                    
                    <button onclick="linkClick()">Викликати LINK метод</button>
                    <p id="out" style="color: blue;"></p>

                    <script>
                        function linkClick(){{
                            fetch("/", {{
                                method: "LINK"
                            }})
                            .then(r => r.text())
                            .then(t => document.getElementById('out').innerText = t);
                        }}
                    </script>
                </body>
            </html>
            """
            self.wfile.write(response_body.encode())


    def do_LINK(self) :
        self.send_response(200, "OK")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("LINK method response".encode())


def main() :
    host = '127.0.0.1'
    port = 8000
    endpoint = (host, port)
    http_server = HTTPServer(endpoint, RequestHandler)
    try :
        print(f"Try start server http://{host}:{port}")
        http_server.serve_forever()
    except :
        print("Server stopped")


if __name__ == '__main__' :
    main()



'''
Модуль HTTP
Альтернативний до CGI підхід у створенні серверних застосунків 
полягає у створенні власного (програмного)
сервера, що є частиною загального прєкту.
+ використовуємо єдину мову програмування (непотрібна конфігурація
стороннього сервера окремою мовою)
+ уніфікуються ліцензійні умови
- дотримання стандартів і протоколів перекладається на проєкт
- частіше за все програмні сервери більш повільні і не сиртифіковані
- необхідність перезапуску сервера після внесення змін до скриптів

У Python такі засоби надає пакет http.server:
HTTPServer, - клас управління сервером(слухання порту, прийом запитів)
BaseHTTPRequestHandler - продовження оброблення, формування відповіді

У результаті досліджень зʼясовуємо
- на кожен запит утворюється новий обʼєкт класу RequestHandler
- print виводить на консоль запуску, а не до відповіді сервера
- path відповідає за повний шлях запиту + параметри (query string)
- command відповідає за методи запиту
- маршрутизація не здійснюється

MVC                                           API
GET  /user/auth     |один                   GET   /user/auth     |різні
POST /user/auth     |обробник               POST  /user/auth     |обробники
GET  /user/profile - інший обробник         GET   /user/profile - той самий, що й для GET /user/auth 
'''