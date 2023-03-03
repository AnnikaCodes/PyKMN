"""
Bindings for libpkmn.

The following specific modules are not re-imported to the top level here:
* `rng`: random number generation (bindings for pkmn_psrng)
* `gen1`: Generation I (RBY) battle simulation (bindings for pkmn_gen1_battle)
"""
from common import BattleChoiceKind, ResultKind, Result  # type: ignore # noqa: F401
