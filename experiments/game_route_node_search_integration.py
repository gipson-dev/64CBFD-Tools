"""Actual owner/Make/padding and strict first-image gates for route search."""

import csv
import hashlib
import io
import json
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
from contextlib import contextmanager
from unittest.mock import patch

from tools.experiments import game_route_node_search_layout as layout
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


core = layout.core
SOURCE, OWNER, FUNCTION = core.SOURCE, core.OWNER, core.FUNCTION
ENTRY, ROM, SIZE = core.ENTRY, core.ROM, 2156
BUILD = layout.BUILD + '/integration'
EXTRA_POSITIONS = {97, 149, 309, 338}


def recovered_makefile(before):
    anchor = '--function-object func_15089BC0=$@.normal.compact'
    added = ' --function-object func_15086364=$@.normal.compact'
    if before.count(anchor) != 1 or added in before:
        raise ValueError('Unknown route-search owner profile predecessor')
    return before.replace(anchor, anchor + added)


def snapshot(output):
    values = {}
    for name, digest in core.INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Route-search predecessor snapshot changed: ' + name)
        values[name] = data
    return values


def guard_bytes(before, raw, bindings):
    if hashlib.sha256(before).hexdigest() != core.INPUTS['conker/retail_word_patches.us.csv']:
        raise ValueError('Unknown route-search guard predecessor')
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(row['filename'] == OWNER and row['function'] == FUNCTION for row in reader):
        raise ValueError('Route-search guards already exist')
    normalized, moved = layout.normalize(raw, bindings)
    old, new = struct.unpack('>535I', raw), struct.unpack('>539I', normalized)
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows, cursor = [], 0
    for i, word in enumerate(old):
        target = cursor
        cursor += 1
        inserted = cursor if cursor in EXTRA_POSITIONS else None
        if inserted is not None:
            if new[inserted] >> 26 not in (35, 43) or new[inserted] & 65535 != 0x600:
                raise ValueError('Route-search inserted word is not its real start spill')
            cursor += 1
        rows.append(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % word, replacement='0x%08X' % new[target],
            expected_relocations=spec(bindings.get(i * 4, [])),
            replacement_relocations=spec(moved.get(target * 4, [])),
            note='Linearize checked route-search C origins, lifetimes and scheduling',
            insert_after='' if inserted is None else '0x%08X' % new[inserted],
            insert_after_relocations='' if inserted is None else spec(moved.get(inserted * 4, [])),
            omit='false'))
    if cursor != 539:
        raise ValueError('Route-search linearized guard extent changed')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + stream.getvalue().encode()


