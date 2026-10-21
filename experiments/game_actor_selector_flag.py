"""Three direct actor selector callbacks with closed owner, Make and image gates."""

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

SOURCE, OWNER, ASM = 'conker/src/game/generated_1048D0.c', 'generated_1048D0', 'conker/asm/1048D0.s'
BUILD = 'conker/build/game-actor-selector-flag/qualified'
OBJECT = 'conker/build/src/game/generated_1048D0.c.o'
BEFORE_OBJECT_SHA = '1986734cc845ec5722487fe02e2ef1326e74074154750b4497083d5f85f7b360'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/src/game/generated_1048D0.c": "d41942fc0e89e60b2589005f2f8d0f8abffbb39f3797130eed4973008f461a76",
    "conker/asm/1048D0.s": "5f63166fdc7311e18d41911a08693f9d25ec4b0a081335aa7bd00772b2aa1389",
    "conker/asm/nonmatchings/generated_1048D0/func_150D765C.s": "81398da8c40b721763dcbe8bf77e770973a13f8b59cccca03e879cdaa61a07e6",
    "conker/asm/nonmatchings/generated_1048D0/func_150D7790.s": "779b9c172c1460860d5b7aec3958496db594dbeabad7c462285a14d1451584fc",
    "conker/asm/nonmatchings/game_16DC80/func_151416E8.s": "dc2b97a14a1a0162720dfb077a6912476c284dcacce7c79c23c1d248b309246b",
    "conker/src/game_16DC80.c": "48500431bc85a41ebb7833a93fc09f6b3b2704312b83316ca547b32a8fc3a966",
    "conker/asm/data/22E730.rodata.s": "04adc08432aaa1052219d977d68d9769ac85e1efca4aa89b8b35b8cddedf8413",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/build/conker.us.elf": "4f4aa719ec9d5aa01e5993ed748c7a7281e8c16200f226b1a308c7f8e953ad0c",
    "conker/retail_word_patches.us.csv": "704d9da0fe81ea2498078c8b5b2f53994ba05cf8e9e88af2ba0cb5dfd38ce71c",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5"
}
TARGETS = {
    'func_150D7420': dict(entry=0x150D7420, rom=0x1048D0, size=188, slot=12,
        SHA256='ec9480cd4f6a3619374bcadf7e04eaab158e903b22a1ec4a79c7de3d8285d469', red=(1,2)),
    'func_150D74DC': dict(entry=0x150D74DC, rom=0x10498C, size=176, slot=13,
        SHA256='6a449956418ab2151a459929fe28f771d9ee02b80d4d0ca4581f04a517c042c7', red=(2,)),
    'func_150D758C': dict(entry=0x150D758C, rom=0x104A3C, size=164, slot=14,
        SHA256='57b44ddc4413b32ee8e4bb5be76e8430293e5138f814e878a93775141fd0f56a', red=()),
}
FUNCTIONS = tuple(TARGETS)
SELECTED = {
    "func_150D7420": "/* Apply selector-dependent flag and byte updates for command 0x36. */\nvoid func_150D7420(u8 *actor, u8 *event, u8 command) {\n    if (command == 0x36) {\n        switch (event[0]) {\n            case 1:\n                *(u32 *)(actor + 0x58) |= 2;\n                actor[0x28] = 0xFF;\n                actor[0x29] = 0;\n                actor[0x2A] = 0;\n                break;\n            case 2:\n                *(u32 *)(actor + 0x58) |= 2;\n                actor[0x28] = 0xFF;\n                actor[0x29] = 0;\n                actor[0x2A] = 0;\n                break;\n            case 3:\n                *(u32 *)(actor + 0x58) |= 2;\n                actor[0x28] = 0;\n                actor[0x29] = 0xFF;\n                actor[0x2A] = 0;\n                break;\n            case 0:\n            default:\n                *(u32 *)(actor + 0x58) &= ~2;\n                break;\n        }\n    }\n}",
    "func_150D74DC": "/* Apply selector-dependent flag and byte updates for command 0x36. */\nvoid func_150D74DC(u8 *actor, u8 *event, u8 command) {\n    if (command == 0x36) {\n        switch (event[0]) {\n            case 1:\n                *(u32 *)(actor + 0x58) &= ~2;\n                break;\n            case 2:\n                *(u32 *)(actor + 0x58) |= 2;\n                actor[0x28] = 0xFF;\n                actor[0x29] = 0;\n                actor[0x2A] = 0;\n                break;\n            case 3:\n                *(u32 *)(actor + 0x58) |= 2;\n                actor[0x28] = 0;\n                actor[0x29] = 0xFF;\n                actor[0x2A] = 0;\n                break;\n            case 0:\n            default:\n                *(u32 *)(actor + 0x58) &= ~2;\n                break;\n        }\n    }\n}",
    "func_150D758C": "/* Apply selector-dependent flag and byte updates for command 0x36. */\nvoid func_150D758C(u8 *actor, u8 *event, u8 command) {\n    if (command == 0x36) {\n        switch (event[0]) {\n            case 1:\n                *(u32 *)(actor + 0x58) &= ~2;\n                break;\n            case 2:\n                *(u32 *)(actor + 0x58) &= ~2;\n                break;\n            case 3:\n                *(u32 *)(actor + 0x58) |= 2;\n                actor[0x28] = 0;\n                actor[0x29] = 0xFF;\n                actor[0x2A] = 0;\n                break;\n            case 0:\n            default:\n                *(u32 *)(actor + 0x58) &= ~2;\n                break;\n        }\n    }\n}"
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Actor selector historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Actor selector padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Actor selector frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Actor selector predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Actor selector snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    result = before
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown actor selector predecessor: ' + name)
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor selector alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output, name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ActorSelectorOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / ASM).read_text(), name)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Actor selector owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        if dc or len(raw) != target['size'] or digest(raw) != target['SHA256'] or raw != truth or bindings:
            raise ValueError('Actor selector isolated direct C differs: ' + name)
        if payload(after, name) != (raw, {}) or payload(original(root, output, name), name) != (raw, {}):
            raise ValueError('Actor selector whole owner/GNU original differs: ' + name)
        rows.append(dict(function=name, words=len(raw)//4, frame=0, bindings=0, new_guards=0))
    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != 4 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Actor selector raw owner neighbor/pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Actor selector frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown actor selector predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Actor selector predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Actor selector padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Actor selector padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Actor selector padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != 4 or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Actor selector padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(targets=rows, total_words=132, compiler_only=True, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_sizes_before=[12,12,12], target_sizes_after=[188,176,164])
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Actor selector shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1048D0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor selector Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1048D0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor selector Make redirect')
            redirect = (conker / args[-1]).resolve();redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Actor selector Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Actor selector Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != 7:
        raise ValueError('Actor selector actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Actor selector actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Actor selector strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Actor selector symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Actor selector image differs from strict three-body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1048D0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown actor selector link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
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
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Actor selector installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Actor selector independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Actor selector changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Actor selector installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Actor selector protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-3, all_addresses_fixed=True,
        target_words=132, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
