"""Direct C recovery and strict owner/image gates for the oscillating-motion update."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_151B8B40', 0x151B8B40, 0x1E5FF0, 160
SOURCE, OWNER, ASM = 'conker/src/game/generated_1E5FF0.c', 'generated_1E5FF0', 'conker/asm/1E5FF0.s'
BUILD = 'conker/build/game-oscillating-motion/qualified'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/src/game/generated_1E5FF0.c": "93bd72366d8b03307b5796dbc3b596b0e1ec222447d23f86f0c7ccc9d291c483",
    "conker/asm/1E5FF0.s": "be9b22bf86c518e8e3b4861928c190d11692b7864f76eb37c04e2e2b950025ef",
    "conker/src/libultra/gu/sinf.c": "ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679",
    "conker/asm/nonmatchings/libultra/gu/sinf/sinf.s": "aaa2e4b725d2370cf7cc8f09860753184858f98c2a54635bc4ffad935b5916bd",
    "conker/src/game_16EE20.c": "7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810",
    "conker/asm/nonmatchings/game_16EE20/func_15144B68.s": "472c6822afc3d244b2471949c6d5143830d08a8b5bc9bc4863e5f97332a757f1",
    "conker/asm/15F680.s": "f697fe44a7ea8c4c6a7a7016236764a088a6922f559686ee4d3731d5c264413b",
    "conker/asm/data/22E370.rodata.s": "42925f1b2e64e1ad241cff05afa857ab4dc3b9e812a2764ef360885fdc2c2612",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/build/conker.us.elf": "93e2e0785b38b376eb6f9715ced30a2ca7d723403fcdda632f90b06818936832",
    "conker/retail_word_patches.us.csv": "016466c90030bca35c3b27892833265d62314b8b8156145fd9c2eae7c3e37623",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be"
}
SINE, WRAP, CLOCK = 0x15047D60, 0x15144B68, 0x800BE9A4
TYPES = '''typedef struct {
    u8 header[0x20];
    f32 x;
    u8 reserved24[4];
    f32 z;
    u8 reserved2C[0x10];
    f32 oscillation;
    u8 reserved40[4];
    f32 phase;
    f32 base;
    f32 phaseRate;
    f32 velocityX;
    u8 reserved54[4];
    f32 velocityZ;
    f32 amplitude;
} OscillatingMotionRecord;
'''
DECLARATIONS = '''extern f32 D_800BE9A4;
f32 func_15144B68(f32);
'''
SELECTED = '''/* Advance the oscillating field, phase and planar coordinates. */
s32 func_151B8B40(OscillatingMotionRecord *record) {
    record->oscillation = sinf(record->phase) * record->amplitude + record->base;
    record->phase += record->phaseRate * D_800BE9A4;
    record->phase = func_15144B68(record->phase);
    record->x += record->velocityX * D_800BE9A4;
    record->z += record->velocityZ * D_800BE9A4;
    return 1;
}'''


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
    if before[lo:hi] != 's32 func_151B8B40() {\n    return 0;\n}':
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
    report = dict(words=40, frame=24, differences=0, relocations=6, new_guards=0,
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


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Oscillating-motion update installed input differs: ' + name)
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
        target_words=40, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
