"""Timed vertical oscillation: direct C recovery and strict owner/image gates."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_151D3D50', 0x151D3D50, 0x201200, 180
SOURCE, OWNER, ASM = 'conker/src/game/generated_200930.c', 'generated_200930', 'conker/asm/200930.s'
BUILD = 'conker/build/game-vertical-bob-match'
OBJECT = 'conker/build/src/game/generated_200930.c.o'
BEFORE_OBJECT_SHA = "a2a4dd879e933ae63561118d0d249fdd7ce5aa5f69dd5e334e2703d615ae3867"
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/15F680.s": "f697fe44a7ea8c4c6a7a7016236764a088a6922f559686ee4d3731d5c264413b",
    "conker/asm/200930.s": "5ce85a7f8a95e7032bf288d82a3b9d318eb42d0280bf443f9bf0f950f03d2ab1",
    "conker/asm/data/22E370.rodata.s": "42925f1b2e64e1ad241cff05afa857ab4dc3b9e812a2764ef360885fdc2c2612",
    "conker/asm/nonmatchings/game_16EE20/func_15144B68.s": "472c6822afc3d244b2471949c6d5143830d08a8b5bc9bc4863e5f97332a757f1",
    "conker/asm/nonmatchings/generated_200930/func_151D3480.s": "868b618d3670d0f399e72fed7de17efd5ccdca8bb8da21e7179c58ac2c4b2d61",
    "conker/asm/nonmatchings/generated_200930/func_151D3E04.s": "9b32cd2b713781bbc8d8d208dc9ec49bcf06f7ede29766f0e20f80b62b4d918c",
    "conker/asm/nonmatchings/generated_200930/func_151D3E6C.s": "eb02bb8dea4f2fc0d27b42394f5b332379c55cba807c1d75c2128ef32f32bbcd",
    "conker/asm/nonmatchings/generated_200930/func_151D3F14.s": "d3195027a4106353a8c38a468326ed62e0eab1eebaa656fe0ab8cf50fa3d4bd0",
    "conker/asm/nonmatchings/generated_200930/func_151D3FF4.s": "62ed53223c6a78c740cbab8d5b848bb41a9a7e3cf3f10590027b7784daac4674",
    "conker/asm/nonmatchings/generated_200930/func_151D40D4.s": "b1aaa92f49dbb7289fc9ac0ad8b5b410f4fd02953f17d212d0f02b27afe24c55",
    "conker/asm/nonmatchings/generated_200930/func_151D42E8.s": "fc6d71d34546d65327d3af39b1e9f3a41a5c2bfb839b1358cb295413b4bc3479",
    "conker/asm/nonmatchings/generated_200930/func_151D4408.s": "12fe323d20d2d730a4e1520c036ae2641ec31a86502e84c803bb14aebe758c67",
    "conker/asm/nonmatchings/generated_200930/func_151D469C.s": "bc04b07af5efcf7655ee7771b10ab1a8ffc71a7dc4be206ccf964d4d47cb63ac",
    "conker/asm/nonmatchings/generated_200930/func_151D4794.s": "20b6e087e74a14e989e82020605888145671507933e9c40b2172b7f9e7fd28c2",
    "conker/asm/nonmatchings/generated_200930/func_151D4DAC.s": "fbadc0aeae82b8c775e9bcccfbc7300326932688e61cccb9d24a275f7e6b7f53",
    "conker/asm/nonmatchings/generated_200930/func_151D5174.s": "a32b841351bfe728a9c0f264766131d48b6c5deaa2d1ff10d53eeac12bf649f8",
    "conker/asm/nonmatchings/generated_200930/func_151D5334.s": "1f085010e1574e1f28975652abb9e4c0bf2538a75f037eecd0e43d2d6332bfd7",
    "conker/asm/nonmatchings/generated_200930/func_151D5404.s": "c26e46d2e9fbbdf67613dc3ee6383e9bc0ec2b894709d795f74832bdc7c5ba80",
    "conker/asm/nonmatchings/generated_200930/func_151D5514.s": "f9c80a67cb88975c279c781746ad2e941c534c8a8ac2dbd077282bc9c7923362",
    "conker/asm/nonmatchings/generated_200930/func_151D57F8.s": "e522fa557911ac8fd3d6386821789d48ec5ce49c397565526406b57a480852f7",
    "conker/asm/nonmatchings/generated_200930/func_151D5A18.s": "bc93fc20f9a91191ccf1b7d0b7eb00b9104db64fdf6b5d74f07a6491d85ba914",
    "conker/asm/nonmatchings/generated_200930/func_151D5B6C.s": "69ee9c34e4cda0e2bd66d1af222225cea041783383864f54c4fdbd3b98bdf88e",
    "conker/asm/nonmatchings/generated_200930/func_151D5D60.s": "d04e3bd7d48cc07684692cb4f47e179c93701ab1f1d830923f7da92b0be208a0",
    "conker/asm/nonmatchings/libultra/gu/sinf/sinf.s": "aaa2e4b725d2370cf7cc8f09860753184858f98c2a54635bc4ffad935b5916bd",
    "conker/build/conker.ld": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
    "conker/build/conker.us.elf": "5ef98eaf08feb4a0553161a5fcde17ad5f05cca08055c99c92e50d73d73a83e3",
    "conker/build/src/game/generated_15F680.c.o": "5579757f73d69cd549d0f7d1e51cd89e6bf99a97ec31fff6446e1a042c2b940b",
    "conker/build/src/game/generated_200930.c.o": "a2a4dd879e933ae63561118d0d249fdd7ce5aa5f69dd5e334e2703d615ae3867",
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
    "conker/src/game/generated_15F680.c": "7bdcdacebf10a75fc8c4090ac82355b45f122f1771457f47d69e61dc19d57e94",
    "conker/src/game/generated_200930.c": "7cdd70fe6156f54b225c7c3a3fc860d9ea1fe3dcf7c01645e33c7eec59811c43",
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
TYPES = "typedef struct { f32 x,y,z; } BobVector200930;\ntypedef struct { s16 remaining; u16 reserved; f32 phase,rate,amplitude; } BobState200930;\ntypedef struct {\n    u8 pad0[0x20]; BobVector200930 position;\n    u8 pad2C[0x24]; BobVector200930 base;\n    u8 pad5C[0x114]; BobState200930 bob;\n} BobActor200930;\n"
DECLARATIONS = "extern f32 D_800BE9A4;\nextern s32 D_800BE9E4;\nf32 func_15144B68(f32);\nf32 sinf(f32);\n"
SELECTED = "/* Advance the vertical oscillation, or restore the base position. */\ns32 func_151D3D50(BobActor200930 *actor) {\n    BobState200930 *bob = &actor->bob;\n\n    if (bob->remaining > 0) {\n        bob->phase += bob->rate * D_800BE9A4;\n        bob->phase = func_15144B68(bob->phase);\n        actor->position.y = sinf(bob->phase) * bob->amplitude + actor->base.y;\n        bob->remaining -= D_800BE9E4;\n    } else {\n        actor->position = actor->base;\n    }\n    return 1;\n}"
RAW_SHA256 = "18d9f2037abaf16971ade9ff8486d8cf72cdb5eb453f282009f311cd309edc3c"
BINDINGS = {16: [("R_MIPS_HI16", "D_800BE9A4")], 32: [("R_MIPS_LO16", "D_800BE9A4")], 60: [("R_MIPS_26", "func_15144B68")], 76: [("R_MIPS_26", "sinf")], 92: [("R_MIPS_HI16", "D_800BE9E4")], 116: [("R_MIPS_LO16", "D_800BE9E4")]}


def checked_payload(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Changed vertical oscillation words/bindings')


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
    if before[lo:hi] != 's32 func_151D3D50() {\n    return 0;\n}':
        raise ValueError('Unknown oscillating-motion source predecessor')
    result = (before[:lo] + SELECTED + before[hi:])
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown oscillating-motion include anchor')
    return result.replace(anchor, anchor + TYPES + DECLARATIONS + '\n', 1)


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
        shutil.copyfile(root / 'conker/build/src/game/generated_200930.c.o', old)
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
    report = dict(words=45, frame=32, differences=0, relocations=6, new_guards=0,
        slot_words=45, alignment_words=0, alignment_bytes_preserved=True,
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
    target = (shadow / 'src/game/generated_200930.c.o').relative_to(conker).as_posix()
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
                if a == 'src/game/generated_200930.c' else a for a in args]
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
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Oscillating-motion update actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Oscillating-motion update actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
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
    old = 'build/src/game/generated_200930.c.o'
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
        target_words=45, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
