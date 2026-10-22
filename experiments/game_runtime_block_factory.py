"""Guarded source-record factory: complete C and a closed return-join fit."""

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

SOURCE, OWNER, ASM = 'conker/src/game/generated_1B74A0.c', 'generated_1B74A0', 'conker/asm/1B74A0.s'
BUILD = 'conker/build/game-runtime-block-factory/qualified'
OBJECT = 'conker/build/src/game/generated_1B74A0.c.o'
BEFORE_OBJECT_SHA = "d01f140505b6a57b3727d28fc3ac79e71f0086bfea707a444318692e4ff81f4b"
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
    "conker/build/conker.us.elf": "2389af8542638298d4a2e4e98adcc44939772f2c3a18ad2146b6b71e01b8b6de",
    "conker/retail_word_patches.us.csv": "704d9da0fe81ea2498078c8b5b2f53994ba05cf8e9e88af2ba0cb5dfd38ce71c",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/src/game/generated_1B74A0.c": "7bbf87b7a0ff27c59806a986b83a96c1c03f6d69680e513cafe97d7d429832e4",
    "conker/asm/1B74A0.s": "301e9000fc526ebd3e35ae2a6e6d0ada4cb25debc33851bd18a4f3d5eadfc940",
    "conker/src/game_16DC80.c": "48500431bc85a41ebb7833a93fc09f6b3b2704312b83316ca547b32a8fc3a966",
    "conker/asm/nonmatchings/game_16DC80/func_151407D0.s": "bfb3d519cd67625477e8cb96946b318b15083873bf7548445a2f501a95846f51",
    "conker/src/game/generated_179F30.c": "8b860798191057de9a10c2a9f7f4b208f00a4cdc7c4562eaf01d5a3642640117",
    "conker/asm/179F30.s": "57d86f46d9b3347bb725e0704c2017240275e5a7d3fbd05a9c604bf1a3ade448",
    "conker/src/libultra/libc/string.c": "6c66f2298d39e0b159e2645570caed26c869928215aedc41e600daebfc7b98d0",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721"
}
TARGETS = {
    'func_15189FF0': dict(entry=0x15189FF0, rom=0x1B74A0, size=164,
        SHA256='66d5f697d6fd3e6b0bdcb92d03c8c49b47905c5369cba1056c0898f26a853998'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = "u8 *func_151407D0(void *, s32, u8 *, u8, u8, u8, u8, s8, u8, s32);\nvoid *memcpy(void *, const void *, size_t);\n"
ISOLATED_HEADER = '#include <ultra64.h>\n'
SELECTED = {'func_15189FF0': "/* Set source subtype 0x0B, create the object, and copy its runtime block. */\nu8 *func_15189FF0(u8 *descriptor, u8 *source, const void *runtime,\n                  u8 kind, u8 mode, u8 first, u8 variant) {\n    u8 *result;\n\n    source[0x58] = 0x0B;\n    result = func_151407D0(source, 0x80, descriptor, kind, mode, first, variant, -1, 0xFF, 1);\n    if (result != NULL) {\n        memcpy(result + 0x170, runtime, 0x20);\n        goto return_created;\n    }\n    goto return_null;\nreturn_created:\n    return result;\nreturn_null:\n    return NULL;\n}"}
BINDINGS = {96: [('R_MIPS_26', 'func_151407D0')], 120: [('R_MIPS_26', 'memcpy')]}



def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Runtime block factory historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Runtime block factory padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Runtime block factory frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Runtime block factory predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Runtime block factory snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    result = before.replace("#include <ultra64.h>\n", "#include <ultra64.h>\n" + DECLARATIONS + "\n")
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown runtime block factory predecessor: ' + name)
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero runtime block factory alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output, name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ActorSelectorOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / ASM).read_text(), name)


def normalized(raw, bindings):
    if len(raw) != 160 or digest(raw) != TARGETS[FUNCTIONS[0]]['SHA256'] or bindings != BINDINGS:
        raise ValueError('Runtime block factory raw body/bindings changed')
    words = list(struct.unpack('>40I', raw))
    if words[33:35] != [0x10000002, 0x00601025]:
        raise ValueError('Runtime block factory return join changed')
    words[33] = 0x10000003
    words.insert(35, 0x10000001)
    return struct.pack('>41I', *words), bindings


def guard_bytes(old):
    reader = csv.DictReader(io.StringIO(old.decode()))
    fields = reader.fieldnames
    required = ['filename','function','offset','expected','replacement','expected_relocations',
                'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if fields != required or any(row['function'] in FUNCTIONS for row in reader):
        raise ValueError('Runtime block factory guard predecessor changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Runtime block factory guard final newline changed')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    for at, expected, replacement, inserted in [
            ('0x084','0x10000002','0x10000003',''),
            ('0x088','0x00601025','0x00601025','0x10000001')]:
        writer.writerow(dict(filename=OWNER,function=FUNCTIONS[0],offset=at,expected=expected,
            replacement=replacement,expected_relocations='-',replacement_relocations='-',
            note='Restore redundant null-return branch and its success-path join',
            insert_after=inserted,insert_after_relocations='-' if inserted else '',omit='false'))
    return old + stream.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Runtime block factory owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, ISOLATED_HEADER + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        fitted, fitted_bindings = normalized(raw, bindings)
        if dc or len(raw) != 160 or digest(raw) != target['SHA256'] or bindings != BINDINGS:
            raise ValueError('Runtime block factory isolated C differs: ' + name)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (fitted, fitted_bindings):
            raise ValueError('Runtime block factory whole owner/GNU original differs: ' + name)
        guards = output / 'proposed-guards.csv'
        guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
        fitted_s = output / 'fitted-selected.s'
        fitted_s.write_text(emit_padded_assembly(after, root / ASM, word_patches_path=guards, filename=OWNER))
        fitted_o = fitted_s.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(root/'conker/include'),
            '-o', str(fitted_o), str(fitted_s)], check=True, capture_output=True)
        text, functions = link_owner(root, output, fitted_o, OWNER)
        at = functions[name]['value']
        if text[at:at + target['size']] != truth:
            raise ValueError('Runtime block factory linked C differs')
        rows.append(dict(function=name, raw_words=len(raw)//4, words=41, frame=56, bindings=2, new_guards=2, inserted_words=1))
    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != 5 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Runtime block factory raw owner neighbor/pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=guards, filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Runtime block factory frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown runtime block factory predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Runtime block factory predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Runtime block factory padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Runtime block factory padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Runtime block factory padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != 5 or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Runtime block factory padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(targets=rows, total_words=41, raw_words=40, compiler_only=False, new_guards=2, inserted_words=1,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_sizes_before=[12], target_sizes_after=[164])
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Runtime block factory shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1B74A0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected runtime block factory Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1B74A0.c' else (output / 'proposed-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown runtime block factory Make redirect')
            redirect = (conker / args[-1]).resolve();redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Runtime block factory Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Runtime block factory Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != 6:
        raise ValueError('Runtime block factory actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Runtime block factory actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Runtime block factory strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Runtime block factory symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Runtime block factory image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1B74A0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown runtime block factory link input')
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
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else guard_bytes(old) if name == 'conker/retail_word_patches.us.csv' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Runtime block factory installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Runtime block factory independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Runtime block factory changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Runtime block factory installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Runtime block factory protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=41, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
