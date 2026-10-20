"""Direct record-payload C recovery with strict owner, caller and image gates."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_151CD2C0', 0x151CD2C0, 0x1FA770, 156
SOURCE, OWNER, ASM = 'conker/src/game/generated_1FA770.c', 'generated_1FA770', 'conker/asm/1FA770.s'
BUILD = 'conker/build/game-effect-record-payload/qualified'
INPUTS = {
    SOURCE: 'e71fd724313d0e8b89251cd8da3bd4238f44ad9ca11561f71e02b08ad9c9ae35',
    'conker/src/game_40490.c': 'b8f927f450741296f1e5834f635d5aba27c47df613ce1284a5fc8fbfc5b809c3',
    ASM: 'cce3e047754e3253d0c7f0d9279cbb86cc922f615e9ef9b79ed786155bde9b60',
    'conker/build/conker.us.elf': '918bb7a8922586bf687eb35db0a5cfb1971b05fe4c12cd723280165692ecc6e1',
    'conker/retail_word_patches.us.csv': '7ca8a25f8ea41d9e2e4a795281619c21048f5c24b252d48a9367eb5cd5e36e76',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
CALLER, CALLER_OWNER = 'conker/src/game_40490.c', 'game_40490'
SPAWN, COPY = 0x15149130, 0x10022EC0
CALLER_ENTRY, CALLER_ROM, CALLER_SIZE = 0x15013F9C, 0x4144C, 40
DECLARATIONS = '''typedef struct {
    void *source;
    s32 value;
    s32 zero;
    u8 selector;
    u8 reserved[3];
} EffectRecordPayload;
void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, u32);
'''
SELECTED = '''/* Capture record state, attach the payload and return the allocated effect. */
void *func_151CD2C0(void *source, u8 variant, s32 parameter) {
    u8 *effect;
    EffectRecordPayload payload;
    payload.source = source;
    payload.value = *(s32 *)((u8 *)source + 0x18);
    payload.zero = 0;
    payload.selector = *(s32 *)((u8 *)source + 0x1C);
    effect = func_15149130(300, -1, -1, -1, 0, 30, 16, variant, parameter);
    if (effect != 0) {
        memcpy(effect + 0x28, &payload, 16);
    }
    return effect;
}'''


def recovered_caller(before):
    anchor = 'struct17 *func_1515F1B0(u8 *arg0);'
    declaration = 'void *func_151CD2C0(void *source, u8 variant, s32 parameter);'
    lo, hi = function_span(before, 'func_15013F9C')
    predecessor = '''s32 func_15013F9C(s32 arg0) {
    func_151CD2C0(arg0, 0xFF, 1);
    return 1;
}'''
    if before.count(anchor) != 1 or declaration in before or before[lo:hi] != predecessor:
        raise ValueError('Unknown record-payload caller predecessor')
    body = '''s32 func_15013F9C(void *source) {
    func_151CD2C0(source, 0xFF, 1);
    return 1;
}'''
    result = before[:lo] + body + before[hi:]
    return result.replace(anchor, anchor + '\n' + declaration)


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))



def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Effect historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Effect predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Effect snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151CD2C0() {\n    return 0;\n}':
        raise ValueError('Unknown effect-payload source predecessor')
    return before[:lo] + DECLARATIONS + '\n' + SELECTED + before[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero effect-payload alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('EffectOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-effect-payload',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Effect compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, linked_functions = link_owner(root, output, isolated, OWNER)
    at = linked_functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or payload(after) != (raw, bindings):
        raise ValueError('Effect direct C differs from retail/whole owner')
    if sum(map(len, bindings.values())) != 2 or payload(original(root, output)) != (raw, bindings):
        raise ValueError('Effect independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Effect raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_1FA770.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown effect-payload padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Effect predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Effect padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Effect padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    caller = recovered_caller(values[CALLER].decode())
    a, da = compile_owner(root, output, values[CALLER].decode(), 'caller-before')
    b, db = compile_owner(root, output, caller, 'caller-after')
    if diagnostics(da) != diagnostics(db) or normalized_pools(a) != normalized_pools(b):
        raise ValueError('Effect caller diagnostics/pools changed')
    caller_count = same_functions(a, b)
    (output / 'proposed-caller.c').write_text(caller)
    report = dict(words=39, frame=72, differences=0, relocations=2, new_guards=0,
        preserved_raw_caller_functions=caller_count,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        inherited_owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Effect shadow source changed')
    if (output / 'proposed-caller.c').read_text() != recovered_caller(values[CALLER].decode()):
        raise ValueError('Effect shadow caller changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    (shadow / 'src').mkdir(parents=True, exist_ok=True)
    targets = ['src/game/generated_1FA770.c.o', 'src/game_40490.c.o']
    target_paths = [(shadow / name).relative_to(conker).as_posix() for name in targets]
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), *target_paths],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    replacements = {'src/game/generated_1FA770.c': 'proposed-owner.c', 'src/game_40490.c': 'proposed-caller.c'}
    commands, compile_flags = [], []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected effect Make command: ' + repr(args))
        args = [(output / replacements[a]).relative_to(conker).as_posix() if a in replacements else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown effect Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = ''
        if args[0] == '../ido/ido5.3_recomp/cc':
            if not all(f in args for f in ('-O2', '-g3')) or any('-loopunroll' in f for f in args):
                raise ValueError('Effect Make changed a normal compiler profile')
            compile_flags.append(['-O2', '-g3'])
            if any('game_40490' in a for a in args):
                expected_diagnostics = (output / 'caller-after-diagnostics.txt').read_text()
            else:
                expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text()
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Effect Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual, caller = [conker / name for name in target_paths]
    if len(commands) != 8 or compile_flags != [['-O2', '-g3']] * 2:
        raise ValueError('Effect actual Make command/profile extent changed')
    if same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Effect Make raw owner changed')
    if same_functions(output / 'caller-after.o', Path(str(caller) + '.compact')) != len(parse_object(output / 'caller-after.o')[1]):
        raise ValueError('Effect Make raw caller changed')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Effect actual Make padding/metadata differs')
    before = output / 'before-caller-padded.o'
    if not before.exists():
        shutil.copyfile(root / 'conker/build/src/game_40490.c.o', before)
    if link_owner(root, output, before, CALLER_OWNER) != link_owner(root, output, caller, CALLER_OWNER):
        raise ValueError('Effect caller padded code/addresses/extents changed')
    if normalized_pools(before) != normalized_pools(caller):
        raise ValueError('Effect caller padded pools changed')
    report = dict(actual_Make_commands=8, compiler_profiles=compile_flags,
        preserved_padded_caller_functions=same_functions(before, caller),
        all_raw_functions_equal=True, padded_code_and_metadata_equal=True,
        cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Effect strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Effect symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Effect image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1FA770.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown effect-payload link input')
    link = output / 'first-link.ld'
    caller = 'build/src/game_40490.c.o'
    if script.count(caller) != 1:
        raise ValueError('Unknown effect caller link input')
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()).replace(
        caller, (output / 'make-shadow/src/game_40490.c.o').relative_to(root / 'conker').as_posix()))
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
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else recovered_caller(old.decode()).encode() if name == CALLER else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Effect installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Effect independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Effect changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Effect protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=39, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
