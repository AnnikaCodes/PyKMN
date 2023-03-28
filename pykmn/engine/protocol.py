"""Code to handle libpkmn binary protocol.

This is not necessarily 100% identical to what Pokémon Showdown would produce,
but it's reasonably similar.

`parse_protocol` is the main function you'll want to use; you can feed the protocol trace from
`pykmn.engine.gen1.Battle.update` into it.

There are also functions to parse individual components of protocol, but most use cases shouldn't
need them.
"""
from pykmn.data.gen1 import MOVE_IDS, SPECIES_IDS, TYPES
from pykmn.engine.common import unpack_u16_from_bytes, Slots
from typing import Union, List, Tuple, Dict
from collections.abc import Callable
import re

moveid_to_name_map: Dict[int, str] = {id: name for name, id in MOVE_IDS.items()}
speciesid_to_name_map: Dict[int, str] = {id: name for name, id in SPECIES_IDS.items()}

MOVE_REASONS = ['', '|[from] ']
MOVE_ADDMOVE_REASON = MOVE_REASONS.index('|[from] ')

# We could make this use the indices from the protocol JSON, but it's a performance penalty:
# doing so runs at around 21 μs per cant, while this runs at around 16 μs.
CANT_REASONS = [
    '|slp', '|frz', '|par', '|partiallytrapped', '|flinch',
    '|Disable|', '|recharge', '|nopp',
]
CANT_ADDMOVE_REASON = CANT_REASONS.index('|Disable|')

DAMAGE_REASONS = [
    '', '|[from] psn', '|[from] brn', '|[from] confusion', '|[from] Leech Seed',
    '|[from] Recoil|[of] ',
]
DAMAGE_ADDPKMN_REASON = DAMAGE_REASONS.index('|[from] Recoil|[of] ')

HEAL_REASONS = ['', '|[silent]', '|[from] drain|[of] ']
HEAL_ADDPKMN_REASON = HEAL_REASONS.index('|[from] drain|[of] ')

STATUS_REASONS = ['', '|[silent]', '|[from] ']
STATUS_ADDMOVE_REASON = STATUS_REASONS.index('|[from] ')

CURESTATUS_REASONS = ['|[msg]', '|[silent]']

FAIL_REASONS = [
    '', '|slp', '|psn', '|brn', '|frz', '|par', '|tox',
    '|move: Substitute', '|move: Substitute|[weak]',
]

ACTIVATE_REASONS = [
    '|Bide', '|confusion', '|move: Haze', '|move: Mist',
    '|move: Struggle', '|Substitute|[damage]', '|move: Splash',
]
ACTIVATE_NO_POKEMON_REASON = ACTIVATE_REASONS.index('|move: Splash')
ACTIVATE_BLOCK_REASON = ACTIVATE_REASONS.index('|move: Mist')

BOOST_REASONS = [
    '|atk|[from] Rage', '|atk', '|def', '|spe', '|spa', '|spd', '|accuracy', '|evasion',
]

START_REASONS = [
    '|Bide', '|confusion', '|confusion|[silent]', '|move: Focus Energy', '|move: Leech Seed',
    '|Light Screen', '|Mist', '|Reflect', '|Substitute', '', # Typechange handled elsewhere
    '|Disable|', '|Mimic|move: ',
]
START_TYPECHANGE_REASON = START_REASONS.index('')
START_ADDMOVE_MIN_REASON = START_REASONS.index('|Disable|')

END_REASONS = [
    '|Disable', '|confusion', '|move: Bide', '|Substitute', '|Disable|[silent]',
    '|confusion|[silent]', '|Mist|[silent]', '|move: Focus Energy|[silent]',
    '|move: Leech Seed|[silent]', '|Toxic counter|[silent]', '|Light Screen|[silent]',
    '|Reflect|[silent]',
]
IMMUNE_REASONS = ['', '|[ohko]']

def parse_protocol(
    binary_protocol: List[int],
    # https://github.com/python/mypy/issues/5068#issuecomment-389882867
    slots: Slots = ([f"Pokémon #{n}" for n in range(1, 7)],)*2, # type: ignore
) -> List[str]:
    """Convert libpkmn binary protocol to Pokémon Showdown protocol messages.

    Args:
        binary_protocol (`List[int]`): An array of byte-length integers of libpkmn protocol.
        slots (`Slots`): A list of Pokémon names in each slot for sides 1 and 2

    Returns:
        **`List[str]`**: An array of PS protocol messages.
    """
    messages: List[str] = []
    i = 0
    while i < len(binary_protocol):
        msg_type_byte = binary_protocol[i]
        i += 1
        if msg_type_byte == 0:
            return messages
        handler = HANDLERS[msg_type_byte]
        res = handler(binary_protocol, i, slots, messages)
        if res is not None:
            (msg, i) = res
            messages.append(msg)
    return messages


def parse_identifier(ident: int, slots: Slots) -> str:
    """Parse a Pokémon identifier.

    Args:
        ident (`int`): the PokemonIdent byte
        slots (`Slots`): descriptions of Pokémon names

    Returns:
        **`str`**: the identifier
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
        moveid (`int`): the MoveIdent byte

    Returns:
        **`str`**: the identifier
    """
    return moveid_to_name_map[moveid]


