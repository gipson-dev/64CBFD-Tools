"""Complete descriptor-pair callback with one checked commutative branch operand swap."""

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

SOURCE, OWNER, ASM = 'conker/src/game/generated_11C2B0.c', 'generated_11C2B0', 'conker/asm/11C2B0.s'
BUILD = 'conker/build/game-descriptor-pair-command/qualified'
OBJECT = 'conker/build/src/game/generated_11C2B0.c.o'
BEFORE_OBJECT_SHA = "4ec8eec907e6ef290d5f43a40d32b327347f5b7dab97b97211572bbb194bdd38"
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
    "conker/build/conker.us.elf": "2e6c870c43314ed068cbf2d51ddb8731b30a1ac0cf38b7fb4275885d99be35e8",
    "conker/retail_word_patches.us.csv": "633b877110c36117635f293063e929c0a7c161480742271ee49f4259406a687f",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/src/game/generated_11C2B0.c": "5df88b0670453317f53006bff864411424255b55e4978347ca3f891519c48265",
    "conker/src/game/generated_1D4E00.c": "7ea32c22fa28c6dabc28705a6480e9299c564dcda606ae120f46b41b979cfe18",
    "conker/src/game_1944C0.c": "328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b",
    "conker/asm/11C2B0.s": "064851c4bd1d09f2eec8dc0b3bbfa579b8e028d24e94c8ce4468d5a1732403db",
    "conker/asm/1D4E00.s": "3b42f9752dbaaf6e4141b6b41581c4c9c86a743567cc69e1cb2c6d2d23185afd",
    "conker/asm/data/234400.rodata.s": "d6168fdd7a677621640e79c747902e0f540671f6fe68fd329741a4de764d1d16"
}
TARGETS = {
    'func_150F07E4': dict(entry=0x150F07E4, rom=0x11DC94, size=168,
        SHA256='dab79f4636f22700ae9848faf934e8c853bb6de256551d9ff4a7e2892e15e84c'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = 'void func_1516972C(struct102 *);\n'
SELECTED = {'func_150F07E4': "/* Handle release notifications and swap the selected descriptor pair. */\nvoid func_150F07E4(u8 *owner, s32 eventAddress, u8 command) {\n    u8 *state = *(u8 **)(owner + 0x60);\n    u8 *event = (u8 *)eventAddress;\n    s32 value = command;\n\n    if (command == 0) {\n        value = *(s32 *)event;\n        if (value == *(s32 *)state || state[4] == event[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (value == 0x2D) {\n        s32 first = *(s32 *)event;\n        value = *(s32 *)state;\n        if (first == value) {\n            *(s32 *)state = *(s32 *)(event + 4);\n            state[4] = event[9];\n        } else if (*(s32 *)(event + 4) == value) {\n            *(s32 *)state = first;\n            state[4] = event[8];\n        }\n    }\n}"}
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
            raise ValueError('Descriptor pair command historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Descriptor pair command padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Descriptor pair command frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Descriptor pair command predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Descriptor pair command snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    result = before.replace('#include "structs.h"\n','#include "structs.h"\n'+DECLARATIONS,1)
    if result.count('func_1516972C(arg0);') != 2:
        raise ValueError('Descriptor pair command known neighboring calls changed')
    result = result.replace('func_1516972C(arg0);','func_1516972C((struct102 *)arg0);')
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown descriptor pair command predecessor: ' + name)
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero descriptor pair command alignment tail')
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
        raise ValueError('Descriptor pair command raw body/bindings changed')
    words = list(struct.unpack('>42I', raw))
    word = words[33]
    if word != 0x546A0005:
        raise ValueError('Descriptor pair command branch predecessor changed')
    swapped = (word & ~0x03FF0000) | ((word >> 16 & 31) << 21) | ((word >> 21 & 31) << 16)
    if swapped != 0x55430005:
        raise ValueError('Descriptor pair command branch is not the same commutative equality test')
    words[33] = swapped
    return struct.pack('>42I', *words), dict(bindings)


def guard_bytes(old):
    if digest(old) != INPUTS['conker/retail_word_patches.us.csv']:
        raise ValueError('Descriptor pair command guard prefix changed')
    reader = csv.DictReader(io.StringIO(old.decode()))
    required = ['filename','function','offset','expected','replacement','expected_relocations',
                'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if reader.fieldnames != required or any(row['function'] in FUNCTIONS for row in reader):
        raise ValueError('Descriptor pair command guard schema/predecessor changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Descriptor pair command guard newline changed')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream,fieldnames=required,lineterminator=newline).writerow(dict(
        filename=OWNER,function=FUNCTIONS[0],offset='0x084',expected='0x546A0005',
        replacement='0x55430005',expected_relocations='-',replacement_relocations='-',
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
        raise ValueError('Descriptor pair command owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n#include "structs.h"\n' + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        fitted, fitted_bindings = normalized(raw, bindings)
        if dc or len(raw) != target['size'] or digest(raw) != target['SHA256'] or bindings != BINDINGS:
            raise ValueError('Descriptor pair command isolated C differs: ' + name)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (fitted, fitted_bindings):
            raise ValueError('Descriptor pair command owner/GNU original differs: ' + name)
        linked, functions = link_owner(root, output, isolated, OWNER)
        at = functions[name]['value']; expected = bytearray(truth)
        struct.pack_into('>I',expected,132,0x546A0005)
        if linked[at:at+168] != expected:
            raise ValueError('Descriptor pair command has more than one branch operand difference')
        rows.append(dict(function=name, words=42, frame=24, bindings=1, new_guards=1))

    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != neighbors_expected or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Descriptor pair command raw owner neighbor/pool changed')
    padded = output / 'padded/generated_11C2B0.c.s'
    padded.parent.mkdir(parents=True,exist_ok=True)
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=output / 'qualified-guards.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Descriptor pair command frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown descriptor pair command predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Descriptor pair command predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Descriptor pair command padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Descriptor pair command padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Descriptor pair command padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != neighbors_expected or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Descriptor pair command padded neighbors/pools changed')
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
        raise ValueError('Descriptor pair command shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_11C2B0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected descriptor pair command Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_11C2B0.c' else a for a in args]
        args = [(output/'qualified-guards.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown descriptor pair command Make redirect')
            redirect = (conker / args[-1]).resolve();redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Descriptor pair command Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Descriptor pair command Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output/'before-padded.o')[1]):
        raise ValueError('Descriptor pair command actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'padded/generated_11C2B0.c.o', OWNER):
        raise ValueError('Descriptor pair command actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Descriptor pair command strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Descriptor pair command symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Descriptor pair command image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_11C2B0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown descriptor pair command link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'padded/generated_11C2B0.c.o').relative_to(root / 'conker').as_posix()))
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
            raise ValueError('Descriptor pair command installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Descriptor pair command independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Descriptor pair command changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'padded/generated_11C2B0.c.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'padded/generated_11C2B0.c.o'):
        raise ValueError('Descriptor pair command installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Descriptor pair command protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=42, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
