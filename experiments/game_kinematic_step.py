"""Direct C recovery and strict owner/image gates for the kinematic step."""

import hashlib
import json
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


FUNCTION, ENTRY, ROM, SIZE = 'func_1519BE1C', 0x1519BE1C, 0x1C92CC, 156
SOURCE, OWNER, ASM = 'conker/src/game/generated_1C2C60.c', 'generated_1C2C60', 'conker/asm/1C2C60.s'
BUILD = 'conker/build/game-kinematic-step/qualified'
INPUTS = {
    SOURCE: '3c76a3f31005679ac149d03a16ca7e756428fb620b93ad4d039811cbeb06759c',
    ASM: '540f52818bc616ff24520ea28277e70ec41dea676c9b54970271364c138f02c0',
    'conker/build/conker.us.elf': '7854836fbb41afc2d971461115bf67053eeb41f9d190434c10e7cb668ca49ecd',
    'conker/retail_word_patches.us.csv': '7ca8a25f8ea41d9e2e4a795281619c21048f5c24b252d48a9367eb5cd5e36e76',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/Makefile': '54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
DECLARATIONS = '''typedef struct {
    f32 x, y, z;
} KinematicVector;
'''
SELECTED = '''/* Advance position from saved velocity and apply vertical acceleration. */
void func_1519BE1C(KinematicVector *position, KinematicVector *velocity,
                   f32 acceleration, f32 timestep) {
    KinematicVector saved = *velocity;
    velocity->y += acceleration * timestep;
    position->x += saved.x * timestep;
    position->y += saved.y * timestep + 0.5f * acceleration * timestep * timestep;
    position->z += saved.z * timestep;
}'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Kinematic historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Kinematic predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Kinematic snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1519BE1C() {\n    return 0;\n}':
        raise ValueError('Unknown kinematic source predecessor')
    return before[:lo] + DECLARATIONS + '\n' + SELECTED + before[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero kinematic alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('KinematicOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-kinematic',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if da or db or dc:
        raise ValueError('Kinematic compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    if raw != truth or bindings or payload(after) != (raw, bindings):
        raise ValueError('Kinematic direct C differs from retail/whole owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Kinematic independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Kinematic raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_1C2C60.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown kinematic padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Kinematic predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Kinematic padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Kinematic padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=39, frame=16, differences=0, relocations=0, new_guards=0,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Kinematic shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_1C2C60.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected kinematic Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_1C2C60.c' else a for a in args]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        if process.returncode or process.stdout or process.stderr:
            raise ValueError('Kinematic Make command failed: ' + process.stdout + process.stderr)
        commands.append(args)
    actual = conker / target
    if not all(flag in commands[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in commands[0]):
        raise ValueError('Kinematic Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) < 1:
        raise ValueError('Kinematic actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Kinematic actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Kinematic strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Kinematic symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Kinematic image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1C2C60.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown kinematic link input')
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
            raise ValueError('Kinematic installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Kinematic independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Kinematic changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Kinematic protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=39, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
