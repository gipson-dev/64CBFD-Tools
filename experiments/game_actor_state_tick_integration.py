"""Actual owner, Make, padding and strict ELF gates for the actor-state tick."""

import argparse
import csv
import hashlib
import io
import json
import shlex
import shutil
import struct
import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_layout as layout
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, read_c_string, parse_object, emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools


core = layout.source.prior.prior.prior
BUILD = layout.BUILD + '/integration'
SOURCE, OWNER, FUNCTION = 'conker/src/game/generated_B3020.c', 'generated_B3020', core.FUNCTION
SIZE, ENTRY, ROM = 2712, core.ENTRY, core.ROM
SYMBOL_ORDER = (('D_8009DA20', '.L15032B30_game_data', 'D_8009D590'),
                ('D_800872E0', 'D_8008CEB0'))


def snapshot(root, output):
    values = {}
    for name, digest in core.INPUTS.items():
        path = output / ('before-' + name.replace('/', '_'))
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Actor-tick predecessor snapshot changed: ' + name)
        values[name] = data
    return values


def recovered_owner(before):
    lo, hi = core.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1508A6FC() {\n    return 0;\n}':
        raise ValueError('Unknown actor-tick source predecessor')
    declarations = core.DECLARATIONS.split('\n', 1)[1].replace(
        's32 func_1508CAD8(s32, s32, s32, s32, s32, s32);', 's32 func_1508CAD8();')
    return before[:lo] + declarations + '\n' + layout.source.SELECTED + before[hi:]


def same_functions(old, new, excluded=()):
    a, b = parse_object(old), parse_object(new)
    if set(a[1]) != set(b[1]):
        raise ValueError('Actor-tick owner function set changed')
    def body(parsed, name):
        f = parsed[1][name]
        return (parsed[0][f['value']:f['value'] + f['size']],
                {at - f['value']: rows for at, rows in parsed[2].items()
                 if f['value'] <= at < f['value'] + f['size']})
    for name in a[1]:
        if name not in excluded and body(a, name) != body(b, name):
            raise ValueError('Actor-tick neighbor changed: ' + name)
    return len(a[1]) - len(excluded)


def elf_slot_offset(data, address, size):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    matches = [h[4] + address - h[3] for h in headers
               if h[1] == 1 and h[3] <= address and address + size <= h[3] + h[5]]
    if len(matches) != 1:
        raise ValueError('Unknown actor-tick ELF slot')
    return matches[0]


def symbol_rows(data):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    rows = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for at in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, at)
            name = read_c_string(names, symbol[0])
            if name:
                rows.append((at, name, symbol, strings[4] + symbol[0]))
    return rows


def symbol_size_offset(data):
    matches = []
    for at, name, symbol, _ in symbol_rows(data):
        if name == FUNCTION:
            if symbol[1] != ENTRY or symbol[2] != 12 or symbol[3] & 15 != 2:
                raise ValueError('Unknown actor-tick predecessor symbol')
            matches.append(at + 8)
    if len(matches) != 1:
        raise ValueError('Ambiguous actor-tick symbol size')
    return matches[0]


def reorder_symbols(image):
    result = bytearray(image)
    rows = symbol_rows(image)
    entries = {name: (at, fields, string) for at, name, fields, string in rows}
    for names in SYMBOL_ORDER:
        group = [entries[name] for name in names]
        start, string_at = group[0][0], group[0][2]
        strings_base = string_at - group[0][1][0]
        if any(row[0] != start + n * SYMBOL.size or row[2] - row[1][0] != strings_base
               for n, row in enumerate(group)):
            raise ValueError('Unknown actor-tick bounded symbol order')
        old = b''.join(name.encode() + b'\0' for name in names)
        if image[string_at:string_at + len(old)] != old:
            raise ValueError('Unknown actor-tick bounded symbol strings')
        for n, name in enumerate(names[1:] + names[:1]):
            fields = list(entries[name][1])
            fields[0] = string_at - strings_base
            SYMBOL.pack_into(result, start + n * SYMBOL.size, *fields)
            literal = name.encode() + b'\0'
            result[string_at:string_at + len(literal)] = literal
            string_at += len(literal)
    canonical = lambda data: sorted((name, fields[1:]) for _, name, fields, _ in symbol_rows(data))
    if canonical(result) != canonical(image):
        raise ValueError('Actor-tick metadata permutation changed named definitions')
    return bytes(result)


def guard_bytes(values, output):
    return layout.private_guards(values['conker/retail_word_patches.us.csv'],
                                 *core.payload(output / 'after-primary.o'))