def qualify(root, output):
    values = core.freeze(root, output)
    unit = core.recovered_owner(values[SOURCE].decode(), layout.SELECTED)
    for label, normal in (('primary', False), ('normal', True)):
        a, da = core.compile_profile(root, output, values[SOURCE].decode(), 'before-' + label, normal)
        b, db = core.compile_profile(root, output, unit, 'after-' + label, normal)
        if da or db or same_functions(a, b, (FUNCTION,)) != 72 or normalized_pools(a) != normalized_pools(b):
            raise ValueError('Route-search changed another raw owner body/pool')
    raw, bindings = core.payload(output / 'after-normal.o')
    layout.normalize(raw, bindings)
    guards = output / 'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'], raw, bindings))
    asm = output / 'qualified-padded.s'
    asm.write_text(emit_padded_assembly(output / 'after-primary.o', root / 'conker/asm/B3020.s',
        function_objects={name: output / 'after-normal.o' for name in
            ('func_150891E8', 'func_1508BC20', 'func_15089BC0', FUNCTION)},
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
        raise ValueError('Route-search actual padding changed the target image')
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown route-search predecessor symbol extent')
    expected[FUNCTION]['size'] = SIZE
    if expected != fb or same_functions(before, obj, (FUNCTION,)) != 72:
        raise ValueError('Route-search changed padded neighbors/addresses/extents')
    if a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:] or normalized_pools(before) != normalized_pools(obj):
        raise ValueError('Route-search changed other padded bytes/pools')
    (output / 'proposed-owner.c').write_text(unit)
    (output / 'proposed-Makefile').write_text(recovered_makefile(values['conker/Makefile'].decode()))
    report = dict(words=539, frame=1536, differences=0, expected_word_rows=535,
        inserted_start_words=4, preserved_neighbors=72, all73_addresses_fixed=True,
        target_symbol_size_before=12, target_symbol_size_after=SIZE,
        prior_guard_bytes_exact_prefix=True, installed=False)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = core.freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != core.recovered_owner(values[SOURCE].decode(), layout.SELECTED):
        raise ValueError('Route-search shadow source changed')
    if (output / 'proposed-Makefile').read_text() != recovered_makefile(values['conker/Makefile'].decode()):
        raise ValueError('Route-search shadow Makefile changed')
    if (output / 'qualified-guards.csv').read_bytes() != guard_bytes(
            values['conker/retail_word_patches.us.csv'], *core.payload(output / 'after-normal.o')):
        raise ValueError('Route-search shadow guards changed')
    conker = root / 'conker'
    shadow = output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_B3020.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-f', (output / 'proposed-Makefile').relative_to(conker).as_posix(),
        '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands, flags = [], []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected route-search shadow command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix() if a == 'src/game/generated_B3020.c'
            else (output / 'qualified-guards.csv').relative_to(conker).as_posix()
            if a == 'retail_word_patches.us.csv' else a for a in args]
        if args[0] == '../ido/ido5.3_recomp/cc':
            flags.append(args.count('-Wo,-loopunroll,0'))
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown route-search shadow redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        if process.returncode or process.stderr or process.stdout and redirect is None:
            raise ValueError('Route-search shadow command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    if len(commands) != 7 or flags != [1, 0]:
        raise ValueError('Route-search actual Make profiles changed')
    if same_functions(output / 'after-primary.o', Path(str(actual) + '.compact')) != 73:
        raise ValueError('Route-search Make primary differs')
    if core.payload(Path(str(actual) + '.normal.compact')) != core.payload(output / 'after-normal.o'):
        raise ValueError('Route-search Make normal target differs')
    if core.link_owner(root, output, output / 'qualified-padded.o', OWNER) != core.link_owner(root, output, actual, OWNER):
        raise ValueError('Route-search actual Make padding/metadata differs')
    report = dict(actual_expanded_Make_commands=7, profile_flags=flags,
        primary_all73_functions_equal=True, normal_payload_equal=True,
        padded_code_and_metadata_equal=True, production_inputs_untouched=True,
        inherited_Make_warnings=plan.stderr, cleanup_skipped=True)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def symbol_size_offset(data):
    matches = [at + 8 for at, name, fields, _ in symbol_rows(data)
        if name == FUNCTION and fields[1] == ENTRY and fields[2] == 12 and fields[3] & 15 == 2]
    if len(matches) != 1:
        raise ValueError('Unknown route-search symbol size')
    return matches[0]


def predicted_image(before, truth):
    if hashlib.sha256(before).hexdigest() != core.INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Route-search image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    struct.pack_into('>I', result, symbol_size_offset(before), SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Route-search image differs from its strict target/size prediction')


def predict(root, output):
    values = core.freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_B3020.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown route-search link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    expected = predicted_image(before, truth)
    if actual != expected:
        mismatches = [i for i, (a, b) in enumerate(zip(actual, expected)) if a != b]
        (output / 'unexpected-image-differences.json').write_text(json.dumps(dict(
            actual_size=len(actual), expected_size=len(expected), different_bytes=len(mismatches),
            first_offsets=mismatches[:100]), indent=2) + '\n')
        raise ValueError('Route-search first image differs from strict target/size prediction')
    changed = sum(a != b for a, b in zip(before, actual))
    at = elf_slot_offset(before, ENTRY, SIZE)
    code_changed = sum(a != b for a, b in zip(before[at:at + SIZE], truth))
    report = dict(exact_prediction=True, SHA256=hashlib.sha256(actual).hexdigest(),
        changed_bytes=changed, target_code_bytes_changed=code_changed,
        metadata_bytes_changed=changed - code_changed,
        only_target_body_and_symbol_size_changed=True)
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    expected = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        if name == SOURCE:
            wanted = core.recovered_owner(old.decode(), layout.SELECTED).encode()
        elif name == 'conker/Makefile':
            wanted = recovered_makefile(old.decode()).encode()
        elif name == 'conker/retail_word_patches.us.csv':
            wanted = guard_bytes(old, *core.payload(output / 'after-normal.o'))
        elif name == 'conker/build/conker.us.elf':
            wanted = expected
        else:
            wanted = old
        if (root / name).read_bytes() != wanted:
            raise ValueError('Route-search installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != expected:
        raise ValueError('Route-search first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Route-search changed another linked body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Route-search changed protected Game data')
    row = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=539, exact_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


@contextmanager
def fixture_context(root):
    if hashlib.sha256((root / SOURCE).read_bytes()).hexdigest() == core.INPUTS[SOURCE]:
        yield False
        return
    output = root / BUILD
    audit(root, output)
    values = snapshot(output)

    def frozen(_root, target):
        target.mkdir(parents=True, exist_ok=True)
        for name, data in values.items():
            path = target / ('before-' + name.replace('/', '_'))
            if path.exists() and path.read_bytes() != data:
                raise ValueError('Route-search historical fixture changed: ' + name)
            if not path.exists():
                path.write_bytes(data)
        return values

    with patch.object(core, 'freeze', frozen):
        yield True


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    for action in (qualify, make_shadow, predict):
        print(json.dumps(action(root, output), indent=2), flush=True)


if __name__ == '__main__':
    main()
