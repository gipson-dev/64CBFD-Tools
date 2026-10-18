"""Qualify the actual Make path and predict/audit the route-vector installation."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_vector_layout as layout
from tools.tests.game_owner_pool import normalized_pools

source = layout.source
prior = source.installed.prior
BUILD = 'conker/build/game-route-vector-integration'
OWNER, FUNCTION, ENTRY, ROM = source.model.OWNER, source.model.FUNCTION, source.model.ENTRY, source.model.ROM
INPUTS = source.INPUTS
AFTER = {
    'conker/build/conker.us.elf': 'e55a6d218b40d9216dbe690c058132eacbae0e57d009c0f2670501ff46aa65b3',
    'conker/src/game/generated_B3020.c': '53bab1289ba22cce5a94208fa441fb9b349cb825185748af3096e293937b685b',
    'conker/retail_word_patches.us.csv': '0d6c65a40cc623678449ea344d3fcb1b4a119f33f619e6964164c4c25b46558e',
}
SYMBOL_ORDERS = ()
SUCCESSOR_FILES = dict(source.installed.SUCCESSOR_FILES)
raw_read, raw_text = Path.read_bytes, Path.read_text


def freeze(root, out):
    return source.freeze(root, out)


def recovered_owner(before):
    return source.model.recovered_owner(before, source.selected())


def qualify(root, out):
    values = freeze(root, out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    body = recovered_owner(before)
    primary, diagnostics = prior.compile_profile(root, out, body, 'primary-no-unroll')
    raw, bindings = source.checked(primary)
    layout.normalize(raw, bindings)
    normal, nd = prior.compile_profile(root, out, body, 'override-normal', True)
    prior.candidate.checked(normal)
    original, od = prior.compile_profile(root, out, before, 'owner-before')
    old_normal, ond = prior.compile_profile(root, out, before, 'baseline-normal', True)
    if any((diagnostics, nd, od, ond)):
        raise ValueError('Unexpected vector profile diagnostics')
    for a, b in ((original, primary), (old_normal, normal)):
        if source.model.same_functions(a, b, (FUNCTION,)) != 72 or normalized_pools(a) != normalized_pools(b):
            raise ValueError('Changed vector owner neighbor or pool')
    guards = layout.private_guards(values['conker/retail_word_patches.us.csv'], raw, bindings)
    (out / 'qualified-guards.csv').write_bytes(guards)
    (out / 'proposed-owner.c').write_text(body)
    (out / 'unchanged-guards.csv').write_bytes(values['conker/retail_word_patches.us.csv'])
    old = prior.padded(root, out, original, 'baseline-padded', out / 'unchanged-guards.csv', old_normal)
    padded = prior.padded(root, out, primary, 'qualified-padded', out / 'qualified-guards.csv', normal)
    a, fa = prior.link_owner(root, out, old, OWNER)
    b, fb = prior.link_owner(root, out, padded, OWNER)
    at = fb[FUNCTION]['value']
    if b[at:at + 332] != values['conker/conker.us.bin'][ROM:ROM + 332] or a[:at] != b[:at] or a[at + 332:] != b[at + 332:]:
        raise ValueError('Private vector padding changed target or another byte')
    if set(fa) != set(fb) or any(fa[n]['value'] != fb[n]['value'] or n != FUNCTION and fa[n] != fb[n] for n in fa):
        raise ValueError('Private vector padding changed another definition')
    if normalized_pools(old) != normalized_pools(padded):
        raise ValueError('Private vector padded pools changed')
    live = hashlib.sha256(raw_read(root / 'conker/build/conker.us.elf')).hexdigest()
    stage = old if live == INPUTS['conker/build/conker.us.elf'] else padded if live == AFTER.get('conker/build/conker.us.elf') else None
    if stage is None:
        raise ValueError('Unknown vector production image stage')
    source.model.same_functions(stage, root / 'conker/build/src/game/generated_B3020.c.o')
    row = dict(words=83, frame=16, differences=56, saved=[(17, 12), (16, 8)], diagnostics='',
               normalized_differences=0, raw_differences=56, guards=83,
               primary_and_normal_neighbors_unchanged=72, all_other_padded_bytes_fixed=True,
               production_installed=False)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return primary, padded, row


def make_shadow(root, out):
    raw, bindings = source.checked(out / 'primary-no-unroll.o')

    def recovered_guards(before, projection_raw, projection_bindings):
        if (projection_raw, projection_bindings) != prior.candidate.checked(out / 'override-normal.o'):
            raise ValueError('Changed vector integration projection override')
        return layout.private_guards(before, raw, bindings)

    with patch.multiple(prior, freeze=freeze, recovered_owner=recovered_owner,
                        recovered_makefile=lambda value: value, recovered_guards=recovered_guards):
        return prior.make_shadow(root, out)


def predicted_image(before, span):
    if len(span) != 332:
        raise ValueError('Wrong vector target extent')
    image = bytearray(before)
    at = prior.elf_slot_offset(before, ENTRY, 332)
    image[at:at + 332] = span
    rows = [row for row in prior.symbol_rows(before) if row[1] == FUNCTION]
    if len(rows) != 1 or rows[0][2][1:3] != (ENTRY, 12):
        raise ValueError('Wrong vector predecessor extent')
    struct.pack_into('>I', image, rows[0][0] + 8, 332)
    with patch.object(source.installed, 'SYMBOL_ORDERS', SYMBOL_ORDERS):
        result = source.installed.metadata_order(bytes(image))
    if hashlib.sha256(result).hexdigest() != AFTER['conker/build/conker.us.elf']:
        raise ValueError('Changed first vector prediction')
    return result


def predict(root, out):
    values = freeze(root, out)
    _, padded, _ = qualify(root, out)
    make_shadow(root, out)
    script = raw_text(root / 'conker/build/conker.ld')
    old = 'build/src/game/' + OWNER + '.c.o'
    if script.count(old) != 1:
        raise ValueError('Unexpected vector linker input')
    ld = out / 'predicted.ld'
    ld.write_text(script.replace(old, padded.relative_to(root / 'conker').as_posix()))
    elf = out / 'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', str(ld.relative_to(root / 'conker')),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', str(elf.relative_to(root / 'conker'))], cwd=root / 'conker', capture_output=True, check=True)
    image = raw_read(elf)
    expected = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + 332])
    if image != expected:
        raise ValueError('First vector ELF prediction changed unrelated bytes')
    after = {'conker/build/conker.us.elf': image,
             'conker/src/game/generated_B3020.c': recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
             'conker/retail_word_patches.us.csv': raw_read(out / 'qualified-guards.csv')}
    for path, data in after.items():
        target = out / SUCCESSOR_FILES[path]
        if target.exists() and raw_read(target) != data:
            raise ValueError('Changed first vector successor: ' + path)
        if not target.exists():
            target.write_bytes(data)
    result = dict(after={path: hashlib.sha256(data).hexdigest() for path, data in after.items()},
                  changed_ELF_bytes=sum(a != b for a, b in zip(values['conker/build/conker.us.elf'], image)),
                  only_target_code_extent_and_closed_metadata_changed=True,
                  metadata_named_groups=len(SYMBOL_ORDERS))
    (out / 'prediction.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def expected_inputs(root, out):
    values = {path: raw_read(out / name) for path, name in SUCCESSOR_FILES.items()}
    if not AFTER or {path: hashlib.sha256(data).hexdigest() for path, data in values.items()} != AFTER:
        raise ValueError('Changed first vector successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(source.checkpoint, INPUTS=INPUTS, AFTER=AFTER, expected_inputs=expected_inputs):
        yield


@contextmanager
def historical_view(root, out):
    with checkpoint_context(), source.checkpoint.historical_view(root, out):
        yield


def verify(root, out, installed=False):
    with checkpoint_context():
        return source.checkpoint.verify(root, out, installed)


def install_guards(root, out):
    expected = expected_inputs(root, out)
    for path in ('conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'):
        before = raw_read(out / ('before-%02d' % list(INPUTS).index(path)))
        if raw_read(root / path) != before:
            raise ValueError('Unexpected vector installation stage: ' + path)
    if raw_read(root / 'conker/src/game/generated_B3020.c') != expected['conker/src/game/generated_B3020.c']:
        raise ValueError('Install qualified vector source first')
    prefix = raw_read(root / 'conker/retail_word_patches.us.csv')
    if not expected['conker/retail_word_patches.us.csv'].startswith(prefix):
        raise ValueError('Vector guard prefix changed')
    (root / 'conker/retail_word_patches.us.csv').write_bytes(expected['conker/retail_word_patches.us.csv'])


def audit(root, out):
    verify(root, out, True)
    for index, (path, digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out / ('before-%02d' % index))).hexdigest() != digest or \
                hashlib.sha256(raw_read(root / path)).hexdigest() != AFTER.get(path, digest):
            raise ValueError('Changed installed vector input: ' + path)
    predecessor = out / ('before-%02d' % list(INPUTS).index('conker/build/conker.us.elf'))
    before = raw_read(predecessor)
    actual = raw_read(root / 'conker/build/conker.us.elf')
    rom = raw_read(root / 'conker/conker.us.bin')
    if actual != raw_read(out / 'after-elf') or actual != predicted_image(before, rom[ROM:ROM + 332]):
        raise ValueError('Installed vector image differs from the first prediction')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    old, _, oa = load_elf_functions(str(predecessor), 'mips-linux-gnu-objdump')
    new, _, na = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if oa != na or old.keys() != new.keys() or [name for name in old if old[name] != new[name]] != [FUNCTION]:
        raise ValueError('Vector changed another linked body or address')
    source.model.same_functions(out / 'qualified-padded.o', root / 'conker/build/src/game/generated_B3020.c.o')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Vector changed protected Game data')
    result = dict(functions=len(old), all_addresses_fixed=True, only_target_body_extent_and_closed_metadata_changed=True,
                  metadata_named_groups=len(SYMBOL_ORDERS), first_prediction_reproduced=True,
                  changed_ELF_bytes=sum(a != b for a, b in zip(before, actual)), game_data=data)
    (out / 'installed-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(audit(root, root / BUILD) if args.audit else predict(root, root / BUILD), indent=2))
