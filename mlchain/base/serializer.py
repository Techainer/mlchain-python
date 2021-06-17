"""
This code referenced a part of aiomas codecs 
Git link: https://gitlab.com/sscherfke/aiomas
and msgpack_numpy:
Git link: https://github.com/lebedov/msgpack-numpy/blob/master/msgpack_numpy.py
"""

import json
import warnings
import base64
import sys
import numpy as np
from msgpack import packb, unpackb
from PIL import Image
from .exceptions import MLChainSerializationError, MlChainError

cv2 = None


def import_cv2():
    global cv2
    if cv2 is None:
        import cv2 as cv
        cv2 = cv


try:
    import blosc
except:
    blosc = None
    warnings.warn("can't import blosc. Not support MsgpackBloscSerializer")

TYPESIZE = 8 if sys.maxsize > 2 ** 32 else 4

if sys.version_info >= (3, 0):
    if sys.platform in ['darwin', 'win32']:
        ndarray_to_bytes = lambda obj: obj.tobytes()
    else:
        ndarray_to_bytes = lambda obj: obj.data if obj.flags['C_CONTIGUOUS'] else obj.tobytes()

    num_to_bytes = lambda obj: obj.data


    def tostr(x):
        if isinstance(x, bytes):
            return x.decode()
        return str(x)
else:
    if sys.platform in ['darwin', 'win32']:
        ndarray_to_bytes = lambda obj: obj.tobytes()
    else:
        ndarray_to_bytes = lambda obj: memoryview(obj.data) if obj.flags['C_CONTIGUOUS'] else obj.tobytes()

    num_to_bytes = lambda obj: memoryview(obj.data)


    def tostr(x):
        return x


class Serializer:
    def __init__(self):
        self._serializers = {}
        self._deserializers = {}

        self.add_serializer(type=set, serialize=_serialize_set,
                            deserialize=_deserialize_set)
        self.add_serializer(type=bytes, serialize=_serialize_bytes,
                            deserialize=_deserialize_bytes)

        # Numpy array bool
        self.add_serializer(type=np.bool_, serialize=lambda obj: bool(obj),
                            deserialize=lambda obj: np.bool(obj))

        # Numpy array integer
        for dtype in [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64]:
            self.add_serializer(type=dtype, serialize=lambda obj: int(obj),
                                deserialize=_get_numpy_deserializer(dtype))

        # Numpy float integer
        for dtype in [np.float32, np.float64, np.longdouble]:
            self.add_serializer(type=dtype, serialize=lambda obj: float(obj),
                                deserialize=_get_numpy_deserializer(dtype))

        self.add_serializer(type=np.generic, serialize=lambda x: float(x),
                            deserialize=lambda x: x)
        self.add_serializer(type=Image.Image, serialize=lambda x: [x.mode, x.size, x.tobytes('raw')],
                            deserialize=lambda x: Image.frombytes(x[0], x[1], [2], decoder_name='raw'))

    def encode(self, data):
        """Encode the given *data* and return a :class:`bytes` object."""
        raise NotImplementedError

    def decode(self, data):
        """Decode *data* from :class:`bytes` to the original data structure."""
        raise NotImplementedError

    def add_serializer(self, type, serialize, deserialize):
        """Add methods to *serialize* and *deserialize* objects typed *type*.

        This can be used to de-/encode objects that the codec otherwise
        couldn't encode.

        *serialize* will receive the unencoded object and needs to return
        an encodable serialization of it.

        *deserialize* will receive an objects representation and should return
        an instance of the original object.

        """
        if type in self._serializers:
            warnings.warn(
                'There is already a serializer for type "{}"'.format(type))
        typeid = len(self._serializers)
        self._serializers[type] = (typeid, serialize)
        self._deserializers[typeid] = deserialize

    def serialize_obj(self, obj):
        """Serialize *obj* to something that the codec can encode."""
        orig_type = otype = type(obj)
        if otype not in self._serializers:
            # Fallback to a generic serializer (if available)
            otype = object

        if isinstance(obj, MlChainError): 
            raise obj

        try:
            typeid, serialize = self._serializers[otype]
        except KeyError:
            if callable(getattr(obj, "to_json", None)):
                return obj.to_json()
            if callable(getattr(obj, "dump_json", None)):
                return obj.dump_json()
            raise MLChainSerializationError('No serializer found for type {0}, or you can define "to_json" function in class'
                                            .format(orig_type))

        try:
            # Handle msgpack_numpy 
            encoded = serialize(obj)
            if isinstance(encoded, dict) and (b'nd' in encoded or b'complex' in encoded):
                return encoded
            return {'__type__': (typeid, encoded)}
        except Exception as ex:
            raise MLChainSerializationError('Could not serialize object "{!r}": {}'.format(obj, ex))

    def deserialize_obj(self, obj_repr):
        """Deserialize the original object from *obj_repr*."""
        # This method is called for *all* dicts so we have to check if it
        # contains a desrializable type.
        if '__type__' in obj_repr:
            typeid, data = obj_repr['__type__']
            if typeid in self._deserializers:
                obj_repr = self._deserializers[typeid](data)
        elif b'nd' in obj_repr or b'complex' in obj_repr:
            return _deserialize_ndarray(obj_repr)

        return obj_repr


