# Conker's Bad Fur Day Decompilation Tools

Build, extraction, byte-matching, and qualification tools for the
[64CBFD decompilation](https://github.com/gipson-dev/64CBFD).
This is the decomp tool repository, not the `64CBFDOGL` PC-port tool set.

No ROMs, extracted game assets, compiler binaries, or local build receipts are
included. Supply your own legally obtained game when a tool requires it.

## Checkout

```sh
git clone --recursive https://github.com/gipson-dev/64CBFD-Tools.git "64CBFD Tools"
cd "64CBFD Tools"
```

The decomp pins this repository at `64CBFD/tools`. Its existing Makefiles,
Python module names, Splat extensions, and documentation commands keep those
paths. For an existing decomp checkout:

```sh
git pull --ff-only
git submodule sync --recursive
git submodule update --init --recursive
```

## Tools

| Area | Entry Points |
| --- | --- |
| Assets and compression | `asset_dump.py`, `rareunzip.py`, `rarezip.py`, `extract_compressed.py`, `compress_dir.py` |
| MIPS fixtures | `mkrawobject`, `mksimpleelf`, `vertconvert.py` |
| Layout and byte matching | `match_progress.py`, `progress.py`, `pad_c_object.py`, `pad_generated_object.py`, `patch_generated_slice_ld.py`, `check_game_data_layout.py` |
| Recovery research | `experiments/` |
| Regression and guest oracles | `tests/` |
| Conker Splat extensions | `splat_ext/` |

Detailed function-specific commands and qualification limits remain in the
decomp's [Tools Guide](https://github.com/gipson-dev/64CBFD/blob/master/DOCS/TOOLS.md)
and [working notes](https://github.com/gipson-dev/64CBFD/blob/master/DOCS/WORKING_NOTES.md).

## ROM-Free Checks

Use Linux, WSL, or Docker with Python 3 and MIPS GNU binutils. For Ubuntu:

```sh
sudo apt-get install binutils-mips-linux-gnu
python3 check_project_tools.py
python3 -m unittest discover -s tests -p test_match_progress.py -v
python3 -m unittest discover -s tests -p test_pad_c_object_word_patches.py -v
python3 -m unittest discover -s tests -p test_pad_generated_pc16.py -v
```

These checks work from this standalone checkout and do not require a game ROM.
The shell wrappers are executable and use LF line endings in fresh checkouts.

Matching experiments and most other regression tests require the **consumer
layout**: this repository mounted at `64CBFD/tools`, with the decomp sources,
IDO compiler, manifests, and any required extracted/local build inputs present.
Do not run the complete suite from the standalone root and expect it to find
`conker/`. From the decomp root, for example:

```sh
make tools-check
python3 -m unittest tools.tests.test_game_node_effect_registration_match -v
python3 -m tools.experiments.game_node_effect_registration_candidates
```

## Dependencies

Seven upstream repositories remain separately pinned submodules: `n64splat`,
`asm-differ`, `asm-processor`, `mips_to_c`, `CBFD_rabbitizer`, `texture2c`, and
`ultralib`. Their revisions were preserved during the split. Run recursive
submodule updates to obtain them; their own documentation and licenses apply.
The consumer's `requirements.txt` and `n64splat/requirements.txt` still define
the decomp Python environment.

`assetmgr/` and `mktextures` are reference-only generators from a different
Rare asset pipeline. They remain disabled by default and are not Conker
builders. See [the compatibility warning](assetmgr/README.md).

## Development

Tool changes are committed here. The decomp records a specific tools commit,
not a moving branch. Coordinate tool changes and the consumer's pin in separate
commits; see [Contributing](CONTRIBUTING.md). GitHub Actions runs only the
ROM-free checks above and repository-configuration tests. It does not claim a
full game build or guest-function qualification.

The import came from decomp commit
[`f0d7300178dc0a4a32fbb3e4e19810ff98879cb4`](https://github.com/gipson-dev/64CBFD/commit/f0d7300178dc0a4a32fbb3e4e19810ff98879cb4).
The original file history remains in that repository. See [Provenance](NOTICE.md).