def qualify(root, output):
    values = core.freeze(root, output)
    unit = recovered_owner(values[SOURCE].decode())
    for label, normal in (('primary', False), ('normal', True)):
        a, da = core.compile_unit(root, output, 'before-' + label, values[SOURCE].decode(), normal)
        b, db = core.compile_unit(root, output, 'after-' + label, unit, normal)
        if da or db or same_functions(a, b, (FUNCTION,)) != 72:
            raise ValueError('Actor-tick changed another raw owner body')
        if normalized_pools(a) != normalized_pools(b):
            raise ValueError('Actor-tick changed raw pools')
        layout.normalize(*core.payload(b))
    guards = output / 'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values, output))
    asm = output / 'qualified-padded.s'
    asm.write_text(emit_padded_assembly(output / 'after-primary.o', root / 'conker/asm/B3020.s',
        function_objects={name: output / 'after-normal.o' for name in
                          ('func_150891E8', 'func_1508BC20', 'func_15089BC0')},
        word_patches_path=guards, filename=OWNER))
    obj = asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(asm)], check=True, capture_output=True)
    before = output / 'before-padded.o'
    if not before.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_B3020.c.o', before)
    a, fa = core.link_owner(root, output, before, OWNER)
    b, fb = core.link_owner(root, output, obj, OWNER)
    at = fb[FUNCTION]['value']
    old = values['conker/build/conker.us.elf']
    slot = elf_slot_offset(old, ENTRY, SIZE)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    if a[at:at + SIZE] != old[slot:slot + SIZE] or b[at:at + SIZE] != truth:
        raise ValueError('Actor-tick actual padding does not reproduce the target')
    expected = {name: dict(f) for name, f in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown actor-tick padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    if expected != fb or same_functions(before, obj, (FUNCTION,)) != 72:
        raise ValueError('Actor-tick changed padded neighbors/addresses/extents')
    if a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:] or normalized_pools(before) != normalized_pools(obj):
        raise ValueError('Actor-tick changed other padded bytes/pools')
    (output / 'proposed-owner.c').write_text(unit)
    rows = list(csv.DictReader(io.StringIO(guards.read_text())))
    count = sum(row['filename'] == OWNER and row['function'] == FUNCTION for row in rows)
    report = dict(words=678, frame=288, differences=0, expected_word_rows=count,
        retained_origins=675, derived_forms=3, conceptual_omissions=3, output_bindings=62,
        preserved_neighbors=72, all73_addresses_fixed=True, other72_extents_fixed=True,
        target_symbol_size_before=12, target_symbol_size_after=SIZE, Makefile_unchanged=True,
        prior_guard_bytes_exact_prefix=True, installed=False)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = core.freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Actor-tick shadow source changed')
    if (output / 'qualified-guards.csv').read_bytes() != guard_bytes(values, output):
        raise ValueError('Actor-tick shadow guards changed')
    conker = root / 'conker'
    shadow = output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_B3020.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
                          cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands, flags = [], []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor-tick shadow Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix() if a == 'src/game/generated_B3020.c'
                else (output / 'qualified-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        if args[0] == '../ido/ido5.3_recomp/cc':
            flags.append(args.count('-Wo,-loopunroll,0'))
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unexpected actor-tick shadow redirection')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        if process.returncode or process.stderr or process.stdout and redirect is None:
            raise ValueError('Actor-tick shadow command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    if len(commands) != 7 or flags != [1, 0]:
        raise ValueError('Actor-tick Make profiles changed')
    if same_functions(output / 'after-primary.o', Path(str(actual) + '.compact')) != 73:
        raise ValueError('Actor-tick Make primary output differs')
    if core.payload(Path(str(actual) + '.normal.compact')) != core.payload(output / 'after-normal.o'):
        raise ValueError('Actor-tick Make normal output differs')
    if core.link_owner(root, output, output / 'qualified-padded.o', OWNER) != core.link_owner(root, output, actual, OWNER):
        raise ValueError('Actor-tick actual Make padding/metadata differs')
    row = dict(actual_expanded_Make_commands=7, profile_flags=flags, primary_all73_functions_equal=True,
               normal_payload_equal=True, padded_code_and_metadata_equal=True,
               production_inputs_untouched=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def predicted_image(before, truth):
    if hashlib.sha256(before).hexdigest() != core.INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Actor-tick image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    struct.pack_into('>I', result, symbol_size_offset(before), SIZE)
    return reorder_symbols(bytes(result))


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Actor-tick image differs from strict target and closed-metadata prediction')


def predict(root, output):
    values = core.freeze(root, output)
    link = output / 'first-link.ld'
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_B3020.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown actor-tick link input')
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    check_image(before, actual, truth)
    changed = sum(a != b for a, b in zip(before, actual))
    target_at = elf_slot_offset(before, ENTRY, SIZE)
    code_changed = sum(a != b for a, b in zip(before[target_at:target_at + SIZE], truth))
    row = dict(exact_prediction=True, SHA256=hashlib.sha256(actual).hexdigest(),
               changed_bytes=changed, target_code_bytes_changed=code_changed,
               metadata_bytes_changed=changed - code_changed, metadata_symbol_order_groups=2,
               only_target_size_and_closed_symbol_order_changed=True)
    (output / 'first-link.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def audit(root, output):
    values = snapshot(root, output)
    expected = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        wanted = recovered_owner(old.decode()).encode() if name == SOURCE else (
            guard_bytes(values, output) if name == 'conker/retail_word_patches.us.csv' else
            expected if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != wanted:
            raise ValueError('Actor-tick installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != expected:
        raise ValueError('Actor-tick retained first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Actor-tick changed another linked body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Actor-tick changed protected Game data')
    row = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
               exact_first_link_reproduced=True, target_words=678, game_data=data, Makefile_unchanged=True)
    (output / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


@contextmanager
def fixture_context(root):
    if hashlib.sha256((root / SOURCE).read_bytes()).hexdigest() == core.INPUTS[SOURCE]:
        yield False
        return
    output = root / BUILD
    audit(root, output)
    values = snapshot(root, output)

    def frozen(_root, target):
        target.mkdir(parents=True, exist_ok=True)
        for name, data in values.items():
            path = target / ('before-' + name.replace('/', '_'))
            if path.exists() and path.read_bytes() != data:
                raise ValueError('Actor-tick historical fixture changed: ' + name)
            if not path.exists():
                path.write_bytes(data)
        return values

    with patch.object(core, 'freeze', frozen):
        yield True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    if args.audit:
        print(json.dumps(audit(root, output), indent=2))
    else:
        for action in (qualify, make_shadow, predict):
            print(json.dumps(action(root, output), indent=2), flush=True)


if __name__ == '__main__':
    main()
