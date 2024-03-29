"""`pykmn.engine.rng` contains tools for generating random numbers.

Currently, the only RNG implementation provided is the one used by Pokémon Showdown: `ShowdownRNG`.
This is the same RNG used by libpkmn when in Showdown compatibility mode (on by default).
Libpkmn has another RNG implementation for Gen I cartridge accuracy,
but it's not exposed as a public API and therefore isn't in PyKMN.
"""
from pykmn.engine.libpkmn import libpkmn_showdown_trace, LibpkmnBinding
from typing import Any


class ShowdownRNG:
    """Wraps `libpkmn`'s implementation of the random number generator used by Pokémon Showdown.

    This RNG is used by Showdown for all generations,
    but is most similar to the cartridge RNG in Generations V and VI.

    PyKMN users shouldn't need to construct this class directly; instead, you can
    use the `ShowdownRNG.from_seed` method to create a new instance.
    """

    def __init__(
        self,
        _pkmn_psrng: Any, # noqa: ANN401
        seed: int,
        _libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """Create a new ShowdownRNG instance with the given seed.

        PyKMN library consumers shouldn't use this since it involves CFFI data.
        Instead, use the static ShowdownRNG.from_seed() method.

        Args:
            _pkmn_psrng (`Any`): A pkmn_psrng struct.
            seed (`int`): The seed for the RNG. Must be an integer of up to 64 bits.
        """
        # pointer to a pkmn_psrng / PKMN_OPAQUE(PKMN_PSRNG_SIZE) / struct { uint8_t bytes[8]; }
        self._psrng = _pkmn_psrng
        self._libpkmn = _libpkmn
        ShowdownRNG._initialize(self._psrng, seed, _libpkmn=_libpkmn)


    @staticmethod
    def _initialize(
        bytes: Any, # noqa: ANN401
        seed: int,
        _libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """Initializes the ShowdownRNG by calling libpkmn's pkmn_psrng_init() function.

        Args:
            bytes (`Any`): A pkmn_psrng struct.
            seed (`int`): The seed for the RNG. Must be an integer of up to 64 bits.
        """
        _libpkmn.lib.pkmn_psrng_init(bytes, seed)

    @staticmethod
    def from_seed(seed: int, _libpkmn: LibpkmnBinding = libpkmn_showdown_trace) -> "ShowdownRNG":
        """Create a new ShowdownRNG instance with the given seed.

        Args:
            seed (`int`): The seed for the RNG. Must be an integer of up to 64 bits.

        Returns:
            **`ShowdownRNG`**: The new RNG instance.
        """
        return ShowdownRNG(_libpkmn.ffi.new("pkmn_psrng *"), seed, _libpkmn=_libpkmn)

    def next(self) -> int:
        """Get the next number from the ShowdownRNG.

        Also advances the seed.

        Returns:
            **`int`**: The next number produced by the RNG.
        """
        return self._libpkmn.lib.pkmn_psrng_next(self._psrng)

    def in_range(self, m: int, n: int) -> int:
        """Get an integer from the ShowdownRNG in the given range [m, n).

        Also advances the seed.

        Based on Pokémon Showdown's MIT-licensed RNG implementation, but behaves differently:
        https://github.com/smogon/pokemon-showdown/blob/master/sim/prng.ts

        Args:
            m (`int`): The lower bound of the range. Defaults to 0.
            n (`int`): The upper bound of the range. Defaults to 1.

        Returns:
            **`int`**: The next number produced by the RNG.
        """
        next = self.next()
        return int(next * (n - m) / (2**32)) + m


    def random_chance(self, numerator: int, denominator: int) -> bool:
        """Get a boolean with a `numerator / denominator` chance of being `True`.

        Also advances the seed.

        Based on Pokémon Showdown's MIT-licensed RNG implementation, but behaves differently:
        https://github.com/smogon/pokemon-showdown/blob/master/sim/prng.ts

        Args:
            numerator (`int`): The numerator of the chance fraction.
            denominator (`int`): The denominator of the chance fraction.

        Returns:
            **`bool`**: Has a `numerator / denominator` chance of being `True`.
        """
        return self.in_range(0, denominator) < numerator

    def seed(self) -> int:
        """Get the current seed of the ShowdownRNG.

        Returns:
            **`int`**: The current seed as a 64-bit integer.
        """
        return self._libpkmn.ffi.cast("uint64_t[1]", self._psrng)[0]
