import logging
import sys
import unittest

import numpy as np
from mlchain.base.serializer import (JsonSerializer, MsgpackBloscSerializer,
                                     MsgpackSerializer)

logger = logging.getLogger()

class TestSerializer(unittest.TestCase):
    def __init__(self,*args,**kwargs):
        self.serializers = [
            JsonSerializer(),
            MsgpackSerializer()
        ]
        if sys.platform != 'win32':
            self.serializers.append(MsgpackBloscSerializer())
        unittest.TestCase.__init__(self,*args,**kwargs)

    def test_numpy(self):
        logger.info("Running serializer numpy test")
        for data in [np.ones((2,3)),np.int64(1),np.float64(1)]:
            for serializer in self.serializers:
                encoded = serializer.encode(data)
                decoded = serializer.decode(encoded)
                self.assertTrue(np.all(data==decoded),"{0}.encode: value: {1}".format(serializer.__class__.__name__,data))

    def test_data(self):
        logger.info("Running serializer python data structure test")
        for data in [{'dict':{'str':'str'}},{'list':[1,2,3,'str',np.float(4)]}]:
            for serializer in self.serializers:
                encoded = serializer.encode(data)
                decoded = serializer.decode(encoded)
                self.assertTrue(data==decoded,"{0}.encode: value: {1}".format(serializer.__class__.__name__,data))


if __name__ == '__main__':
    unittest.main()
