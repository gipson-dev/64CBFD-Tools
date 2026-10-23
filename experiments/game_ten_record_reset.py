"""Ten-record reset: semantic C, closed address folds and strict owner/image gates."""

import hashlib
import csv
import io
import json
import re
from pathlib import Path
import shlex
import shutil
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows, SYMBOL
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


FUNCTION, ENTRY, ROM, SIZE = 'func_150A00F0', 0x150A00F0, 0xCD5A0, 172
SOURCE, OWNER, ASM = 'conker/src/game/generated_CD5A0.c', 'generated_CD5A0', 'conker/asm/CD5A0.s'
BUILD = 'conker/build/game-ten-record-reset/qualified'
OBJECT = 'conker/build/src/game/generated_CD5A0.c.o'
BEFORE_OBJECT_SHA = 'ac16c42cf29d212f1163f5c203d940d15a829aa351ad7a43557345f847ad03ea'
INPUTS = {'conker/include/structs.h': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69', 'conker/include/functions.h': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81', 'conker/include/variables.h': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8', 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769', 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d', 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd', 'conker/symbol_addrs.us.txt': 'd0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106', 'conker/undefined_funcs_auto.txt': '3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6', 'conker/undefined_syms_auto.txt': 'a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd', 'conker/undefined_funcs.us.txt': '92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a', 'conker/undefined_syms.us.txt': 'd678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e', 'conker/build/conker.us.elf': '28e5b2e952e95ae65484b3668a712fadf9e93d046d893ee8f41d5b3f1d1802e2', 'conker/retail_word_patches.us.csv': 'fb52b3db3529db91f553ee7746a5c68adf7968ccbd085bd4e571e0a821fb0585', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf', 'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be', 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d', 'conker/conker.ld': '217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8', 'conker/retail_layout.us.txt': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5', 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5', 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721', 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6', 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4', 'conker/src/game/generated_CD5A0.c': 'd38bfd44d9d24f12c1c273b93445053033da45b1c042a47f645adc2dcf8798f1', 'conker/asm/CD5A0.s': '2de187fc024a9ce7a28a3c7e51c02aa59f6aac2a7af0d6e45e3a55da5f8498ff', 'conker/src/game_44C40.c': '473261778b35a24e065a82c5b09de440aa2bce1d77325b5f9a031a98e69b6755', 'conker/build/src/game_44C40.c.o': '69c050b3711483b9c81df1a45334f18ef33675a60bfde07105e4fd97baf89295'}
DECLARATIONS = 'typedef struct {\n    u8 status;\n    u8 pad1[3];\n    s32 value;\n    s32 unk8;\n} GeneratedCD5A0Record;\n\nextern GeneratedCD5A0Record D_800D3010[];\n\n'
SELECTED = '/* Clear the active bit and both counters in all ten records. */\nvoid func_150A00F0(void) {\n    s32 index;\n    for (index = 0; index < 10; index++) {\n        D_800D3010[index].status &= (u16)~0x80;\n        D_800D3010[index].value = 0;\n        D_800D3010[index].unk8 = 0;\n    }\n}'


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Ten-record reset historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    data = (root / OBJECT).read_bytes() if not old.exists() else old.read_bytes()
    if digest(data) != BEFORE_OBJECT_SHA:
        raise ValueError('Ten-record-reset padded predecessor changed')
    if not old.exists():
        old.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Ten-record reset predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Ten-record reset snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150A00F0() {\n    return 0;\n}':
        raise ValueError('Unknown ten-record-reset predecessor')
    return before[:lo]+SELECTED+before[hi:]



def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero ten-record-reset alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('MaskedFieldsOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-ten-record-reset',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Ten-record reset compiler diagnostics changed: ' + da + db + dc)
    raw, bindings = payload(isolated)
    fitted, relocations = normalized(raw, bindings)
    if payload(after) != (raw, bindings) or payload(original(root, output)) != (fitted, relocations):
        raise ValueError('Ten-record reset whole owner or independent GNU original differs')
    guards = output / 'qualified-guards.csv'
    guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv']))
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM, word_patches_path=guards, filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                    '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], capture_output=True, check=True)
    old = output / 'before-padded.o'
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name,info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown ten-record reset predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    truth = values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at+SIZE] != values['conker/build/conker.us.elf'][slot:slot+SIZE]:
        raise ValueError('Ten-record reset predecessor object/image mismatch')
    if expected != fb or b[at:at+SIZE] != truth or a[:at] != b[:at] or a[at+SIZE:] != b[at+SIZE:]:
        raise ValueError('Ten-record reset padding changed another extent, body or address')
    neighbors = same_functions(before, after, (FUNCTION,))
    if neighbors != 4 or same_functions(old, obj, (FUNCTION,)) != neighbors:
        raise ValueError('Ten-record reset neighboring functions changed')
    if normalized_pools(before) != normalized_pools(after) or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Ten-record reset owner pools changed')
    caller = recovered_caller(values[CALLER_SOURCE].decode())
    caller_obj, caller_diagnostics = compile_owner(root, output, caller, 'typed-caller')
    before_caller, before_diagnostics = compile_owner(root, output, values[CALLER_SOURCE].decode(), 'before-caller')
    if diagnostics(caller_diagnostics) != diagnostics(before_diagnostics) or same_functions(before_caller, caller_obj, ()) != 6:
        raise ValueError('Ten-record reset typed caller compact code or diagnostics changed')
    caller_assembly = output / 'typed-caller-padded.s'
    subprocess.run(['python3', str(root/'tools/pad_c_object.py'), str(caller_obj),
                    str(root/'conker/retail_layout.us.txt'), 'game_44C40', str(caller_assembly),
                    '--word-patches', str(guards)], capture_output=True, check=True)
    caller_padded = caller_assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                    '-I', str(root/'conker/include'), '-o', str(caller_padded), str(caller_assembly)],
                   capture_output=True, check=True)
    if caller_padded.read_bytes() != values[CALLER_OBJECT]:
        raise ValueError('Ten-record reset typed caller object changed')
    (output / 'proposed-caller.c').write_text(caller)
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=43, raw_words=46, frame=0, differences=0, relocations=len(relocations),
        new_guards=20, omitted_high_loads=3, inserted_words=0, compiler_only=False,
        raw_SHA256=digest(raw), preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_size_before=12, target_size_after=SIZE, whole_caller_object_unchanged=True,
        caller_object_SHA256=digest(caller_padded.read_bytes()), caller_diagnostics=caller_diagnostics)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Ten-record reset shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_CD5A0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected ten-record-reset Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_CD5A0.c' else (output / 'qualified-guards.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown ten-record-reset Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Ten-record reset Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Ten-record reset Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Ten-record reset actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Ten-record reset actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Ten-record reset strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Ten-record reset symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    symbols = {name: (offset, fields, string_at) for offset,name,fields,string_at in symbol_rows(before)}
    # New alias references reorder six existing linker hash chains, not their values.
    for old_order,new_order in SYMBOL_ORDERS:
        if set(old_order) != set(new_order) or len(set(old_order)) != len(old_order):
            raise ValueError('Ten-record reset symbol serialization cycle is not closed')
        records = [symbols[name] for name in old_order]
        offsets = [row[0] for row in records]
        if offsets != list(range(offsets[0], offsets[0]+16*len(records), 16)):
            raise ValueError('Ten-record reset symbol chain predecessor changed')
        strings = b''.join(name.encode()+b'\0' for name in old_order)
        start = records[0][2]
        if before[start:start+len(strings)] != strings:
            raise ValueError('Ten-record reset string chain predecessor changed')
        result[start:start+len(strings)] = b''.join(name.encode()+b'\0' for name in new_order)
        name_at = records[0][1][0]
        for offset,name in zip(offsets,new_order):
            fields = list(symbols[name][1])
            fields[0] = name_at
            SYMBOL.pack_into(result, offset, *fields)
            name_at += len(name)+1
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Ten-record reset image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_CD5A0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown ten-record-reset link input')
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
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else recovered_caller(old.decode()).encode() if name == CALLER_SOURCE else guard_bytes(old) if name == 'conker/retail_word_patches.us.csv' else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Ten-record reset installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Ten-record reset independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Ten-record reset changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Ten-record reset protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=43, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

