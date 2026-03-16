class RestStatus:
    def __init__(self, isOk: bool = True, code: int = 200, phrase: str = "OK"):
        self.isOk = isOk
        self.code = code
        self.phrase = phrase

    def __json__(self):
        return {
            "isOk": self.isOk,
            "code": self.code,
            "phrase": self.phrase
        }

    # Статические методы для быстрых ответов
    @staticmethod
    def OK(): return RestStatus(True, 200, "OK")
    
    @staticmethod
    def NOT_FOUND(msg="Not Found"): 
        return RestStatus(False, 404, msg)
    
    @staticmethod
    def METHOD_NOT_ALLOWED(msg="Method Not Allowed"): 
        return RestStatus(False, 405, msg)
    
    @staticmethod
    def UNSUPPORTED_MEDIA_TYPE(msg="Unsupported Media Type"): 
        return RestStatus(False, 415, msg)
    
    @staticmethod
    def INTERNAL_SERVER_ERROR(msg="Internal Server Error"): 
        return RestStatus(False, 500, msg)
    
    @staticmethod
    def NOT_IMPLEMENTED(msg="Not Implemented"): 
        return RestStatus(False, 501, msg)


class RestResponse:
    def __init__(self, status: RestStatus | None = None, data: any = None):
        self.status = status if status is not None else RestStatus.OK()
        self.data = data

    def __json__(self):
        return {
            "status": self.status.__json__(),
            "data": self.data
        }