def parse_status(status: int) -> str:
    """Parse a status identifier.

    Args:
        status (`int`): the StatusIdent byte

    Returns:
        **`str`**: the identifier
    """
    # code is from @pkmn/engine
    # https://github.com/pkmn/engine/blob/main/src/pkg/protocol.ts#L463-L471
    if status & 0b111:
        return 'slp'
    if (status >> 7) & 1:
        return 'tox'
    if (status >> 6) & 1:
        return 'par'
    if (status >> 5) & 1:
        return 'frz'
    if (status >> 4) & 1:
        return 'brn'
    if (status >> 3) & 1:
        return 'psn'
    return ''

ParseResult = Tuple[str, int]
Parser = Callable[[List[int], int, Slots, list], Union[ParseResult, None]]

def _lastx_parser(kind: str) -> Parser:
    def parser(_b: List[int], _i: int, _s: Slots, messages: List[str]) -> Union[ParseResult, None]:
        to_append = f"|[{kind.lower()}]"
        idx = len(messages) - 1
        while idx >= 0:
            if messages[idx].startswith("|move|"):
                if kind == "Still":
                    messages[idx] = re.sub(r"\|p\d[ab]: [^|]*$", to_append, messages[idx])
                else:
                    messages[idx] += to_append
                break
            idx -= 1
        if idx == -1:
            raise Exception(f"Last{kind} byte without a previous |move| to append to")
        return None
    return parser

