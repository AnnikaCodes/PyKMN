from pykmn.engine.common import unpack_u16_from_bytes, pack_u16_as_bytes, \
    pack_two_u4s, unpack_two_u4s
import unittest

class TestBitpack(unittest.TestCase):
    def test_u16(self):
        """Test packing and unpacking u16s."""
        for x in range(2**16):
            packed = pack_u16_as_bytes(x)
            self.assertEqual(x, unpack_u16_from_bytes(packed[0], packed[1]))

    def test_u4(self):
        """Test packing and unpacking u4s."""
        for x in range(2**4):
            for y in range(2**4):
                packed = pack_two_u4s(x, y)
                unpacked = unpack_two_u4s(packed)
                self.assertEqual(x, unpacked[0])
                self.assertEqual(y, unpacked[1])