RAW_SHA256 = '987d077d095b9342bb7e2bb3e8802539659266bdae9af7fa95b454a2b69972f4'
RAW_WORDS = (1007550464, 2446196736, 1006698496, 1008205824, 835714943, 2687434752, 1006698496, 2887778308, 1006698496, 2887778312, 2467823628, 1006698496, 1006829568, 857341823, 2688090124, 1006698496, 2887778320, 1006698496, 1006764032, 608305272, 2887778324, 610467864, 2422865932, 2422997016, 2423128100, 2422734848, 610467888, 827064191, 831389567, 835714943, 822738815, 2691694580, 2691563496, 2691432412, 2892038112, 2892038116, 2892038124, 2892038128, 2892038136, 2892038140, 2691301328, 2892038100, 342032363, 2892038104, 65011720, 0)
RAW_BINDINGS = {0: [('R_MIPS_HI16', 'D_800D3010')], 4: [('R_MIPS_LO16', 'D_800D3010')], 8: [('R_MIPS_HI16', 'D_800D3010')], 20: [('R_MIPS_LO16', 'D_800D3010')], 24: [('R_MIPS_HI16', 'D_800D3010')], 28: [('R_MIPS_LO16', 'D_800D3010')], 32: [('R_MIPS_HI16', 'D_800D3010')], 36: [('R_MIPS_LO16', 'D_800D3010')], 12: [('R_MIPS_HI16', 'D_800D3010')], 40: [('R_MIPS_LO16', 'D_800D3010')], 44: [('R_MIPS_HI16', 'D_800D3010')], 56: [('R_MIPS_LO16', 'D_800D3010')], 60: [('R_MIPS_HI16', 'D_800D3010')], 64: [('R_MIPS_LO16', 'D_800D3010')], 68: [('R_MIPS_HI16', 'D_800D3010')], 80: [('R_MIPS_LO16', 'D_800D3010')], 48: [('R_MIPS_HI16', 'D_800D3010')], 84: [('R_MIPS_LO16', 'D_800D3010')], 72: [('R_MIPS_HI16', 'D_800D3010')], 76: [('R_MIPS_LO16', 'D_800D3010')]}
ORDER = (0, 1, 6, 7, 4, 5, 8, 9, 3, 10, 12, 18, 13, 14, 15, 16, 20, 19, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45)
OMITTED = (2, 11, 17)
ALIASES = {0: 0, 1: 0, 2: 4, 3: 4, 5: 0, 6: 8, 7: 8, 8: 12, 9: 12, 10: 24, 11: 120, 13: 12, 14: 16, 15: 16, 16: 20, 17: 120, 18: 24}
CALLER_SOURCE = 'conker/src/game_44C40.c'
CALLER_OBJECT = 'conker/build/src/game_44C40.c.o'
SYMBOL_ORDERS = (
    (('D_800D3018','func_1514E920'),('func_1514E920','D_800D3018')),
    (('D_800991D4','D_8009E6E4'),('D_8009E6E4','D_800991D4')),
    (('D_800D3024','D_800D301C'),('D_800D301C','D_800D3024')),
    (('D_800A08C0','func_15194408','D_8009F098'),('D_8009F098','D_800A08C0','func_15194408')),
    (('D_800A6BE4','D_80098D64'),('D_80098D64','D_800A6BE4')),
    (('D_800D3088','D_8008EA00'),('D_8008EA00','D_800D3088')),
)

