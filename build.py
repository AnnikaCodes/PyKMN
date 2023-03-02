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
import sys
import hashlib
import os

GREEN = '\033[92m'
ORANGE = '\033[93m'
RED = '\033[91m'

got_own_zig = False

indent = 1
def log(message: str, color=GREEN) -> None:
    global indent
    print(f"{color}{'=' * indent}> {message}\033[0m")
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

def extract_zig(tarball_name: str, output_dir: str) -> None:
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        pass

    if not tarball_name.endswith('.zip'):
        try:
            subprocess.call(['tar', '-xf', tarball_name, '-C', output_dir])
            return
        except:
            # tar not available, we'll use Python's modules instead
            pass

    if tarball_name.endswith('.zip'):
        import zipfile
        zipfile.ZipFile(tarball_name).extractall(output_dir)
    else: # .tar.xz
        import lzma
        import tarfile
        with lzma.open(tarball_name) as tarball:
            tarfile.open(fileobj=tarball).extractall(output_dir)


# This function returns the path to a workable Zig (new enough version), installing it if needed
def find_zig() -> str:
    log("Looking for a Zig compiler...")
    system_zig = shutil.which("zig")
    if system_zig is not None:
        system_zig_env = json.loads(subprocess.getoutput(f"{system_zig} env"))

        if is_new_enough(parse_zig_version(system_zig_env['version'])):
            return system_zig
        else:
            log(f"Found installed Zig, but the version ({system_zig_env['version']}) is too old :(", color=ORANGE)

    got_own_zig = True # TODO: clean up at the end
    log("Fetching Zig download index")
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
        log(f"Couldn't find a Zig compiler for your platform ({zig_platform}). Please manually install Zig; version {version} should be compatible with pykmn.", color=RED)
        exit(1)

    tarball_url = zig_download_index[version][zig_platform]['tarball']

    log(f"Downloading Zig version {version} for {zig_platform} from {tarball_url}")
    tarball_stream = requests.get(tarball_url, stream=True)
    tarball_name = tarball_url.split("/")[-1]
    sys.stdout.write("1 dot = 1 mibibyte [")
    sys.stdout.flush()

    hash = hashlib.sha256()
    with open(tarball_name, 'wb') as fd:
        for chunk in tarball_stream.iter_content(chunk_size=2**20):
            sys.stdout.write(".")
            sys.stdout.flush()
            hash.update(chunk)
            fd.write(chunk)
    print("]")

    hash_value = hash.hexdigest()
    if hash_value != zig_download_index[version][zig_platform]['shasum']:
        log(f"SHA-256 hash for downloaded Zig doesn't match (got {hash_value}, expected {zig_download_index[version][zig_platform]['shasum']})", color=RED)
        log(f"The download may be corrupted; please try again.", color=RED)
        exit(1)
    else:
        log(f"Verified downloaded Zig (hash={hash_value})")

    log(f"Extracting Zig from '{tarball_name}'")
    extract_zig(tarball_name, "zig-toolchain")
    os.unlink(tarball_name)

    zig_directory = tarball_name[0:-4] if tarball_name.endswith(".zip") else tarball_name[0:-7]
    return os.path.join(os.getcwd(), "zig-toolchain", zig_directory, "zig")

# Gets the git submodule
def fetch_pkmn_engine() -> None:
    log("Fetching @pkmn/engine code")
    try:
        subprocess.call(['git', 'submodule', 'init'])
        subprocess.call(['git', 'submodule', 'update'])
    except:
        log("Couldn't fetch pkmn-engine submodule. Please make sure you have git installed.", color=RED)
        exit(1)

# Builds the @pkmn/engine library
def build_pkmn_engine(zig_path: str) -> None:
    log("Building @pkmn/engine")
    try:
        # TODO: support -Dshowdown, -Dtrace
        subprocess.call([zig_path, "build", "-Doptimize=ReleaseFast"], cwd="engine")
    except Exception as e:
        log(f"Failed to build pkmn-engine. Error: {e}", color=RED)
        exit(1)

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

zig_path = find_zig()
log(f"Using Zig at {zig_path}")
fetch_pkmn_engine()
build_pkmn_engine(zig_path)

ffibuilder = FFI()
ZIG_OUT_PATH="engine/zig-out"

log("Building bindings")
header_text = open(f"{ZIG_OUT_PATH}/include/pkmn.h").read()
ffibuilder.cdef(simplify_pkmn_header(header_text))
ffibuilder.set_source(
    "_pkmn_engine_bindings",
    f"#include \"{ZIG_OUT_PATH}/include/pkmn.h\"",
    libraries=['pkmn'],
    library_dirs=[f"{ZIG_OUT_PATH}/lib"],
)

if got_own_zig:
    log("Removing Zig toolchain")
    os.unlink("zig-toolchain")

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)