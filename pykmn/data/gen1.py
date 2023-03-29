"""Gen I data.

See `pykmn.data.loader` for documentation on the data.
(Due to limitations of this documentation generation tool, it's all there.)

However, you can import anything in `pykmn.data.loader` that's prefixed with `GEN1_`
from `pykmn.data.gen1` as well, by dropping the `GEN1_` prefix.
"""
from pykmn.data.loader import GEN1_TYPES as TYPES, GEN1_SPECIES as SPECIES, \
    GEN1_MOVES as MOVES, GEN1_SPECIES_IDS as SPECIES_IDS, \
    GEN1_MOVE_IDS as MOVE_IDS, Gen1SpeciesData, Gen1StatData, GEN1_LAYOUT_SIZES as LAYOUT_SIZES, \
    GEN1_LAYOUT_OFFSETS as LAYOUT_OFFSETS, GEN1_MOVE_ID_LOOKUP as MOVE_ID_LOOKUP, \
    GEN1_SPECIES_ID_LOOKUP as SPECIES_ID_LOOKUP, PartialGen1StatData # noqa: F401
