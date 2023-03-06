"""Code to handle libpkmn binary protocol."""
from typing import List, Dict
from pykmn.data.gen1 import LIBPKMN_MOVE_IDS, LIBPKMN_SPECIES_IDS
from pykmn.data.protocol import MESSAGES, REASON_LOOKUP

moveid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_MOVE_IDS.items()}
speciesid_to_name_map: Dict[int, str] = {id: name for name, id in LIBPKMN_SPECIES_IDS.items()}


def parse_identifier(ident: int, slots: List[str]) -> str:
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
    slot = ident & 0x07
    msg = f"p{player}{position}: {slots[slot - 1]}"
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
        return 'slp'
    if (status >> 3) & 1:
        return 'psn'
    if (status >> 4) & 1:
        return 'brn'
    if (status >> 5) & 1:
        return 'frz'
    if (status >> 6) & 1:
        return 'par'
    if (status >> 7) & 1:
        return 'tox'
    return ''


def parse_protocol(
    binary_protocol: List[int],
    # https://github.com/python/mypy/issues/5068#issuecomment-389882867
    slots: List[str] = [f"Pokémon #{n}" for n in range(1, 7)]  # type: ignore
) -> List[str]:
    """Convert libpkmn binary protocol to Pokémon Showdown protocol messages.

    Args:
        binary_protocol (List[int]): An array of byte-length integers of libpkmn protocol.
        slots (List[str], optional): An array of Pokémon names in each slot.

    Returns:
        List[str]: An array of PS protocol messages.
    """
    assert len(slots) == 6, "Must pass in 6 Pokémon names."
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
            source = parse_identifier(next(bytes_iterator), slots)
            move = parse_move(next(bytes_iterator))
            target = parse_identifier(next(bytes_iterator), slots)
            msg = f"|move|{source}|{move}|{target}"
            reason = REASON_LOOKUP[msg_type][next(bytes_iterator)]
            if reason == "From":
                msg += f"|[from] {parse_move(next(bytes_iterator))}"
            messages.append(msg)

        elif msg_type == "Switch" or msg_type == "Drag":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            species = speciesid_to_name_map[next(bytes_iterator)]
            level = next(bytes_iterator)
            current_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            max_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            status = parse_status(next(bytes_iterator))

            messages.append(
                f"|{msg_type.lower()}|{pokemon}|{species}, L{level}|" +
                f"{current_hp}/{max_hp}{' ' + status if status else ''}"
            )

        elif msg_type == "Cant":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            reason = REASON_LOOKUP[msg_type][next(bytes_iterator)]
            message = f"|cant|{pokemon}"
            if reason == "Sleep":
                message += "|slp"
            elif reason == "Freeze":
                message += "|frz"
            elif reason == "Paralysis":
                message += "|par"
            elif reason == "Bound":
                message += "|partiallytrapped"
            elif reason == "Flinch":
                message += "|flinch"
            elif reason == "Disable":
                move = parse_move(next(bytes_iterator))
                message += f"|Disable|{move}"
            elif reason == "Recharge":
                message += "|recharge"
            elif reason == "PP":
                message += "|nopp"
            else:
                message += f"|{reason}"
            messages.append(message)

        elif msg_type == "Faint":
            target = parse_identifier(next(bytes_iterator), slots)
            messages.append(f"|faint|{target}")

        elif msg_type == "Turn":
            turn = next(bytes_iterator) + (next(bytes_iterator) << 8)
            messages.append(f"|turn|{turn}")

        elif msg_type == "Win":
            player = next(bytes_iterator)
            messages.append(f"|win|p{player + 1}")

        elif msg_type == "Tie":
            messages.append("|tie")

        elif msg_type == "Damage" or msg_type == "Heal":
            target = parse_identifier(next(bytes_iterator), slots)

            # hp is a 16-bit uint
            current_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            max_hp = next(bytes_iterator) + (next(bytes_iterator) << 8)
            status = parse_status(next(bytes_iterator))
            msg = (
                f"|-{msg_type.lower()}|{target}|{current_hp}/{max_hp}" +
                f"{' ' + status if status else ''}"
            )
            reason = REASON_LOOKUP[msg_type][next(bytes_iterator)]
            if reason == "None":
                pass
            elif reason == "Poison":
                msg += "|[from] psn"
            elif reason == "Burn":
                msg += "|[from] brn"
            elif reason == "Confusion":
                msg += "|[from] confusion"
            elif reason == "LeechSeed":
                msg += "|[from] leechseed"
            elif reason == "RecoilOf":
                recoil_of = parse_identifier(next(bytes_iterator), slots)
                msg += f"|[from] recoil|[of] {recoil_of}"
            elif reason == "Silent":
                msg += "|[silent]"
            elif reason == "Drain":
                drain_of = parse_identifier(next(bytes_iterator), slots)
                msg += f"|[from] drain|[of] {drain_of}"
            else:
                msg += f"|[from] {reason}"

            messages.append(msg)
            # TODO: handle Reason
            # TODO: add tests

        elif msg_type == "SuperEffective":
            target = parse_identifier(next(bytes_iterator), slots)
            messages.append(f"|-supereffective|{target}")
        else:
            messages.append("Unknown message type encountered: {}".format(msg_type))
            return messages
