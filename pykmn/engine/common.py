"""This file includes common functionality like bindings for pkmn_result."""
from enum import Enum, IntEnum
from typing import Union
from pykmn.engine.libpkmn import libpkmn_showdown_trace, LibpkmnBinding

# This file needs some testing, but I think it makes sense to test it
# along with the battle simulation tests.


class ChoiceType(Enum):
    """An enum representing the types of choice players can make in a Pokémon battle.

    Python version of pkmn_choice_kind.
    """

    PASS = 0
    MOVE = 1
    SWITCH = 2


class ResultType(IntEnum):
    """An enum representing the result of a move in a Pokémon battle.

    Python version of pkmn_result_kind.
    """

    NONE = 0
    PLAYER_1_WIN = 1
    PLAYER_2_WIN = 2
    TIE = 3
    ERROR = 4


class Player(IntEnum):
    """An enum representing the players in a Pokémon battle.

    Python version of pkmn_player.
    """

    P1 = 0
    P2 = 1


class Result:
    """Represents the result of updating a Pokémon battle.

    Python version of pkmn_result.

    Consumers of the PyKMN library shouldn't need to construct this class themselves.
    """

    def __init__(
        self,
        _pkmn_result: int,
        _libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """Create a new Result object. You shouldn't need to do this.

        Args:
            _pkmn_result (int): The value of the C pkmn_result type.
        """
        self._pkmn_result = _pkmn_result
        self._libpkmn = _libpkmn

    def type(self) -> ResultType:
        """Get the type of result.

        Python version of pkmn_result_type.
        """
        return self._libpkmn.lib.pkmn_result_type(self._pkmn_result)

    def p1_choice_type(self) -> ChoiceType:
        """Get the type of choice the first player made.

        Python version of pkmn_result_p1.
        """
        return ChoiceType(self._libpkmn.lib.pkmn_result_p1(self._pkmn_result))

    def p2_choice_type(self) -> ChoiceType:
        """Get the type of choice the second player made.

        Python version of pkmn_result_p2.
        """
        return ChoiceType(self._libpkmn.lib.pkmn_result_p2(self._pkmn_result))

    def is_error(self) -> bool:
        """Check if the result is an error.

        Python version of pkmn_error.
        """
        return self._libpkmn.lib.pkmn_error(self._pkmn_result)

    def __repr__(self) -> str:
        """Provide a string representation of the Result."""
        return (
            f"Result(type: {self.type()}, player 1 choice: {self.p1_choice_type()}, "
            f"player 2 choice: {self.p2_choice_type()})"
        )


class Choice:
    """Represents a choice a player makes in a Pokémon battle.

    Python version of pkmn_choice.

    Consumers of the PyKMN library should not construct this class themselves, but instead
    use the `possible_choices` method of the Battle class for the generation they are simulating.
    """

    def __init__(
        self,
        _pkmn_choice: int,
        _libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """DON'T CALL THIS CONSTRUCTOR.

        If you pass an invalid choice to libpkmn, it may behave unpredictably or cause errors.

        Use the `possible_choices` method of the Battle class to get Choice objects.
        """
        self._pkmn_choice = _pkmn_choice  # uint8_t
        self._libpkmn = _libpkmn

    @staticmethod
    def PASS() -> "Choice":
        """Create a PASS choice."""
        return Choice(0)

    def type(self) -> ChoiceType:
        """Get the type of the choice (pass/move/switch).

        Python version of pkmn_choice_type.
        """
        return ChoiceType(self._libpkmn.lib.pkmn_choice_type(self._pkmn_choice))

    def data(self) -> Union[int, None]:
        """Get the data associated with the choice.

        Returns:
            int | None: slot number for a switch or move index for a move
        """
        if self.type() == ChoiceType.PASS:
            return None
        return self._libpkmn.lib.pkmn_choice_data(self._pkmn_choice)

    def __repr__(self) -> str:
        """Provide a string representation of the Choice."""
        type = self.type()
        if type == ChoiceType.MOVE:
            data = self.data()
            if data == 0:
                return "Choice(can't select a move)"
            return f"Choice(move #{self.data()})"
        elif type == ChoiceType.SWITCH:
            return f"Choice(switch to slot #{self.data()})"
        else:
            return "Choice(pass)"


class Softlock(Exception):
    """This exception may be raised when a battle has softlocked."""

    pass


def pack_u16_as_bytes(n: int) -> tuple[int, int]:
    """Pack an unsigned 16-bit integer into a pair of bytes.

    Args:
        n (int): The unsigned 16-bit integer to pack.

    Returns:
        Tuple[int, int]: The pair of bytes.
    """
    return (n & 0xFF, (n >> 8))

def unpack_u16_from_bytes(a: int, b: int) -> int:
    """Unpack a pair of bytes into an unsigned 16-bit integer.

    Args:
        a (int): The first byte.
        b (int): The second byte.

    Returns:
        int: The unsigned 16-bit integer.
    """
    return (b << 8) | a

def pack_two_u4s(a: int, b: int) -> int:
    """Pack two unsigned 4-bit integers into a single byte.

    Args:
        a (int): The first unsigned 4-bit integer to pack.
        b (int): The second unsigned 4-bit integer to pack.

    Returns:
        int: The single byte.
    """
    return (a & 0x0F) | ((b & 0x0F) << 4)

def unpack_two_u4s(n: int) -> tuple[int, int]:
    """Unpack a single byte into two unsigned 4-bit integers.

    Args:
        n (int): The single byte.

    Returns:
        Tuple[int, int]: The two unsigned 4-bit integers.
    """
    return (n & 0x0F, (n >> 4) & 0x0F)



def pack_two_i4s(a: int, b: int) -> int:
    """Pack two signed 4-bit integers into a single byte.

    Args:
        a (int): The first signed 4-bit integer to pack.
        b (int): The second signed 4-bit integer to pack.

    Returns:
        int: The single byte.
    """
    return pack_two_u4s(a & 0x0F, b & 0x0F)

def unpack_two_i4s(n: int) -> tuple[int, int]:
    """Unpack a single byte into two signed 4-bit integers.

    Args:
        n (int): The single byte.

    Returns:
        Tuple[int, int]: The two signed 4-bit integers.
    """
    a, b = unpack_two_u4s(n)
    return (a if a < 8 else a - 16, b if b < 8 else b - 16)

def insert_unsigned_int_at_offset(byte: int, n: int, length: int, offset: int) -> int:
    """Insert an unsigned integer into a byte.

    Args:
        byte (int): The byte to insert into.
        n (int): The unsigned integer to insert.
        length (int): The number of bits in the unsigned integer.
        offset (int): The offset at which to insert the unsigned integer.

    Returns:
        int: The byte with the unsigned integer inserted.
    """
    # zero the n bits at the offset
    mask = (1 << length) - 1
    byte &= ~(mask << offset)
    # insert the n bits at the offset
    byte |= (n & mask) << offset
    return byte

def extract_unsigned_int_at_offset(byte: int, length: int, offset: int) -> int:
    """Extract an unsigned integer from a byte.

    Args:
        byte (int): The byte to extract from.
        length (int): The number of bits in the unsigned integer.
        offset (int): The offset in bits at which to extract the unsigned integer.

    Returns:
        int: The unsigned integer extracted from the byte.
    """
    return (byte >> offset) & ((1 << length) - 1)
