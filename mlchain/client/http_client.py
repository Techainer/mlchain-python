from .base import MLClient
import httpx
from mlchain.storage import Path
from mlchain.base.log import except_handler, logger
from mlchain.server.base import RawResponse, JsonResponse, FileResponse
import os
from io import BytesIO


class HttpClient(MLClient):
    def __init__(self, api_key=None, api_address=None, serializer='msgpack', image_encoder=None, name=None,
                 version='lastest', check_status=False, headers=None, **kwargs):
        MLClient.__init__(self, api_key=api_key, api_address=api_address, serializer=serializer,
                          image_encoder=image_encoder, name=name,
                          version=version, check_status=check_status, headers=headers, **kwargs)
        if isinstance(self.api_address, str):
            self.api_address = self.api_address.strip()
            if len(self.api_address) > 0 and self.api_address[-1] == '/':
                self.api_address = self.api_address[:-1]

            if len(self.api_address) > 0 and self.api_address[0] != 'h':
                self.api_address = 'http://{0}'.format(api_address)

        self.content_type = 'application/{0}'.format(self.serializer_type)
        try:
            ping = self.get('ping', timeout=5)
            logger.info("Connected to server {0}: {1}".format(api_address, ping))
        except Exception as e:
            logger.info("Can't connect to server {0}: {1}".format(api_address, e))
        if check_status:
            output_description = self.get('description', timeout=20)
            if 'error' in output_description:
                with except_handler():
                    raise AssertionError("ERROR: Model {0} in version {1} is not found".format(name, version))
            else:
                output_description = output_description['output']
                self.__doc__ = output_description['__main__']
                self.all_func_des = output_description['all_func_des']
                self.all_func_params = output_description['all_func_params']
                self.all_attributes = output_description['all_attributes']

    def __format_error(self, response):
        if response.status_code == 404:
            return {
                'error': 'This request url is not found',
                'time': 0
            }
        else:
            try:
                error = self.serializer.decode(response.content)
            except:
                error = self.json_serializer.decode(response.content)

            if 'error' in error:
                return error
            else:
                return {
                    'error': 'Server run error, please try again',
                    'time': 0
                }

    def check_response_ok(self, response):
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        try:
            response.raise_for_status()
        except:
            return False
        return True

    def _get(self, api_name, headers=None, timeout=None):
        """
        GET data from url
        """
        if headers is None:
            headers = {}
        headers = {
            'Content-type': self.content_type,
            **headers
        }

        with httpx.Client(timeout=timeout or self.timeout) as client:
            output = client.get("{0}/api/{1}".format(self.api_address, api_name), headers=headers)

        if not self.check_response_ok(output):
            return self.__format_error(output)

        output_decoded = self.serializer.decode(output.content)
        return output_decoded

    def _post(self, function_name, headers=None, args=None, kwargs=None):
        files = []
        for idx, value in enumerate(args):
            if isinstance(value, bytes):
                file_name = '__file__{0}'.format(idx)
                files.append((file_name, (file_name, BytesIO(value), 'application/octet-stream')))
                args[idx] = file_name
            elif isinstance(value, Path):
                file_name = '__file__{0}'.format(idx)
                files.append((file_name, (os.path.basename(value), open(value, 'rb'), 'application/octet-stream')))
                args[idx] = file_name
        for key, value in kwargs.items():
            if isinstance(value, bytes):
                file_name = '__file__{0}'.format(key)
                files.append((file_name, (file_name, BytesIO(value), 'application/octet-stream')))
                kwargs[key] = file_name
            elif isinstance(value, Path):
                file_name = '__file__{0}'.format(key)
                files.append((file_name, (os.path.basename(value), open(value, 'rb'), 'application/octet-stream')))
                kwargs[key] = file_name

        with httpx.Client(timeout=self.timeout) as client:
            input_encoded = self.serializer.encode((args, kwargs))
            files.append(("__parameters__", ('parameters', BytesIO(input_encoded), 'application/octet-stream')))
            headers['mlchain-serializer'] = self.serializer_type
            if self.api_key is not None:
                headers['api-key'] = self.api_key
            files = dict(files)
            output = client.post("{0}/call/{1}".format(self.api_address, function_name), headers=headers,
                                 files=files)

        if 'response-type' in output.headers:
            response_type = output.headers.get('response-type', 'mlchain/raw')
            if response_type == 'mlchain/json':
                return JsonResponse(self.json_serializer.decode(output.content))
            else:
                return RawResponse(output.content)
        if not self.check_response_ok(output):
            if output.status_code == 404:
                raise Exception("This request url is not found")
            return output.content

        return output.content
