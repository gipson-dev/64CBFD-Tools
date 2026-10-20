"""Semantic list cleanup, closed saved-role setup and strict owner/image gates."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_1514D310', 0x1514D310, 0x17A7C0, 160
SOURCE, OWNER, ASM = 'conker/src/game/generated_179F30.c', 'generated_179F30', 'conker/asm/179F30.s'
BUILD = 'conker/build/game-list-node-cleanup/qualified'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/src/game/generated_179F30.c": "aaa41d633e41ca79645b563e1f5a5e86e50f06a88ea22375d7dd8eed66661d92",
    "conker/asm/179F30.s": "57d86f46d9b3347bb725e0704c2017240275e5a7d3fbd05a9c604bf1a3ade448",
    "conker/src/game_1944C0.c": "328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b",
    "conker/asm/data/22F530.rodata.s": "a40f94b644c76ea797fae3f9e5686651a4446f511c818604a33a86b93f5582d1",
    "conker/asm/data/22F650.rodata.s": "4f01fa2f87eb8d6bbe96dd41e5237c57f36274c5e809ea7b41301130e6f56a6e",
    "conker/asm/data/24A920.rodata.s": "a1342a9812797d2a5270415c7fa47a9bd035c2e804a89031d42dfc56f40b0855",
    "conker/asm/nonmatchings/game_83300/func_15060F28.s": "226c20ce9b9de365628c2ff1bae26fd7b4164dc435bfbf1028ea3b2ee0c8452f",
    "conker/build/conker.us.elf": "180ab67fdf083d4adb81720eee40f661390c74bcd488f2b2bbbfc7c7b447d1a8",
    "conker/retail_word_patches.us.csv": "36513f2bad7fd30dbf191f428a3e0d154726fa4e9bfb619d5f0a36bda28987ae",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be"
}
REMOVE, CALLBACKS, DESCRIPTORS = 0x1516972C, 0x8008AB58, 0x8008ABE8
CALLER, JOIN, CALLER_ROM = 0x15060F28, 0x15060F48, 0x8E3D8
RAW_BINDINGS = {0x20:[('R_MIPS_HI16','D_8008AB58')],0x24:[('R_MIPS_LO16','D_8008AB58')],
    0x30:[('R_MIPS_HI16','D_8008ABE8')],0x34:[('R_MIPS_LO16','D_8008ABE8')],
    0x6C:[('R_MIPS_26','func_1516972C')]}
GUARDS = (
    (0x2c,0x2413ffff,0x3c130000,'-','R_MIPS_HI16:D_8008ABE8'),
    (0x30,0x3c120000,0x26730000,'R_MIPS_HI16:D_8008ABE8','R_MIPS_LO16:D_8008ABE8'),
    (0x34,0x26520000,0x2412ffff,'R_MIPS_LO16:D_8008ABE8','-'),
    (0x44,0x24fc021,0x26fc021,'-','-'),
    (0x50,0x10530006,0x12420006,'-','-'),
)
GUARD_SUFFIX = b'''generated_179F30,func_1514D310,0x02C,0x2413FFFF,0x3C130000,-,R_MIPS_HI16:D_8008ABE8,Normalize closed cleanup saved roles and pure setup schedule,,,false
generated_179F30,func_1514D310,0x030,0x3C120000,0x26730000,R_MIPS_HI16:D_8008ABE8,R_MIPS_LO16:D_8008ABE8,Normalize closed cleanup saved roles and pure setup schedule,,,false
generated_179F30,func_1514D310,0x034,0x26520000,0x2412FFFF,R_MIPS_LO16:D_8008ABE8,-,Normalize closed cleanup saved roles and pure setup schedule,,,false
generated_179F30,func_1514D310,0x044,0x024FC021,0x026FC021,-,-,Normalize closed cleanup saved roles and pure setup schedule,,,false
generated_179F30,func_1514D310,0x050,0x10530006,0x12420006,-,-,Normalize closed cleanup saved roles and pure setup schedule,,,false
'''
TYPES = '''typedef struct GameListNode {
    u8 pad0[0x10];
    s32 unk10;
    struct GameListNode *next;
    struct GameListNode *prev;
    s16 unk1C;
} GameListNode;
'''
DECLARATIONS = '''extern void (*D_8008AB58[])();
extern s16 *D_8008ABE8[];
void func_1516972C();
'''
SELECTED = '''/* Run each list node's optional payload callback, then remove the node. */
s32 func_1514D310(u8 *owner) {
    GameListNode *next;
    GameListNode *node = *(GameListNode **)(owner + 0x2F4);
    s16 callback;

    while (node != NULL) {
        next = node->next;
        callback = D_8008ABE8[node->unk1C][1];
        if (callback != -1) {
            D_8008AB58[callback](node->unk10);
        }
        func_1516972C(node);
        node = next;
    }
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
            raise ValueError('List node cleanup historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('List node cleanup predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('List node cleanup snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1514D310() {\n    return 0;\n}':
        raise ValueError('Unknown list-node-cleanup source predecessor')
    if before.count(TYPES) != 1 or before.count('s32 func_1516972C();') != 1:
        raise ValueError('List node cleanup layout/removal declaration predecessor changed')
    result = (before[:lo] + SELECTED + before[hi:]).replace('s32 func_1516972C();\n', '', 1)
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown list-node-cleanup include anchor')
    return result.replace(anchor, anchor + DECLARATIONS + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero list-node-cleanup alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('HeadingOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-list-node-cleanup',
        (root / ASM).read_text(), FUNCTION)


def normalized(raw, bindings):
    if len(raw) != SIZE or bindings != RAW_BINDINGS:
        raise ValueError('List cleanup raw extent/bindings changed')
    result = bytearray(raw)
    fitted = {at: list(entries) for at, entries in bindings.items()}
    for at, old, new, old_binding, new_binding in GUARDS:
        actual = ';'.join(kind + ':' + name for kind, name in bindings.get(at, ())) or '-'
        if struct.unpack_from('>I', raw, at)[0] != old or actual != old_binding:
            raise ValueError('List cleanup closed word/binding predecessor changed')
        struct.pack_into('>I', result, at, new)
        fitted.pop(at, None)
        if new_binding != '-':
            kind, name = new_binding.split(':', 1)
            fitted[at] = [(kind, name)]
    return bytes(result), fitted


def guard_bytes(values):
    before = values['conker/retail_word_patches.us.csv']
    if not before.endswith(b'\n') or b'generated_179F30,func_1514D310,' in before:
        raise ValueError('List cleanup guard prefix changed')
    return before + GUARD_SUFFIX


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + TYPES + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('List node cleanup compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    fitted, fit_bindings = normalized(raw, bindings)
    linked_raw = bytearray(linked[at:at + SIZE])
    original_linked, original_functions = link_owner(root, output, original(root, output), OWNER)
    original_at = original_functions[FUNCTION]['value']
    for offset, _, _, _, _ in GUARDS:
        linked_raw[offset:offset + 4] = original_linked[original_at + offset:original_at + offset + 4]
    if bytes(linked_raw) != truth or sum(map(len, bindings.values())) != 5 or payload(after) != (raw, bindings):
        raise ValueError('List node cleanup direct C differs from retail/whole owner')
    if payload(original(root, output)) != (fitted, fit_bindings):
        raise ValueError('List node cleanup independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('List node cleanup raw owner pool changed')
    guards = output / 'proposed-guards.csv'
    guards.write_bytes(guard_bytes(values))
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=guards, filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_179F30.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown list-node-cleanup padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('List node cleanup predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('List node cleanup padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('List node cleanup padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=40, frame=48, differences=0, relocations=5, new_guards=5,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=False, raw_differences=5, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('List node cleanup shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_179F30.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected list-node-cleanup Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_179F30.c' else (output / 'proposed-guards.csv').relative_to(conker).as_posix()
                if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown list-node-cleanup Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('List node cleanup Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('List node cleanup Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('List node cleanup actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('List node cleanup actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('List node cleanup strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('List node cleanup symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    # The first C reference rotates this two-entry GNU symbol/string bucket.
    names = ('D_8008ABE8', 'func_1503DF48')
    records = {name: (offset, fields, string) for offset, name, fields, string
               in symbol_rows(before) if name in names}
    if set(records) != set(names):
        raise ValueError('List cleanup metadata names changed')
    start, fields, string_start = records[names[0]]
    old_strings = b''.join(name.encode() + b'\0' for name in names)
    if (tuple(records[name][0] for name in names) != (start, start + 16)
            or tuple(records[name][2] for name in names) != (string_start, string_start + 11)
            or before[string_start:string_start + len(old_strings)] != old_strings):
        raise ValueError('List cleanup metadata predecessor ordering changed')
    string_index = fields[0]
    reordered = names[::-1]
    for index, name in enumerate(reordered):
        old_fields = records[name][1]
        struct.pack_into('>IIIBBH', result, start + 16 * index, string_index, *old_fields[1:])
        string_index += len(name) + 1
    result[string_start:string_start + len(old_strings)] = b''.join(name.encode() + b'\0' for name in reordered)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('List node cleanup image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_179F30.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown list-node-cleanup link input')
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
            raise ValueError('List node cleanup installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('List node cleanup independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('List node cleanup changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('List node cleanup protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=40, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
