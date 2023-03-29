"""Alternative libpkmn builds with different features.

To use, pass your desired `LibpkmnBinding` to the `pykmn.engine.gen1.Battle` constructor
via the `libpkmn=` named parameter.

The default is `libpkmn_showdown_trace`; using other bindings may restrict behavior.
Be sure to read the documentation for the particular bindning you're considering!
"""

import libpkmn_no_trace as _no_trace # type: ignore
import libpkmn_trace as _trace # type: ignore
import libpkmn_showdown_trace as _showdown_trace # type: ignore
import libpkmn_showdown_no_trace as _showdown_no_trace # type: ignore

from typing import Any

# TODO: document how to use these bindings
class LibpkmnBinding:
    """A generic type for libpkmn library bindings.

    This class just wraps a libpkmn binding for typing and documentation purposes.

    To get one for use, import one from `pykmn.engine.libpkmn`.
    """
    ffi: Any
    lib: Any

    def __init__(self, other: Any) -> None: # noqa: ANN401
        """You don't need to use this!"""
        self.ffi = other.ffi
        self.lib = other.lib


libpkmn_showdown_trace = LibpkmnBinding(_showdown_trace)
"""libpkmn bindings with both protocol trace logging and compatibility with Pokémon Showdown.

This is the default `LibpkmnBinding` used by PyKMN.
"""

libpkmn_trace = LibpkmnBinding(_trace)
"""libpkmn bindings with protocol trace logging, but no compatibility with Pokémon Showdown.

If you specify your own RNG seed to `pykmn.engine.gen1.Battle`,
you'll need to specify a list of 10 8-bit unsigned integers rather than the 64-bit unsigned integer
that the Showdown-compatible RNG accepts.

This binding also doesn't reproduce Pokémon Showdown's behavior where it diverges from the behavior
of the real Generation I games from GameFreak.

Otherwise, you can use this binding similarly to the default.
"""

libpkmn_showdown_no_trace = LibpkmnBinding(_showdown_no_trace)
"""libpkmn bindings with no protocol trace logging, but with compatibility with Pokémon Showdown.

The second tuple element from `pykmn.engine.gen1.Battle.update()`, which normally contains
a protocol trace, will be a null value while using this binding.
Attempting to parse it will not work;
choose a different `LibpkmnBinding` if you need to look at protocol messages.
"""

libpkmn_no_trace = LibpkmnBinding(_no_trace)
"""libpkmn bindings with no protocol trace logging or compatibility with Pokémon Showdown.

The caveats from both `libpkmn_showdown_no_trace` and `libpkmn_trace` apply here.
"""

__all__ = [
    "libpkmn_showdown_trace",
    "libpkmn_trace",
    "libpkmn_showdown_no_trace",
    "libpkmn_no_trace",
    "LibpkmnBinding",
]


