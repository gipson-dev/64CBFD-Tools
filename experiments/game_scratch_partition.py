"""Direct C recovery and strict owner/image gates for the scratch partition."""

import csv
import io
import sys
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
from tools.pad_generated_object import parse_object
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout


FUNCTION, ENTRY, ROM, SIZE = 'func_15002754', 0x15002754, 0x2FC04, 164
SOURCE, OWNER, ASM = 'conker/src/game_2DF70.c', 'game_2DF70', 'conker/asm/nonmatchings/game_2DF70/func_15002754.s'
BUILD = 'conker/build/game-scratch-partition/qualified'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/src/game_2DF70.c": "b0d712f3db86c593c8ba2ee5db9e8ae6e7f3228fe8650e9b180aaa78f92dccaf",
    "conker/asm/nonmatchings/game_2DF70/func_15002754.s": "282849677d7bb5c67d0f49bf44ed25aa80b0da85af54751e32448d5897116ab2",
    "conker/asm/nonmatchings/game_2DF70/func_15000AD0.s": "e6901fdde97df5a8209b533d92695cbf6bdb8a329eef3842f7cfdfdbb101c6c9",
    "conker/asm/nonmatchings/game_2DF70/func_15001460.s": "96b0302e619d7437e253db34838fbfe373646dee2733423a4eb6fd75a73f2400",
    "conker/asm/nonmatchings/game_2DF70/func_15001A08.s": "02ace33980fee2384f5f2138fe4febb723833f2b6d9ad97f47eb9e8ad75e0815",
    "conker/asm/nonmatchings/game_2DF70/func_15002008.s": "d6dfeb2547b0765afafecab6626464cd1b66323cb2c395a4c3f79c8561d824bf",
    "conker/asm/nonmatchings/game_2DF70/func_15002248.s": "5c76128c4448601f6aecb75e25c0425bc1231fd22a799b7ae57c34b7a8d781e9",
    "conker/asm/nonmatchings/game_2DF70/func_150028BC.s": "2e98626662916904c257eee6abf88590e287fecdea6e47a7e345c5d0452f0ee3",
    "conker/asm/data/22DF70.rodata.s": "b87978cd4a95213a0c1076bfabc554d2fee7a8c46425f7f0e16001c19d358b71",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/asm/nonmatchings/game_305D0/func_15003668.s": "621e290e6c31f8c97fb72f916b7efe6a8c52701e149fa7ec2b28a97e87e91549",
    "conker/src/game_305D0.c": "c9b6635643bd970b7f4c98775af471209d56594b223dda9613546b49edce8cdc",
    "conker/asm/13BB20.s": "155a5922bb8c45502bef0b64e42a71cc118f4c00531b22333c05ddd71a7c3824",
    "conker/src/game/generated_13BB20.c": "493b9f11ee18424092263af1b6503e68570ec34c31526377f62c27ac2378076e",
    "conker/asm/nonmatchings/generated_D0F20/func_150A49F4.s": "6d146a8c6c1f9ca1375bd432c6436c546c0bb5cf2193c6c28052ab2998768946",
    "conker/asm/D0F20.s": "44d1af8afb53ccdd652b6a8f6ce57bfa235b4caf1e215a6f27cf5585ba46b533",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/build/conker.us.elf": "da4591cc23d4cbd8c1bdc20ce7ee2035e6f60dd87133e32222e0d695186c9ec4",
    "conker/retail_word_patches.us.csv": "016466c90030bca35c3b27892833265d62314b8b8156145fd9c2eae7c3e37623",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be"
}
OBJECT = 'conker/build/src/game_2DF70.c.o'
BEFORE_OBJECT_SHA = '6fe65fdd0594abc949d6d709ecfa42343c79946bb699c6f685f9bcb146accd2d'
RAW_SHA = 'ad79c62ccd743c79b7fab7852569707b8c00b923591889e705ad64f67c58051b'
RAW_BINDINGS = {4: [("R_MIPS_HI16", "D_800B0DC0")],
    8: [("R_MIPS_LO16", "D_800B0DC0")],
    24: [("R_MIPS_HI16", "D_800DBE38")],
    40: [("R_MIPS_LO16", "D_800DBE38")],
    44: [("R_MIPS_HI16", "D_800DBE50")],
    48: [("R_MIPS_LO16", "D_800DBE50")],
    56: [("R_MIPS_HI16", "D_800DBDD8")],
    76: [("R_MIPS_LO16", "D_800DBDD8")],
    84: [("R_MIPS_HI16", "D_800DBDE8")],
    100: [("R_MIPS_LO16", "D_800DBDE8")],
    108: [("R_MIPS_HI16", "D_800DBDF8")],
    124: [("R_MIPS_LO16", "D_800DBDF8")],
    132: [("R_MIPS_26", "func_1510F800")],
    140: [("R_MIPS_HI16", "D_800DBE38")],
    144: [("R_MIPS_LO16", "D_800DBE38")]}
