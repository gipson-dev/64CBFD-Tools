"""Inline descriptor-pair callback semantics and one checked branch operand swap."""

import csv
import io
import hashlib
import json
import re
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

SOURCE, OWNER, ASM = 'conker/src/game/generated_1E73B0.c', 'generated_1E73B0', 'conker/asm/1E73B0.s'
BUILD = 'conker/build/game-inline-pair-command/qualified'
OBJECT = 'conker/build/src/game/generated_1E73B0.c.o'
BEFORE_OBJECT_SHA = "8a41254ab5a08b4e6c87bb033a36a34c34a1836304d8b22b047bc8a0556f8525"
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/build/conker.us.elf": "a20101cab134c884657b2297912eb50fec0deb7b75da37d3ae46a877bf60e1fd",
    "conker/retail_word_patches.us.csv": "3df347b1965ccdb83b5d79e61efa890de8027d4116db62059b40769c9548dbb5",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/src/game/generated_1E73B0.c": "a856ec8a7a4d91f997db39865e2e59d0d133e3456667b71a50e17f4aa9432328",
    "conker/asm/1E73B0.s": "cf8247d9488c2a99d0c43f008a8564acd8b3652cb60e6a571b3b70a06a89ae56",
    "conker/src/game_1944C0.c": "328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b",
    "conker/asm/data/22FF90.rodata.s": "9150a226f309b306c5a590f6b5d18d9eaf6227c16cc1ae390454e91dd48902af",
    "conker/src/game_161520.c": "d3e9a447f86d0bb6f9dc4b5f36439a6fb079250042fb7eabc068854bac3dac12",
    "conker/asm/nonmatchings/game_161520/func_15134C98.s": "34f891146581cbd260841a95d1e311741d9f74ac2f535ff0f0d2b6332880fdc2",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BA518.s": "35a279b1aac9addbb4104f9fe4ac8814cc569f4de8448f0598acb74481d71a8c",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BBA9C.s": "72d581afbb71ba42707ae70a3023fe8015ae02f1d5834420ae2ce5adae918c7a",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BBEE4.s": "6e3cd7196f3910c77b059464493f4b0b7c7596f02238a7442c6fa911c98cb309",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BBFBC.s": "eaaa9a25dabd65edc5f11666f24a5fd7d2d8ca60237f7966a2a7b0a26cd33496",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BD828.s": "d7b5c586988bafc32cf57d2fd20ebb060dae5012a996025ed3c0b2878e863cdb",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BDD8C.s": "8441260e6404b164e779ee462e604f07b2d75c5d02f9b8350fd0482f32d6f3c5",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BE0AC.s": "21b55c5c4d7fce771ed397b4629ad8537eb9e38e876b12a2666572e2b9e9fb88",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BE138.s": "a079bc5a2eaad0d79c8bd2276da1d1f58348e691e8b5d193cb9d69f6afdc652a",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BE210.s": "48fad5829da93a1b1a0f7659db131de95aff239051c60453fa67bae268a2b74e",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BE4B8.s": "7e953def5447a1e7995e21edb239c9c9f59fdf8a1a2ea76efd8e9010c200bcf4",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BE558.s": "8dd13c73499b4fe01f46dc798dd909ec02805701d7e0e0f099e863f3b5ed4340",
    "conker/asm/nonmatchings/generated_1E73B0/func_151BE6CC.s": "c6c509329bc7e4ee5e9de97ea0d1999ae9327176a53d243b6ca8a64dcfd52d2f"
}
TARGETS = {
    'func_151BC5A4': dict(entry=0x151BC5A4, rom=0x1E9A54, size=168,
        SHA256='006f7d76bc4c09b30ad199c5bfea553ad2937600feda57d8287a2cc93df3a1e2'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = '#include "structs.h"\nvoid func_1516972C(struct102 *);\n'
SELECTED = {"func_151BC5A4":"/* Handle release notifications and update the inline descriptor pair. */\nvoid func_151BC5A4(struct102 *object, s32 eventAddress, u8 command) {\n    u8 *owner = (u8 *)object;\n    u8 *state = owner + 0x40;\n    s32 first = *(s32 *)state;\n    u8 *event = (u8 *)eventAddress;\n    s32 code = command;\n\n    if (command == 0) {\n        if (first == *(s32 *)event || event[4] == owner[0x44]) {\n            func_1516972C(object);\n        }\n    } else if (code == 0x2D) {\n        s32 value = *(s32 *)state;\n        first = *(s32 *)event;\n        if (first == value) {\n            *(s32 *)state = *(s32 *)(event + 4);\n            state[4] = event[9];\n        } else if (*(s32 *)(event + 4) == value) {\n            *(s32 *)state = first;\n            state[4] = event[8];\n        }\n    }\n}"}
BINDINGS = {64: [('R_MIPS_26', 'func_1516972C')]}



def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Inline pair command historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Inline pair command padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Inline pair command frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Inline pair command predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Inline pair command snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    result = before.replace('#include "structs.h"\n','',1)
    result = result.replace('#include <ultra64.h>\n','#include <ultra64.h>\n#include "structs.h"\n',1)
    result = result.replace('void func_1516972C(void *arg0);','void func_1516972C(struct102 *arg0);',1)
    lo, hi = function_span(result, 'func_151BFBFC')
    neighbor = result[lo:hi]
    if neighbor.count('func_1516972C(arg0);') != 1:
        raise ValueError('Unknown inline pair canonical helper call')
    result = result[:lo] + neighbor.replace('func_1516972C(arg0);','func_1516972C((struct102 *)arg0);') + result[hi:]
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown inline pair command predecessor: ' + name)
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero inline pair command alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output, name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ActorSelectorOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / ASM).read_text(), name)



