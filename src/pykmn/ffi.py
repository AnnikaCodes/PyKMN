ZIG_OUT_PATH="./zig-out"

from cffi import FFI
import re
ffibuilder = FFI()

# Simplifies the pkmn.h file so that cffi can parse it
def simplify_pkmn_header(header_text: str) -> str:
    # Remove anything C++-specific
    without_cpp_only = re.sub(r'#ifdef __cplusplus(.*?)#endif', "", header_text, flags=re.DOTALL)
    # Remove preprocessor directives: #ifndef, #ifdef, #include, #endif
    without_preprocessor = re.sub(r"(#((ifn?|un)def|include) .*|#endif)", "", without_cpp_only)
    # Remove defines that are NOT numeric constants
    without_defines = re.sub(r"#define [^\s]{1,}(\s[^\d]+)?\n", "", without_preprocessor)
    # remove PKMN_OPAQUE definition replace PKMN_OPAQUE types with their definition
    without_pkmn_opaque_definition = without_defines.replace("#define PKMN_OPAQUE(n) typedef struct { uint8_t bytes[n]; }\n", "")
    return re.sub(r'PKMN_OPAQUE\(([^)]*)\)', r'typedef struct { uint8_t bytes[\1]; }', without_pkmn_opaque_definition)

# all the definitions to get exported
# see https://github.com/pkmn/engine/blob/main/src/include/pkmn.h
header_text = open(f"{ZIG_OUT_PATH}/include/pkmn.h").read()
ffibuilder.cdef(simplify_pkmn_header(header_text))
ffibuilder.set_source(
    "_pkmn_engine",
    f"#include \"{ZIG_OUT_PATH}/include/pkmn.h\"",
    libraries=['pkmn'],
    library_dirs=[f"{ZIG_OUT_PATH}/lib"],
)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)