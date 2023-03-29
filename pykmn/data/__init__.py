"""Repackaged data for libpkmn.

PyKMN users mostly shouldn't need to use this module directly; check out `pykmn.engine` instead.

All data is from pre's [pkmn engine](https://github.com/pkmn/engine), which is also where libpkmn
comes from. The data is repackaged here to make it easier to use in Python; PyKMN uses this data
a great deal internally.

`pykmn.data` is broken up into the following submodules:
* `pykmn.data.gen1`: data for the first generation of Pokémon games
* `pykmn.data.gen2`: data for the second generation of Pokémon games
* `pykmn.data.protocol`: data for the libpkmn protocol
* `pykmn.data.loader`: loading logic and types for the other three modules
"""
import pykmn.data.gen1  # noqa: F401
import pykmn.data.gen2  # noqa: F401
import pykmn.data.protocol  # noqa: F401
