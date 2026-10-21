"""Guarded C recovery and closed image gates for the color/table reset."""

import csv
import io
import hashlib
import json
import re
from functools import partial
from pathlib import Path
import shlex
import shutil
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import function_span, link_owner
from tools.experiments.game_view_list_setup import compile_owner as compile_profile
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import SYMBOL, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions, load_symbol_addrs
from tools.check_game_data_layout import audit_layout

compile_owner = partial(compile_profile, no_unroll=True)

FUNCTION, ENTRY, ROM, SIZE = 'func_150B6C90', 0x150B6C90, 0xE4140, 164
SOURCE, OWNER, ASM = 'conker/src/game/generated_E4070.c', 'generated_E4070', 'conker/asm/E4070.s'
BUILD = 'conker/build/game-color-table-reset/qualified'
OBJECT = 'conker/build/src/game/generated_E4070.c.o'
BEFORE_OBJECT_SHA = '0ea31300ad8af9399f9f78986b405043c1771d4530eb146199b17c6267b05dd5'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/src/game/generated_E4070.c": "7f46fa4a9c885556b87f8fa94e18b6f32a9fb363db0658051c0bbb83114cb3ad",
    "conker/asm/E4070.s": "587d77f05ef6fa1ee49d5de1e66e53e9d03161c369e2e66b78b2ec683efb5ca8",
    "conker/src/game/generated_1D0840.c": "06ef7666971ad798cd12ea4157c4e34d7f1e57b7ee5caca001f3d40a827cffc4",
    "conker/asm/1D0840.s": "776840f022dd4079a066a510afdd122e15116e9a284c80698b48d1cf10b8d34e",
    "conker/src/game_1944C0.c": "328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b",
    "conker/asm/nonmatchings/game_1944C0/func_15167A68.s": "e10b48863a06a3abf7ab49384fc059fbb54f5005fd9d8c7bf716cd687a52a801",
    "conker/asm/nonmatchings/game_1944C0/func_15168A4C.s": "011fa8da4029145e824359c696705e6b58bd17cded005bbada9879a878db2ebd",
    "conker/asm/nonmatchings/init_3C40/func_10003C6C.s": "96f8cb8122b418261c5615a057c84e6a049dd67539a1ba9d0dcb63aacdeded55",
    "conker/asm/1A1E50.s": "e9e139cbca83c15ad1f2d4147af554c6c140ae5ededc3ee0272008948e3496e9",
    "conker/src/game/generated_1A1E50.c": "41b3927c5db740644a926f20b9d57ec0720c8fff01281bf2d48af0d083a8522d",
    "conker/asm/data/231730.rodata.s": "887c6f85ceaa241c4e55cca63b76edcb87af5dd9d04e8a2ae9d292e384421f6c",
    "conker/asm/data/2447B0.rodata.s": "43ebcf56bff42357057123f89268c0714ed958bb8205f5f893e824bc9f1aba1a",
    "conker/asm/data/22FF90.rodata.s": "9150a226f309b306c5a590f6b5d18d9eaf6227c16cc1ae390454e91dd48902af",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "conker/build/conker.us.elf": "9c49b22ea18204941236929c1b2b692fde1a23003166cb685ea767423482d44b",
    "conker/retail_word_patches.us.csv": "e609b709c5802441176732684079e39fd0d8cad476c51f2a04b00d458adafeed",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be"
}
RAW_SHA = '7b497a19b145f7227726bce9a461154ae646dd89bc1c3c7aaa12b3e89750cf01'
SYMBOL_ORDER = (('D_800D98A0', 'D_80088860'),
                ('D_800D989C', 'func_10004FE0', 'func_1508BF14'))
