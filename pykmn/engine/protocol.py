"""Code to handle libpkmn binary protocol."""
from typing import List, Dict
from enum import IntEnum
from pykmn.data.gen1 import LIBPKMN_MOVE_IDS, LIBPKMN_SPECIES_IDS
from pykmn.engine.gen1 import Status

moveid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_MOVE_IDS.items()}
speciesid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_SPECIES_IDS.items()}


# see https://github.com/pkmn/engine/blob/main/docs/PROTOCOL.md
class MessageType(IntEnum):
    """The type of a message."""

    TERMINATOR = 0x00
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

def status_to_human(status: int) -> str:
    """Parse a status identifier.

    Args:
        status (int): the StatusIdent byte

    Returns:
        str: the human-readable identifier
    """
    # code is from @pkmn/engine
    # https://github.com/pkmn/engine/blob/main/src/pkg/protocol.ts#L436-L446
    if status & 0b111:
        return 'asleep'
    if (status >> 3) & 1:
        return 'poisoned'
    if (status >> 4) & 1:
        return 'burned'
    if (status >> 5) & 1:
        return 'frozen'
    if (status >> 6) & 1:
        return 'paralyzed'
    if (status >> 7) & 1:
        return 'badly poisoned'
    return 'healthy'


def binary_to_human(binary_protocol: List[int]) -> List[str]:
    """Convert libpkmn binary protocol to human-readable messages.

    Args:
        binary_protocol (List[int]): An array of byte-length integers of libpkmn protocol.

    Returns:
        List[str]: An array of human-readable messages.
    """
    bytes_iterator = iter(binary_protocol)
    messages: List[str] = []
    while True:
        try:
            msg_type = next(bytes_iterator)
        except StopIteration:
            return messages

        if msg_type == MessageType.TERMINATOR:
            return messages

        elif msg_type == MessageType.MOVE:
            source = ident_to_human(next(bytes_iterator))
            move = move_to_human(next(bytes_iterator))
            target = ident_to_human(next(bytes_iterator))
            msg = f"{source} used {move} on {target}"
            reason = next(bytes_iterator)
            if reason == 0x02:
                msg += f"(from {move_to_human(next(bytes_iterator))})"
            messages.append(msg + ".")

        elif msg_type == MessageType.SWITCH:
            position = ident_to_human(next(bytes_iterator))
            species = speciesid_to_name_map[next(bytes_iterator)]
            level = next(bytes_iterator)
            current_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            max_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            status = status_to_human(next(bytes_iterator))

            messages.append(
                f"A {status} level {level} {species} with {current_hp}/{max_hp} HP" +
                f" switched in for {position}."
            )

        elif msg_type == MessageType.CANNOT:
            pokemon = ident_to_human(next(bytes_iterator))
            reason = next(bytes_iterator)
            message = f"{pokemon}"
            if reason == 0x00:
                message += " is fast asleep."
            elif reason == 0x01:
                message += " is frozen solid."
            elif reason == 0x02:
                message += " is fully paralyzed."
            elif reason == 0x03:
                message += " is trapped."
            elif reason == 0x04:
                message += " flinched and couldn't move."
            elif reason == 0x05:
                move = move_to_human(next(bytes_iterator))
                message += f"'s move {move} is disabled."
            elif reason == 0x06:
                message += " must recharge."
            elif reason == 0x07:
                message += "'s move is out of PP."
            else:
                message += f" couldn't move due to reason code 0x{reason:0>2X}"
            messages.append(message)

        elif msg_type == MessageType.FAINT:
            target = ident_to_human(next(bytes_iterator))
            messages.append(f"{target} fainted.")

        elif msg_type == MessageType.TURN:
            turn = next(bytes_iterator) + (next(bytes_iterator) << 8)
            messages.append(f"It is now turn {turn}.")

        elif msg_type == MessageType.WIN:
            player = next(bytes_iterator)
            messages.append(f"Player {player + 1} won the battle!")

        elif msg_type == MessageType.TIE:
            messages.append("The battle ended in a tie!")

        elif msg_type == MessageType.DAMAGE:
            target = ident_to_human(next(bytes_iterator))

            # hp is a 16-bit uint
            current_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            max_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            status = status_to_human(next(bytes_iterator))

            if next(bytes_iterator) == 0x04:
                source = f" from {ident_to_human(next(bytes_iterator))}"
            else:
                source = ""
            messages.append(
                f"Damage dealt to {target}{source}, which now has {current_hp} HP" +
                f" out of {max_hp} HP and is {status}."
            )
            # TODO: handle Reason
            # TODO: add tests

        elif msg_type == MessageType.SUPEREFFECTIVE:
            target = ident_to_human(next(bytes_iterator))
            messages.append(f"Super-effective hit on {target}!")
        else:
            messages.append("Unknown message type encountered: {}".format(msg_type))
            return messages
