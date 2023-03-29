"""`pykmn.engine.common` contains common types and functions used by the PyKMN engine.

Most of the contents of this submodule aren't things you'll need to construct/call yourself,
but `Result` and `Choice` both include important methods
for when you get them from a `pykmn.engine.gen1.Battle` object.
"""
from enum import Enum, IntEnum
from typing import Union, Tuple, NewType, List
from pykmn.engine.libpkmn import libpkmn_showdown_trace, LibpkmnBinding

# This file needs some testing, but I think it makes sense to test it
# along with the battle simulation tests.


Slots = NewType('Slots', Tuple[List[str], List[str]])
r"""
The Slots type is used to store Pokémon names.
You can pass it into `pykmn.engine.protocol.parse_protocol` to make protocol messages include
Pokémon names instead of just "Pokémon #n".

Here's an example:
```python
from pykmn.engine.protocol import parse_protocol
from pykmn.engine.common import Slots

slots = Slots((
    # Player 1's Pokémon
    ["Charmander", "Pikachu", "Bulbasaur", "Squirtle", "Caterpie", "Weedle"],
    # Player 2's Pokémon
    ["Mewtwo", "Charizard", "Articuno", "Dragonite", "Mew", "Starmie"],
))

# assuming `trace` has already been populated by a call to Battle.update()
protocol = parse_protocol(trace, slots)
print("\n".join(protocol))
```

Check out the
[`sample_teams` code](https://github.com/AnnikaCodes/PyKMN/blob/main/examples/sample_teams.py)
for another example of how to use `Slots`.
"""

class ChoiceType(Enum):
    """An enum representing the types of choice players can make in a Pokémon battle.

    `ChoiceType` is a Python version of libpkmn's `pkmn_choice_kind`.
    It's returned from `Result.p1_choice_type` and `Result.p2_choice_type`, as well as
    `Choice.type`.
    """

    PASS = 0
    MOVE = 1
    SWITCH = 2

class ResultType(IntEnum):
    """An enum representing the result of a move in a Pokémon battle.

    This is returned by `Result.type`, and can be used to check if a battle has ended
    (at which point you need to stop calling `pykmn.engine.gen1.Battle.update`!)
    and who, if any, has won.
    """

    NONE = 0
    PLAYER_1_WIN = 1
    PLAYER_2_WIN = 2
    TIE = 3
    ERROR = 4

class Player(IntEnum):
    """An enum representing the players in a Pokémon battle.

    This is the Python version of libpkmn's `pkmn_player`.
    """

    P1 = 0
    """Player 1."""
    P2 = 1
    """Player 2."""