def recovered_caller(before):
    marker = '#include "variables.h"\n'
    if before.count(marker) != 1 or before.count('func_150A00F0();') != 1:
        raise ValueError('Unknown ten-record-reset caller interface')
    return before.replace(marker, marker + '\nvoid func_150A00F0(void);\n', 1)

def normalized(raw, bindings):
    if digest(raw) != RAW_SHA256 or bindings != RAW_BINDINGS or len(raw) != 184:
        raise ValueError('Ten-record reset raw body or relocation precondition changed')
    words = struct.unpack('>46I', raw)
    if len(set(ORDER)) != 43 or set(range(46)) - set(ORDER) != set(OMITTED):
        raise ValueError('Ten-record reset schedule is not a closed permutation/fold')
    for i in OMITTED:
        if words[i] != 0x3C010000 or bindings[i*4] != [('R_MIPS_HI16', 'D_800D3010')]:
            raise ValueError('Ten-record reset omitted word is not its redundant high load')
    fitted = [words[i] for i in ORDER]
    relocations = {i*4: bindings[k*4] for i,k in enumerate(ORDER) if k*4 in bindings}
    for i, offset in ALIASES.items():
        entries = relocations[i*4]
        if len(entries) != 1 or entries[0][1] != 'D_800D3010':
            raise ValueError('Ten-record reset alias is not based on the record array')
        kind = entries[0][0]
        if fitted[i] & 65535 != (offset if kind == 'R_MIPS_LO16' else 0):
            raise ValueError('Ten-record reset source-field addend changed')
        fitted[i] &= 0xFFFF0000
        relocations[i*4] = [(kind, 'D_%08X' % (0x800D3010 + offset))]
    return struct.pack('>43I', *fitted), relocations

def guard_bytes(old):
    if digest(old) != INPUTS['conker/retail_word_patches.us.csv']:
        raise ValueError('Ten-record reset guard predecessor changed')
    reader = csv.DictReader(io.StringIO(old.decode()))
    fields = reader.fieldnames
    if any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Ten-record reset already has guards in its predecessor')
    fitted, bindings = normalized(struct.pack('>46I', *RAW_WORDS), RAW_BINDINGS)
    words = struct.unpack('>43I', fitted)
    destination = {old: new for new,old in enumerate(i for i in range(46) if i not in OMITTED)}
    newline = '\r\n' if old.endswith(b'\r\n') else '\n'
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator=newline)
    spec = lambda entries: '|'.join(kind+':'+name for kind,name in entries) or '-'
    count = 0
    for i, word in enumerate(RAW_WORDS):
        replacement, rel = (0, []) if i in OMITTED else (words[destination[i]], bindings.get(destination[i]*4, []))
        current = RAW_BINDINGS.get(i*4, [])
        if i in OMITTED or word != replacement or current != rel:
            writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%03X' % (i*4),
                expected='0x%08X' % word, replacement='0x%08X' % replacement,
                expected_relocations=spec(current), replacement_relocations=spec(rel),
                note='Normalize fixed-layout record high-address folds, field aliases and independent reset scheduling',
                insert_after='', insert_after_relocations='', omit='true' if i in OMITTED else 'false'))
            count += 1
    if count != 20:
        raise ValueError('Ten-record reset guard count changed')
    return old + stream.getvalue().encode()
