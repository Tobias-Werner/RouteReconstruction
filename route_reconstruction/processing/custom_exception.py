class CustomException(Exception):
    def __init__(self, message):
        super(CustomException, self).__init__(message)
