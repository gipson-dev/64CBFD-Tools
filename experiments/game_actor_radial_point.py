"""Direct C recovery and strict owner/image gates for the actor radial point."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_150F2230', 0x150F2230, 0x11F6E0, 156
SLOT = 160
CALLER_SOURCE = 'conker/src/game_981E0.c'
CALLER_DECLARATION = 'void func_150F2230(struct127 *, u8, s32);'
SOURCE, OWNER, ASM = 'conker/src/game/generated_11C2B0.c', 'generated_11C2B0', 'conker/asm/11C2B0.s'
BUILD = 'conker/build/game-actor-radial-point/qualified'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/src/game/generated_11C2B0.c": "efddb2eaa9b7967f0659db1482799c6a90789abf499f2df92dfb22408c770013",
    "conker/src/game_981E0.c": "d58bc552743bb1f23aeb271910d14635ae14398e3ae97576d473cae72a411814",
    "conker/asm/11C2B0.s": "064851c4bd1d09f2eec8dc0b3bbfa579b8e028d24e94c8ce4468d5a1732403db",
    "conker/asm/nonmatchings/generated_1EF500/func_151C329C.s": "7b33a7fa52c9e0be800656502457da813890b5ed238bd0665deac9d1cc822e30",
    "conker/asm/nonmatchings/game_16EE20/func_15143874.s": "d2d917ab1aa381b20693c384db6fbd21865f71bae85a022df6d19f339f1a1660",
    "conker/asm/nonmatchings/game_16EE20/func_15143134.s": "6279833e1ee189fdaabd7b639d051c5301b6ba953bcf4185ad91769fd573390a",
    "conker/src/game_16EE20.c": "7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810",
    "conker/build/conker.us.elf": "36e0666a72ffef1d745ead26517a1e9b5a3072e5366d44c5977615bade991c49",
    "conker/retail_word_patches.us.csv": "7ccd028cda1fdbe5f212c315aa649188f3b88f72b7003cf5573eb5c01d048115",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be"
}
INTEGER_RNG, DIRECTION, TRANSFORM, SUBMIT = 0x150ADA20, 0x15143874, 0x15143134, 0x151C329C
CALLER_ENTRY, CALLER_ROM, CALLER_WORDS = 0x15071D08, 0x9F1B8, 12
DECLARATIONS = '''#include "structs.h"
s32 func_150ADA20(void);
void func_15143874(s16, f32, f32 *, f32 *);
void func_15143134(f32 *, f32 *, u8 *);
void func_151C329C(struct17 *, s32, s32);
'''
SELECTED = '''/* Transform a random horizontal offset through the actor's matrix and submit it. */
void func_150F2230(struct127 *actor, u8 kind, s32 flags) {
    struct17 offset;
    struct17 point;

    if (actor->unk1D4 != 0 && (actor->unk74 & 0xF) != 0xF) {
        offset.unk0 = 0.0f;
        offset.unk4 = 0.0f;
        offset.unk8 = 0.0f;
        func_15143874((u8)func_150ADA20(), 100.0f, &offset.unk0, &offset.unk8);
        func_15143134((f32 *)&offset, (f32 *)&point, (u8 *)((u32)actor->unk1D4 + 0x4C0));
        func_151C329C(&point, kind, flags);
    }
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
            raise ValueError('Actor radial point historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Actor radial point predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Actor radial point snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_150F2230() {\n    return 0;\n}':
        raise ValueError('Unknown actor-radial-point source predecessor')
    result = before[:lo] + SELECTED + before[hi:]
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown actor-radial-point include anchor')
    return result.replace(anchor, anchor + DECLARATIONS + '\n', 1)


def recovered_caller(before):
    anchor = 'void func_150F10D4(void *source);'
    if before.count(anchor) != 1 or CALLER_DECLARATION in before:
        raise ValueError('Unknown actor-radial-point caller declaration predecessor')
    return before.replace(anchor, CALLER_DECLARATION + '\n' + anchor, 1)


def qualify_caller(root, output, values):
    old = values[CALLER_SOURCE].decode()
    proposed = recovered_caller(old)
    a, da = compile_owner(root, output, old, 'caller-before')
    b, db = compile_owner(root, output, proposed, 'caller-after')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Actor radial point caller diagnostics changed')
    count = same_functions(a, b, ())
    if count != 328 or normalized_pools(a) != normalized_pools(b):
        raise ValueError('Actor radial point caller code/bindings/pools changed')
    if link_owner(root, output, a, 'game_981E0') != link_owner(root, output, b, 'game_981E0'):
        raise ValueError('Actor radial point caller linked content/metadata changed')
    (output / 'proposed-caller.c').write_text(proposed)
    report = dict(functions_fixed=count, all_bindings_and_pools_fixed=True,
        linked_code_and_metadata_fixed=True, inherited_diagnostics_fixed=True)
    (output / 'caller-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor-radial-point alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('HeadingOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-actor-radial-point',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Actor radial point compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or sum(map(len, bindings.values())) != 4 or payload(after) != (raw, bindings):
        raise ValueError('Actor radial point direct C differs from retail/whole owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Actor radial point independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Actor radial point raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_11C2B0.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown actor-radial-point padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Actor radial point predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Actor radial point padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Actor radial point padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=39, slot_words=40, frame=56, differences=0, relocations=4, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    report['caller'] = qualify_caller(root, output, values)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Actor radial point shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_11C2B0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor-radial-point Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_11C2B0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor-radial-point Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Actor radial point Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Actor radial point Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Actor radial point actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Actor radial point actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Actor radial point strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Actor radial point symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Actor radial point image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_11C2B0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown actor-radial-point link input')
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
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else recovered_caller(old.decode()).encode() if name == CALLER_SOURCE else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Actor radial point installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Actor radial point independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Actor radial point changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Actor radial point protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=39, slot_words=40, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
