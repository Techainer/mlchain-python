import os
import glob
import math
import sys
from io import BytesIO
import threading
from boto3.session import Session
import numpy as np
from mlchain import logger
from mlchain.config import object_storage_config
from mlchain.base.exceptions import MlChainError
from .base import MLStorage

cv2 = None


def import_cv2():
    if cv2 is None:
        import cv2 as cv
        return cv
    return cv2


class ProgressPercentage:
    def __init__(self, filename, filesize):
        self._filename = filename
        self._size = filesize
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        def convertSize(size):
            if (size == 0):
                return '0B'
            size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
            i_name = int(math.floor(math.log(size, 1024)))
            chunk = math.pow(1024, i_name)
            size = round(size / chunk, 2)
            return '%.2f %s' % (size, size_name[i_name])

        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)        " % (self._filename, convertSize(self._seen_so_far),
                                                     convertSize(self._size), percentage))
            sys.stdout.flush()


class ObjectStorage(MLStorage):
    def __init__(self, bucket=None, client=None, url=None,
                 access_key=None, secret_key=None, provider=None, ping=False):
        MLStorage.__init__(self)
        self.bucket = bucket or object_storage_config.BUCKET
        self._client = client
        self.url = url or object_storage_config.URL
        self.access_key = access_key or object_storage_config.ACCESS_KEY
        self.secret_key = secret_key or object_storage_config.SECRET_KEY
        self.provider = provider or object_storage_config.PROVIDER or 's3'
        if ping:
            try:
                self.client.list_buckets()
            except Exception:
                MlChainError("Can't connect to Object Storage", code="S000", status_code=500)
        if self.bucket:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    @property
    def client(self):
        if self._client is None:
            session = Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key)
            self._client = session.client(self.provider, endpoint_url=self.url)
        return self._client

    def download_file(self, key, local_path, bucket_name=None, use_basename=False):
        """
        Download a file from S3.
        Args:
            key: `str`. S3 key that will point to the file.
            local_path: `str`. the path to download to.
            bucket_name: `str`. Name of the bucket in which to store the file.
            use_basename: `bool`. whether or not to use the basename of the key.
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        local_path = os.path.abspath(local_path)
        if use_basename:
            local_path = os.path.join(local_path, os.path.basename(key))
        dir_name = os.path.dirname(local_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        try:
            content_length = self.client.head_object(Bucket=bucket_name, Key=key)["ContentLength"]
            progress = ProgressPercentage(key, content_length)
            self.client.download_file(bucket_name, key, local_path, Callback=progress)
            return True
        except Exception as ex:
            logger.error(str(ex))
            raise MlChainError(str(ex), code="S001", status_code=500)

    def download_bytes(self, key, bucket_name=None, use_basename=True):
        """
        Download a file from S3.
        Args:
            key: `str`. S3 key that will point to the file.
            local_path: `str`. the path to download to.
            bucket_name: `str`. Name of the bucket in which to store the file.
            use_basename: `bool`. whether or not to use the basename of the key.
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        try:
            buffer = BytesIO()
            self.client.download_fileobj(bucket_name, key, buffer)
            return buffer.getvalue()
        except Exception as ex:
            logger.error(str(ex))
            raise MlChainError(str(ex), code="S002", status_code=500)

    def download_cv2(self, key, bucket_name=None):
        """
        Download a file from S3.
        Args:
            key: `str`. S3 key that will point to the file.
            local_path: `str`. the path to download to.
            bucket_name: `str`. Name of the bucket in which to store the file.
            use_basename: `bool`. whether or not to use the basename of the key.
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        try:
            buffer = BytesIO()
            self.client.download_fileobj(bucket_name, key, buffer)
            cv2 = import_cv2()
            return cv2.imdecode(
                np.asarray(bytearray(buffer.getvalue()), dtype="uint8"),
                cv2.IMREAD_COLOR)
        except Exception as ex:
            logger.error(str(ex))
            raise MlChainError(str(ex), code="S003", status_code=500)

    def download_dir(self, prefix, dir_path, bucket_name=None):
        bucket_name = bucket_name or self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        if prefix.endswith('/'):
            prefix = prefix[:-1]
        if len(prefix) > 0:
            prefix = '{0}/'.format(prefix)
        try:
            results = self.list(bucket_name=bucket_name, prefix=prefix)
            for file in results['keys']:
                self.download_file(prefix + file, os.path.join(dir_path, file),
                                   bucket_name=bucket_name)
            for dir in results['prefixes']:
                self.download_dir(prefix + dir, os.path.join(dir_path, dir),
                                  bucket_name=bucket_name)
        except Exception as ex:
            logger.error(str(ex))
            raise MlChainError(str(ex), code="S004", status_code=500)

    def upload_file(self, filename,
                    key,
                    bucket_name=None,
                    overwrite=False,
                    encrypt=False,
                    acl=None,
                    use_basename=False):
        """
        Uploads a local file to S3.
        Args:
            filename: `str`. name of the file to upload.
            key: `str`. S3 key that will point to the file.
            bucket_name: `str`. Name of the bucket in which to store the file.
            overwrite: `bool`. A flag to decide whether or not to overwrite the key
                if it already exists. If replace is False and the key exists, an
                error will be raised.
            encrypt: `bool`. If True, the file will be encrypted on the server-side
                by S3 and will be stored in an encrypted form while at rest in S3.
            acl: `str`. ACL to use for uploading, e.g. "public-read".
            use_basename: `bool`. whether or not to use the basename of the filename.
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        if use_basename:
            key = os.path.join(key, os.path.basename(filename))
        try:
            self.client.upload_file(filename, bucket_name, key)
        except Exception as ex:
            logger.error(str(ex))
            raise MlChainError(str(ex), code="S005", status_code=500)

    def upload_bytes(self, bytes_data,
                     key,
                     bucket_name=None,
                     overwrite=False,
                     encrypt=False,
                     acl=None):
        """
        Uploads bytes to S3
        This is provided as a convenience to drop a string in S3. It uses the
        boto infrastructure to ship a file to s3.
        Args:
            bytes_data: `bytes`. bytes to set as content for the key.
            key: `str`. S3 key that will point to the file.
            bucket_name: `str`. Name of the bucket in which to store the file.
            overwrite: `bool`. A flag to decide whether or not to overwrite the key
                if it already exists.
            encrypt: `bool`. If True, the file will be encrypted on the server-side
                by S3 and will be stored in an encrypted form while at rest in S3.
            acl: `str`. ACL to use for uploading, e.g. "public-read".
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        filelike_buffer = BytesIO(bytes_data)
        try:
            self.client.upload_fileobj(filelike_buffer, bucket_name, key)
        except Exception as ex:
            logger.info(str(ex))
            raise MlChainError(str(ex), code="S006", status_code=500)

    def upload_cv2(self, img,
                   key,
                   bucket_name=None,
                   overwrite=False,
                   quality=95,
                   img_fmt='.jpg',
                   acl=None):
        """
        Uploads bytes to S3
        This is provided as a convenience to drop a string in S3. It uses the
        boto infrastructure to ship a file to s3.
        Args:
            bytes_data: `bytes`. bytes to set as content for the key.
            key: `str`. S3 key that will point to the file.
            bucket_name: `str`. Name of the bucket in which to store the file.
            overwrite: `bool`. A flag to decide whether or not to overwrite the key
                if it already exists.
            encrypt: `bool`. If True, the file will be encrypted on the server-side
                by S3 and will be stored in an encrypted form while at rest in S3.
            acl: `str`. ACL to use for uploading, e.g. "public-read".
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        try:
            jpg_formats = ['.JPG', '.JPEG']
            png_formats = ['.PNG']
            encode_params = None
            img_fmt = '.{0}'.format(img_fmt.strip('.')).upper()
            cv2 = import_cv2()
            if img_fmt in jpg_formats:
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            elif img_fmt in png_formats:
                encode_params = [cv2.IMWRITE_PNG_COMPRESSION, quality]
            ret, buf = cv2.imencode(img_fmt, img, encode_params)

            filelike_buffer = BytesIO(buf.tostring())

            self.client.upload_fileobj(filelike_buffer, bucket_name, key)
        except Exception as ex:
            logger.info(str(ex))
            raise MlChainError(str(ex), code="S007", status_code=500)

    def upload_dir(self, dir_path, prefix, bucket_name=None):
        bucket_name = bucket_name or self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        try:
            for file in glob.glob(os.path.join(dir_path, '*'), recursive=True):
                file_name = file[len(dir_path):].replace('\\', '/')
                if file_name.startswith('/'):
                    file_name = file_name[1:]
                key = os.path.join(prefix, file_name).replace('\\', '/')
                if os.path.isfile(file):
                    self.upload_file(file, key, bucket_name)
                else:
                    self.upload_dir(file, key, bucket_name)
        except Exception as ex:
            logger.info(str(ex))
            raise MlChainError(str(ex), code="S008", status_code=500)

    def list(self,
             bucket_name=None,
             prefix='',
             delimiter='/',
             page_size=None,
             max_items=None,
             keys=True,
             prefixes=True):
        """
        Lists prefixes and contents in a bucket under prefix.
        Args:
            bucket_name: `str`. the name of the bucket
            prefix: `str`. a key prefix
            delimiter: `str`. the delimiter marks key hierarchy.
            page_size: `str`. pagination size
            max_items: `int`. maximum items to return
            keys: `bool`. if it should include keys
            prefixes: `boll`. if it should include prefixes
        """
        if not bucket_name:
            bucket_name = self.bucket
        if bucket_name is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        config = {
            'PageSize': page_size,
            'MaxItems': max_items,
        }
        try:
            paginator = self.client.get_paginator('list_objects_v2')

            response = paginator.paginate(Bucket=bucket_name,
                                          Prefix=prefix,
                                          Delimiter=delimiter,
                                          PaginationConfig=config)

            def get_keys(contents):
                list_keys = []
                for cont in contents:
                    list_keys.append(cont['Key'][len(prefix):])

                return list_keys

            def get_prefixes(page_prefixes):
                list_prefixes = []
                for pref in page_prefixes:
                    list_prefixes.append(pref['Prefix'][len(prefix): -1])
                return list_prefixes

            results = {
                'keys': [],
                'prefixes': []
            }
            for page in response:
                if prefixes:
                    results['prefixes'] += get_prefixes(page.get('CommonPrefixes', []))
                if keys:
                    results['keys'] += get_keys(page.get('Contents', []))

            return results
        except Exception as ex:
            logger.info(str(ex))
            raise MlChainError(str(ex), code="S009", status_code=500)

    def listdir(self, path, bucket=None):
        bucket = bucket or self.bucket
        if bucket is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        try:
            results = self.list(bucket_name=bucket, prefix=path)
            return {'files': results['keys'], 'dirs': results['prefixes']}
        except Exception as ex:
            logger.info(str(ex))
            raise MlChainError(str(ex), code="S010", status_code=500)

    def delete(self, path, bucket=None):
        bucket = bucket or self.bucket
        if bucket is None:
            raise MlChainError("bucket can't be None", code="S000", status_code=500)
        try:
            self.client.remove_object(bucket, path)
        except Exception as ex:
            logger.info(str(ex))
            raise MlChainError(str(ex), code="S011", status_code=500)
