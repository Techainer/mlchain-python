import os


class Path(str):
    def __init__(self, local_path: str = ""):
        if os.path.exists(local_path):
            self.local_path = local_path
        else:
            self.local_path = os.path.join(os.getcwd(), local_path)
            if not os.path.exists(self.local_path):
                raise Exception("Path should be exist")
        str.__init__(self, self.local_path)

    def __str__(self):
        return self.local_path

    def __repr__(self):
        return self.local_path


class MLStorage:
    '''
    Class base of Storage
    '''