def _move_parser(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    source = parse_identifier(binary_protocol[i], slots)
    move = parse_move(binary_protocol[i + 1])
    target = parse_identifier(binary_protocol[i + 2], slots)
    reason = binary_protocol[i + 3]
    i += 4
    msg = f"|move|{source}|{move}|{target}{MOVE_REASONS[reason]}"
    if reason == MOVE_ADDMOVE_REASON:
        msg += parse_move(binary_protocol[i])
        i += 1
    return (msg, i)

def _switch_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    species = speciesid_to_name_map[binary_protocol[i + 1]]
    level = binary_protocol[i + 2]
    current_hp = binary_protocol[i + 3] + (binary_protocol[i + 4] << 8)
    max_hp = binary_protocol[i + 5] + (binary_protocol[i + 6] << 8)
    status = parse_status(binary_protocol[i + 7])
    i += 8
    return ((
        f"|switch|{pokemon}|{species}{f', L{level}' if level != 100 else ''}|" +
        (f"{current_hp}/{max_hp}{' ' + status if status else ''}" if current_hp != 0 else "0 fnt")
    ), i)

def _cant_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    reason = binary_protocol[i + 1]
    i += 2
    message = f"|cant|{pokemon}"
    message += CANT_REASONS[reason]
    if reason == CANT_ADDMOVE_REASON:
        message += parse_move(binary_protocol[i])
        i += 1

    return (message, i)

def _turn_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    turn = unpack_u16_from_bytes(binary_protocol[i], binary_protocol[i + 1])
    return (f"|turn|{turn}", i + 2)

def _win_handler(binary_protocol: List[int], i: int, _s: Slots, _: List[str]) -> ParseResult:
    winner = binary_protocol[i]
    i += 1
    return (f"|win|p{winner + 1}", i)

def _tie_handler(_b: List[int], i: int, _s: Slots, _: List[str]) -> ParseResult:
    return ("|tie", i)

def _damage_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    target = parse_identifier(binary_protocol[i], slots)

    # hp is a 16-bit uint
    current_hp = binary_protocol[i + 1] + (binary_protocol[i + 2] << 8)
    max_hp = binary_protocol[i + 3] + (binary_protocol[i + 4] << 8)
    status = parse_status(binary_protocol[i + 5])
    msg = (
        f"|-damage|{target}|" +
        (f"{current_hp}/{max_hp}{' ' + status if status else ''}" if current_hp != 0 else "0 fnt")
    )
    reason = binary_protocol[i + 6]
    i += 7
    msg += DAMAGE_REASONS[reason]
    if reason == DAMAGE_ADDPKMN_REASON:
        msg += parse_identifier(binary_protocol[i], slots)
        i += 1
    return (msg, i)

def _heal_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    target = parse_identifier(binary_protocol[i], slots)

    # hp is a 16-bit uint
    current_hp = binary_protocol[i + 1] + (binary_protocol[i + 2] << 8)
    max_hp = binary_protocol[i + 3] + (binary_protocol[i + 4] << 8)
    status = parse_status(binary_protocol[i + 5])
    msg = (
        f"|-heal|{target}|" +
        (f"{current_hp}/{max_hp}{' ' + status if status else ''}" if current_hp != 0 else "0 fnt")
    )
    reason = binary_protocol[i + 6]
    i += 7
    msg += HEAL_REASONS[reason]
    if reason == HEAL_ADDPKMN_REASON:
        msg += parse_identifier(binary_protocol[i], slots)
        i += 1
    return (msg, i)

def _status_parser(name: str) -> Parser:
    is_status = name == "Status"
    reasons = STATUS_REASONS if is_status else CURESTATUS_REASONS
    def handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
        pokemon = parse_identifier(binary_protocol[i], slots)
        status = parse_status(binary_protocol[i + 1])
        reason = binary_protocol[i + 2]
        i += 3
        msg = f"|-{name.lower()}|{pokemon}|{status}{reasons[reason]}"
        if is_status and reason == STATUS_ADDMOVE_REASON:
            msg += f"move: {parse_move(binary_protocol[i])}"
            i += 1

        return (msg, i)
    return handler

def _returner(msg: str) -> Parser:
    def handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
        return (msg, i)
    return handler

def _boost_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    reason = binary_protocol[i + 1]
    boost_amount = binary_protocol[i + 2] - 6
    i += 3
    name = 'boost' if boost_amount > 0 else 'unboost'
    message = f"|-{name}|{pokemon}{BOOST_REASONS[reason]}|{abs(boost_amount)}"
    return (message, i)

def _fail_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    reason = binary_protocol[i + 1]
    i += 2
    return (f"|-fail|{pokemon}{FAIL_REASONS[reason]}", i)

def _generic_message_parser(name: str) -> Parser:
    def handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
        pokemon = parse_identifier(binary_protocol[i], slots)
        i += 1
        return (f"|{name}|{pokemon}", i)
    return handler

def _hitcount_handler(
    binary_protocol: List[int],
    i: int,
    slots: Slots,
    _: List[str]
) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    hit_count = binary_protocol[i + 1]
    i += 2
    return (f"|-hitcount|{pokemon}|{hit_count}", i)

def _prepare_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    move = parse_move(binary_protocol[i + 1])
    i += 2
    return (f"|-prepare|{pokemon}|{move}", i)

def _activate_handler(
    binary_protocol:
    List[int], i: int,
    slots: Slots,
    _: List[str]
) -> ParseResult:
    pokemon = '' \
        if binary_protocol[i + 1] == ACTIVATE_NO_POKEMON_REASON \
        else parse_identifier(binary_protocol[i], slots)
    protocol = 'block' if binary_protocol[i + 1] == ACTIVATE_BLOCK_REASON else \
        'activate'
    return (f"|-{protocol}|{pokemon}{ACTIVATE_REASONS[binary_protocol[i + 1]]}", i + 2)

def _start_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    reason = binary_protocol[i + 1]
    i += 2
    msg = f"|-start|{pokemon}"

    # optimization: hardcode indcies for perf gain?
    msg += START_REASONS[reason]
    if reason == START_TYPECHANGE_REASON:
        # types_byte has two types in each of its 4-bit halves
        types_byte = binary_protocol[i]
        type1 = TYPES[types_byte & 0xF]
        type2 = TYPES[types_byte >> 4]
        target = parse_identifier(binary_protocol[i + 1], slots)
        i += 2
        msg += f"|typechange|{type1}{f'/{type2}' if type1 != type2 else ''}"
        msg += f"|[from] move: Conversion|[of] {target}"
    elif reason >= START_ADDMOVE_MIN_REASON:
        msg += parse_move(binary_protocol[i])
        i += 1

    return (msg, i)


def _end_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    """Handles |-end| messages."""
    pokemon = parse_identifier(binary_protocol[i], slots)
    reason = binary_protocol[i + 1]
    i += 2
    msg = f"|-end|{pokemon}{END_REASONS[reason]}"
    return (msg, i)

def _immune_handler(binary_protocol: List[int], i: int, slots: Slots, _: List[str]) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    reason = binary_protocol[i + 1]
    i += 2
    msg = f"|-immune|{pokemon}{IMMUNE_REASONS[reason]}"
    return (msg, i)

def _transform_handler(
    binary_protocol: List[int],
    i: int,
    slots: Slots,
    _: List[str]
) -> ParseResult:
    pokemon = parse_identifier(binary_protocol[i], slots)
    target = parse_identifier(binary_protocol[i + 1], slots)
    i += 2
    return (f"|-transform|{pokemon}|{target}", i)

HANDLERS: List[Parser] = [
    # (just to not have a 0-index)
    None, # type: ignore
    _lastx_parser('Still'),
    _lastx_parser('Miss'),
    _move_parser,
    _switch_handler,
    _cant_handler,
    _generic_message_parser('faint'),
    _turn_handler,
    _win_handler,
    _tie_handler,
    _damage_handler,
    _heal_handler,
    _status_parser('Status'),
    _status_parser('CureStatus'),
    _boost_handler,
    _returner('|-clearallboost|[silent]'),
    _fail_handler,
    _generic_message_parser('-miss'),
    _hitcount_handler,
    _prepare_handler,
    _generic_message_parser('-mustrecharge'),
    _activate_handler,
    _returner('|-fieldactivate|move: Pay Day'), # will need to be changed for future generations
    _start_handler,
    _end_handler,
    _returner('|-ohko'),
    _generic_message_parser('-crit'),
    _generic_message_parser('-supereffective'),
    _generic_message_parser('-resisted'),
    _immune_handler,
    _transform_handler,
]

