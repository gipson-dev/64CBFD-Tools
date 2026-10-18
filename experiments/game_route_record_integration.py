"""Actual Make qualification, immutable first prediction and installed setup audit."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_record_reload as source
from tools.experiments import game_route_record_reload_layout as layout
from tools.tests.game_owner_pool import normalized_pools

prior = source.installed.prior
checkpoint = source.installed.source.checkpoint
BUILD = 'conker/build/game-route-record-integration'
OWNER, FUNCTION, ENTRY, ROM = source.OWNER, source.FUNCTION, source.ENTRY, source.ROM
INPUTS = source.INPUTS
AFTER = {
    'conker/build/conker.us.elf': '3c8fd0411cd80d7a66440b81db22eef663fc8d557d365cdbbf5b3ce43dd5591a',
    'conker/src/game/generated_B3020.c': 'fb512dd6fda54a37ab8adb84fa5efc50527941de4c622d66e12c6c3481c8ddbd',
    'conker/retail_word_patches.us.csv': 'cc92cdc4549964c1e9ebca306ee85ff5b7e57392a657bd9b15386384a8ab49d4',
}
SUCCESSOR_FILES = {'conker/build/conker.us.elf': 'after-elf',
    'conker/src/game/generated_B3020.c': 'after-owner',
    'conker/retail_word_patches.us.csv': 'after-guards'}
raw_read, raw_text = Path.read_bytes, Path.read_text


def freeze(root, out):
    return source.freeze(root, out)


def recovered_owner(before):
    return source.recovered_owner(before, source.selected())


def qualify(root, out):
    primary, _, row = source.qualify(root, out)
    values = freeze(root, out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    normal, nd = prior.compile_profile(root, out, recovered_owner(before), 'override-normal', True)
    old_normal, od = prior.compile_profile(root, out, before, 'baseline-normal', True)
    if nd or od:
        raise ValueError('Unexpected setup normal-profile diagnostics')
    prior.candidate.checked(normal)
    if source.installed.source.model.same_functions(old_normal, normal, (FUNCTION,)) != 72 or normalized_pools(old_normal) != normalized_pools(normal):
        raise ValueError('Changed setup normal-profile neighbor or pool')
    raw, bindings = source.checked(primary)
    (out / 'primary-no-unroll.o').write_bytes(raw_read(primary))
    (out / 'qualified-guards.csv').write_bytes(layout.private_guards(values['conker/retail_word_patches.us.csv'], raw, bindings))
    (out / 'unchanged-guards.csv').write_bytes(values['conker/retail_word_patches.us.csv'])
    (out / 'proposed-owner.c').write_text(recovered_owner(before))
    old = prior.padded(root, out, out / 'owner-before.o', 'baseline-padded', out / 'unchanged-guards.csv', old_normal)
    padded = prior.padded(root, out, primary, 'qualified-padded', out / 'qualified-guards.csv', normal)
    a, fa = prior.link_owner(root, out, old, OWNER)
    b, fb = prior.link_owner(root, out, padded, OWNER)
    at = fb[FUNCTION]['value']
    if b[at:at + 640] != values['conker/conker.us.bin'][ROM:ROM + 640] or (a[:at], a[at + 640:]) != (b[:at], b[at + 640:]):
        raise ValueError('Private setup padding changed target or unrelated bytes')
    if set(fa) != set(fb) or any(fa[n]['value'] != fb[n]['value'] or n != FUNCTION and fa[n] != fb[n] for n in fa):
        raise ValueError('Changed unrelated padded setup-owner definition')
    if normalized_pools(old) != normalized_pools(padded):
        raise ValueError('Changed padded setup pools')
    live = hashlib.sha256(raw_read(root / 'conker/build/conker.us.elf')).hexdigest()
    stage = old if live == INPUTS['conker/build/conker.us.elf'] else padded if live == AFTER.get('conker/build/conker.us.elf') else None
    if stage is None:
        raise ValueError('Unknown setup production image stage')
    source.installed.source.model.same_functions(stage, root / 'conker/build/src/game/generated_B3020.c.o')
    row.update(normalized_differences=0, guards=160, primary_and_normal_neighbors_unchanged=72,
               all_other_padded_bytes_fixed=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return primary, padded, row


def make_shadow(root, out):
    raw, bindings = source.checked(out / 'qualified.o')

    def recovered_guards(before, projection_raw, projection_bindings):
        if (projection_raw, projection_bindings) != prior.candidate.checked(out / 'override-normal.o'):
            raise ValueError('Changed actual Make projection override')
        return layout.private_guards(before, raw, bindings)

    with patch.multiple(prior, freeze=freeze, recovered_owner=recovered_owner,
                        recovered_makefile=lambda value: value, recovered_guards=recovered_guards):
        return prior.make_shadow(root, out)


def predicted_image(before, span):
    if hashlib.sha256(before).hexdigest() != INPUTS['conker/build/conker.us.elf'] or len(span) != 640:
        raise ValueError('Unknown setup predecessor or target extent')
    image = bytearray(before)
    at = prior.elf_slot_offset(before, ENTRY, 640)
    image[at:at + 640] = span
    rows = [r for r in prior.symbol_rows(before) if r[1] == FUNCTION]
    if len(rows) != 1 or rows[0][2][1:3] != (ENTRY, 12):
        raise ValueError('Wrong setup predecessor symbol extent')
    struct.pack_into('>I', image, rows[0][0] + 8, 640)
    result = bytes(image)
    if AFTER and hashlib.sha256(result).hexdigest() != AFTER['conker/build/conker.us.elf']:
        raise ValueError('Changed immutable setup prediction')
    return result


def predict(root, out):
    values = freeze(root, out)
    _, padded, _ = qualify(root, out)
    make_shadow(root, out)
    script = raw_text(root / 'conker/build/conker.ld')
    old = 'build/src/game/' + OWNER + '.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown setup linker owner input')
    ld = out / 'predicted.ld'
    ld.write_text(script.replace(old, padded.relative_to(root / 'conker').as_posix()))
    elf = out / 'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', str(ld.relative_to(root / 'conker')),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', str(elf.relative_to(root / 'conker'))], cwd=root / 'conker', capture_output=True, check=True)
    image = raw_read(elf)
    if image != predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + 640]):
        raise ValueError('First setup link changed unrelated bytes or metadata')
    after = {'conker/build/conker.us.elf': image,
        'conker/src/game/generated_B3020.c': recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv': raw_read(out / 'qualified-guards.csv')}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in after.items()}
    if AFTER and hashes != AFTER:
        raise ValueError('Changed first setup successor hashes')
    for name, data in after.items():
        target = out / SUCCESSOR_FILES[name]
        if target.exists() and raw_read(target) != data:
            raise ValueError('Changed immutable setup successor: ' + name)
        if not target.exists():
            target.write_bytes(data)
    result = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip(values['conker/build/conker.us.elf'], image)),
        only_target_code_and_symbol_extent_changed=True, metadata_order_groups=0)
    (out / 'prediction.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def expected_inputs(root, out):
    values = {name: raw_read(out / leaf) for name, leaf in SUCCESSOR_FILES.items()}
    if not AFTER or {name: hashlib.sha256(data).hexdigest() for name, data in values.items()} != AFTER:
        raise ValueError('Changed immutable first setup successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(checkpoint, INPUTS=INPUTS, AFTER=AFTER, expected_inputs=expected_inputs):
        yield


@contextmanager
def historical_view(root, out):
    with checkpoint_context(), checkpoint.historical_view(root, out):
        yield


def verify(root, out, installed=False):
    with checkpoint_context():
        return checkpoint.verify(root, out, installed)


def install_guards(root, out):
    expected = expected_inputs(root, out)
    for name in ('conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'):
        before = raw_read(out / ('before-%02d' % list(INPUTS).index(name)))
        if raw_read(root / name) != before:
            raise ValueError('Unexpected setup installation stage: ' + name)
    if raw_read(root / 'conker/src/game/generated_B3020.c') != expected['conker/src/game/generated_B3020.c']:
        raise ValueError('Install qualified setup source before guards')
    prefix = raw_read(root / 'conker/retail_word_patches.us.csv')
    if not expected['conker/retail_word_patches.us.csv'].startswith(prefix):
        raise ValueError('Changed original guard prefix')
    (root / 'conker/retail_word_patches.us.csv').write_bytes(expected['conker/retail_word_patches.us.csv'])


def audit(root, out):
    verify(root, out, True)
    for i, (name, digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out / ('before-%02d' % i))).hexdigest() != digest or \
                hashlib.sha256(raw_read(root / name)).hexdigest() != AFTER.get(name, digest):
            raise ValueError('Changed installed setup input: ' + name)
    predecessor = out / ('before-%02d' % list(INPUTS).index('conker/build/conker.us.elf'))
    before, actual = raw_read(predecessor), raw_read(root / 'conker/build/conker.us.elf')
    rom = raw_read(root / 'conker/conker.us.bin')
    if actual != raw_read(out / 'after-elf') or actual != predicted_image(before, rom[ROM:ROM + 640]):
        raise ValueError('Installed setup did not reproduce first whole-image prediction')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    old, _, oa = load_elf_functions(str(predecessor), 'mips-linux-gnu-objdump')
    new, _, na = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if oa != na or old.keys() != new.keys() or [n for n in old if old[n] != new[n]] != [FUNCTION]:
        raise ValueError('Setup changed another linked body or address')
    source.installed.source.model.same_functions(out / 'qualified-padded.o', root / 'conker/build/src/game/generated_B3020.c.o')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Setup changed protected Game data')
    result = dict(functions=len(old), all_addresses_fixed=True, other_bodies_fixed=len(old) - 1,
        only_target_code_and_symbol_extent_changed=True, metadata_order_groups=0,
        changed_ELF_bytes=sum(a != b for a, b in zip(before, actual)), first_prediction_reproduced=True, game_data=data)
    (out / 'installed-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(audit(root, root / BUILD) if args.audit else predict(root, root / BUILD), indent=2))
