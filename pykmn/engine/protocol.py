"""Code to handle libpkmn binary protocol."""
from typing import List, Dict
from enum import IntEnum
from pykmn.data.gen1 import LIBPKMN_MOVE_IDS

moveid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_MOVE_IDS.items()}


# see https://github.com/pkmn/engine/blob/main/docs/PROTOCOL.md
class MessageType(IntEnum):
    """The type of a message."""

    MOVE = 0x03
    SWITCH = 0x04
    CANNOT = 0x05
    FAINT = 0x06
    TURN = 0x07
    WIN = 0x08
    TIE = 0x09
    DAMAGE = 0x0A
    HEAL = 0x0B
    STATUS = 0x0C
    CURE_STATUS = 0x0D
    BOOST = 0x0E
    CLEAR_ALL_BOOSTS = 0x0F
    FAIL = 0x10
    MISS = 0x11
    HIT_COUNT = 0x12
    PREPARE = 0x13
    MUST_RECHARGE = 0x14
    ACTIVATE = 0x15
    FIELD_ACTIVATE = 0x16
    START = 0x17
    END = 0x18
    OHKO = 0x19
    CRIT = 0x1A
    SUPEREFFECTIVE = 0x1B
    RESISTED = 0x1C
    IMMUNE = 0x1D
    TRANSFORM = 0x1E


def ident_to_human(ident: int, include_position=False) -> str:
    """Parse a Pokémon identifier.

    Args:
        ident (int): the PokemonIdent byte

    Returns:
        str: the human-readable identifier
    """
    # 5th most significant bit is the player number
    player = '2' if ((ident >> 3) & 1) == 1 else '1'
    # lowest 3 bits are the slot number
    slot = str(ident & 0x07)
    msg = f"Player {player}'s Pokémon in slot {slot}"
    if include_position:
        # 4th most significant bit is the position
        position = 'b' if ((ident >> 4) & 1) == 1 else 'a'
        msg += f", position {position}"
    return msg


def move_to_human(moveid: int) -> str:
    """Parse a move identifier.

    Args:
        move (int): the MoveIdent byte

    Returns:
        str: the human-readable identifier
    """
    return moveid_to_name_map[moveid]


def binary_to_human(binary_protocol: List[int]) -> List[str]:
    """Convert libpkmn binary protocol to human-readable messages.

    Args:
        binary_protocol (List[int]): An array of byte-length integers of libpkmn protocol.

    Returns:
        List[str]: An array of human-readable messages.
    """
    bytes_iterator = iter(binary_protocol)
    messages = []
    while True:
        try:
            msg_type = next(bytes_iterator)
        except StopIteration:
            break
        if msg_type == MessageType.MOVE:
            source = ident_to_human(next(bytes_iterator))
            move = move_to_human(next(bytes_iterator))
            target = ident_to_human(next(bytes_iterator))
            msg = f"{source} used {move} on {target}"
            reason = next(bytes_iterator)
            if reason == 0x02:
                msg += f"(from {move_to_human(next(bytes_iterator))})"
            messages.append(msg + ".")
        else:
            raise ValueError("Unknown message type: {}".format(msg_type))
    return messages
