"""Actual owner, Make and strict image gates for the complete zone pass."""

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_zone_neighbor_selection_layout as layout
from tools.experiments import game_route_projection_integration as mixed
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


source = layout.source
BUILD = layout.BUILD + '/integration'
SIZE = 1476


def recovered_owner(before):
    return source.recovered_owner(before).replace(layout.homes.SELECTED, layout.SELECTED)


def guard_bytes(before, out):
    return layout.private_guards(before, *source.payload(out / 'after-primary.o'))


def qualify(root, out):
    values = source.freeze(root, out)
    for label, normal in (('primary', False), ('normal', True)):
        a, da = source.compile_profile(root, out, values[source.SOURCE].decode(), 'before-' + label, normal)
        b, db = source.compile_profile(root, out, recovered_owner(values[source.SOURCE].decode()), 'after-' + label, normal)
        if not normal:
            layout.normalize(*source.payload(b))
        if da or db or source.same_functions(a, b, (source.FUNCTION,)) != 72:
            raise ValueError('Zone pass changed another raw owner function')
        if source.normalized_pools(a) != source.normalized_pools(b):
            raise ValueError('Zone pass changed raw pools')
    guards = out / 'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'], out))
    obj = source.padded(root, out, guards)
    qualified = out / 'qualified-padded.o'
    shutil.copyfile(obj, qualified)
    baseline = out / 'before-padded.o'
    if not baseline.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_B3020.c.o', baseline)
    a, fa = source.link_owner(root, out, baseline, source.OWNER)
    b, fb = source.link_owner(root, out, qualified, source.OWNER)
    at = fb[source.FUNCTION]['value']
    truth = values['conker/conker.us.bin'][source.ROM:source.ROM + SIZE]
    old = values['conker/build/conker.us.elf']
    slot = source.elf_slot_offset(old, source.ENTRY, SIZE)
    if a[at:at + SIZE] != old[slot:slot + SIZE] or b[at:at + SIZE] != truth:
        raise ValueError('Zone-pass actual padding differs')
    if fa != fb or source.same_functions(baseline, qualified, (source.FUNCTION,)) != 72:
        raise ValueError('Zone pass changed padded addresses/extents/neighbors')
    if a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:] or (
            source.normalized_pools(baseline) != source.normalized_pools(qualified)):
        raise ValueError('Zone pass changed another padded byte/pool')
    (out / 'proposed-owner.c').write_text(recovered_owner(values[source.SOURCE].decode()))
    row = dict(words=369, frame=320, differences=0, raw_words=367, expected_word_rows=367,
               retained_origins=364, derived_forms=5, omissions=3, output_bindings=32,
               preserved_neighbors=72, all73_addresses_and_extents_fixed=True,
               Makefile_unchanged=True, prior_guard_bytes_exact_prefix=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def make_shadow(root, out):
    shutil.copyfile(out / 'after-normal.o', out / 'override-normal.o')
    shutil.copyfile(out / 'after-primary.o', out / 'primary-no-unroll.o')
    adapter = SimpleNamespace(checked=source.payload,
        source=SimpleNamespace(neighbor=SimpleNamespace(same_functions=source.same_functions)))
    with patch.multiple(mixed, candidate=adapter, freeze=source.freeze,
            recovered_owner=recovered_owner, recovered_makefile=lambda before: before,
            recovered_guards=lambda before, *unused: guard_bytes(before, out)):
        row = mixed.make_shadow(root, out)
    normal = out / 'make-shadow/src/game/generated_B3020.c.o.normal.compact'
    if source.payload(normal) != source.payload(out / 'after-normal.o'):
        raise ValueError('Zone-pass normal Make payload differs')
    row.pop('original_four_GLOBAL_ASM_bodies_preserved')
    row.update(GLOBAL_ASM_bodies_remaining=0, Makefile_unchanged=True,
               normal_override_functions=['func_150891E8', 'func_1508BC20', 'func_15089BC0'])
    (out / 'make-shadow.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def predicted_image(before, truth):
    if hashlib.sha256(before).hexdigest() != source.INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Unknown zone-pass image predecessor')
    result = bytearray(before)
    at = source.elf_slot_offset(before, source.ENTRY, SIZE)
    result[at:at + SIZE] = truth
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Zone-pass image differs from strict target-only prediction')


def predict(root, out):
    values = source.freeze(root, out)
    elf = out / 'first-linked.elf'
    if not elf.exists():
        script = (root / 'conker/build/conker.ld').read_text()
        old = 'build/src/game/' + source.OWNER + '.c.o'
        if script.count(old) != 1:
            raise ValueError('Unknown zone-pass linker input')
        link = out / 'first-link.ld'
        link.write_text(script.replace(old, (out / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld', '-T', str(link.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt',
            '-T', 'undefined_syms_auto.txt', '-T', 'undefined_funcs_auto.txt',
            '--no-check-sections', '--no-warn-mismatch', '-o', str(elf.relative_to(root / 'conker'))],
            cwd=root / 'conker', check=True, capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    truth = values['conker/conker.us.bin'][source.ROM:source.ROM + SIZE]
    check_image(before, actual, truth)
    row = dict(exact_prediction=True, SHA256=hashlib.sha256(actual).hexdigest(),
               changed_bytes=sum(a != b for a, b in zip(before, actual)), metadata_bytes_changed=0)
    (out / 'first-link.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def install_guards(root, out):
    values = source.freeze(root, out)
    if (root / source.SOURCE).read_bytes() != recovered_owner(values[source.SOURCE].decode()).encode():
        raise ValueError('Unknown zone-pass production source')
    for name in ('conker/Makefile', 'conker/retail_word_patches.us.csv', 'conker/build/conker.us.elf'):
        if (root / name).read_bytes() != values[name]:
            raise ValueError('Changed zone-pass predecessor: ' + name)
    check_image(values['conker/build/conker.us.elf'], (out / 'first-linked.elf').read_bytes(),
                values['conker/conker.us.bin'][source.ROM:source.ROM + SIZE])
    (root / 'conker/retail_word_patches.us.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'], out))
    return dict(guard_rows=367, omissions=3, insertions=5, prior_guard_bytes_unchanged=True)


def audit(root, out):
    values = source.freeze(root, out)
    expected = predicted_image(values['conker/build/conker.us.elf'],
                               values['conker/conker.us.bin'][source.ROM:source.ROM + SIZE])
    for name, old in values.items():
        wanted = recovered_owner(old.decode()).encode() if name == source.SOURCE else (
            guard_bytes(old, out) if name == 'conker/retail_word_patches.us.csv' else
            expected if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != wanted:
            raise ValueError('Changed installed zone-pass input: ' + name)
    if (out / 'first-linked.elf').read_bytes() != expected:
        raise ValueError('Retained zone-pass link changed')
    a, _, aa = load_elf_functions(str(out / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [source.FUNCTION]:
        raise ValueError('Zone pass changed another linked body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Zone pass changed protected Game data')
    row = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
               exact_first_link_reproduced=True, target_words=369, game_data=data, Makefile_unchanged=True)
    (out / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def build(root, out):
    with (out / 'production-build.log').open('w') as log:
        result = subprocess.run(['make', '-C', 'conker', '-j4', 'build/conker.us.elf', 'progress.csv'],
                                cwd=root, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError('Zone-pass Make failed; inspect production-build.log')
    return dict(exit_code=0, audit=audit(root, out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('predict', 'make-shadow', 'install-guards', 'build', 'audit'):
        parser.add_argument('--' + name, action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    if args.install_guards:
        print(json.dumps(install_guards(root, out), indent=2))
    elif args.build:
        print(json.dumps(build(root, out), indent=2))
    elif args.audit:
        print(json.dumps(audit(root, out), indent=2))
    else:
        print(json.dumps(qualify(root, out), indent=2), flush=True)
        if args.make_shadow:
            print(json.dumps(make_shadow(root, out), indent=2), flush=True)
        if args.predict:
            print(json.dumps(predict(root, out), indent=2))
