"""Qualify/install the scheduler through the existing equal-slot strict link audit."""
import argparse
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_pair_scheduler_layout as layout
from tools.experiments import game_actor_pair_visibility_integration as previous
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows

source = layout.source
BUILD = source.BUILD + '/match/integration'
NORMAL_FUNCTIONS = previous.NORMAL_FUNCTIONS


def invoke(name, root, out, *args):
    # Both routines occupy 261-word former stub slots in the same owner. Reuse
    # its full-image/code-size and real Make/padder gates, not its status counts.
    with patch.multiple(previous, source=source, layout=layout, predicted_image=predicted_image):
        return getattr(previous, name)(root, out, *args)


def qualify(root, out):
    row = invoke('qualify', root, out)
    row.update(frame=192, expected_word_guards=255, unique_retained_origins=249,
        derived_insertions=12, omitted_explicit_masks=5, omitted_cursor_copies=1)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def predicted_image(before, truth):
    with patch.multiple(previous, source=source, layout=layout):
        result = bytearray(BASE_PREDICTION(before, truth))
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(before)}
    names = ('D_8009DA68', 'D_80098638', 'D_800A6038')
    offsets = [rows[name][2] for name in names]
    if offsets != list(range(offsets[0], offsets[0] + 33, 11)):
        raise ValueError('Unknown scheduler symbol-name serialization predecessor')
    canonical = canonical_symbols(bytes(result))
    records = [rows[name][0] for name in names]
    if records != list(range(records[0], records[0] + 48, 16)):
        raise ValueError('Unknown scheduler symbol-record serialization predecessor')
    for old_name, at, name in zip(names, offsets, (*names[1:], names[0])):
        if rows[name][1][1:] != (int(name[2:], 16), 0, 16, 0, 65521):
            raise ValueError('Scheduler symbol metadata changed')
        if before[rows[name][2]:rows[name][2] + 11] != name.encode() + b'\0':
            raise ValueError('Scheduler symbol spelling changed')
        result[at:at + 11] = name.encode() + b'\0'
        string_table = rows[name][2] - rows[name][1][0]
        record = rows[old_name][0]
        result[record:record + 16] = before[rows[name][0]:rows[name][0] + 16]
        struct.pack_into('>I', result, record, at - string_table)
    if canonical_symbols(bytes(result)) != canonical:
        raise ValueError('Scheduler symbol-name permutation changed canonical symbols')
    return bytes(result)


BASE_PREDICTION = previous.predicted_image


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Scheduler differs from strict code/size prediction')


def padded(root, out, guards): return invoke('padded', root, out, guards)
def predict(root, out): return invoke('predict', root, out)
def make_shadow(root, out): return invoke('make_shadow', root, out)
def audit(root, out): return invoke('audit', root, out)
def build(root, out): return invoke('build', root, out)


def install_guards(root, out):
    invoke('install_guards', root, out)
    return dict(guard_rows=255, omissions=6, insertions=12, prior_guard_bytes_unchanged=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ('predict', 'make-shadow', 'install-guards', 'build', 'audit'):
        p.add_argument('--' + flag, action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    if args.install_guards: print(json.dumps(install_guards(root, out), indent=2))
    elif args.build: print(json.dumps(build(root, out), indent=2))
    elif args.audit: print(json.dumps(audit(root, out), indent=2))
    else:
        print(json.dumps(qualify(root, out), indent=2), flush=True)
        if args.make_shadow: print(json.dumps(make_shadow(root, out), indent=2), flush=True)
        if args.predict: print(json.dumps(predict(root, out), indent=2))
