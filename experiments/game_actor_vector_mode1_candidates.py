"""Recover the mode-1 actor/global-vector snapshot callback."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_vector_snapshot_candidates as vector

ENTRY, ROM, WORDS = 0x1506A968, 0x97E18, 40
FUNCTION = 'func_1506A968'
MODE, TABLE_INDEX, TABLE_ROM = 1, 7, 0x22ABEC
MEASUREMENTS = 'conker/build/game-actor-vector-mode1/measurements.json'
SOURCE, MARKER = vector.SOURCE, vector.MARKER
ORIGINAL = 's32 func_1506A968() {\n    return 0;\n}'
VECTORS, DECLARATIONS, SYMBOLS = vector.VECTORS, vector.DECLARATIONS, vector.SYMBOLS
POSITION, DIFFERENCE, compiler = vector.POSITION, vector.DIFFERENCE, vector.compiler
SELECTED = vector.SELECTED.replace(vector.FUNCTION, FUNCTION).replace(
    'difference, NULL, 0,', 'difference, NULL, 1,')


def candidates():
    with patch.object(vector, 'SELECTED', SELECTED):
        yield from vector.candidates()


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(vector, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            SYMBOLS=SYMBOLS):
        return vector.compile_candidate(root, out, name, body, profile)


def recovered_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count(DECLARATIONS) != 1:
        raise ValueError('Expected one mode-1 placeholder and the existing vector prototype')
    return before.replace(ORIGINAL, body, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / Path(MEASUREMENTS).parent
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (root / MEASUREMENTS).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
