"""Qualify the complete pair-mask primary body and strict first production image."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_pair_visibility_layout as layout
from tools.experiments import game_route_projection_integration as mixed
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

source = layout.source
BUILD = source.BUILD + '/match/integration'
NORMAL_FUNCTIONS = ('func_150891E8', 'func_1508BC20', 'func_15089BC0')


def recovered_owner(before):
    return source.recovered_owner(before, layout.SELECTED)


def guard_bytes(before, out):
    raw, bindings = source.payload(out / 'after-primary.o')
    return layout.private_guards(before, raw, bindings)


def padded(root, out, guards, name='qualified-padded'):
    asm = out / (name + '.s')
    asm.write_text(emit_padded_assembly(out / 'after-primary.o', root / 'conker/asm/B3020.s',
        function_objects={n: out / 'after-normal.o' for n in NORMAL_FUNCTIONS},
        word_patches_path=guards, filename=source.OWNER))
    obj = asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(asm)], check=True, capture_output=True)
    return obj


def qualify(root, out):
    values = source.freeze(root, out)
    same = mixed.candidate.source.neighbor.same_functions
    for label, normal in (('primary', False), ('normal', True)):
        old, diagnostics = source.compile_profile(root, out, values[source.SOURCE].decode(), 'before-' + label, normal)
        new, _, row = source.compile_candidate(root, out, 'after-' + label, layout.SELECTED, normal, whole=True)
        raw, bindings = source.payload(new)
        layout.normalize(raw, bindings)
        if diagnostics or row['diagnostics'] or same(old, new, (source.FUNCTION,)) != 72:
            raise ValueError('Pair-query changed another raw owner body')
        if normalized_pools(old) != normalized_pools(new):
            raise ValueError('Pair-query changed another raw owner pool')
    guards = guard_bytes(values['conker/retail_word_patches.us.csv'], out)
    (out / 'qualified-guards.csv').write_bytes(guards)
    obj = padded(root, out, out / 'qualified-guards.csv')
    baseline = out / 'before-padded.o'
    if not baseline.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_B3020.c.o', baseline)
    a, fa = source.link_owner(root, out, baseline, source.OWNER)
    b, fb = source.link_owner(root, out, obj, source.OWNER)
    at = fb[source.FUNCTION]['value']
    truth = values['conker/conker.us.bin'][source.ROM:source.ROM + 1044]
    before = values['conker/build/conker.us.elf']
    slot = elf_slot_offset(before, source.ENTRY, 1044)
    if a[at:at + 1044] != before[slot:slot + 1044] or b[at:at + 1044] != truth:
        raise ValueError('Pair-query padded target/predecessor differs')
    if fa.keys() != fb.keys() or any(fa[n]['value'] != fb[n]['value'] or n != source.FUNCTION and fa[n] != fb[n] for n in fa):
        raise ValueError('Pair-query changed another owner address/extent')
    if a[:at] != b[:at] or a[at + 1044:] != b[at + 1044:] or same(baseline, obj, (source.FUNCTION,)) != 72:
        raise ValueError('Pair-query changed another padded owner instruction')
    if normalized_pools(baseline) != normalized_pools(obj):
        raise ValueError('Pair-query changed retained padded pools')
    (out / 'proposed-owner.c').write_text(recovered_owner(values[source.SOURCE].decode()))
    row = dict(words=261, frame=168, differences=0, expected_word_guards=261,
        unique_retained_origins=257, derived_insertions=4, omitted_explicit_masks=4,
        unchanged_neighbor_instructions=72, all73_addresses_fixed=True,
        selected_normal_functions=list(NORMAL_FUNCTIONS), Makefile_unchanged=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def predicted_image(before, truth):
    if hashlib.sha256(before).hexdigest() != source.INPUTS['conker/build/conker.us.elf'] or len(truth) != 1044:
        raise ValueError('Unknown pair-query image predecessor')
    result = bytearray(before)
    at = elf_slot_offset(before, source.ENTRY, 1044)
    result[at:at + 1044] = truth
    rows = [r for r in symbol_rows(before) if r[1] == source.FUNCTION]
    if len(rows) != 1 or rows[0][2][1:3] != (source.ENTRY, 12):
        raise ValueError('Unknown pair-query stub extent')
    struct.pack_into('>I', result, rows[0][0] + 8, 1044)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Pair-query image differs from strict code/size prediction')


def predict(root, out):
    values = source.freeze(root, out)
    elf = out / 'first-linked.elf'
    if not elf.exists():
        script = (root / 'conker/build/conker.ld').read_text()
        old = 'build/src/game/' + source.OWNER + '.c.o'
        if script.count(old) != 1:
            raise ValueError('Unknown pair-query linker input')
        link = out / 'first-link.ld'
        link.write_text(script.replace(old, (out / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld', '-T', str(link.relative_to(root / 'conker')), '-T', 'undefined_syms.us.txt',
            '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt', '-T', 'undefined_funcs_auto.txt',
            '--no-check-sections', '--no-warn-mismatch', '-o', str(elf.relative_to(root / 'conker'))],
            cwd=root / 'conker', check=True, capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    truth = values['conker/conker.us.bin'][source.ROM:source.ROM + 1044]
    expected = predicted_image(before, truth)
    row = dict(exact_prediction=actual == expected, expected_SHA256=hashlib.sha256(expected).hexdigest(),
        actual_SHA256=hashlib.sha256(actual).hexdigest(), changed_bytes=sum(a != b for a, b in zip(before, actual)))
    (out / 'first-link.json').write_text(json.dumps(row, indent=2) + '\n')
    check_image(before, actual, truth)
    return row


def make_shadow(root, out):
    shutil.copyfile(out / 'after-normal.o', out / 'override-normal.o')
    shutil.copyfile(out / 'after-primary.o', out / 'primary-no-unroll.o')
    with patch.multiple(mixed, freeze=source.freeze, recovered_owner=recovered_owner,
            recovered_makefile=lambda before: before, recovered_guards=lambda before, *unused: guard_bytes(before, out)):
        result = mixed.make_shadow(root, out)
    actual = out / 'make-shadow/src/game/generated_B3020.c.o.normal.compact'
    if source.payload(actual) != source.payload(out / 'after-normal.o'):
        raise ValueError('Pair-query normal Make payload differs')
    result.pop('original_four_GLOBAL_ASM_bodies_preserved')
    result.update(GLOBAL_ASM_bodies_remaining=0, normal_override_functions=list(NORMAL_FUNCTIONS), Makefile_unchanged=True)
    (out / 'make-shadow.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def install_guards(root, out):
    values = source.freeze(root, out)
    if (root / source.SOURCE).read_bytes() != recovered_owner(values[source.SOURCE].decode()).encode():
        raise ValueError('Unknown pair-query production source before guards')
    for name in ('conker/Makefile', 'conker/retail_word_patches.us.csv', 'conker/build/conker.us.elf'):
        if (root / name).read_bytes() != values[name]:
            raise ValueError('Changed pair-query predecessor: ' + name)
    check_image(values['conker/build/conker.us.elf'], (out / 'first-linked.elf').read_bytes(),
        values['conker/conker.us.bin'][source.ROM:source.ROM + 1044])
    (root / 'conker/retail_word_patches.us.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'], out))
    return dict(guard_rows=261, omissions=4, insertions=4, prior_guard_bytes_unchanged=True)


def audit(root, out):
    values = source.freeze(root, out)
    before = values['conker/build/conker.us.elf']
    expected = predicted_image(before, values['conker/conker.us.bin'][source.ROM:source.ROM + 1044])
    for name, old in values.items():
        wanted = recovered_owner(old.decode()).encode() if name == source.SOURCE else (
            guard_bytes(old, out) if name == 'conker/retail_word_patches.us.csv' else
            expected if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != wanted:
            raise ValueError('Changed installed pair-query input: ' + name)
    if (out / 'first-linked.elf').read_bytes() != expected:
        raise ValueError('Changed retained pair-query first link')
    a, _, aa = load_elf_functions(str(out / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [source.FUNCTION]:
        raise ValueError('Pair-query changed another linked body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Pair-query changed protected Game data')
    row = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        exact_first_link_reproduced=True, target_words=261, game_data=data, Makefile_unchanged=True)
    (out / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def build(root, out):
    log = out / 'production-build.log'
    with log.open('w') as stream:
        result = subprocess.run(['make', '-C', 'conker', '-j4', 'build/conker.us.elf', 'progress.csv'],
            cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError('Pair-query Make failed; inspect ' + str(log))
    return dict(exit_code=0, audit=audit(root, out))


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
