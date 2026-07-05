class BizError(Exception):
    """业务错误：转换为 {code, message} envelope，HTTP 400（除非指定）。"""

    def __init__(self, message: str, code: int = 400, http_status: int = 400):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)
