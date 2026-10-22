"""Direct C oriented-triangle record builder, with owner, caller and closed image gates."""

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

SOURCE, OWNER, ASM = 'conker/src/game/generated_17CAF0.c', 'generated_17CAF0', 'conker/asm/17CAF0.s'
BUILD = 'conker/build/game-oriented-triangle-record/qualified'
OBJECT = 'conker/build/src/game/generated_17CAF0.c.o'
BEFORE_OBJECT_SHA = "f3f082730823761355f78b0a4789f596998a35b0b8907df6cf8c6064cea57aa3"
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
    "conker/build/conker.us.elf": "f8c55e69ec6b971d1d6c8b9178ad99763ec468034df57481dbfc1c3eaf587138",
    "conker/retail_word_patches.us.csv": "031ddcd7aa719513a46f9a671106e2fe20892b768d71e3cb3d98e60f0a00e6ab",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/src/game/generated_17CAF0.c": "ef7ce9ba93d701256bdebeb6dac2194115b0e33252b83e3bba4a1bae5661c015",
    "conker/asm/17CAF0.s": "a312244a25c771c8c66ffaaa5e148c251cf544d82f5a0908e64f8c5c2446a25e",
    "conker/src/game_16EE20.c": "7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810",
    "conker/asm/nonmatchings/game_16EE20/func_15144E80.s": "f732bbbfc9524e83b5b24f2c85a8bcf4d3d739885f9ab47aafab063474bedf00",
    "conker/asm/nonmatchings/generated_17CAF0/func_1514F8F8.s": "2204e8970a46f5563c903250002e50b59efb67e62fcc9b8833784c81269f2a66",
    "conker/asm/nonmatchings/generated_17CAF0/func_1514FB98.s": "a770c7d22e84c4c0256274cbf01eb07d52e721bdd894d32ef8a1784d3adb2c56",
    "conker/asm/nonmatchings/generated_17CAF0/func_1514FBFC.s": "79d770e81d2e51d3f992a65f2f64c552bccd91cdb5e4392baea95685791d9ba2",
    "conker/asm/nonmatchings/generated_17CAF0/func_1514FCE8.s": "08986aa75dd8ad8d405191e156315c656aa2e1e4e40ad04bf90c906d19d65940",
    "conker/asm/nonmatchings/generated_17CAF0/func_15151D6C.s": "c2501583214627ba8c623258e6ee7b922578df95284c27585192bbf590d0105f",
    "conker/asm/nonmatchings/generated_17CAF0/func_15153634.s": "0a1cd9cd097c6f5fdb2cac409ef12f19103f7d4ac8f16a3bb9eb34d77ae6ae03",
    "conker/asm/nonmatchings/generated_17CAF0/func_151541B8.s": "aa2615b5937684739c390d3eb14cd5fe0828bff227376e6f3499416bda4ac051",
    "conker/asm/nonmatchings/generated_17CAF0/func_1515452C.s": "bb45ca17f68129d7f0b0e5acbd6846d5528f85433639bf5bcd363729d792bacf",
    "conker/asm/nonmatchings/generated_17CAF0/func_15154884.s": "4501bf094f6f6682e6e1d225a868c7d0e02e294c707ac296d2ee836e6826adc0",
    "conker/asm/nonmatchings/generated_17CAF0/func_15154A88.s": "9a8b13cd381d5fa350caad9413b6d6bc43fe5ef27f85e58194ca7c2fc399f30a",
    "conker/asm/nonmatchings/generated_17CAF0/func_1515548C.s": "77e398f79da73fa9fa0883f9558201d6af00d821b7b7e85f5b16d8c2c088df7d",
    "conker/asm/nonmatchings/generated_17CAF0/func_151555AC.s": "e98aae809b7c00e082c1378a74defacafcce5e818c5bc640b95b85d07fcc38a0"
}
TARGETS = {
    'func_1514F640': dict(entry=0x1514F640, rom=0x17CAF0, size=168,
        SHA256='596ae263014e50a7262b2ebe7f2a163f0f1f8e6a9edafb103d24c07c4f6341db'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = 's32 func_15144E80(s16 *, f32 *, f32 *, f32 *);\nf32 func_15144A74(f32 *, f32 *);\n'
SELECTED = {'func_1514F640': "/* Build triangle vectors and orient the normal toward the source vector. */\nvoid func_1514F640(u8 *source, u8 *output) {\n    output[0] = 2;\n    *(f32 *)(output + 0x28) = *(f32 *)(source + 0x20);\n    if (func_15144E80((s16 *)(source + 0xC), (f32 *)(output + 0x10),\n                     (f32 *)(output + 0x1C), (f32 *)(output + 4))) {\n        if (func_15144A74((f32 *)(output + 4), (f32 *)source) < 0.0f) {\n            *(f32 *)(output + 4) = -*(f32 *)(output + 4);\n            *(f32 *)(output + 8) = -*(f32 *)(output + 8);\n            *(f32 *)(output + 0xC) = -*(f32 *)(output + 0xC);\n        }\n    }\n}"}
BINDINGS = {60: [('R_MIPS_26', 'func_15144E80')],80: [('R_MIPS_26', 'func_15144A74')]}



def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Oriented triangle record historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Oriented triangle record padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Oriented triangle record frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Oriented triangle record predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Oriented triangle record snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    result = before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+DECLARATIONS,1)
    if result.count('func_1514F640(arg0, temp);') != 2:
        raise ValueError('Oriented triangle record known wrapper calls changed')
    result = result.replace('func_1514F640(arg0, temp);','func_1514F640((u8 *)arg0, temp);')
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown oriented triangle record predecessor: ' + name)
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero oriented triangle record alignment tail')
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
    neighbors_expected = len(parse_object(output/'before-padded.o')[1])-1
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Oriented triangle record owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        if dc or len(raw) != target['size'] or digest(raw) != target['SHA256'] or bindings != BINDINGS:
            raise ValueError('Oriented triangle record isolated direct C differs')
        if payload(after,name) != (raw,bindings) or payload(original(root,output,name),name) != (raw,bindings):
            raise ValueError('Oriented triangle record whole owner/GNU original differs')
        text,functions = link_owner(root,output,isolated,OWNER);at=functions[name]['value']
        if text[at:at+168] != truth:
            raise ValueError('Oriented triangle record linked C differs')
        rows.append(dict(function=name,words=42,frame=40,bindings=2,new_guards=0))

    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != neighbors_expected or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Oriented triangle record raw owner neighbor/pool changed')
    padded = output / 'padded/generated_17CAF0.c.s'
    padded.parent.mkdir(parents=True,exist_ok=True)
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Oriented triangle record frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown oriented triangle record predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Oriented triangle record predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Oriented triangle record padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Oriented triangle record padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Oriented triangle record padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != neighbors_expected or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Oriented triangle record padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(targets=rows, total_words=42, compiler_only=True, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_sizes_before=[12], target_sizes_after=[168])
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Oriented triangle record shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_17CAF0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected oriented triangle record Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_17CAF0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown oriented triangle record Make redirect')
            redirect = (conker / args[-1]).resolve();redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Oriented triangle record Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Oriented triangle record Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output/'before-padded.o')[1]):
        raise ValueError('Oriented triangle record actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'padded/generated_17CAF0.c.o', OWNER):
        raise ValueError('Oriented triangle record actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Oriented triangle record strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Oriented triangle record symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Oriented triangle record image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_17CAF0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown oriented triangle record link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'padded/generated_17CAF0.c.o').relative_to(root / 'conker').as_posix()))
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
            raise ValueError('Oriented triangle record installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Oriented triangle record independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Oriented triangle record changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'padded/generated_17CAF0.c.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'padded/generated_17CAF0.c.o'):
        raise ValueError('Oriented triangle record installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Oriented triangle record protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=42, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
