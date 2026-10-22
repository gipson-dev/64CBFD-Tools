"""Source-backed descriptor, relocation-aware schedule and strict image gates."""

import hashlib
import json
import re
from pathlib import Path
import shlex
import shutil
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


FUNCTION, ENTRY, ROM, SIZE = 'func_151A4590', 0x151A4590, 0x1D1A40, 168
SOURCE, OWNER, ASM = 'conker/src/game/generated_1D0840.c', 'generated_1D0840', 'conker/asm/1D0840.s'
BUILD = 'conker/build/game-owner-descriptor-preset/qualified'
OBJECT = 'conker/build/src/game/generated_1D0840.c.o'
BEFORE_OBJECT_SHA = 'fbccadbdf0bd7e6a3f51eba4edabd2fb99729d0026b06c343317864429274626'
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
    "conker/build/conker.us.elf": "89134335a538fb554c187234e3c8760c25fd89a85470de9abe1fc96ae84a45f0",
    "conker/retail_word_patches.us.csv": "0787cba1980f53179a9baccafcda47df1446d8e8a7965c40791fb7210bf183f3",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/src/game/generated_1D0840.c": "d00b2fb2550cee3153a620e3e03f9a3da00fc015c1baab3e4eee5f4eb6fd3364",
    "conker/asm/1D0840.s": "776840f022dd4079a066a510afdd122e15116e9a284c80698b48d1cf10b8d34e",
    "conker/src/game_161520.c": "d3e9a447f86d0bb6f9dc4b5f36439a6fb079250042fb7eabc068854bac3dac12",
    "conker/asm/nonmatchings/game_161520/func_1513418C.s": "a2a6fac090ca48fc0535534c995b15c1c3262e3729ebfd24eb02f381a0a86530",
    "conker/asm/nonmatchings/generated_1D0840/func_151A5170.s": "fad3f65b4b826b42e687a654bdb2f7eec8e831162644b215272be03fb36a33b3"
}
RAW_SHA = '27bda6bd1307115c17b901dff63d08112f9be14d11961ded5e9bf2a4acffff1e'
DECLARATIONS = 'typedef struct {\n    u32 zero0, zero4;\n    u8 ownerSelector, reserved09[3];\n    u8 *owner;\n    u8 attachment, reserved11[3];\n    f32 vector[3];\n    f32 value20, value24;\n    s16 value28;\n    u8 flags, value2B;\n    s8 value2C;\n    u8 value2D;\n} OwnerPresetDescriptor1D0840;\nextern f32 D_800A8D5C;\nvoid *func_1513418C(OwnerPresetDescriptor1D0840 *, s32, u8, s32);\n'
OWNER_DECLARATIONS = 'typedef struct {\n    u32 zero0, zero4;\n    u8 ownerSelector, reserved09[3];\n    u8 *owner;\n    u8 attachment, reserved11[3];\n    f32 vector[3];\n    f32 value20, value24;\n    s16 value28;\n    u8 flags, value2B;\n    s8 value2C;\n    u8 value2D;\n} OwnerPresetDescriptor1D0840;\nextern f32 D_800A8D5C;\nvoid *func_1513418C(OwnerPresetDescriptor1D0840 *, s32, u8, s32);\n'
SELECTED = '/* Submit the source-backed descriptor preset for the selected variant. */\nvoid func_151A4590(u8 * volatile owner, u8 variant) {\n    OwnerPresetDescriptor1D0840 descriptor;\n\n    if (owner != NULL) {\n        descriptor.zero0 = 0;\n        descriptor.zero4 = 0;\n        descriptor.owner = owner;\n        descriptor.ownerSelector = descriptor.owner[0x3B];\n        descriptor.attachment = 1;\n        descriptor.vector[0] = 0.0f;\n        descriptor.vector[1] = 0.0f;\n        descriptor.vector[2] = 0.0f;\n        descriptor.value20 = D_800A8D5C;\n        descriptor.value24 = 3.0f;\n        descriptor.value28 = 100;\n        descriptor.flags = 10;\n        descriptor.value2B = 1;\n        descriptor.value2C = -1;\n        descriptor.value2D = 0;\n        func_1513418C(&descriptor, 0, variant, 0);\n    }\n}'
BINDINGS = {28: [('R_MIPS_HI16', 'D_800A8D5C')], 64: [('R_MIPS_LO16', 'D_800A8D5C')], 144: [('R_MIPS_26', 'func_1513418C')]}



