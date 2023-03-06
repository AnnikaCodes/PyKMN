"""Code to handle libpkmn binary protocol."""
from typing import List, Dict, Tuple
from pykmn.data.gen1 import MOVE_IDS, SPECIES_IDS, TYPES
from pykmn.data.protocol import MESSAGES, REASONS

moveid_to_name_map: Dict[int, str] = {id: name for name, id in MOVE_IDS.items()}
speciesid_to_name_map: Dict[int, str] = {id: name for name, id in SPECIES_IDS.items()}


def parse_identifier(ident: int, slots: Tuple[List[str], List[str]]) -> str:
    """Parse a Pokémon identifier.

    Args:
        ident (int): the PokemonIdent byte

    Returns:
        str: the identifier
    """
    position = 'b' if ((ident >> 4) & 1) == 1 else 'a'
    # 5th most significant bit is the player number
    player = (ident >> 3) & 1
    # lowest 3 bits are the slot number
    slot = ident & 0x07
    msg = f"p{player + 1}{position}: {slots[player][slot - 1]}"
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
    slots: Tuple[List[str], List[str]] = ([f"Pokémon #{n}" for n in range(1, 7)],)*2  # type: ignore
) -> List[str]:
    """Convert libpkmn binary protocol to Pokémon Showdown protocol messages.

    Args:
        binary_protocol (List[int]): An array of byte-length integers of libpkmn protocol.
        slots (Tuple[List[str], List[str]]): A list of Pokémon names in each slot for sides 1 and 2

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

        elif msg_type == "LastStill" or msg_type == "LastMiss":
            to_append = f"|[{msg_type[4:].lower()}]"
            idx = len(messages) - 1
            while idx >= 0:
                if messages[idx].startswith("|move|"):
                    messages[idx] += to_append
                    break
                idx -= 1
            if idx == -1:
                raise Exception(f"{msg_type} byte without a previous |move| to append to")

        elif msg_type == "Move":
            source = parse_identifier(next(bytes_iterator), slots)
            move = parse_move(next(bytes_iterator))
            target = parse_identifier(next(bytes_iterator), slots)
            msg = f"|move|{source}|{move}|{target}"
            reason = REASONS[msg_type][next(bytes_iterator)]
            if reason == "None":
                pass
            elif reason == "From":
                msg += f"|[from] {parse_move(next(bytes_iterator))}"
            else:
                msg += f"|{reason}"
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
            reason = REASONS[msg_type][next(bytes_iterator)]
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
            reason = REASONS[msg_type][next(bytes_iterator)]
            if reason == "None":
                pass
            # is this actually how things are on PS? or should it be |psn?
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

        elif msg_type == "Status" or msg_type == "CureStatus":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            status = parse_status(next(bytes_iterator))
            reason = REASONS[msg_type][next(bytes_iterator)]
            msg = f"|-{msg_type.lower()}|{pokemon}|{status}"

            if reason == "None":
                pass
            elif reason == "Silent":
                msg += "|[silent]"
            elif reason == "From":
                msg += f"|[from] {parse_move(next(bytes_iterator))}"
            elif reason == "Message":
                msg += "|[msg]"
            else:
                msg += f"|{reason}"

            messages.append(msg)

        elif msg_type == "ClearAllBoost":
            messages.append("|-clearallboost")

        elif msg_type == "Fail":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            reason = REASONS[msg_type][next(bytes_iterator)]
            msg = f"|-fail|{pokemon}"
            if reason == "None":
                pass
            elif reason == "Sleep":
                msg += "|slp"
            elif reason == "Poison":
                msg += "|psn"
            elif reason == "Burn":
                msg += "|brn"
            elif reason == "Freeze":
                msg += "|frz"
            elif reason == "Paralysis":
                msg += "|par"
            elif reason == "Toxic":
                msg += "|tox"
            elif reason == "Substitute":
                msg += "|move: Substitute"
            elif reason == "Weak":
                msg += "|move: Substitute|[weak]"
            else:
                msg += f"|{reason}"
            messages.append(msg)

        elif msg_type in ["Miss", "MustRecharge", "SuperEffective", "Crit", "Resisted"]:
            pokemon = parse_identifier(next(bytes_iterator), slots)
            messages.append(f"|-{msg_type.lower()}|{pokemon}")

        elif msg_type == "HitCount":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            count = next(bytes_iterator)
            messages.append(f"|-hitcount|{pokemon}|{count}")

        elif msg_type == "Prepare":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            move = parse_move(next(bytes_iterator))
            messages.append(f"|-prepare|{pokemon}|{move}")

        elif msg_type == "Activate":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            msg = f"|-activate|{pokemon}"
            reason = REASONS[msg_type][next(bytes_iterator)]
            if reason == "Bide":
                msg += "|Bide"
            elif reason == "Confusion":
                msg += '|confusion'
            elif reason == "Haze":
                msg += '|move: Haze'
            elif reason == "Mist":
                msg += '|move: Mist'
            elif reason == "Struggle":
                msg += '|move: Struggle'
            elif reason == "Substitute":
                msg += '|Substitute|[damage]'
            elif reason == "Splash":
                msg += '||move: Splash'
            else:
                msg += f"|{reason}"

            messages.append(msg)

        elif msg_type == "Boost":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            reason = REASONS['Boost'][next(bytes_iterator)]
            boost_amount = next(bytes_iterator) - 6
            name = 'boost' if boost_amount > 0 else 'unboost'
            message = f"|-{name}|{pokemon}"
            if reason == "Rage":
                message += "|atk|[from] Rage"
            elif reason == "Attack":
                message += "|atk"
            elif reason == "Defense":
                message += "|def"
            elif reason == "Speed":
                message += "|spe"
            elif reason == "SpecialAttack":
                message += "|spa"
            elif reason == "SpecialDefense":
                message += "|spd"
            elif reason == "Accuracy":
                message += "|accuracy"
            elif reason == "Evasion":
                message += "|evasion"
            else:
                message += f"|{reason}"
            message += f"|{abs(boost_amount)}"
            messages.append(message)

        elif msg_type == "FieldActivate" or msg_type == "OHKO":
            messages.append(f"|-{msg_type.lower()}|")

        elif msg_type == "Start":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            reason = REASONS[msg_type][next(bytes_iterator)]
            msg = f"|-start|{pokemon}"
            if reason == "Bide":
                msg += "|Bide"
            elif reason == "Confusion":
                msg += "|confusion"
            elif reason == "ConfusionSilent":
                msg += "|confusion|[silent]"
            elif reason == "FocusEnergy":
                msg += "|move: Focus Energy"
            elif reason == "LeechSeed":
                msg += "|move: Leech Seed"
            elif reason == "LightScreen":
                msg += "|Light Screen"
            elif reason == "Mist":
                msg += "|Mist"
            elif reason == "Reflect":
                msg += "|Reflect"
            elif reason == "Substitute":
                msg += "|Substitute"
            elif reason == "TypeChange":
                # types_byte has two types in each of its 4-bit halves
                types_byte = next(bytes_iterator)
                type1 = TYPES[types_byte >> 4]
                type2 = TYPES[types_byte & 0xF]
                msg += f"|typechange|{type1}/{type2}|[from] move: Conversion|[of]"
            elif reason == "Disable" or reason == "Mimic":
                move = parse_move(next(bytes_iterator))
                msg += f"|{reason}|move: {move}"
            else:
                msg += f"|{reason}"
            messages.append(msg)

        elif msg_type == "End":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            reason = REASONS[msg_type][next(bytes_iterator)]
            msg = f"|-end|{pokemon}"
            if reason == "Disable":
                msg += "|Disable"
            elif reason == "Confusion":
                msg += "|confusion"
            elif reason == "Bide":
                msg += "|move: Bide"
            elif reason == "Substitute":
                msg += "|Substitute"
            elif reason == "DisableSilent":
                msg += "|Disable|[silent]"
            elif reason == "ConfusionSilent":
                msg += "|confusion|[silent]"
            elif reason == "Mist":
                msg += "|mist|[silent]"
            elif reason == "FocusEnergy":
                msg += "|focusenergy|[silent]"
            elif reason == "LeechSeed":
                msg += "|leechseed|[silent]"
            elif reason == "Toxic":
                msg += "|Toxic counter|[silent]"
            elif reason == "LightScreen":
                msg += "|lightscreen|[silent]"
            elif reason == "Reflect":
                msg += "|reflect|[silent]"
            else:
                msg += f"|{reason}"
            messages.append(msg)

        elif msg_type == "Immune":
            pokemon = parse_identifier(next(bytes_iterator), slots)
            reason = REASONS[msg_type][next(bytes_iterator)]
            msg = f"|-immune|{pokemon}"
            if reason == "None":
                pass
            elif reason == "OHKO":
                msg += "|[ohko]"
            else:
                msg += f"|{reason}"
            messages.append(msg)

        elif msg_type == "Transform":
            source = parse_identifier(next(bytes_iterator), slots)
            target = parse_identifier(next(bytes_iterator), slots)
            messages.append(f"|-transform|{source}|{target}")

        else:
            messages.append("Unknown message type encountered: {}".format(msg_type))
            return messages
