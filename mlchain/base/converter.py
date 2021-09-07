import os
import io
import json
from base64 import b64decode
from typing import List, Union, Dict, Set
from inspect import signature, _empty, iscoroutinefunction
from collections import defaultdict
import numpy as np
from PIL import Image, ImageSequence
from .exceptions import MLChainAssertionError
from ..config import mlconfig
from ..context import mlchain_context
import ast 

cv2 = None
ALL_LOWER_TRUE = set(["true", "yes", "yeah", "y"])
ALL_LOWER_FALSE = set(["none", 'false', 'n', 'null', 'no'])
ALL_LOWER_NULL = set(['none', 'null', 'nil'])

if mlconfig.image_rgba is None:
    CV2FLAG = 1
elif mlconfig.image_rgba.lower() in ALL_LOWER_TRUE:
    CV2FLAG = -1
else:
    CV2FLAG = 1


def import_cv2():
    global cv2
    if cv2 is None:
        import cv2 as cv
        cv2 = cv

def ast_json_parse_string(value: str): 
    try: 
        l = ast.literal_eval(value)
        return l 
    except Exception as ex:
        try:
            l = json.loads(value)
            return l
        except Exception as ex1:
            raise MLChainAssertionError("Can't convert {0} to Python list, dict, set. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

def bytes2ndarray(value: bytes) -> np.ndarray: 
    import_cv2()
    nparr = np.fromstring(value, np.uint8)
    img = cv2.imdecode(nparr, CV2FLAG)
    if img is not None:
        return img
    else:
        raise MLChainAssertionError("Can't decode bytes {0} to ndarray. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

def str2ndarray(value: str) -> np.ndarray:
    if value.lower() in ALL_LOWER_NULL:
        return None
    if value[0:4] == 'http':
        from mlchain.base.utils import is_image_url_and_ready
        # If it is a url image
        if is_image_url_and_ready(value):
            from mlchain.base.utils import read_image_from_url_cv2
            return read_image_from_url_cv2(value, CV2FLAG)
        else:
            raise MLChainAssertionError("Image url is not valid. Please check the variable {0}".format(mlchain_context.CONVERT_VARIABLE))
    if os.path.exists(value):
        import_cv2()
        return cv2.imread(value)
    if value.startswith('data:image/') and 'base64' in value:
        import_cv2()
        content = value[value.index('base64') + 7:]
        nparr = np.fromstring(b64decode(content), np.uint8)
        img = cv2.imdecode(nparr, CV2FLAG)
        if img is not None:
            return img
        else:
            raise MLChainAssertionError("Can't decode base64 {0} to ndarray. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

    try:
        d = json.loads(value)
        if isinstance(d, list):
            return np.array(d)
    except:
        pass
    import_cv2()
    # If it is a base64 encoded array
    try:
        nparr = np.fromstring(b64decode(value), np.uint8)
        img = cv2.imdecode(nparr, CV2FLAG)
        if img is not None:
            return img
    except:
        pass

    try:
        l = ast_json_parse_string(value)

        # If it is a string array
        arr = np.array(l)
        if arr is not None:
            return arr
    except:
        raise MLChainAssertionError(
            "There's no way to convert to numpy array with variable {0}. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))
    raise MLChainAssertionError("Can't convert {0} to ndarray. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))


def list2ndarray(value: list) -> np.ndarray:
    raise MLChainAssertionError("Not allow multi value. Please check the variable {0}".format(mlchain_context.CONVERT_VARIABLE), code="convert")


def str2int(value: str) -> int:
    try:
        return int(value)
    except: 
        raise MLChainAssertionError("Can't convert {0} to type int. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

def str2float(value: str) -> float:
    try:
        return float(value)
    except:
        raise MLChainAssertionError("Can't convert {0} to type float. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))


def str2bool(value: str) -> bool:
    if value.lower() in ALL_LOWER_TRUE:
        return True
    if value.lower() in ALL_LOWER_FALSE:
        return False
    raise MLChainAssertionError("Can't convert {0} to type boolean. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))


def str2list(value: str) -> List:
    try: 
        l = ast_json_parse_string(value)
        return l 
    except Exception as ex:
        return [value]

def str2dict(value: str) -> dict:
    try:
        l = ast_json_parse_string(value)
        return l
    except Exception as ex:
        raise MLChainAssertionError("Can't convert {0} to dict. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

def str2set(value: str) -> set: 
    try:
        l = ast_json_parse_string(value)
        return l
    except Exception as ex:
        raise MLChainAssertionError("Can't convert {0} to set. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

def str2bytes(value: str) -> bytes:
    return value.encode()


def cv2imread(filename, value) -> np.ndarray:
    import_cv2()
    value = cv2.imdecode(
        np.asarray(bytearray(value), dtype="uint8"),
        CV2FLAG)
    if value is None:
        raise MLChainAssertionError("Can't read image from {0}. Please check the variable {1}".format(filename, mlchain_context.CONVERT_VARIABLE))
    return value


def cv2imread_to_list(filename, value) -> List[np.ndarray]:
    import_cv2()
    value = cv2.imdecode(
        np.asarray(bytearray(value), dtype="uint8"),
        CV2FLAG)
    if value is None:
        raise MLChainAssertionError("Can't read image from {0}. Please check the variable {1}".format(filename, mlchain_context.CONVERT_VARIABLE))
    return [value]


def pilimread_one_img(filename, img_bytes) -> np.ndarray:
    output = []
    im = Image.open(io.BytesIO(img_bytes))

    for i, page in enumerate(ImageSequence.Iterator(im)):
        return np.array(page)
    raise MLChainAssertionError("Can't convert file {0} to ndarray. Please check the variable {1}".format(filename, mlchain_context.CONVERT_VARIABLE))


def pilimread_list_img(filename, img_bytes) -> List[np.ndarray]:
    try:
        output = []
        im = Image.open(io.BytesIO(img_bytes))

        for i, page in enumerate(ImageSequence.Iterator(im)):
            output.append(np.array(page))
        return output
    except: 
        raise MLChainAssertionError("Can't convert file {0} to List[np.ndarray]. Please check the variable {1}".format(filename, mlchain_context.CONVERT_VARIABLE))


def storage2bytes(filename, value) -> bytes:
    return value


def storage2json(filename, value) -> Union[List, Dict]:
    try:
        return json.loads(value, encoding='utf-8')
    except: 
        raise MLChainAssertionError("Can't convert file {0} to List or Dict. Please check the variable {1}".format(filename, mlchain_context.CONVERT_VARIABLE))


def storage2str(filename, value) -> str:
    return value.decode()


def get_type(t):
    if t == List:
        return list, None
    elif t == Dict:
        return dict, None
    elif t == Set:
        return set, None
    elif isinstance(t, (tuple, list)):
        return Union, tuple(t)
    if getattr(t, '__origin__', None) is None:
        return t, None
    else:
        return t.__origin__, t.__args__


class Converter:
    convert_dict = defaultdict(dict)
    file_converters = {}
    map_type = {
        List: list,
        Dict: dict,
        Set: set
    }

    def __init__(self, file_storage_type=None, get_file_name=None, get_data=None):
        self.FILE_STORAGE_TYPE = file_storage_type
        self._get_file_name = get_file_name
        self._get_data = get_data

    @staticmethod
    def add_convert(function, in_type=None, out_type=None):
        sig = signature(function)
        parameters = sig.parameters
        for key, input_types in parameters.items():
            if in_type is None:
                input_types = input_types.annotation
            else:
                input_types = in_type
            if out_type is None:
                output_types = sig.return_annotation
            else:
                output_types = out_type
            if input_types == Union:
                input_types = input_types.__args__
            else:
                input_types = [input_types]

            if output_types == Union:
                output_types = output_types.__args__
            else:
                output_types = [output_types]

            for i_type in input_types:
                for o_type in output_types:
                    Converter.convert_dict[i_type][o_type] = function
            break

    @staticmethod
    def add_convert_file(extensions, function, output_type=None):
        sig = signature(function)
        input_types = extensions.split(',')
        input_types = tuple(sorted(e.strip() for e in input_types))
        if output_type is None:
            output_types = sig.return_annotation

            if output_types == Union:
                output_types = output_types.__args__
            else:
                output_types = (output_types,)
        else:
            output_types = (output_type,)
        for o_type in output_types:
            Converter.file_converters[(input_types, o_type)] = function

    def convert_file(self, file_name, data, out_type):
        ext = file_name.rsplit('.')[-1].lower()
        out_type = Union[out_type]
        if out_type == Union:
            out_type = out_type.__args__
        else:
            out_type = (out_type,)
        for (k, o), converter in self.file_converters.items():
            if (ext in k or '*' in k) and (out_type == o or o in out_type):
                return converter(file_name, data)
        raise MLChainAssertionError(
            "Not found convert file {0} to {1}. Please check the variable {2}".format(file_name, out_type, mlchain_context.CONVERT_VARIABLE))

    def convert(self, value, out_type):
        '''
        Convert type of value to out_type
        :param value:
        :param out_type:
        :return:
        '''
        origin, args = get_type(out_type)
        if origin == _empty:
            return value
        if origin in [List, Set, Dict, list, set, dict] and args is not None:
            if isinstance(value, (List, list)):
                if origin in [List, list]:
                    return [self.convert(v, args) for v in value]
                if origin in [Set, set]:
                    return set(self.convert(v, args) for v in value)
            elif isinstance(value, (Dict, dict)):
                if origin in [Dict, list]:
                    if len(args) == 2:
                        return {self.convert(k, args[0]): self.convert(v, args[1])
                                for k, v in value.items()}
                    if len(args) == 1:
                        return {k: self.convert(v, args[0]) for k, v in value.items()}
            else:
                if type(value) == self.FILE_STORAGE_TYPE:
                    return self.convert_file(self._get_file_name(value),
                                             self._get_data(value), out_type)
                if origin in [List, list]:
                    value = str2list(value)
                    return [self.convert(v, args) for v in value]
                if origin in [Set, set]:
                    value = str2set(value)
                    return {self.convert(value, args) for v in value}
                raise MLChainAssertionError(
                    "Can't convert value {0} to {1}. Please check the variable {2}".format(value, out_type, mlchain_context.CONVERT_VARIABLE),
                    code="convert")
        else:
            try:
                if isinstance(value, out_type):
                    return value
            except:
                pass
        if origin == Union:
            out_type = args
        else:
            out_type = (out_type,)
        if type(value) in out_type:
            return value

        for i_type in self.convert_dict:
            if isinstance(value, i_type):
                for o_type in self.convert_dict[i_type]:
                    if o_type in out_type:
                        return self.convert_dict[i_type][o_type](value)

        if type(value) == self.FILE_STORAGE_TYPE:
            return self.convert_file(self._get_file_name(value), self._get_data(value), out_type)

        for o_type in out_type:
            if callable(getattr(o_type, "from_json", None)):
                if iscoroutinefunction(o_type.from_json):
                    raise MLChainAssertionError("You need to use Starlette Server to use async convert function")
                else:
                    return o_type.from_json(value)

        raise MLChainAssertionError("Not found converter from {0} to {1}. Please check the variable {2}".format(type(value), out_type, mlchain_context.CONVERT_VARIABLE))

class AsyncConverter(Converter):
    async def convert(self, value, out_type):
        '''
        Convert type of value to out_type
        :param value:
        :param out_type:
        :return:
        '''
        origin, args = get_type(out_type)
        if origin == _empty:
            return value
        if origin in [List, Set, Dict, list, set, dict] and args is not None:
            if isinstance(value, (List, list)):
                if origin in [List, list]:
                    return [await self.convert(v, args) for v in value]
                if origin in [Set, set]:
                    return set(await self.convert(v, args) for v in value)
            elif isinstance(value, (Dict, dict)):
                if origin in [Dict, list]:
                    if len(args) == 2:
                        return {await self.convert(k, args[0]): await self.convert(v, args[1])
                                for k, v in value.items()}
                    if len(args) == 1:
                        return {k: await self.convert(v, args[0]) for k, v in value.items()}
            else:
                if type(value) == self.FILE_STORAGE_TYPE:
                    byte_data = await self._get_data(value)
                    return self.convert_file(self._get_file_name(value),
                                             byte_data, out_type)
                if origin in [List, list]:
                    return [await self.convert(value, args)]
                if origin in [Set, set]:
                    return {await self.convert(value, args)}
                raise MLChainAssertionError(
                    "Can't convert value {0} to {1}. Please check the variable {2}".format(value, out_type, mlchain_context.CONVERT_VARIABLE),
                    code="convert")
        else:
            try:
                if isinstance(value, out_type):
                    return value
            except:
                pass
        if origin == Union:
            out_type = args
        else:
            out_type = (out_type,)
        if type(value) in out_type:
            return value

        for i_type in self.convert_dict:
            if isinstance(value, i_type):
                for o_type in self.convert_dict[i_type]:
                    if o_type in out_type:
                        return self.convert_dict[i_type][o_type](value)
        
        if type(value) == self.FILE_STORAGE_TYPE:
            byte_data = await self._get_data(value)
            return self.convert_file(self._get_file_name(value), byte_data, out_type)
        
        for o_type in out_type:
            if callable(getattr(o_type, "from_json", None)):
                if iscoroutinefunction(o_type.from_json):
                    return await o_type.from_json(value)
                else: 
                    return o_type.from_json(value)

        raise MLChainAssertionError("Not found converter from {0} to {1}. Please check the variable {2}".format(type(value), out_type, mlchain_context.CONVERT_VARIABLE))

Converter.add_convert(lambda x: str(x), int, str)
Converter.add_convert(bytes2ndarray)
Converter.add_convert(str2ndarray)
Converter.add_convert(list2ndarray)
Converter.add_convert(str2int)
Converter.add_convert(str2float)
Converter.add_convert(str2bool)
Converter.add_convert(str2bytes, str, bytes)
Converter.add_convert(str2bytes, str, bytearray)
Converter.add_convert(str2list, str, list)
Converter.add_convert(str2list, str, List)
Converter.add_convert(str2set, str, set)
Converter.add_convert(str2set, str, Set)
Converter.add_convert(str2dict, str, Dict)
Converter.add_convert(str2dict, str, dict)
Converter.add_convert_file('jpg,jpeg,png,gif,bmp,jpe,jp2,pbm,pgm,ppm,sr,ras',
                           cv2imread,
                           output_type=np.ndarray)
Converter.add_convert_file('jpg,jpeg,png,gif,bmp,jpe,jp2,pbm,pgm,ppm,sr,ras',
                           cv2imread_to_list,
                           output_type=List[np.ndarray])
Converter.add_convert_file('tif,tiff',
                           pilimread_one_img,
                           output_type=np.ndarray)
Converter.add_convert_file('tif,tiff',
                           pilimread_list_img,
                           output_type=List[np.ndarray])
Converter.add_convert_file('*', storage2bytes, output_type=bytes)
Converter.add_convert_file('json', storage2json, output_type=dict)
Converter.add_convert_file('txt', storage2str, output_type=str)


def pilimread(filename, img_bytes) -> Image.Image:
    try:
        im = Image.open(io.BytesIO(img_bytes))
        return im
    except Exception as e:
        raise MLChainAssertionError(
            "Can't convert file {0} to PIL Image. Error: {1}. Please check the variable {2}".format(filename, e, mlchain_context.CONVERT_VARIABLE))


def pilimread_list(filename, img_bytes) -> List[Image.Image]:
    output = []
    im = Image.open(io.BytesIO(img_bytes))

    for i, page in enumerate(ImageSequence.Iterator(im)):
        output.append(page)
    return output


def str2pil(value: str) -> Image.Image:
    if value.lower() in ALL_LOWER_NULL:
        return None
    if value[0:4] == 'http':
        from mlchain.base.utils import is_image_url_and_ready
        # If it is a url image
        if is_image_url_and_ready(value):
            from mlchain.base.utils import read_image_from_url_pil
            return read_image_from_url_pil(value)
        raise MLChainAssertionError("Image url is not valid. Please check the variable {0}".format(mlchain_context.CONVERT_VARIABLE))
    if os.path.exists(value):
        return Image.open(open(value, 'rb'))
    if value.startswith('data:image/') and 'base64' in value:

        content = value[value.index('base64') + 7:]
        try:
            data = io.BytesIO(b64decode(content))
            return Image.open(data)
        except:
            raise MLChainAssertionError(
                "Can't decode base64 {0} to PIL Image. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))

        # If it is a base64 encoded array
    try:
        data = io.BytesIO(b64decode(value))
        return Image.open(data)
    except:
        pass

    try:
        l = ast_json_parse_string(value)

        # If it is a string array
        return Image.fromarray(l)
    except:
        raise MLChainAssertionError(
            "There's no way to convert to PIL Image with variable {0}. Please check the variable {1}".format(value, mlchain_context.CONVERT_VARIABLE))


Converter.add_convert_file('jpg,jpeg,png,gif,bmp,jpe,jp2,pbm,pgm,ppm,sr,ras',
                           pilimread,
                           output_type=Image.Image)
Converter.add_convert_file('jpg,jpeg,png,gif,bmp,jpe,jp2,pbm,pgm,ppm,sr,ras',
                           lambda a, b: [pilimread(a, b)],
                           output_type=List[Image.Image])
Converter.add_convert_file('tif,tiff',
                           lambda a, b: pilimread_list(a, b)[0],
                           output_type=Image.Image)
Converter.add_convert_file('tif,tiff',
                           pilimread_list,
                           output_type=List[Image.Image])
Converter.add_convert(str2pil, in_type=str, out_type=Image.Image)