def _serialize_set(obj): 
    return list(obj)

def _deserialize_set(obj):
    return set(obj)

def _serialize_ndarray(obj):
    if isinstance(obj, np.ndarray):
        if obj.dtype.kind == 'V':
            kind = b'V'
            descr = obj.dtype.descr
        else:
            kind = b''
            descr = obj.dtype.str
        return {b'nd': True,
                b'type': descr,
                b'kind': kind,
                b'shape': obj.shape,
                b'data': ndarray_to_bytes(obj)}
    if isinstance(obj, (np.bool_, np.number)):
        return {b'nd': False,
                b'type': obj.dtype.str,
                b'data': num_to_bytes(obj)}
    if isinstance(obj, complex):
        return {b'complex': True,
                b'data': obj.__repr__()}


def _serialize_ndarray_json(obj):
    if isinstance(obj, np.ndarray):
        if obj.dtype.kind == 'V':
            kind = 'V'
            descr = obj.dtype.descr
        else:
            kind = ''
            descr = obj.dtype.str
        return {'nd': True,
                'type': descr,
                'kind': kind,
                'shape': obj.shape,
                'data': obj.tobytes()}
    if isinstance(obj, (np.bool_, np.number)):
        return {'nd': False,
                'type': obj.dtype.str,
                'data': num_to_bytes(obj)}
    if isinstance(obj, complex):
        return {'complex': True,
                'data': obj.__repr__()}


def _serialize_ndarray_binary(obj, image_enc_type='.png'):
    # Use PNG to keep image the same after sending
    # Use JPG to have smaller size

    if 2 <= len(obj.shape) <= 4:
        try:
            import_cv2()
            return np.array(cv2.imencode(image_enc_type, obj)[1]).tostring()
        except Exception as ex:
            pass

    return _serialize_ndarray(obj)


def _serialize_ndarray_png(obj):
    return _serialize_ndarray_binary(obj, image_enc_type=".png")


def _serialize_ndarray_jpg(obj):
    return _serialize_ndarray_binary(obj, image_enc_type=".jpg")


def _deserialize_ndarray(obj):
    if isinstance(obj, dict):
        if b'nd' in obj:
            if obj[b'nd'] is True:
                # Check if b'kind' is in obj to enable decoding of data
                # serialized with older versions (#20):
                if b'kind' in obj and obj[b'kind'] == b'V':
                    descr = [tuple(tostr(t) if type(t) is bytes else t for t in d) \
                             for d in obj[b'type']]
                else:
                    descr = obj[b'type']
                return np.frombuffer(obj[b'data'],
                                     dtype=np.dtype(descr)).reshape(obj[b'shape'])
            else:
                descr = obj[b'type']
                return np.frombuffer(obj[b'data'],
                                     dtype=np.dtype(descr))[0]
        elif 'nd' in obj:
            if obj['nd'] is True:
                # Check if b'kind' is in obj to enable decoding of data
                # serialized with older versions (#20):
                if 'kind' in obj and obj['kind'] == 'V':
                    descr = [tuple(tostr(t) if type(t) is bytes else t for t in d) \
                             for d in obj['type']]
                else:
                    descr = obj['type']
                return np.frombuffer(obj['data'],
                                     dtype=np.dtype(descr)).reshape(obj['shape'])
            else:
                descr = obj['type']
                return np.frombuffer(obj['data'],
                                     dtype=np.dtype(descr))[0]
        elif b'complex' in obj:
            return complex(tostr(obj[b'data']))
        elif 'complex' in obj:
            return complex(tostr(obj['data']))

    if isinstance(obj, np.ndarray):
        return obj
    else:
        import_cv2()
        nparr = np.frombuffer(obj, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)


