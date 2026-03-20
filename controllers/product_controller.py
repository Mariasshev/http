import json
from .rest_response import RestStatus
from .utils import RestPagination 

class ProductController:
    def __init__(self, handler):
        self.handler = handler
        self.products_db = [
            {"id": i, "name": f"Товар {i}", "price": i * 100} 
            for i in range(1, 26)
        ]

    def serve(self):
        if self.handler.command == "GET":
            self.get_products()
        else:
            status = RestStatus.METHOD_NOT_ALLOWED()
            self.handler.send_error(status.code, status.phrase)

    def get_products(self):
        page = self.handler.query_params.get('page', 1)
        page_size = self.handler.query_params.get('page_size', 5)

        response_data = RestPagination.paginate(
            data=self.products_db, 
            page=page, 
            page_size=page_size
        )

        self.handler.send_response(200)
        self.handler.send_header("Content-Type", "application/json")
        self.handler.end_headers()
        
        response_json = json.dumps(response_data, ensure_ascii=False)
        self.handler.wfile.write(response_json.encode('utf-8'))