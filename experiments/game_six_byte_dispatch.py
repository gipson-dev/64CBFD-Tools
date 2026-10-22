"""Six ordered byte submissions with source, ABI and strict image qualification."""

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

SOURCE, OWNER, ASM = 'conker/src/game/generated_E1280.c', 'generated_E1280', 'conker/asm/E1280.s'
BUILD = 'conker/build/game-six-byte-dispatch/qualified'
OBJECT = 'conker/build/src/game/generated_E1280.c.o'
BEFORE_OBJECT_SHA = 'f28724a90761f649b06045be641e0e5063c2c073cc51d860f0237c034e1aed0f'
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
    "conker/build/conker.us.elf": "6e51b1a879d012d3b84bec32cce212f34ef9e08e302574a69afdfd74ecd21110",
    "conker/retail_word_patches.us.csv": "704d9da0fe81ea2498078c8b5b2f53994ba05cf8e9e88af2ba0cb5dfd38ce71c",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/src/game/generated_E1280.c": "0088612fcdb3d2096ecc70e98dc90776bdb902d0618cfcdfc0aff0f5b7667652",
    "conker/asm/E1280.s": "36c268ebed056b4afd5b68856a07831e8aa871ff7337d77877a9656356c8a40d",
    "conker/asm/data/24A230.rodata.s": "58647232dab722f5c10c6e3a8fd95698a1ee171fa8dbd3b55c46031caf0c2ac3",
    "conker/asm/data/24A220.rodata.s": "b283dbe0127815615aab5a5fbbd5038d634d3d12af33a1a7b617f56d5bc633be",
    "conker/asm/data/22FF40.rodata.s": "79390c57d68092ea4bcaa684d91ad9a6ab011bdb56f2e9bccff00266eb794158",
    "conker/src/game/done/game_1765E0.c": "19dd4f8a4e0561ad2de70ee59e12e50c11a9938357816dd0eacb2334d8c0c5af",
    "conker/src/game/generated_174BF0.c": "40464d9f5aac3206d524f16c6f3574ea04005d2965d36d3f87d688cf562937c5",
    "conker/asm/174BF0.s": "08aa8b9b889ba15853edf2a93e523f1029a0b2f88536bd48750fb7df4d4aa62e",
    "conker/src/game_1944C0.c": "328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b",
    "conker/asm/nonmatchings/game_1944C0/func_15169260.s": "109c491ae0588400a68be58abee1f230520ce4d42e97af9e71253588d2da48fb",
    "conker/src/game/generated_C9EC0.c": "c1aab1b79f7759a0d8a4039b2c61c4129f5a5dd8cf032924a0c7b338b7d47e01",
    "conker/asm/C9EC0.s": "c9f63165853a82a51b1ffae7a9c421863f453c28fd223520a4462f2cc9a35f83",
    "conker/asm/data/243B90.rodata.s": "bdda5089901de9157e95d6d9aea695b6185f01b2afa4503f9640ad6f85aac658"
}
TARGETS = {
    'func_150B3DD0': dict(entry=0x150B3DD0, rom=0xE1280, size=164,
        SHA256='dfa8426fa9150a1b4cc5336888199f15b34a74b4dab22581f7e4c4561c5ec142'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = "void func_15147D64(void *, u8);\nvoid func_151494E0(void *, u8);\n"
SELECTED = {'func_150B3DD0': "/* Submit the six ordered byte selections after initializing the first group. */\nvoid func_150B3DD0(void) {\n    u8 selection[4];\n\n    func_15147D64(0, 5);\n    selection[0] = 0;\n    func_151494E0(selection, 0x18);\n    selection[0] = 2;\n    func_151494E0(selection, 0x18);\n    selection[0] = 4;\n    func_151494E0(selection, 0x18);\n    selection[0] = 1;\n    func_151494E0(selection, 0x18);\n    selection[0] = 3;\n    func_151494E0(selection, 0x18);\n    selection[0] = 5;\n    func_151494E0(selection, 0x18);\n}"}
BINDINGS = {16: [('R_MIPS_26', 'func_15147D64')]}
BINDINGS.update({at: [('R_MIPS_26', 'func_151494E0')] for at in (36, 56, 76, 96, 116, 136)})



def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Six-byte dispatch historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Six-byte dispatch padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Six-byte dispatch frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Six-byte dispatch predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Six-byte dispatch snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    result = before.replace("#include <ultra64.h>\n", "#include <ultra64.h>\n" + DECLARATIONS + "\n")
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown six-byte dispatch predecessor: ' + name)
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero six-byte dispatch alignment tail')
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
        raise ValueError('Six-byte dispatch owner diagnostics changed: ' + da + db)
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        if dc or len(raw) != target['size'] or digest(raw) != target['SHA256'] or bindings != BINDINGS:
            raise ValueError('Six-byte dispatch isolated direct C differs: ' + name)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (raw, bindings):
            raise ValueError('Six-byte dispatch whole owner/GNU original differs: ' + name)
        text, functions = link_owner(root, output, isolated, OWNER)
        at = functions[name]['value']
        if text[at:at + target['size']] != truth:
            raise ValueError('Six-byte dispatch linked C differs')
        rows.append(dict(function=name, words=len(raw)//4, frame=40, bindings=7, new_guards=0))
    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != 9 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Six-byte dispatch raw owner neighbor/pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Six-byte dispatch frozen object changed')
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    changed_ranges = []
    for name, target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown six-byte dispatch predecessor extent')
        expected[name]['size'] = target['size']
        at = fb[name]['value'];changed_ranges.append((at, at + target['size']))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'], target['entry'], target['size'])
        if a[at:at + target['size']] != values['conker/build/conker.us.elf'][slot:slot + target['size']]:
            raise ValueError('Six-byte dispatch predecessor object/ELF mismatch')
        if b[at:at + target['size']] != values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]:
            raise ValueError('Six-byte dispatch padded target differs')
    if expected != fb or len(a) != len(b):
        raise ValueError('Six-byte dispatch padding changed function metadata')
    if any(x != y and not any(lo <= at < hi for lo, hi in changed_ranges) for at, (x, y) in enumerate(zip(a, b))):
        raise ValueError('Six-byte dispatch padding changed another body')
    if same_functions(old, obj, FUNCTIONS) != 9 or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Six-byte dispatch padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(targets=rows, total_words=41, compiler_only=True, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        target_sizes_before=[12], target_sizes_after=[164])
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Six-byte dispatch shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_E1280.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected six-byte dispatch Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_E1280.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown six-byte dispatch Make redirect')
            redirect = (conker / args[-1]).resolve();redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Six-byte dispatch Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Six-byte dispatch Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != 10:
        raise ValueError('Six-byte dispatch actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Six-byte dispatch actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Six-byte dispatch strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Six-byte dispatch symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Six-byte dispatch image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_E1280.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown six-byte dispatch link input')
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
            raise ValueError('Six-byte dispatch installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Six-byte dispatch independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Six-byte dispatch changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Six-byte dispatch installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Six-byte dispatch protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=41, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
