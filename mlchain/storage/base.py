import os


class Path(str):
    def __init__(self, local_path: str = ""):
        str.__init__(self)
        if os.path.exists(local_path):
            self.local_path = local_path
        else:
            self.local_path = os.path.join(os.getcwd(), local_path)
            if not os.path.exists(self.local_path):
                raise Exception("Path should be exist")

    def __str__(self):
        return self.local_path

    def __repr__(self):
        return self.local_path


class MLStorage:
    def __init__(self):
        pass

    def download_file(self, src, des):
        pass

    def download_bytes(self, *args, **kwargs):
        pass

    def upload_file(self, src_local, des):
        pass

    def upload_bytes(self, bytes, des):
        pass

    def listdir(self, prefix):
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        raise NotImplementedError

    def download_dir(self, *args, **kwargs):
        raise NotImplementedError

    def upload_dir(self, *args, **kwargs):
        raise NotImplementedError
