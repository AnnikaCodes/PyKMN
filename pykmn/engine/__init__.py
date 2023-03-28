"""`pykmn.engine` wraps libpkmn's battle simulation engine.

The functionality is broken down by generation; currently, only Generation I is supported,
and it can be found in `pykmn.engine.gen1`.
If you're looking to start simulating battles right away,
you'll want to jump straight to `pykmn.engine.gen1.Battle`.

The following submodules are found in `pykmn.engine`:
* `pykmn.engine.common`: common types and functions used by the battle simulation engine across
   generations, like `pykmn.engine.common.Choice` and `pykmn.engine.common.Player`.
* `pykmn.engine.rng`: random number generation tools,
   primarily libpkmn's reimplementations of Pokémon Showdown's PRNG
   (`pykmn.engine.rng.ShowdownRNG`). These are bindings for libpkmn's `pkmn_psrng` struct.
* `pykmn.engine.gen1`: Generation I battle simulation (bindings for libpkmn's `pkmn_gen1_battle`).
   In particular, `pykmn.engine.gen1.Battle` is the main class for simulating battles.
* `pykmn.engine.protocol`: code to parse libpkmn's binary protocol.
   * While in theory this should work with any generation, some Gen I-related assumptions are made.
     PyKMN will update this submodule, potentially moving it into `pykmn.engine.gen1`,
     as more generations are supported.
* `pykmn.engine.libpkmn`: for more advanced users, this submodule's functionality lets you
   select which `libpkmn` binding to use —
   you can disable logging protocol messages or set libpkmn to be more accurate to the behavior
   of Gen I games on cartridge
   (at the cost of being less accurate to Pokémon Showdown's implementation).
"""
from pykmn import engine  # noqa: F401
from pykmn.engine import common, gen1, rng, protocol, libpkmn  # noqa: F401