def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Owner descriptor preset historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Owner descriptor preset padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Owner descriptor preset frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Owner descriptor preset predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Owner descriptor preset snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151A4590() {\n    return 0;\n}':
        raise ValueError('Unknown owner-descriptor-preset source predecessor')
    result = before[:lo] + SELECTED + before[hi:]
    result = result.replace('/* Non-matching placeholders for the text-only asm slice asm/1D0840.s. */',
        '/* Partially recovered text-only slice asm/1D0840.s. */', 1)
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1 or OWNER_DECLARATIONS in result:
        raise ValueError('Unknown owner-preset declaration anchor')
    return result.replace(anchor, anchor + OWNER_DECLARATIONS + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero owner-descriptor-preset alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('OwnerPresetOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-owner-descriptor-preset',
        (root / ASM).read_text(), FUNCTION)



SCHEDULE_INPUTS = {
    13: 0xAFAF0024, 14: 0x91F8003B, 15: 0x44800000, 16: 0xC4240000,
    17: 0x3C014040, 18: 0x44813000, 19: 0x2409000A, 20: 0x240A0001,
    21: 0x240BFFFF, 22: 0xA3B90028, 23: 0xA7A80040, 24: 0xA3A90042,
    25: 0xA3AA0043, 26: 0xA3AB0044, 27: 0xA3A00045, 28: 0x27A40018,
    29: 0x00002825, 30: 0x00003825,
}
SCHEDULE_LAYOUT = {13: 14, 14: 15, 15: 16, 16: 17, 17: 18, 18: 19, 19: 20, 20: 21, 21: 22, 22: 23, 23: 24, 24: 25, 25: 26, 26: 27, 27: 28, 28: 29, 29: 30, 30: 13}


def schedule_patches():
    if set(SCHEDULE_LAYOUT) != set(SCHEDULE_INPUTS) or set(SCHEDULE_LAYOUT.values()) != set(SCHEDULE_INPUTS):
        raise ValueError('Payload schedule is not a closed word permutation')
    if any(word >> 26 not in (0, 9, 15, 17, 35, 36, 40, 41, 43, 49, 57) or
           (word >> 26 == 0 and word & 63 != 37) for word in SCHEDULE_INPUTS.values()):
        raise ValueError('Payload schedule includes control flow or an unknown operation')
    return {at * 4: (SCHEDULE_INPUTS[at], SCHEDULE_INPUTS[origin])
            for at, origin in SCHEDULE_LAYOUT.items()}


def patch_schedule(raw):
    if len(raw) != SIZE:
        raise ValueError('Payload schedule extent changed')
    original = struct.unpack('>42I', raw)
    words = list(original)
    for offset, (expected, _) in schedule_patches().items():
        mask = 0xFFFF0000 if offset == 64 else 0xFFFFFFFF
        if original[offset // 4] & mask != expected:
            raise ValueError('Payload expected scheduling word changed')
        words[offset // 4] = original[SCHEDULE_LAYOUT[offset // 4]]
    return struct.pack('>42I', *words)


def scheduled_bindings(bindings):
    moved = {origin * 4: destination * 4 for destination, origin in SCHEDULE_LAYOUT.items()}
    result = {moved.get(at, at): list(rows) for at, rows in bindings.items()}
    if len(result) != len(bindings):
        raise ValueError('Descriptor scheduling merged relocation slots')
    return result


def normalized(raw, bindings):
    if digest(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Payload raw body or call bindings changed')
    return patch_schedule(raw), scheduled_bindings(bindings)


def guard_bytes(old):
    import csv, io
    if digest(old) != INPUTS['conker/retail_word_patches.us.csv']:
        raise ValueError('Payload guard predecessor changed')
    reader = csv.DictReader(io.StringIO(old.decode()))
    fields = ['filename','function','offset','expected','replacement','expected_relocations',
              'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if reader.fieldnames != fields or any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Payload guard schema or target prefix changed')
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):
        raise ValueError('Payload guard newline changed')
    stream = io.StringIO(newline='')
    relocated = scheduled_bindings(BINDINGS)
    spec = lambda rows: ';'.join(kind + ':' + name for kind, name in rows) or '-'
    for offset, (expected, replacement) in schedule_patches().items():
        csv.DictWriter(stream, fieldnames=fields, lineterminator=newline).writerow(dict(
            filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,expected='0x%08X'%expected,
            replacement='0x%08X'%replacement,expected_relocations=spec(BINDINGS.get(offset, [])),
            replacement_relocations=spec(relocated.get(offset, [])),
            note='Normalize closed owner-descriptor preset schedule and float-load relocation',
            insert_after='',insert_after_relocations='',omit='false'))
    return old + stream.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Owner descriptor preset compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    fitted, fitted_bindings = normalized(raw, bindings)
    if len(raw) != SIZE or digest(raw) != RAW_SHA or patch_schedule(linked[at:at + SIZE]) != truth or bindings != BINDINGS or payload(after) != (raw, bindings):
        raise ValueError('Owner descriptor preset direct C differs from retail/whole owner')
    if payload(original(root, output)) != (fitted, fitted_bindings):
        raise ValueError('Owner descriptor preset independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Owner descriptor preset raw owner pool changed')
    (output / 'qualified-guards.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=output / 'qualified-guards.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Owner descriptor preset frozen padded predecessor changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown owner-descriptor-preset padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Owner descriptor preset predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Owner descriptor preset padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Owner descriptor preset padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=42, frame=72, differences=0, relocations=3, new_guards=18,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=False, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Owner descriptor preset shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1D0840.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected owner-descriptor-preset Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1D0840.c' else a for a in args]
        args = [(output / 'qualified-guards.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown owner-descriptor-preset Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Owner descriptor preset Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Owner descriptor preset Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Owner descriptor preset actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Owner descriptor preset actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Owner descriptor preset strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Owner descriptor preset symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Owner descriptor preset image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1D0840.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown owner-descriptor-preset link input')
    link = output / 'first-link.ld'
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
    at = elf_slot_offset(before, ENTRY, SIZE)
    code = sum(a != b for a, b in zip(before[at:at + SIZE], truth))
    report = dict(exact_prediction=True, SHA256=digest(actual), changed_bytes=changed,
        code_bytes_changed=code, metadata_bytes_changed=changed - code, metadata_exclusions=0)
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else guard_bytes(old) if name == 'conker/retail_word_patches.us.csv' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Owner descriptor preset installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Owner descriptor preset independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Owner descriptor preset changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Owner descriptor preset installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Owner descriptor preset protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=42, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
