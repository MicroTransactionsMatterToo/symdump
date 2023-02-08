from io import BytesIO

class ObjectFile:
    def __init__(self, name: str):
        self.name = name
        self.children = []
        self.children_names = []