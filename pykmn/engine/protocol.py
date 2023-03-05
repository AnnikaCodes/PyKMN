"""Code to handle libpkmn binary protocol."""
from typing import List, Dict
from pykmn.data.gen1 import LIBPKMN_MOVE_IDS, LIBPKMN_SPECIES_IDS
from pykmn.data.protocol import MESSAGES, REASON_LOOKUP

moveid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_MOVE_IDS.items()}
speciesid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_SPECIES_IDS.items()}


def parse_identifier(ident: int) -> str:
    """Parse a Pokémon identifier.

    Args:
        ident (int): the PokemonIdent byte

    Returns:
        str: the identifier
    """
    position = 'b' if ((ident >> 4) & 1) == 1 else 'a'
    # 5th most significant bit is the player number
    player = '2' if ((ident >> 3) & 1) == 1 else '1'
    # lowest 3 bits are the slot number
    slot = str(ident & 0x07)
    msg = f"p{player}{position}: Pokémon #{slot}"  # TODO: support passing in a slot<->name map
    return msg


def parse_move(moveid: int) -> str:
    """Parse a move identifier.

    Args:
        move (int): the MoveIdent byte

    Returns:
        str: the identifier
    """
    return moveid_to_name_map[moveid]


def parse_status(status: int) -> str:
    """Parse a status identifier.

    Args:
        status (int): the StatusIdent byte

    Returns:
        str: the identifier
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


def parse_protocol(binary_protocol: List[int]) -> List[str]:
    """Convert libpkmn binary protocol to Pokémon Showdown protocol messages.

    Args:
        binary_protocol (List[int]): An array of byte-length integers of libpkmn protocol.

    Returns:
        List[str]: An array of PS protocol messages.
    """
    bytes_iterator = iter(binary_protocol)
    messages: List[str] = []
    while True:
        try:
            msg_type_byte = next(bytes_iterator)
        except StopIteration:
            return messages

        msg_type = MESSAGES[msg_type_byte]

        if msg_type == "None":
            return messages

        elif msg_type == "Move":
            source = parse_identifier(next(bytes_iterator))
            move = parse_move(next(bytes_iterator))
            target = parse_identifier(next(bytes_iterator))
            msg = f"|move|{source}|{move}|{target}"
            reason = REASON_LOOKUP[msg_type][next(bytes_iterator)]
            if reason == "From":
                msg += f"|from|{parse_move(next(bytes_iterator))})"
            messages.append(msg)

        elif msg_type == "Switch" or msg_type == "Drag":
            pokemon = parse_identifier(next(bytes_iterator))
            species = speciesid_to_name_map[next(bytes_iterator)]
            level = next(bytes_iterator)
            current_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            max_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            status = parse_status(next(bytes_iterator))

            messages.append(
                f"|{msg_type.lower()}|{pokemon}|{species}, L{level}|{current_hp}/{max_hp} {status}"
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
