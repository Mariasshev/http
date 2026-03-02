import json

class BaseController:
    """Базовий клас для всіх контролерів з підтримкою REST-відповідей"""
    def __init__(self, handler):
        self.handler = handler

    def send_json(self, data, status=200):
        self.handler.send_response(status)
        self.handler.send_header("Content-type", "application/json")
        self.handler.end_headers()
        self.handler.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def response_with_pagination(self, data_list, total_items):
        page = self.handler.page
        per_page = self.handler.per_page
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        
        # шлях для посилань
        path = f"/{self.handler.api['service']}"
        if self.handler.api['section']:
            path += f"/{self.handler.api['section']}"

        def make_link(p):
            return f"{path}?page={p}&per_page={per_page}"

        response = {
            "data": data_list,
            "meta": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": per_page
            },
            "links": {
                "self": make_link(page),
                "first": make_link(1),
                "last": make_link(total_pages),
                "next": make_link(page + 1) if page < total_pages else None,
                "prev": make_link(page - 1) if page > 1 else None
            }
        }
        self.send_json(response)

class UsersController(BaseController):
    def do_GET(self):
        # Імітація бази даних 
        mock_db = [{"id": i, "name": f"User_{i}"} for i in range(1, 46)]
        
        total = len(mock_db)
        start = (self.handler.page - 1) * self.handler.per_page
        end = start + self.handler.per_page
        
        # зріз даних
        paged_data = mock_db[start:end]
        
        # за межами даних
        if not paged_data and self.handler.page > 1:
            self.send_json({"error": "Page not found"}, 404)
            return

        self.response_with_pagination(paged_data, total)