def normalized(raw, bindings):
    if len(raw) != 168 or digest(raw) != TARGETS[FUNCTIONS[0]]['SHA256'] or bindings != BINDINGS:
        raise ValueError('Inline pair command raw body/bindings changed')
    words = list(struct.unpack('>42I', raw))
    word = words[33]
    if word != 0x548A0005:
        raise ValueError('Inline pair command branch predecessor changed')
    swapped = (word & ~0x03FF0000) | ((word >> 16 & 31) << 21) | ((word >> 21 & 31) << 16)
    if swapped != 0x55440005:
        raise ValueError('Inline pair command branch is not the same commutative equality test')
    words[33] = swapped
    return struct.pack('>42I', *words), dict(bindings)


def guard_bytes(old):
    if digest(old) != INPUTS['conker/retail_word_patches.us.csv']:
        raise ValueError('Inline pair command guard prefix changed')
    reader = csv.DictReader(io.StringIO(old.decode()))
    required = ['filename','function','offset','expected','replacement','expected_relocations',
                'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if reader.fieldnames != required or any(row['function'] in FUNCTIONS for row in reader):
        raise ValueError('Inline pair command guard schema/predecessor changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Inline pair command guard newline changed')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream,fieldnames=required,lineterminator=newline).writerow(dict(
        filename=OWNER,function=FUNCTIONS[0],offset='0x084',expected='0x548A0005',
        replacement='0x55440005',expected_relocations='-',replacement_relocations='-',
        note='Preserve retail commutative bnel register operand order',
        insert_after='',insert_after_relocations='',omit='false'))
    return old + stream.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    (output/'qualified-guards.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    neighbors_expected = len(parse_object(output/'before-padded.o')[1])-1
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Inline pair command owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        fitted, fitted_bindings = normalized(raw, bindings)
        if dc or len(raw) != target['size'] or digest(raw) != target['SHA256'] or bindings != BINDINGS:
            raise ValueError('Inline pair command isolated C differs: ' + name)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (fitted, fitted_bindings):
            raise ValueError('Inline pair command owner/GNU original differs: ' + name)
        linked, functions = link_owner(root, output, isolated, OWNER)
        at = functions[name]['value']; expected = bytearray(truth)
        struct.pack_into('>I',expected,132,0x548A0005)
        if linked[at:at+168] != expected:
            raise ValueError('Inline pair command has more than one branch operand difference')
        rows.append(dict(function=name, words=42, frame=24, bindings=1, new_guards=1))

    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != neighbors_expected or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Inline pair command raw owner neighbor/pool changed')
    padded = output / 'padded/generated_1E73B0.c.s'
    padded.parent.mkdir(parents=True,exist_ok=True)
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=output / 'qualified-guards.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Inline pair command frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown inline pair command predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Inline pair command predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Inline pair command padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Inline pair command padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Inline pair command padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != neighbors_expected or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Inline pair command padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(targets=rows, total_words=42, compiler_only=False, new_guards=1,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_sizes_before=[12], target_sizes_after=[168])
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Inline pair command shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1E73B0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected inline pair command Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1E73B0.c' else a for a in args]
        args = [(output/'qualified-guards.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown inline pair command Make redirect')
            redirect = (conker / args[-1]).resolve();redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Inline pair command Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Inline pair command Make changed the normal compiler profile')
    processors = [args for args in commands if args[:2] == ['python3', '../tools/asm-processor/asm_processor.py']]
    if len(processors) != 2 or not all('-O2' in args and '-g3' in args for args in processors):
        raise ValueError('Inline pair command changed the GLOBAL_ASM processing profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output/'before-padded.o')[1]):
        raise ValueError('Inline pair command actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'padded/generated_1E73B0.c.o', OWNER):
        raise ValueError('Inline pair command actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, asm_processor_commands=2, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Inline pair command strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Inline pair command symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Inline pair command image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1E73B0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown inline pair command link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'padded/generated_1E73B0.c.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    before, actual, rom = values['conker/build/conker.us.elf'], elf.read_bytes(), values['conker/conker.us.bin']
    check_image(before, actual, rom)
    changed = sum(a != b for a, b in zip(before, actual));code = 0
    for target in TARGETS.values():
        at = elf_slot_offset(before, target['entry'], target['size'])
        code += sum(a != b for a, b in zip(before[at:at + target['size']], rom[target['rom']:target['rom'] + target['size']]))
    report = dict(exact_prediction=True, SHA256=digest(actual), changed_bytes=changed,
        code_bytes_changed=code, metadata_bytes_changed=changed-code, metadata_exclusions=0)
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else guard_bytes(old) if name == 'conker/retail_word_patches.us.csv' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Inline pair command installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Inline pair command independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Inline pair command changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'padded/generated_1E73B0.c.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'padded/generated_1E73B0.c.o'):
        raise ValueError('Inline pair command installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Inline pair command protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=42, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