GUARDS = (
    (0x18, 0x3c050000, 0x3c060000, "R_MIPS_HI16:D_800DBE38"),
    (0x28, 0x8ca50000, 0x8cc60000, "R_MIPS_LO16:D_800DBE38"),
    (0x34, 0x5c880, 0x6c880, "-"),
    (0x3c, 0x325c823, 0x326c823, "-"),
    (0x40, 0x43080, 0x42880, "-"),
    (0x44, 0x260821, 0x250821, "-"),
    (0x5c, 0x260821, 0x250821, "-"),
    (0x60, 0x548c0, 0x648c0, "-"),
    (0x74, 0x260821, 0x250821, "-"),
    (0x78, 0x55880, 0x65880, "-"),
)
TYPES = ''
DECLARATIONS = '''extern s32 D_800B0DC0, D_800DBE38, D_800DBE50;
extern s32 D_800DBDD8[], D_800DBDE8[], D_800DBDF8[];
void func_1510F800(s32);
'''
BEFORE_BODY = '''void func_15002754(void) {
    s32 aligned;
    s32 index = D_800DBE50;
    s32 count = D_800DBE38;

    aligned = (D_800B0DC0 + 3) & ~3;
    D_800B0DC0 = aligned;
    D_800DBDD8[index] = aligned;
    aligned += count * 12;
    D_800B0DC0 = aligned;
    D_800DBDE8[index] = aligned;
    aligned += count * 8;
    D_800B0DC0 = aligned;
    D_800DBDF8[index] = aligned;
    D_800B0DC0 = aligned + (count * 4);
    func_1510F800(index);
    D_800DBE38 = 0;
}'''
SELECTED = '''/* Partition the current context's scratch arrays, then reset the count. */
void func_15002754(void) {
    u32 count;
    s32 index;

    D_800B0DC0 = (s32) (((u32) D_800B0DC0 + 3U) & ~3U);
    count = (u32) D_800DBE38;
    index = D_800DBE50;
    D_800DBDD8[index] = D_800B0DC0;
    D_800B0DC0 = (s32) ((u32) D_800B0DC0 + count * 12U);
    D_800DBDE8[index] = D_800B0DC0;
    D_800B0DC0 = (s32) ((u32) D_800B0DC0 + count * 8U);
    D_800DBDF8[index] = D_800B0DC0;
    D_800B0DC0 = (s32) ((u32) D_800B0DC0 + count * 4U);
    func_1510F800(index);
    D_800DBE38 = 0;
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
            raise ValueError('Scratch partition historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Scratch-partition padded predecessor changed')
        old.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Scratch partition predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Scratch partition snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != BEFORE_BODY:
        raise ValueError('Unknown scratch-partition source predecessor')
    result = before[:lo] + SELECTED + before[hi:]
    anchor = 's32 func_150027F8(s32 arg0);\n'
    if result.count(anchor) != 1 or 'void func_1510F800(s32);' in result:
        raise ValueError('Unknown scratch-partition declaration anchor')
    return result.replace(anchor, anchor + 'void func_1510F800(s32);\n', 1)



def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero scratch-partition alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('PartitionOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-scratch-partition',
        (root / ASM).read_text(), FUNCTION)


def normalized(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA or bindings != RAW_BINDINGS:
        raise ValueError('Scratch-partition closed raw body/bindings changed')
    result = bytearray(raw)
    for at, old, new, relocation in GUARDS:
        actual = ';'.join(kind + ':' + name for kind, name in bindings.get(at, ())) or '-'
        if struct.unpack_from('>I', raw, at)[0] != old or actual != relocation:
            raise ValueError('Scratch-partition guarded word/binding changed')
        struct.pack_into('>I', result, at, new)
    return bytes(result), bindings


def guard_bytes(values):
    before = values['conker/retail_word_patches.us.csv']
    if not before.endswith(b'\n') or (OWNER + ',' + FUNCTION + ',').encode() in before:
        raise ValueError('Scratch-partition guard prefix changed')
    rows = io.StringIO(newline='')
    writer = csv.writer(rows, lineterminator='\n')
    for at, old, new, relocation in GUARDS:
        writer.writerow((OWNER, FUNCTION, '0x%03X' % at, '0x%08X' % old,
            '0x%08X' % new, relocation, relocation,
            'Normalize closed scratch partition count/index allocation', '', '', 'false'))
    return before + rows.getvalue().encode()



def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + TYPES + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Scratch partition compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    fitted, fit_bindings = normalized(raw, bindings)
    original_obj = original(root, output)
    original_linked, original_functions = link_owner(root, output, original_obj, OWNER)
    original_at = original_functions[FUNCTION]['value']
    patched = bytearray(linked[at:at + SIZE])
    for offset, _, _, _ in GUARDS:
        patched[offset:offset + 4] = original_linked[original_at + offset:original_at + offset + 4]
    if bytes(patched) != truth or sum(map(len, bindings.values())) != 15 or payload(after) != (raw, bindings):
        raise ValueError('Scratch-partition guarded C differs from retail/whole owner')
    if payload(original_obj) != (fitted, fit_bindings):
        raise ValueError('Scratch-partition independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Scratch partition raw owner pool changed')
    padded = output / 'qualified-padded.s'
    guards = output / 'proposed-guards.csv'
    guards.write_bytes(guard_bytes(values))
    padded.write_text('.include "asm_processor_prelude.inc"\n' + pad_c_object.emit_padded_assembly(
        after, root / 'conker/retail_layout.us.txt', OWNER, word_patches_path=guards))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game_2DF70.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 152:
        raise ValueError('Unknown scratch-partition padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Scratch partition predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Scratch partition padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Scratch partition padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=41, frame=24, differences=0, relocations=15, new_guards=10,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=False, raw_differences=10, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=152, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Scratch partition shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game_2DF70.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected scratch-partition Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game_2DF70.c' else (output / 'proposed-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown scratch-partition Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Scratch partition Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Scratch partition Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Scratch partition actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Scratch partition actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Scratch partition strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 152) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Scratch partition symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Scratch partition image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game_2DF70.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown scratch-partition link input')
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
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else guard_bytes(values) if name == 'conker/retail_word_patches.us.csv' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Scratch partition installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Scratch partition independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Scratch partition changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Scratch-partition installed padded object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Scratch partition protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=41, strict_first_link_reproduced=True, old_guard_prefix_preserved=True, new_guards=10, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
