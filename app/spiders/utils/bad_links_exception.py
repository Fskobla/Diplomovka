# Own exception for Bad links table - reason
class BadLinkException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message
