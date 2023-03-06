"""Builds the importable _pkmn_engine_bindings module."""

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
from pathlib import Path

# from https://github.com/pkmn/engine/blob/main/src/bin/install-pkmn-engine#L11
MINIMUM_ZIG_MAJOR_VERSION = 0
MINIMUM_ZIG_MINOR_VERSION = 11
MINIMUM_ZIG_PATCH_VERSION = 0
MINIMUM_ZIG_DEV_VERSION = 1711

ZIG_DOWNLOAD_INDEX_URL = 'https://ziglang.org/download/index.json'

GREEN = '\033[92m'
ORANGE = '\033[93m'
RED = '\033[91m'

got_own_zig = False

indent = 1


def log(message: str, color=GREEN) -> None:
    """Log a message to the console with progressing arrows and color.

    Args:
        message (str): the message to log
        color (str, optional): the terminal color string to print with it. Defaults to GREEN.
    """
    global indent
    print(f"{color}{'=' * indent}> {message}\033[0m")
    indent += 1

# First, we need to find/install Zig
# This part is based on pre's `install-pkmn-engine` script:
# https://github.com/pkmn/engine/blob/main/src/bin/install-pkmn-engine


def parse_zig_version(version: str) -> tuple[int, int, int, int | None]:
    """Parse a Zig version string.

    Args:
        version (str): the Zig version string

    Returns:
        tuple[int, int, int, int | None]: a tuple of (major, minor, patch, dev) version information
            dev is None if there's no dev version in the string.
            Returns (-1, 0, 0, None) if the version string provided is 'master'.
    """
    if version == 'master':
        return (-1, 0, 0, None)
    try:
        parsed_version = [int(re.sub(r'[^\d].*', '', part)) for part in version.split(".")]
    except ValueError:
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
    """Check if a Zig version can build libpkmn based on the constants in this file.

    Args:
        version (tuple[int, int, int, int | None]): the Zig version from parse_zig_version()

    Returns:
        bool: True if the version can build libpkmn, else False
    """
    [major, minor, patch, dev] = version
    return major >= MINIMUM_ZIG_MAJOR_VERSION and minor >= MINIMUM_ZIG_MINOR_VERSION and \
        patch >= MINIMUM_ZIG_PATCH_VERSION and (dev is None or dev >= MINIMUM_ZIG_DEV_VERSION)


def extract_zig(tarball_name: str, output_dir: str) -> None:
    """Extract a Zig release tarball.

    Args:
        tarball_name (str): the path to the tarball
        output_dir (str): the path to a folder to extract it into
    """
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        pass

    if not tarball_name.endswith('.zip'):
        try:
            subprocess.call(['tar', '-xf', tarball_name, '-C', output_dir])
            return
        except FileNotFoundError:
            # tar not available, we'll use Python's modules instead
            pass

    if tarball_name.endswith('.zip'):
        import zipfile
        zipfile.ZipFile(tarball_name).extractall(output_dir)
    else:  # .tar.xz
        import lzma
        import tarfile
        with lzma.open(tarball_name) as tarball:
            tarfile.open(fileobj=tarball).extractall(output_dir)


# This function returns the path to a workable Zig (new enough version), installing it if needed
def find_zig() -> str:
    """Find a version of Zig new enough to build libpkmn, installing it if needed.

    Returns:
        str: the path to a usable Zig executable
    """
    global got_own_zig
    log("Looking for a Zig compiler...")
    system_zig = shutil.which("zig")
    if system_zig is not None:
        system_zig_env = json.loads(subprocess.getoutput(f"{system_zig} env"))

        if is_new_enough(parse_zig_version(system_zig_env['version'])):
            return system_zig
        else:
            log(
                f"Found installed Zig, but the version ({system_zig_env['version']}) is too old :(",
                color=ORANGE,
            )

    got_own_zig = True
    log("Fetching Zig download index")
    zig_download_index = requests.get(ZIG_DOWNLOAD_INDEX_URL).json()
    newest_version = sorted(
        zig_download_index.keys(),
        key=lambda x: parse_zig_version(x),
        reverse=True,
    ).pop()
    if is_new_enough(parse_zig_version(newest_version)):
        version = newest_version
    else:
        version = 'master'

    arch = platform.machine()
    system = platform.system().lower()

    if system == "darwin":
        system = "macos"
    if arch == "AMD64":
        arch = "x86_64"

    zig_platform = f'{arch}-{system}'
    if zig_platform not in zig_download_index[version]:
        log(
            f"Couldn't find a Zig compiler for your platform ({zig_platform}). " +
            "Please manually install Zig; version {version} should be compatible with pykmn.",
            color=RED
        )
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
        log(
            f"SHA-256 hash for downloaded Zig doesn't match (got {hash_value}, " +
            f"expected {zig_download_index[version][zig_platform]['shasum']})",
            color=RED,
        )
        log("The download may be corrupted; please try again.", color=RED)
        exit(1)
    else:
        log(f"Verified downloaded Zig (hash={hash_value})")

    log(f"Extracting Zig from '{tarball_name}'")
    extract_zig(tarball_name, "zig-toolchain")
    os.unlink(tarball_name)

    zig_directory = tarball_name[0:-4] if tarball_name.endswith(".zip") else tarball_name[0:-7]
    return os.path.join(os.getcwd(), "zig-toolchain", zig_directory, "zig")