RAW_BINDINGS = {
    8: [("R_MIPS_HI16", "D_800D9894")],
    12: [("R_MIPS_LO16", "D_800D9894")],
    24: [("R_MIPS_26", "func_1516972C")],
    32: [("R_MIPS_HI16", "D_800BE9E8")],
    36: [("R_MIPS_LO16", "D_800BE9E8")],
    68: [("R_MIPS_26", "func_151A4FD0")],
    76: [("R_MIPS_HI16", "D_800D9894")],
    80: [("R_MIPS_LO16", "D_800D9894")],
    84: [("R_MIPS_HI16", "D_800D9898")],
    88: [("R_MIPS_HI16", "D_800D9890")],
    96: [("R_MIPS_LO16", "D_800D9898")],
    100: [("R_MIPS_LO16", "D_800D9890")],
    104: [("R_MIPS_HI16", "D_800D98A0")],
    108: [("R_MIPS_HI16", "D_800D98C0")],
    120: [("R_MIPS_LO16", "D_800D98A0")],
    124: [("R_MIPS_LO16", "D_800D98C0")],
}
GUARDS = (
    (0x54, 0x3C040000, 0x3C010000, "R_MIPS_HI16:D_800D9898", "R_MIPS_HI16:D_800D9890", False),
    (0x58, 0x3C010000, 0x240F0003, "R_MIPS_HI16:D_800D9890", "-", False),
    (0x5C, 0x240F0003, 0xA02F0000, "-", "R_MIPS_LO16:D_800D9890", False),
    (0x60, 0x24840000, 0x24840000, "R_MIPS_LO16:D_800D9898", "R_MIPS_LO16:D_800D9898", True),
    (0x64, 0xA02F0000, 0x3C010000, "R_MIPS_LO16:D_800D9890", "R_MIPS_HI16:D_800D9898", False),
    (0x68, 0x3C030000, 0x3C020000, "R_MIPS_HI16:D_800D98A0", "R_MIPS_HI16:D_800D98A0", False),
    (0x6C, 0x3C020000, 0x3C030000, "R_MIPS_HI16:D_800D98C0", "R_MIPS_HI16:D_800D98C0", False),
    (0x70, 0xAC800000, 0x24630000, "-", "R_MIPS_LO16:D_800D98C0", False),
    (0x74, 0xAC800004, 0x24420000, "-", "R_MIPS_LO16:D_800D98A0", False),
    (0x78, 0x24630000, 0xAC200000, "R_MIPS_LO16:D_800D98A0", "R_MIPS_LO16:D_800D9898", False),
    (0x7C, 0x24420000, 0xAC200000, "R_MIPS_LO16:D_800D98C0", "R_MIPS_LO16:D_800D989C", False),
    (0x80, 0x24630010, 0x24420010, "-", "-", False),
    (0x84, 0xAC60FFF4, 0xAC40FFF4, "-", "-", False),
    (0x88, 0xAC60FFF8, 0xAC40FFF8, "-", "-", False),
    (0x8C, 0xAC60FFFC, 0xAC40FFFC, "-", "-", False),
    (0x90, 0x1462FFFB, 0x1443FFFB, "-", "-", False),
    (0x94, 0xAC60FFF0, 0xAC40FFF0, "-", "-", False),
)
TYPES = ''
DECLARATIONS = '''extern u8 D_800D9890;
extern u8 D_800D9898[], D_800D98A0[], D_800D98C0[];
extern void *D_800D9894;
extern s32 D_800BE9E8;
void func_1516972C(void *);
void *func_151A4FD0(s32, u32, s32, s32, s32, s32, u8, u32);
'''
OWNER_DECLARATIONS = '''extern s32 D_800BE9E8;
extern u8 D_800D98A0[];
void *func_151A4FD0(s32, u32, s32, s32, s32, s32, u8, u32);
'''
SELECTED = '''/* Replace the color record and reset the ten pointer slots. */
void func_150B6C90(void) {
    void **current;

    if (D_800D9894 != NULL) {
        func_1516972C(D_800D9894);
    }
    D_800D9894 = func_151A4FD0(0, 0, 255, 0, 0, D_800BE9E8, 0, 0);
    D_800D9890 = 3;
    ((void **)D_800D9898)[0] = NULL;
    ((void **)D_800D9898)[1] = NULL;
    current = (void **)D_800D98A0;
    do {
        current[1] = NULL;
        current[2] = NULL;
        current[3] = NULL;
        current[0] = NULL;
        current += 4;
    } while (current != (void **)D_800D98C0);
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
            raise ValueError('Color/table reset historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    if not old.exists():
        data = (root / OBJECT).read_bytes()
        if digest(data) != BEFORE_OBJECT_SHA:
            raise ValueError('Color/table reset padded predecessor changed')
        old.write_bytes(data)
    if digest(old.read_bytes()) != BEFORE_OBJECT_SHA:
        raise ValueError('Color/table reset frozen padded object changed')
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Color/table reset predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Color/table reset snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    validate_layout(load_symbol_addrs(str(root / 'conker/undefined_syms_auto.txt')))
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_150B6C90() {\n    return 0;\n}':
        raise ValueError('Unknown color/table reset source predecessor')
    result = before[:lo] + SELECTED + before[hi:]
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown color/table reset include anchor')
    return result.replace(anchor, anchor + OWNER_DECLARATIONS + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero color-table-reset alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('Type5AOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-color-table-reset',
        (root / ASM).read_text(), FUNCTION)


def validate_layout(symbols):
    base = symbols['D_800D9898']
    expected = {'D_800D989C': (base + 4) & 0xFFFFFFFF,
                'D_800D98A0': (base + 8) & 0xFFFFFFFF,
                'D_800D98C0': (base + 40) & 0xFFFFFFFF}
    if base & 3 or any(symbols[name] != value for name, value in expected.items()):
        raise ValueError('Color/table reset pointer-slot layout changed')
    high = lambda address: ((address + 0x8000) >> 16) & 0xFFFF
    if high(base) != high(symbols['D_800D989C']):
        raise ValueError('Color/table reset pair crosses its shared adjusted-HI16 page')


def cooked_program(raw, bindings):
    words = struct.unpack('>42I', raw)
    code, tags = [], {}
    def emit(at, word=None, replacement=None):
        index = len(code) * 4
        code.append(words[at // 4] if word is None else word)
        entries = bindings.get(at, []) if replacement is None else replacement
        if entries:
            tags[index] = list(entries)
    def swap(word):
        for shift in (21, 16):
            value = word >> shift & 31
            if value in (2, 3):
                word = (word & ~(31 << shift)) | ((5 - value) << shift)
        return word
    for at in range(0, 0x54, 4):
        emit(at)
    for at in (0x58, 0x5C, 0x64):
        emit(at)
    emit(0x54, (words[0x54 // 4] & ~(31 << 16)) | (1 << 16))
    for at in (0x68, 0x6C, 0x7C, 0x78):
        emit(at, swap(words[at // 4]))
    for at, name in ((0x70, 'D_800D9898'), (0x74, 'D_800D989C')):
        emit(at, (words[at // 4] & ~((31 << 21) | 0xFFFF)) | (1 << 21),
             [('R_MIPS_LO16', name)])
    for at in range(0x80, 0x98, 4):
        emit(at, swap(words[at // 4]))
    for at in range(0x98, 0xA8, 4):
        emit(at)
    return struct.pack('>41I', *code), tags


def normalized(raw, bindings):
    if len(raw) != 168 or digest(raw) != RAW_SHA or bindings != RAW_BINDINGS:
        raise ValueError('Color/table reset closed raw body/bindings changed')
    result, tags = cooked_program(raw, bindings)
    records, emitted = [], 0
    spec = lambda rows: ';'.join(kind + ':' + name for kind, name in rows) or '-'
    for at in range(0, len(raw), 4):
        old = struct.unpack_from('>I', raw, at)[0]
        before = spec(bindings.get(at, []))
        if at == 0x60:
            records.append((at, old, old, before, before, True))
            continue
        new = struct.unpack_from('>I', result, emitted)[0]
        after = spec(tags.get(emitted, []))
        if old != new or before != after:
            records.append((at, old, new, before, after, False))
        emitted += 4
    if tuple(records) != GUARDS or len(result) != SIZE:
        raise ValueError('Color/table reset derived normalization changed')
    return result, tags


def guard_bytes(values):
    before = values['conker/retail_word_patches.us.csv']
    if not before.endswith(b'\n') or (OWNER + ',' + FUNCTION + ',').encode() in before:
        raise ValueError('Color/table reset guard prefix changed')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    for at, old, new, expected, replacement, omit in GUARDS:
        writer.writerow((OWNER, FUNCTION, '0x%03X' % at, '0x%08X' % old,
            '0x%08X' % new, expected, replacement,
            'Normalize fixed-layout pointer pair address fold and closed reset setup/loop allocation',
            '', '', 'true' if omit else 'false'))
    return before + stream.getvalue().encode()


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Color/table reset compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    fitted, fitted_bindings = normalized(raw, bindings)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    original_obj = original(root, output)
    if payload(original_obj) != (fitted, fitted_bindings) or payload(after) != (raw, bindings):
        raise ValueError('Color/table reset derived C differs from GNU original/whole owner')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Color/table reset raw neighbor/pool changed')
    padded, guards = output / 'qualified-padded.s', output / 'proposed-guards.csv'
    guards.write_bytes(guard_bytes(values))
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=guards, filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    a, fa = link_owner(root, output, output / 'before-padded.o', OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown color/table reset predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Color/table reset predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Color/table reset padding changed another body/address/extent')
    if same_functions(output / 'before-padded.o', obj, (FUNCTION,)) != neighbors or normalized_pools(output / 'before-padded.o') != normalized_pools(obj):
        raise ValueError('Color/table reset padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    raw_words = list(struct.unpack_from('>42I', linked, functions[FUNCTION]['value']))
    retail_words = list(struct.unpack('>41I', truth))
    report = dict(words=41, raw_words=42, frame=40, differences=0, raw_differences=
        sum(a != b for a, b in zip(raw_words, retail_words)) + 1,
        raw_relocations=16, relocations=17, compiler_only=False, new_guards=17,
        omitted_address_words=1, inserted_words=0, raw_SHA256=digest(raw),
        preserved_neighbors=neighbors, all_owner_addresses_fixed=True,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        retail_no_unroll=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Color/table reset shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_E4070.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected color-table-reset Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_E4070.c' else (output / 'proposed-guards.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown color-table-reset Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Color/table reset Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or '-Wo,-loopunroll,0' not in compilers[0]:
        raise ValueError('Color/table reset Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Color/table reset actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Color/table reset actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, retail_no_unroll=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Color/table reset strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Color/table reset symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    # The first references rotate these two bounded GNU symbol/name groups.
    entries = {name: (offset, fields, string) for offset, name, fields, string
               in symbol_rows(before)}
    canonical = lambda data: sorted((name, fields[1:]) for _, name, fields, _ in symbol_rows(data))
    definitions = canonical(result)
    for names in SYMBOL_ORDER:
        group = [entries[name] for name in names]
        start, string_at = group[0][0], group[0][2]
        strings_base = string_at - group[0][1][0]
        old_strings = b''.join(name.encode() + b'\0' for name in names)
        if (any(row[0] != start + index * SYMBOL.size or row[2] - row[1][0] != strings_base
                for index, row in enumerate(group))
                or before[string_at:string_at + len(old_strings)] != old_strings):
            raise ValueError('Color/table reset bounded metadata predecessor changed')
        for index, name in enumerate(names[1:] + names[:1]):
            fields = list(entries[name][1]);fields[0] = string_at - strings_base
            SYMBOL.pack_into(result, start + index * SYMBOL.size, *fields)
            literal = name.encode() + b'\0'
            result[string_at:string_at + len(literal)] = literal
            string_at += len(literal)
    if canonical(result) != definitions:
        raise ValueError('Color/table reset metadata permutation changed named definitions')
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Color/table reset image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_E4070.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown color-table-reset link input')
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
        code_bytes_changed=code, metadata_bytes_changed=changed - code, metadata_exclusions=0,
        metadata_symbol_name_groups=len(SYMBOL_ORDER))
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else wanted if name == 'conker/build/conker.us.elf' else guard_bytes(values) if name == 'conker/retail_word_patches.us.csv' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Color/table reset installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Color/table reset independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Color/table reset changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Color/table reset installed padded object changed')
    validate_layout(load_symbol_addrs(str(root / 'conker/undefined_syms_auto.txt')))
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Color/table reset protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=41, strict_first_link_reproduced=True, old_guard_prefix_preserved=True, new_guards=17, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
