class FakeModelClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.messages = []

    def parse_request(self, text):
        self.messages.append(text)
        if self.error:
            raise self.error
        return self.result
