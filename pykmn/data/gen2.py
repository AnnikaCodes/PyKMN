"""Gen II data.

See `pykmn.data.loader` for documentation on the data.
(Due to limitations of this documentation generation tool, it's all there.)

However, you can import anything in `pykmn.data.loader` that's prefixed with `GEN2_`
from `pykmn.data.gen2` as well, by dropping the `GEN2_` prefix.
"""
from pykmn.data.loader import GEN2_TYPES as TYPES, GEN2_SPECIES as SPECIES, GEN2_MOVES as MOVES, \
    GEN2_ITEMS as ITEMS, Gen2SpeciesData, Gen2StatData  # noqa: F401
