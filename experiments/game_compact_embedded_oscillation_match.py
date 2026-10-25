"""Embedded oscillating motion: direct C recovery and strict owner/image gates."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_151B8CFC', 0x151B8CFC, 0x1E61AC, 172
SOURCE, OWNER, ASM = 'conker/src/game/generated_1E5FF0.c', 'generated_1E5FF0', 'conker/asm/1E5FF0.s'
BUILD = 'conker/build/game-compact-embedded-oscillation-match'
OBJECT = 'conker/build/src/game/generated_1E5FF0.c.o'
BEFORE_OBJECT_SHA = 'bab75054f2d6dff8ee64d5b045be8bdd7e843bafdba560d5cf2168aeacdddc2a'
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/1E5FF0.s": "be9b22bf86c518e8e3b4861928c190d11692b7864f76eb37c04e2e2b950025ef",
    "conker/asm/data/22E730.rodata.s": "04adc08432aaa1052219d977d68d9769ac85e1efca4aa89b8b35b8cddedf8413",
    "conker/asm/nonmatchings/game_169510/func_1513CFE4.s": "cbdedd2bb802ac4c33454cdd7c62417b531e263524f5a79757fd5697e3d82815",
    "conker/asm/nonmatchings/game_16EE20/func_15144B68.s": "472c6822afc3d244b2471949c6d5143830d08a8b5bc9bc4863e5f97332a757f1",
    "conker/asm/nonmatchings/libultra/gu/sinf/sinf.s": "aaa2e4b725d2370cf7cc8f09860753184858f98c2a54635bc4ffad935b5916bd",
    "conker/build/conker.us.elf": "d44b751638695c2eefa8ed8db23ea9fa15d201907c3bb6bb4fdba7fc05e1ed35",
    "conker/build/src/game/generated_1E5FF0.c.o": "bab75054f2d6dff8ee64d5b045be8bdd7e843bafdba560d5cf2168aeacdddc2a",
    "conker/build/src/game_169510.c.o": "95374151740bf29c76b8ade5e52c775a098e20041fccc984eb78095278a50b8c",
    "conker/build/src/game_16EE20.c.o": "a89b632e30be0d30fd43255a7d009ae0e87cdd439c4f90030e7dcc34e0c6d163",
    "conker/build/src/libultra/gu/sinf.c.o": "100de92468889c8cce6f771bf2ca3ebe8fd9b78ead6ecf013f47834f525d2c42",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/libc/stdarg.h": "759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/retail_word_patches.us.csv": "876afb871a1a6c41916b69b192d8b9fc786b688ad91a2381bfdcd9a698814d3b",
    "conker/src/game/generated_1E5FF0.c": "dbc7f355a42826ed4e57e78f8ae1177a48865df78dcd24d6882d957a835beff6",
    "conker/src/game_169510.c": "cb2f5e4bc1df3d0c31b27ccf4094a98834cac2caee9b18cc00944207ed2647f8",
    "conker/src/game_16EE20.c": "fc2cdab1d1d3952842fc82335c3599725171c5dad3fb4afd0e2ea31cc1c1b12a",
    "conker/src/libultra/gu/sinf.c": "ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "tools/experiments/game_embedded_oscillating_motion.py": "bdc4fd1afe704a708035378f27306c85514d2d020243eb0b91f53d9c5e6e0128",
    "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
    "tools/tests/test_game_actor_counter_motion.py": "0d47a852ddc422a347470fe8df6c361cef96e04ed047aade0212ec198c10f7b0",
    "tools/tests/test_game_embedded_oscillating_motion.py": "a04909d07c4b20e596378a79aba0b5f9b3cd290c027cdcc18243a5e7b6018614"
}

SINE, WRAP, CLOCK = 0x15047D60, 0x15144B68, 0x800BE9A4
TYPES = 'typedef struct {\n    f32 base;\n    f32 amplitude;\n    f32 phase;\n    f32 phaseRate;\n    f32 velocityX;\n    u8 reserved14[4];\n    f32 velocityZ;\n} CompactEmbeddedOscillatingMotion;\n'
DECLARATIONS = '''extern f32 D_800BE9A4;
f32 func_15144B68(f32);
'''
SELECTED = '/* Advance the compact oscillation, phase and planar coordinates. */\ns32 func_151B8CFC(u8 *actor) {\n    CompactEmbeddedOscillatingMotion *motion = (CompactEmbeddedOscillatingMotion *)(actor + 0x110);\n    *(f32 *)(actor + 0x38) = sinf(motion->phase) * motion->amplitude + motion->base;\n    motion->phase += motion->phaseRate * D_800BE9A4;\n    motion->phase = func_15144B68(motion->phase);\n    *(f32 *)(actor + 0x40) += motion->velocityX * D_800BE9A4;\n    *(f32 *)(actor + 0x48) += motion->velocityZ * D_800BE9A4;\n    return 1;\n}'
RAW_SHA256 = 'fa2bba2b02a026c254cf9379bd07e03a033ff51b03b68b1155973f79af3fbfd6'
BINDINGS = {12: [('R_MIPS_26', 'sinf')], 24: [('R_MIPS_HI16', 'D_800BE9A4')],
            52: [('R_MIPS_LO16', 'D_800BE9A4')], 80: [('R_MIPS_26', 'func_15144B68')],
            96: [('R_MIPS_HI16', 'D_800BE9A4')], 100: [('R_MIPS_LO16', 'D_800BE9A4')]}


def checked_payload(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Changed compact oscillation words/bindings')


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Oscillating-motion update historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    data = (root / OBJECT).read_bytes() if not old.exists() else old.read_bytes()
    if digest(data) != BEFORE_OBJECT_SHA:
        raise ValueError('Embedded-motion padded predecessor changed')
    if not old.exists():
        old.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Oscillating-motion update predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Oscillating-motion update snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151B8CFC() {\n    return 0;\n}':
        raise ValueError('Unknown oscillating-motion source predecessor')
    result = (before[:lo] + SELECTED + before[hi:])
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown oscillating-motion include anchor')
    return result.replace(anchor, anchor + TYPES + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero oscillating-motion alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('MotionOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-oscillating-motion',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + TYPES + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Oscillating-motion update compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    checked_payload(raw, bindings)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or sum(map(len, bindings.values())) != 6 or payload(after) != (raw, bindings):
        raise ValueError('Oscillating-motion update direct C differs from retail/whole owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Oscillating-motion update independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Oscillating-motion update raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_1E5FF0.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown oscillating-motion padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Oscillating-motion update predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Oscillating-motion update padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Oscillating-motion update padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=43, frame=32, differences=0, relocations=6, new_guards=0,
        slot_words=45, alignment_words=2, alignment_bytes_preserved=True,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Oscillating-motion update shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1E5FF0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected oscillating-motion Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1E5FF0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown oscillating-motion Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Oscillating-motion update Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Oscillating-motion update Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Oscillating-motion update actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Oscillating-motion update actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Oscillating-motion update strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Oscillating-motion update symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Oscillating-motion update image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1E5FF0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown oscillating-motion link input')
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


def audit_inputs(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        expected = (recovered_owner(old.decode()).encode() if name == SOURCE else
                    (output / 'qualified-padded.o').read_bytes() if name == OBJECT else
                    wanted if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != expected:
            raise ValueError('Oscillating-motion update installed input differs: ' + name)
    return values, wanted


def audit(root, output):
    values, wanted = audit_inputs(root, output)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Oscillating-motion update independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Oscillating-motion update changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Oscillating-motion update protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=43, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
