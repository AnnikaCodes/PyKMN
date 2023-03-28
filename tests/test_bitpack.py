"""Tests for bit-packing methods."""
from pykmn.engine.common import unpack_u16_from_bytes, pack_u16_as_bytes, \
    pack_two_u4s, unpack_two_u4s, pack_two_i4s, unpack_two_i4s
import unittest

class TestBitpack(unittest.TestCase):
    """Tests bit-packing methods."""

    def test_u16(self) -> None:
        """Test packing and unpacking u16s."""
        for x in range(2**16):
            packed = pack_u16_as_bytes(x)
            self.assertEqual(x, unpack_u16_from_bytes(packed[0], packed[1]))

    def test_u4(self) -> None:
        """Test packing and unpacking u4s."""
        for x in range(2**4):
            for y in range(2**4):
                packed = pack_two_u4s(x, y)
                unpacked = unpack_two_u4s(packed)
                self.assertEqual(x, unpacked[0])
                self.assertEqual(y, unpacked[1])

    def test_i4(self) -> None:
        """Test packing and unpacking i4s."""
        for x in range(-2**3, 2**3):
            for y in range(-2**3, 2**3):
                packed = pack_two_i4s(x, y)
                unpacked = unpack_two_i4s(packed)
                self.assertEqual(x, unpacked[0])
                self.assertEqual(y, unpacked[1])