class Result:
    """Represents the result of updating a Pokémon battle.

    `Result` is the Python version of pkmn_result.
    Consumers of the PyKMN library should never need to construct this class themselves;
    you can get `Result`s from `pykmn.engine.gen1.Battle.update`.
    """


    def __init__(
        self,
        _pkmn_result: int,
        _libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """You don't need to use this!"""
        self._pkmn_result = _pkmn_result
        self._libpkmn = _libpkmn

    def type(self) -> ResultType:
        """Get the type of result this is.

        If it's `ResultType.NONE`,
        the battle is still going on and you can keep calling `pykmn.engine.gen1.Battle.update`.
        Otherwise, the `ResultType` value tells how the battle ended.

        Returns:
            **`ResultType`**: The type of result this is.
        """
        return self._libpkmn.lib.pkmn_result_type(self._pkmn_result)

    def p1_choice_type(self) -> ChoiceType:
        """Get the type of choice Player 1 made.

        This is a Python version of libpkmn's `pkmn_result_p1`.

        Returns:
            **`ChoiceType`**: The type of choice Player 1 made.
        """
        return ChoiceType(self._libpkmn.lib.pkmn_result_p1(self._pkmn_result))

    def p2_choice_type(self) -> ChoiceType:
        """Get the type of choice the Player 2 made.

        This is a Python version of libpkmn's `pkmn_result_p2`.

        Returns:
            **`ChoiceType`**: The type of choice Player 2 made.
        """
        return ChoiceType(self._libpkmn.lib.pkmn_result_p2(self._pkmn_result))

    def is_error(self) -> bool:
        """Check if this result represents an error.

        Errors are already checked for in `pykmn.engine.gen1.Battle.update`
        (which throws an error if one is encountered), so you shouldn't need to use this.
        This is a Python version of libpkmn's `pkmn_error`.

        Returns:
            **`bool`**: `True` if this `Result` represents an error, and `False` otherwise.
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

    Consumers of the PyKMN library should NEVER construct this class themselves, but instead
    use the `pykmn.engine.gen1.Battle.possible_choices` method to get a list of valid `Choice`s,
    or construct the initial choice with `Choice.PASS`.

    **If you construct this class yourself, it may be invalid and cause crashes or wrong behavior
    from libpkmn!**
    """

    def __init__(
        self,
        _pkmn_choice: int,
        _libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """You don't need to use this!"""
        self._pkmn_choice = _pkmn_choice  # uint8_t
        self._libpkmn = _libpkmn

    @staticmethod
    def PASS() -> "Choice":
        r"""Construct a `Choice` that represents a player doing nothing.

        Most commonly used at the start of a battle to simulate both players sending out their
        first Pokémon:

        ```python
        from pykmn.engine import common, gen1, protocol

        battle = gen1.Battle(...)
        (result, trace) = battle.update(common.Choice.PASS(), common.Choice.PASS())

        print("\n".join(protocol.parse_protocol(trace)))
        # |switch|p1a: Pokémon #1|...
        # |switch|p2a: Pokémon #1|...
        # |turn|1
        ```

        Returns:
            **`Choice`**: A `Choice` that represents a player doing nothing.
        """
        return Choice(0)

    def type(self) -> ChoiceType:
        """Get the type of the choice (move, switch, or pass).

        Returns:
            **`ChoiceType`**: The type of the choice.
        """
        return ChoiceType(self._libpkmn.lib.pkmn_choice_type(self._pkmn_choice))

    def data(self) -> Union[int, None]:
        """Get the data associated with the choice.

        Returns:
            **`int` | `None`**: slot number for a switch,
            move index for a move, and `None` for a pass.
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


def pack_u16_as_bytes(n: int) -> Tuple[int, int]:
    """Pack an unsigned 16-bit integer into a pair of bytes.

    Args:
        n (`int`): The unsigned 16-bit integer to pack.

    Returns:
        **`Tuple[int, int]`**: The pair of bytes.
    """
    return (n & 0xFF, (n >> 8))

def unpack_u16_from_bytes(a: int, b: int) -> int:
    """Unpack a pair of bytes into an unsigned 16-bit integer.

    Args:
        a (`int`): The first byte.
        b (`int`): The second byte.

    Returns:
        **`int`**: The unsigned 16-bit integer.
    """
    return (b << 8) | a

def pack_two_u4s(a: int, b: int) -> int:
    """Pack two unsigned 4-bit integers into a single byte.

    Args:
        a (`int`): The first unsigned 4-bit integer to pack.
        b (`int`): The second unsigned 4-bit integer to pack.

    Returns:
        **`int`**: The single byte.
    """
    return (a & 0x0F) | ((b & 0x0F) << 4)

def unpack_two_u4s(n: int) -> Tuple[int, int]:
    """Unpack a single byte into two unsigned 4-bit integers.

    Args:
        n (`int`): The single byte.

    Returns:
        **`Tuple[int, int]`**: The two unsigned 4-bit integers.
    """
    return (n & 0x0F, (n >> 4) & 0x0F)



def pack_two_i4s(a: int, b: int) -> int:
    """Pack two signed 4-bit integers into a single byte.

    Args:
        a (`int`): The first signed 4-bit integer to pack.
        b (`int`): The second signed 4-bit integer to pack.

    Returns:
        **`int`**: The single byte.
    """
    return pack_two_u4s(a & 0x0F, b & 0x0F)

def unpack_two_i4s(n: int) -> Tuple[int, int]:
    """Unpack a single byte into two signed 4-bit integers.

    Args:
        n (`int`): The single byte.

    Returns:
        **`Tuple[int, int]`**: The two signed 4-bit integers.
    """
    a, b = unpack_two_u4s(n)
    return (a if a < 8 else a - 16, b if b < 8 else b - 16)

def insert_unsigned_int_at_offset(byte: int, n: int, length: int, offset: int) -> int:
    """Insert an unsigned integer into a byte.

    Args:
        byte (`int`): The byte to insert into.
        n (`int`): The unsigned integer to insert.
        length (`int`): The number of bits in the unsigned integer.
        offset (`int`): The offset at which to insert the unsigned integer.

    Returns:
        **`int`**: The byte with the unsigned integer inserted.
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
        byte (`int`): The byte to extract from.
        length (`int`): The number of bits in the unsigned integer.
        offset (`int`): The offset in bits at which to extract the unsigned integer.

    Returns:
        **`int`**: The unsigned integer extracted from the byte.
    """
    return (byte >> offset) & ((1 << length) - 1)
