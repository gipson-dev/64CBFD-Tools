"""Qualify crossing owner/Make isolation and an exact code-only ELF prediction."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from tools.experiments import game_barrier_crossing_home_fit as source
from tools.experiments import game_barrier_crossing_layout as layout
from tools.experiments import game_route_projection_integration as mixed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import emit_padded_assembly

BUILD = source.BUILD + '/integration'
NORMAL_FUNCTIONS = ('func_150891E8', 'func_1508BC20')


def guard_bytes(before, obj):
    return layout.private_guards(before, *source.payload(obj))


def padded(root, out, obj, name, guards, normal):
    script = out / (name + '.s')
    script.write_text(emit_padded_assembly(obj, root / 'conker/asm/B3020.s',
        function_objects={name: normal for name in NORMAL_FUNCTIONS},
        word_patches_path=guards, filename=source.OWNER))
    result = script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(result), str(script)], check=True, capture_output=True)
    return result


def qualify(root, out):
    values = source.freeze(root, out)
    same = mixed.candidate.source.neighbor.same_functions
    objects = {}
    for label, normal in (('primary', False), ('normal', True)):
        old, diagnostics = source.compile_profile(root, out, values[source.SOURCE].decode(), 'before-' + label, normal)
        new, _, row = source.compile_candidate(root, out, 'after-' + label, whole=True, normal=normal)
        layout.normalize(*source.payload(new))
        if diagnostics or row['diagnostics'] or same(old, new, (source.FUNCTION,)) != 72 or normalized_pools(old) != normalized_pools(new):
            raise ValueError('Crossing changed an owner neighbor, pool or compiler profile')
        objects[label] = new
    guards = guard_bytes(values['conker/retail_word_patches.us.csv'], objects['primary'])
    (out / 'qualified-guards.csv').write_bytes(guards)
    obj = padded(root, out, objects['primary'], 'qualified-padded', out / 'qualified-guards.csv', objects['normal'])
    baseline = out / 'before-padded.o'
    if not baseline.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_B3020.c.o', baseline)
    a, fa = source.link_owner(root, out, baseline, source.OWNER)
    b, fb = source.link_owner(root, out, obj, source.OWNER)
    at = fb[source.FUNCTION]['value']
    truth = values['conker/conker.us.bin'][source.ROM:source.ROM + 828]
    before = values['conker/build/conker.us.elf']
    slot = elf_slot_offset(before, source.ENTRY, 828)
    if a[at:at + 828] != before[slot:slot + 828] or b[at:at + 828] != truth:
        raise ValueError('Crossing padded predecessor or target bytes differ')
    if fa != fb or a[:at] != b[:at] or a[at + 828:] != b[at + 828:] or same(baseline, obj, (source.FUNCTION,)) != 72:
        raise ValueError('Crossing changed another owner address, extent or instruction')
    if normalized_pools(baseline) != normalized_pools(obj):
        raise ValueError('Crossing changed padded owner pools')
    (out / 'proposed-owner.c').write_text(source.recovered_owner(values[source.SOURCE].decode()))
    row = dict(words=207, frame=144, differences=0, guards=207, retained_source_origins=206,
        omitted_redundant_copy=1, derived_tangent_copy=1, all5_bindings_retained=True,
        neighbors_each_profile=72, all73_addresses_and_extents_fixed=True, normal_overrides_unchanged=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def predicted_image(before, truth):
    if hashlib.sha256(before).hexdigest() != source.INPUTS['conker/build/conker.us.elf'] or len(truth) != 828:
        raise ValueError('Unknown crossing image predecessor')
    rows = [row for row in symbol_rows(before) if row[1] == source.FUNCTION]
    if len(rows) != 1 or rows[0][2][1:3] != (source.ENTRY, 828):
        raise ValueError('Unknown crossing existing C symbol extent')
    result = bytearray(before)
    at = elf_slot_offset(before, source.ENTRY, 828)
    result[at:at + 828] = truth
    return bytes(result)


def check_image(before, actual, truth):
    expected = predicted_image(before, truth)
    if actual != expected:
        raise ValueError('Crossing image differs from the strict code-only prediction')
    return expected


def predict(root, out):
    values = source.freeze(root, out)
    elf = out / 'first-linked.elf'
    if not elf.exists():
        script = (root / 'conker/build/conker.ld').read_text()
        old = 'build/src/game/' + source.OWNER + '.c.o'
        if script.count(old) != 1:
            raise ValueError('Unknown crossing linker input')
        link = out / 'first-link.ld'
        link.write_text(script.replace(old, (out / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld', '-T', str(link.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str(elf.relative_to(root / 'conker'))], cwd=root / 'conker', check=True, capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    truth = values['conker/conker.us.bin'][source.ROM:source.ROM + 828]
    expected = predicted_image(before, truth)
    row = dict(exact_prediction=actual == expected, expected_SHA256=hashlib.sha256(expected).hexdigest(),
        actual_SHA256=hashlib.sha256(actual).hexdigest(), changed_bytes=sum(a != b for a, b in zip(before, actual)),
        symbol_or_metadata_bytes_changed=0)
    (out / 'first-link.json').write_text(json.dumps(row, indent=2) + '\n')
    check_image(before, actual, truth)
    return row


def make_shadow(root, out):
    shutil.copyfile(out / 'after-normal.o', out / 'override-normal.o')
    shutil.copyfile(out / 'after-primary.o', out / 'primary-no-unroll.o')
    with patch.multiple(mixed, freeze=source.freeze, recovered_owner=source.recovered_owner,
            recovered_makefile=lambda before: before,
            recovered_guards=lambda before, *unused: guard_bytes(before, out / 'after-primary.o')):
        result = mixed.make_shadow(root, out)
    actual = out / 'make-shadow/src/game/generated_B3020.c.o.compact'
    if source.payload(actual) != source.payload(out / 'after-primary.o'):
        raise ValueError('Crossing primary Make payload differs')
    result.pop('original_four_GLOBAL_ASM_bodies_preserved')
    result.update(GLOBAL_ASM_bodies_remaining=0, normal_override_functions=list(NORMAL_FUNCTIONS),
        target_is_primary_no_unroll=True, Makefile_unchanged=True)
    (out / 'make-shadow.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def install_guards(root, out):
    values = source.freeze(root, out)
    for name in ('conker/Makefile', 'conker/retail_word_patches.us.csv', 'conker/build/conker.us.elf'):
        if (root / name).read_bytes() != values[name]:
            raise ValueError('Changed crossing input before guard installation: ' + name)
    if (root / source.SOURCE).read_bytes() != source.recovered_owner(values[source.SOURCE].decode()).encode():
        raise ValueError('Unknown crossing source before guards')
    check_image(values['conker/build/conker.us.elf'], (out / 'first-linked.elf').read_bytes(),
        values['conker/conker.us.bin'][source.ROM:source.ROM + 828])
    (root / 'conker/retail_word_patches.us.csv').write_bytes(guard_bytes(
        values['conker/retail_word_patches.us.csv'], out / 'after-primary.o'))
    return dict(generated_guard_rows=207, historical_prefix_preserved=True)


def audit(root, out):
    values = source.freeze(root, out)
    before = values['conker/build/conker.us.elf']
    expected = predicted_image(before, values['conker/conker.us.bin'][source.ROM:source.ROM + 828])
    for name, old in values.items():
        wanted = source.recovered_owner(old.decode()).encode() if name == source.SOURCE else (
            guard_bytes(old, out / 'after-primary.o') if name == 'conker/retail_word_patches.us.csv' else
            expected if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != wanted:
            raise ValueError('Changed installed crossing input: ' + name)
    if (out / 'first-linked.elf').read_bytes() != expected:
        raise ValueError('Changed retained crossing first link')
    a, _, aa = load_elf_functions(str(out / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [name for name in a if a[name] != b[name]] != [source.FUNCTION]:
        raise ValueError('Crossing changed another linked body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Crossing changed protected Game data')
    row = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        exact_first_link_reproduced=True, all_symbol_extents_and_metadata_fixed=True,
        target_words=207, game_data=data)
    (out / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def build(root, out):
    values = source.freeze(root, out)
    if (root / source.SOURCE).read_bytes() != source.recovered_owner(values[source.SOURCE].decode()).encode() or (
            root / 'conker/retail_word_patches.us.csv').read_bytes() != guard_bytes(
                values['conker/retail_word_patches.us.csv'], out / 'after-primary.o'):
        raise ValueError('Unknown crossing production source/guards')
    log = out / 'production-build.log'
    with log.open('w') as stream:
        result = subprocess.run(['make', '-C', 'conker', '-j4', 'build/conker.us.elf', 'progress.csv'],
            cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError('Crossing production Make failed; inspect ' + str(log))
    return dict(exit_code=0, audit=audit(root, out))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ('predict', 'make-shadow', 'install-guards', 'build', 'audit'):
        p.add_argument('--' + flag, action='store_true')
    args = p.parse_args()
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
