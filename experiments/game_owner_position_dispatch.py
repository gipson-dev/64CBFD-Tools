"""Direct C actor-position dispatch, including closed overflow-removal accounting."""

import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, read_c_string, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object


FUNCTION, ENTRY, ROM, SIZE = 'func_15070C40', 0x15070C40, 0x9E0F0, 156
SOURCE, OWNER = 'conker/src/game_981E0.c', 'game_981E0'
BUILD = 'conker/build/game-owner-position-dispatch/qualified'
CURRENT, ACTORS, DISPATCH = 0x800D154C, 0x800CC2D0, 0x15103E40
OVERFLOW = '__retail_overflow_' + FUNCTION
INPUTS = {
    SOURCE: '95818fdb67454729c8e1903f350d81d876bbe13812a8882c9592e29d71e5e3ae',
    'conker/include/structs.h': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/retail_layout.us.txt': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5',
    'conker/build/conker.us.elf': '69b7bb9032dcf6d3c48b8e131d24e91b6da6fc96219252b6e551f48fb1e49e87',
    'conker/retail_word_patches.us.csv': '7ca8a25f8ea41d9e2e4a795281619c21048f5c24b252d48a9367eb5cd5e36e76',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
DECLARATIONS = '''#include <ultra64.h>
#include "structs.h"
extern struct127 *D_800D154C;
extern struct127 D_800CC2D0[26];
void func_15103E40(struct127 *, struct127 *, struct17 *, u8, s32, s32, s32);
'''
SELECTED = '''/* Dispatch the captured position using the current or selected actor. */
void func_15070C40(u8 mode) {
    struct17 position;
    struct127 *actor = D_800D154C;

    position.unk0 = actor->x_position;
    position.unk4 = actor->y_position;
    position.unk8 = actor->z_position;
    func_15103E40(actor->unk124 != 0 ? &D_800CC2D0[actor->unk124 - 1] : actor,
                 actor, &position, mode, 0, 0xFF, 0);
}'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {name: (output / ('before-' + name.replace('/', '_'))).read_bytes() for name in INPUTS}
    for name, data in values.items():
        if digest(data) != INPUTS[name]:
            raise ValueError('Position dispatch historical input changed: ' + name)
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Position dispatch predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Position dispatch frozen input changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    old = before[lo:hi]
    if not all(s in old for s in ('phi_a0 = temp_a1 = D_800D154C;', 'if (temp_a1->unk124 != 0)',
                                  'func_15103E40(phi_a0, temp_a1, &tmp, arg0, 0, 0xFF, 0);')):
        raise ValueError('Unknown position dispatch source predecessor')
    return before[:lo] + SELECTED + before[hi:]


def payload(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero position dispatch object tail')
    return raw[:end * 4], {at - f['value']: rows for at, rows in relocations.items()
                          if f['value'] <= at < f['value'] + end * 4}


def assemble(root, path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    asm = path.with_suffix('.s')
    asm.write_text(text)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                    '-I', str(root / 'conker/include'), '-o', str(path), str(asm)],
                   capture_output=True, check=True)
    return path


def original(root, output):
    # Recover symbolic assembly independently from retail opcodes, not the C object.
    words = list(struct.unpack_from('>39I', snapshot(output)['conker/conker.us.bin'], ROM))
    lines = ['.text', '.set noreorder', '.globl ' + FUNCTION, '.type ' + FUNCTION + ', @function', FUNCTION + ':']
    bindings = {4: ('lui $a1, %hi(D_800D154C)'), 5: ('lw $a1, %lo(D_800D154C)($a1)'),
                6: ('lui $t8, %hi(D_800CC2D0)'), 7: ('addiu $t8, $t8, %lo(D_800CC2D0)'),
                33: 'jal func_15103E40'}
    for i, word in enumerate(words):
        lines.append(bindings.get(i, '.word 0x%08X' % word))
    lines.append('.size ' + FUNCTION + ', . - ' + FUNCTION)
    return assemble(root, output / 'original.o', '\n'.join(lines) + '\n')


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Position dispatch compiler diagnostics changed')
    raw, bindings = payload(isolated)
    linked, funcs = link_owner(root, output, isolated, OWNER)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    at = funcs[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or payload(after) != (raw, bindings) or len(raw) != SIZE:
        raise ValueError('Position dispatch direct C/whole owner is not exact')
    if payload(original(root, output)) != (raw, bindings) or sum(map(len, bindings.values())) != 5:
        raise ValueError('Position dispatch independent original/bindings differ')
    if same_functions(before, after, (FUNCTION,)) != 327 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Position dispatch changed a neighbor or pool')
    obj = assemble(root, output / 'padded/game_981E0.c.o', pad_c_object.emit_padded_assembly(
        after, root / 'conker/retail_layout.us.txt', OWNER,
        word_patches_path=root / 'conker/retail_word_patches.us.csv'))
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game_981E0.c.o', old)
    if same_functions(old, obj, (FUNCTION,)) != 327 or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Position dispatch changed a padded neighbor/pool')
    a, b = sections(old), sections(obj)
    if a['.game_overflow'][1][:-160] != b['.game_overflow'][1]:
        raise ValueError('Position dispatch did not remove only its old terminal overflow')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=39, frame=64, differences=0, relocations=5, guards=0, compiler_only=True,
                  unchanged_raw_and_padded_neighbors=327, pools_unchanged=True,
                  old_raw_words=40, old_slot_words=39, removed_overflow_bytes=160,
                  owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    freeze(root, output)
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game_981E0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
                          cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('python3', '../ido/ido5.3_recomp/cc', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected position dispatch Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game_981E0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unexpected Make redirection')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        p = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        diagnostic = (output / 'after-owner-diagnostics.txt').read_text() if args[0].endswith('/cc') else ''
        if p.returncode or diagnostics(p.stderr + (p.stdout if redirect is None else '')) != diagnostics(diagnostic):
            raise ValueError('Position dispatch Make command failed: ' + p.stdout + p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [a for a in commands if a[0].endswith('/cc')]
    if len(commands) != 5 or len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2', '-g3')):
        raise ValueError('Position dispatch Make profile changed')
    if same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != 328:
        raise ValueError('Position dispatch actual Make raw functions differ')
    for name in ('.text', '.game_overflow'):
        if sections(actual)[name] != sections(output / 'padded/game_981E0.c.o')[name]:
            raise ValueError('Position dispatch actual Make padded content differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
                  cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def inspect_image(before_path, after_path, truth, conker):
    before, after = before_path.read_bytes(), after_path.read_bytes()
    a, b = sections(before_path), sections(after_path)
    if a.keys() != b.keys():
        raise ValueError('Position dispatch ELF section set changed')
    sa = {n: f[1:] for _, n, f, _ in symbol_rows(before)}
    sb = {n: f[1:] for _, n, f, _ in symbol_rows(after)}
    expected = dict(sa)
    address, size, *_ = expected.pop(OVERFLOW)
    if size != 160:
        raise ValueError('Unexpected position dispatch old overflow size')
    moved = {}
    for name, fields in sa.items():
        if name.startswith('__retail_overflow_') and fields[0] > address:
            expected[name] = (fields[0] - 160, *fields[1:])
            moved[fields[0]] = fields[0] - 160
    for name in ('debugger_overflow_ROM_START', '__romPos'):
        expected[name] = (sa[name][0] - 160, *sa[name][1:])
    if len(moved) != 6 or expected != sb:
        raise ValueError('Position dispatch ELF named definitions changed outside closed overflow accounting')
    old_overflow = a['.game_overflow'][1]
    offset = address - a['.game_overflow'][0]
    expected_overflow = old_overflow[:offset] + old_overflow[offset + 160:]
    if b['.game_overflow'] != (a['.game_overflow'][0], expected_overflow):
        raise ValueError('Position dispatch changed another overflow body')
    game = bytearray(a['.game'][1])
    start = ENTRY - a['.game'][0]
    game[start:start + SIZE] = truth
    trampolines = []
    for i in range(0, len(game), 4):
        if start <= i < start + SIZE:
            continue
        word = struct.unpack_from('>I', game, i)[0]
        target = ((a['.game'][0] + i + 4) & 0xF0000000) | ((word & 0x3FFFFFF) << 2)
        if word >> 26 == 2 and target in moved:
            struct.pack_into('>I', game, i, (word & 0xFC000000) | (moved[target] >> 2 & 0x3FFFFFF))
            trampolines.append(a['.game'][0] + i)
    if len(trampolines) != 4 or b['.game'] != (a['.game'][0], bytes(game)):
        raise ValueError('Position dispatch changed another Game instruction')
    metadata = {'.symtab', '.strtab'}
    for name in a.keys() - metadata - {'.game', '.game_overflow'}:
        if a[name] != b[name]:
            raise ValueError('Position dispatch changed protected ELF section: ' + name)
    # Reconstruct the complete ELF, including suffix-shared names and every
    # header/offset. No section or metadata bytes are excluded from the gate.
    header = list(ELF_HEADER.unpack_from(before))
    headers = [list(SECTION_HEADER.unpack_from(before, header[6] + i * header[11])) for i in range(header[12])]
    if (header[10], header[12], headers[8][3], headers[9][1], headers[10][1]) != (7,12,0x15F00000,2,3):
        raise ValueError('Unknown position dispatch ELF layout')
    strings = a['.strtab'][1]
    literal, anchor = OVERFLOW.encode() + b'\0', b'D_800E0DEC\0'
    if strings.count(literal) != 1 or strings.count(anchor) != 1:
        raise ValueError('Unknown position dispatch shared symbol strings')
    new_strings = strings.replace(literal, b'')
    at = new_strings.index(anchor) + len(anchor)
    new_strings = new_strings[:at] + FUNCTION.encode() + b'\0' + new_strings[at:]
    new_symbols = bytearray()
    old_symbols = a['.symtab'][1]
    for at in range(0, len(old_symbols), SYMBOL.size):
        fields = list(SYMBOL.unpack_from(old_symbols, at))
        name = read_c_string(strings, fields[0])
        if name == OVERFLOW:
            continue
        if name:
            fields[0] = new_strings.index(name.encode() + b'\0')
            fields[1:] = expected[name]
        new_symbols.extend(SYMBOL.pack(*fields))
    predicted = bytearray(before[:headers[8][4]])
    slot = elf_slot_offset(before, a['.game'][0], len(game))
    predicted[slot:slot + len(game)] = game
    predicted.extend(expected_overflow)
    headers[8][5] -= 160
    for index, content in ((9,bytes(new_symbols)),(10,new_strings),(11,a['.shstrtab'][1])):
        align = max(1, headers[index][8])
        predicted.extend(b'\0' * (-len(predicted) % align))
        headers[index][4], headers[index][5] = len(predicted), len(content)
        if index == 9:
            headers[index][7] -= 1
        predicted.extend(content)
    predicted.extend(b'\0' * (-len(predicted) % 4))
    header[6] = len(predicted)
    for fields in headers:
        predicted.extend(SECTION_HEADER.pack(*fields))
    ELF_HEADER.pack_into(predicted, 0, *header)
    ph_at = header[5] + 6 * header[9]
    ph = list(struct.unpack_from('>8I', before, ph_at))
    if ph[4:6] != [3072,3072]:
        raise ValueError('Unknown position dispatch overflow program header')
    ph[4] -= 160
    ph[5] -= 160
    struct.pack_into('>8I', predicted, ph_at, *ph)
    if predicted != after:
        raise ValueError('Position dispatch complete ELF differs from independent byte prediction')
    data = audit_layout(after_path, conker)
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Position dispatch protected Game data changed')
    return dict(retail_entry_addresses_fixed=True, unchanged_owner_neighbors=327,
                moved_overflow_bodies=6, moved_overflow_instructions_unchanged=True,
                removed_overflow_bytes=160, relocated_trampolines=trampolines,
                closed_symbol_changes=True, protected_sections_equal=True, game_data=data,
                complete_ELF_byte_prediction=True, metadata_exclusions=0)


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game_981E0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown position dispatch link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'padded/game_981E0.c.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
                    '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
                    '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
                    '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    report = inspect_image(output / 'before-conker_build_conker.us.elf', elf,
                           values['conker/conker.us.bin'][ROM:ROM + SIZE], root / 'conker')
    report['SHA256'] = digest(elf.read_bytes())
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else (
            (output / 'first-linked.elf').read_bytes() if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != expected:
            raise ValueError('Position dispatch installed input differs: ' + name)
    report = inspect_image(output / 'before-conker_build_conker.us.elf', root / 'conker/build/conker.us.elf',
                           values['conker/conker.us.bin'][ROM:ROM + SIZE], root / 'conker')
    report.update(first_link_reproduced_byte_for_byte=True, target_words=39, guards=0)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