def _serialize_bytes(obj):
    return base64.b64encode(obj).decode('ascii')


def _deserialize_bytes(obj):
    return base64.b64decode(obj)


def _get_numpy_deserializer(dtype):
    return lambda obj: dtype(obj)


class JsonSerializer(Serializer):
    """ 
        Use Json to Encode and Decode Message
    """

    def __init__(self):
        super().__init__()
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray_json,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray_json,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray_json,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return json.dumps(data, default=self.serialize_obj).encode()

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return json.loads(data.decode(), object_hook=self.deserialize_obj)


class MsgpackSerializer(Serializer):
    """ 
        Use MsgPack to Encode and Decode Message
    """

    def __init__(self):
        super().__init__()
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return packb(
            data, default=self.serialize_obj, use_bin_type=True)

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return unpackb(data,
                       object_hook=self.deserialize_obj,
                       use_list=True, raw=False)


class PngMsgpackSerializer(Serializer):
    """ 
        Use MsgPack to Encode and Decode Message, compress Opencv image as PNG (by ~50%)
    """

    def __init__(self):
        super().__init__()
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray_png,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return packb(
            data, default=self.serialize_obj, use_bin_type=True)

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return unpackb(data,
                       object_hook=self.deserialize_obj,
                       use_list=True, raw=False)


class JpgMsgpackSerializer(Serializer):
    """ 
        Use MsgPack to Encode and Decode Message, compress Opencv image as JPG (Down quality but higher compression, by ~80%)
    """

    def __init__(self):
        super().__init__()
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray_jpg,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return packb(
            data, default=self.serialize_obj, use_bin_type=True)

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return unpackb(data,
                       object_hook=self.deserialize_obj,
                       use_list=True, raw=False)


class MsgpackBloscSerializer(Serializer):
    """ 
        Use MsgPack to Encode and Decode Message and blosc to Compress Message
    """

    def __init__(self):
        super().__init__()
        if blosc is None:
            raise ImportError("please install python-blosc to use MsgpackBloscSerializer")
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return blosc.compress(packb(
            data, default=self.serialize_obj, use_bin_type=True), TYPESIZE)

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return unpackb(blosc.decompress(bytes(data)),
                       object_hook=self.deserialize_obj,
                       use_list=True, raw=False)


class JpgMsgpackBloscSerializer(Serializer):
    """ 
        Use MsgPack to Encode and Decode Message and blosc to Compress Message, encode jpg if detected numpy image
    """

    def __init__(self):
        super().__init__()
        if blosc is None:
            raise ImportError("please install python-blosc to use MsgpackBloscSerializer")
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray_jpg,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return blosc.compress(packb(
            data, default=self.serialize_obj, use_bin_type=True), TYPESIZE)

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return unpackb(blosc.decompress(bytes(data)),
                       object_hook=self.deserialize_obj,
                       use_list=True, raw=False)


class PngMsgpackBloscSerializer(Serializer):
    """ 
        Use MsgPack to Encode and Decode Message and blosc to Compress Message, encode jpg if detected numpy image
    """

    def __init__(self):
        super().__init__()
        if blosc is None:
            raise ImportError("please install python-blosc to use MsgpackBloscSerializer")
        self.add_serializer(type=np.ndarray, serialize=_serialize_ndarray_png,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=(np.bool_, np.number), serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)
        self.add_serializer(type=complex, serialize=_serialize_ndarray,
                            deserialize=_deserialize_ndarray)

    def encode(self, data):
        return blosc.compress(packb(
            data, default=self.serialize_obj, use_bin_type=True), TYPESIZE)

    def decode(self, data):
        if not data:
            return {
                'input': ([], {})
            }
        return unpackb(blosc.decompress(bytes(data)),
                       object_hook=self.deserialize_obj,
                       use_list=True, raw=False)
