class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SessionExpiredException(AppException):
    def __init__(self, message: str = "Session has expired or does not exist."):
        super().__init__(message, status_code=404)


class CSVValidationException(AppException):
    def __init__(self, message: str = "Invalid CSV structure or data format."):
        super().__init__(message, status_code=422)


class SQLSecurityException(AppException):
    def __init__(self, message: str = "SQL query violated security rules or session isolation."):
        super().__init__(message, status_code=403)
