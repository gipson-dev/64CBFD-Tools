"""Semantic parameterized payload, checked schedule and strict image gates."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_15192D48', 0x15192D48, 0x1C01F8, 168
SOURCE, OWNER, ASM = 'conker/src/game/generated_1BFDD0.c', 'generated_1BFDD0', 'conker/asm/1BFDD0.s'
BUILD = 'conker/build/game-parameterized-selector-payload/qualified'
OBJECT = 'conker/build/src/game/generated_1BFDD0.c.o'
BEFORE_OBJECT_SHA = 'fcd9a187584a9f75d64de58a7317a658c2d1fc32bc9b23fa78a7169c8d397be8'
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
    "conker/build/conker.us.elf": "e67fa8d07884ef2f7722b75813bd3490e7094a3c8d9af70c5b97eaff818baefd",
    "conker/retail_word_patches.us.csv": "5df67f0153c78c0d36a213a5e3a6e701a1e871531d1567ef5c2605f3ea6ca1f5",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/src/game/generated_1BFDD0.c": "16efa9b728a62290af9f5372459bc736bc21d6bcda066b52ebdd909acd4c0046",
    "conker/asm/1BFDD0.s": "6e52416334bc91fae5b0a3c5c1968c921503766a72e93d5fc9475e551b6c15f6",
    "conker/src/game/generated_50D80.c": "b24a3bfada6d6003f33b080e1bea3c5f328d1c829e70dd1ab5b067cdaac6e318",
    "conker/asm/50D80.s": "58dec15b45859c1dface2fc227f074871296eb4884e6499e4cfee37b8389111c"
}
RAW_SHA = 'e05cc6731ff218816a73d608e4dc2767763d53bf49bb215158fc28a8b668ed8f'
DECLARATIONS = 'void *func_151491F4(s16 arg0, s8 arg1, s8 arg2, u8 arg3, u8 arg4, s32 arg5, u8 arg6, s32 arg7);\n\ntypedef struct {\n    void *owner;\n    u8 selector;\n    u8 pad5[3];\n    f32 value;\n} Generated1BFDD0Payload;\n\n'
OWNER_DECLARATIONS = ''
SELECTED = '''/* Allocate an owner/selector payload record with the requested lifetime. */
void *func_15192D48(u8 * volatile owner, s16 volatile lifetime,
                   u8 volatile selector, s32 volatile parameter) {
    u8 *record;
    Generated1BFDD0Payload payload;

    if (owner == NULL) {
        return NULL;
    }
    payload.owner = owner;
    payload.selector = ((u8 *)payload.owner)[0x3B];
    payload.value = 0.0f;
    record = func_151491F4(lifetime, -1, 0x18, 1, 0x16, 0xC, selector, parameter);
    if (record != NULL) {
        memcpy(record + 0x28, &payload, sizeof(payload));
    }
    return record;
}'''
BINDINGS = {108: [('R_MIPS_26', 'func_151491F4')], 136: [('R_MIPS_26', 'memcpy')]}



def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Parameterized selector payload historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Parameterized selector payload padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Parameterized selector payload frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Parameterized selector payload predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Parameterized selector payload snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15192D48() {\n    return 0;\n}':
        raise ValueError('Unknown parameterized-selector-payload source predecessor')
    result = before[:lo] + SELECTED + before[hi:]
    result = result.replace('/* Non-matching placeholders for the text-only asm slice asm/1BFDD0.s. */',
        '/* Partially recovered text-only slice asm/1BFDD0.s. */', 1)
    return result


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero parameterized-selector-payload alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ParameterizedPayloadOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-parameterized-selector-payload',
        (root / ASM).read_text(), FUNCTION)



SCHEDULE_INPUTS = {
    7: 0x2405FFFF, 8: 0x24060018, 10: 0x24070001, 13: 0x8FAF0038,
    14: 0x87A4003E, 15: 0x93A90043, 16: 0xAFAF0028, 17: 0x91F8003B,
    18: 0x44802000, 19: 0x8FAA0044, 20: 0x24190016, 21: 0x2408000C,
    22: 0xAFA80014, 23: 0xAFB90010, 24: 0xAFA90018, 25: 0xA3B8002C,
    26: 0xE7A40030,
}
SCHEDULE_LAYOUT = {7: 13, 8: 7, 10: 8, 13: 16, 14: 17, 15: 18, 16: 15,
                   17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 14,
                   23: 10, 24: 25, 25: 26, 26: 24}


def schedule_patches():
    if set(SCHEDULE_LAYOUT) != set(SCHEDULE_INPUTS) or set(SCHEDULE_LAYOUT.values()) != set(SCHEDULE_INPUTS):
        raise ValueError('Payload schedule is not a closed word permutation')
    if any(word >> 26 not in (9, 17, 33, 35, 36, 40, 43, 57) for word in SCHEDULE_INPUTS.values()):
        raise ValueError('Payload schedule includes control flow or an unknown operation')
    return {at * 4: (SCHEDULE_INPUTS[at], SCHEDULE_INPUTS[origin])
            for at, origin in SCHEDULE_LAYOUT.items()}


def patch_schedule(raw):
    if len(raw) != SIZE:
        raise ValueError('Payload schedule extent changed')
    words = list(struct.unpack('>42I', raw))
    for offset, (expected, replacement) in schedule_patches().items():
        if words[offset // 4] != expected:
            raise ValueError('Payload expected scheduling word changed')
        words[offset // 4] = replacement
    return struct.pack('>42I', *words)


def normalized(raw, bindings):
    if digest(raw) != RAW_SHA or bindings != BINDINGS:
        raise ValueError('Payload raw body or call bindings changed')
    return patch_schedule(raw), dict(bindings)


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
    for offset, (expected, replacement) in schedule_patches().items():
        csv.DictWriter(stream, fieldnames=fields, lineterminator=newline).writerow(dict(
            filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,expected='0x%08X'%expected,
            replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',
            note='Normalize closed owner-selector payload and argument-home schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    return old + stream.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Parameterized selector payload compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    fitted, fitted_bindings = normalized(raw, bindings)
    if len(raw) != SIZE or digest(raw) != RAW_SHA or patch_schedule(linked[at:at + SIZE]) != truth or bindings != BINDINGS or payload(after) != (raw, bindings):
        raise ValueError('Parameterized selector payload direct C differs from retail/whole owner')
    if payload(original(root, output)) != (fitted, fitted_bindings):
        raise ValueError('Parameterized selector payload independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Parameterized selector payload raw owner pool changed')
    (output / 'qualified-guards.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=output / 'qualified-guards.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Parameterized selector payload frozen padded predecessor changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown parameterized-selector-payload padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Parameterized selector payload predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Parameterized selector payload padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Parameterized selector payload padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=42, frame=56, differences=0, relocations=2, new_guards=17,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=False, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Parameterized selector payload shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1BFDD0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected parameterized-selector-payload Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1BFDD0.c' else a for a in args]
        args = [(output / 'qualified-guards.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown parameterized-selector-payload Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Parameterized selector payload Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Parameterized selector payload Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Parameterized selector payload actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Parameterized selector payload actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Parameterized selector payload strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Parameterized selector payload symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Parameterized selector payload image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1BFDD0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown parameterized-selector-payload link input')
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
            raise ValueError('Parameterized selector payload installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Parameterized selector payload independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Parameterized selector payload changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Parameterized selector payload installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Parameterized selector payload protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=42, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