def build_pkmn_engine() -> None:
    """Build libpkmn, populating the zig-out directory with a library file."""
    output_path = Path("engine/zig-out/lib")
    try:
        # TODO: support -Dshowdown, -Dtrace
        if output_path.exists():
            # check to see if we need to rebuild
            try:
                library_file = os.listdir(output_path)[0]
                library_mtime = os.path.getmtime(os.path.join(output_path, library_file))
                source_mtime = max(
                    max(os.path.getmtime(root) for root, _, _ in os.walk('engine/src')),
                    os.path.getmtime('engine/build.zig'),
                    os.path.getmtime(__file__)  # changes to build_bindings.py
                )
                if library_mtime > source_mtime:
                    log(
                        "No change to libpkmn source files since last build, skipping rebuild",
                        color=ORANGE
                    )
                    return
            except StopIteration:
                pass

        zig_path = find_zig()
        log(f"Building libpkmn with Zig at {zig_path}")
        subprocess.call([
            zig_path, "build", "-Dpic=true",
            "-Dshowdown=true", "-Dtrace=true", "-Doptimize=Debug",
        ], cwd="engine")
    except Exception as e:
        log(f"Failed to build libpkmn. Error: {e}", color=RED)
        exit(1)


def simplify_pkmn_header(header_text: str) -> str:
    """Simplifiy the pkmn.h file so that cffi can parse it.

    Currently discussing whether to do this or just hardcode a copy/pasted slimmed-down pkmn.h

    Args:
        header_text (str): The text of pkmn.h

    Returns:
        str: the simplified, parseable header declarations
    """
    # Remove anything C++-specific
    without_cpp_only = re.sub(r'#ifdef __cplusplus(.*?)#endif', "", header_text, flags=re.DOTALL)
    # Remove preprocessor directives: #ifndef, #ifdef, #include, #endif
    without_preprocessor = re.sub(r"(#((ifn?|un)def|include) .*|#endif)", "", without_cpp_only)
    # Remove defines that are NOT numeric constants
    without_defines = re.sub(r"#define [^\s]{1,}(\s[^\d]+)?\n", "", without_preprocessor)
    # remove PKMN_OPAQUE definition replace PKMN_OPAQUE types with their definition
    without_pkmn_opaque_definition = without_defines.replace(
        "#define PKMN_OPAQUE(n) typedef struct { uint8_t bytes[n]; }\n",
        "",
    )

    return re.sub(
        r'PKMN_OPAQUE\(([^)]*)\)',
        r'typedef struct { uint8_t bytes[\1]; }',
        without_pkmn_opaque_definition,
    )


build_pkmn_engine()

# Copy data json in
data_folder = os.path.join(os.getcwd(), "engine", "src", "data")

for json_file in ["data.json", "protocol.json", "layout.json"]:
    shutil.copyfile(
        os.path.join(data_folder, json_file),
        os.path.join(os.getcwd(), "pykmn", "data", json_file)
    )

ffibuilder = FFI()
zig_out_path = os.path.join(os.getcwd(), "engine", "zig-out")
pkmn_h_path = os.path.join(zig_out_path, "include", "pkmn.h")

log("Building bindings")
header_text = open(pkmn_h_path, 'r').read()
ffibuilder.cdef(simplify_pkmn_header(header_text))
ffibuilder.set_source(
    "_pkmn_engine_bindings",
    f"#include \"{pkmn_h_path}\"",
    libraries=['pkmn-showdown'],
    library_dirs=[os.path.join(zig_out_path, "lib")],
    extra_compile_args=["-fPIC", "-shared"],
    extra_link_args=["-fPIC"],
)

if got_own_zig:
    log("Removing Zig toolchain")
    shutil.rmtree("zig-toolchain")

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
