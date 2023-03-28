"""Alternative libpkmn builds with different features."""

import libpkmn_no_trace as _no_trace # type: ignore
import libpkmn_trace as _trace # type: ignore
import libpkmn_showdown_trace as _showdown_trace # type: ignore
import libpkmn_showdown_no_trace as _showdown_no_trace # type: ignore

from typing import Any

# TODO: document how to use these bindings
class LibpkmnBinding:
    """A generic type for libpkmn library bindings.

    This isn't actually a class; it's just here to make typing work well.
    You definitely shouldn't ever construct it.
    Instead, import a libpkmn binding from pykmn.engine.libpkmn.
    """

    ffi: Any
    lib: Any

"""libpkmn bindings with protocol trace logging, but no compatibility with Pokémon Showdown."""
libpkmn_trace: LibpkmnBinding = _trace

"""libpkmn bindings with no protocol trace logging or compatibility with Pokémon Showdown."""
libpkmn_no_trace: LibpkmnBinding = _no_trace

"""libpkmn bindings with both protocol trace logging and compatibility with Pokémon Showdown."""
libpkmn_showdown_trace: LibpkmnBinding = _showdown_trace

"""libpkmn bindings with no protocol trace logging, but with compatibility with Pokémon Showdown."""
libpkmn_showdown_no_trace: LibpkmnBinding = _showdown_no_trace
