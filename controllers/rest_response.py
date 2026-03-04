
class RestStatus:
    def __init__(self, isOk:bool=True, code:int=200, phrase:str="OK"):
        self.isOk = isOk
        self.code = code
        self.phrase = phrase

    def __json__(self):
        return {
            "isOk": self.isOk,
            "code": self.code,
            "phrase": self.phrase
        }

class RestResponse :
    def __init__(self, status:RestStatus|None=None, data:any=None):
        self.status = status if status != None else RestStatus()
        self.data = data

    def __json__(self):
        return {
            "status": self.status.__json__(),
            "data": self.data
        }