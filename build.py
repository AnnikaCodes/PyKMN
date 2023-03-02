# Builds the importable _pkmn_engine_bindings module

# from ttps://github.com/pkmn/engine/blob/main/src/bin/install-pkmn-engine#L11
MINIMUM_ZIG_MAJOR_VERSION = 0
MINIMUM_ZIG_MINOR_VERSION = 11
MINIMUM_ZIG_PATCH_VERSION = 0
MINIMUM_ZIG_DEV_VERSION = 1711

ZIG_DOWNLOAD_INDEX_URL = 'https://ziglang.org/download/index.json'

from cffi import FFI
import shutil
import subprocess
import json
import re
import platform
import requests

indent = 1
def log(message: str) -> None:
    global indent
    print(f"{'=' * indent}> {message}")
    indent += 1

# First, we need to find/install Zig
# This part is based on pre's `install-pkmn-engine` script:
# https://github.com/pkmn/engine/blob/main/src/bin/install-pkmn-engine

def parse_zig_version(version: str) -> tuple[int, int, int, int | None]:
    if version == 'master':
        return (-1, 0, 0, 0)
    try:
        parsed_version = [int(re.sub(r'[^\d].*', '', part)) for part in version.split(".")]
    except:
        parsed_version = []

    if len(parsed_version) == 3:
        [major, minor, patch] = parsed_version
        dev = None
    elif len(parsed_version) == 4:
        [major, minor, patch, dev] = parsed_version
    else:
        log(f"Couldn't parse Zig version '{version}'")
    return (major, minor, patch, dev)

def is_new_enough(version: tuple[int, int, int, int | None]) -> bool:
    [major, minor, patch, dev] = version
    return major >= MINIMUM_ZIG_MAJOR_VERSION and minor >= MINIMUM_ZIG_MINOR_VERSION and \
        patch >= MINIMUM_ZIG_PATCH_VERSION and dev >= MINIMUM_ZIG_DEV_VERSION

# This function returns the path to a workable Zig (new enough version), installing it if needed
def find_zig() -> str:
    log("Looking for a Zig compiler...")
    system_zig = shutil.which("zig")
    if system_zig is not None:
        system_zig_env = json.loads(subprocess.getoutput(f"{system_zig} env"))

        if is_new_enough(parse_zig_version(system_zig_env['version'])):
            log(f"Found system `zig` version {system_zig_env['version']}")
            return system_zig
        else:
            log(f"Found system `zig`, but the installed version ({system_zig_env['version']}) is too old :(")

    log("Fetching Zig download index...")
    zig_download_index = requests.get(ZIG_DOWNLOAD_INDEX_URL).json()
    newest_version = sorted(zig_download_index.keys(), key=lambda x: parse_zig_version(x), reverse=True).pop()
    if is_new_enough(parse_zig_version(newest_version)):
        version = newest_version
    else:
        version = 'master'

    arch = platform.machine()
    system = platform.system().lower()
    if system == "darwin":
        system = "macos"
    zig_platform = f'{arch}-{system}'
    if zig_platform not in zig_download_index[version]:
        log(f"Couldn't find a Zig compiler for your platform ({zig_platform}). Please manually install Zig; version {version} should be compatible with pykmn.")
        exit(1)

    tarball_url = zig_download_index[version][zig_platform]['tarball']
    log(f"Downloading Zig version {version} for {zig_platform}...")
    # TODO: make it work


zig_path = find_zig()

ffibuilder = FFI()
ZIG_OUT_PATH="./zig-out"

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

header_text = open(f"{ZIG_OUT_PATH}/include/pkmn.h").read()
ffibuilder.cdef(simplify_pkmn_header(header_text))
ffibuilder.set_source(
    "_pkmn_engine_bindings",
    f"#include \"{ZIG_OUT_PATH}/include/pkmn.h\"",
    libraries=['pkmn'],
    library_dirs=[f"{ZIG_OUT_PATH}/lib"],
)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)