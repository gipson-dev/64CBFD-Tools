"""Four-player live health dispatch: direct C and strict owner/image gates."""
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

FUNCTION, ENTRY, ROM, SIZE = 'func_15085ABC', 0x15085ABC, 0xB2F6C, 176
SOURCE, OWNER, ASM = 'conker/src/game/generated_B21B0.c', 'generated_B21B0', 'conker/asm/B21B0.s'
BUILD = 'conker/build/game-four-record-mask-dispatch-match'
OBJECT = 'conker/build/src/game/generated_B21B0.c.o'
CALLER_SOURCE = 'conker/src/game_45B80.c'
CALLER_OBJECT = 'conker/build/src/game_45B80.c.o'
PROTOTYPE = 'void func_15085ABC(s16);\n'
BEFORE_OBJECT_SHA = '021d86cd3b9d65d13b10934738354f17cda60e46669c8cc1eb0e4a21bb4fb91f'
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/B21B0.s": "b579807db904bbbbc9d68a556346f4aa38f7e5ba97d0c5cc6d5b58b09d2098b7",
    "conker/build/conker.us.elf": "cc82d9781d419bde3fe004381a1c4ee34101f384336cb8e5f50ad8aa386f5388",
    "conker/build/src/game/generated_B21B0.c.o": "021d86cd3b9d65d13b10934738354f17cda60e46669c8cc1eb0e4a21bb4fb91f",
    "conker/build/src/game_45B80.c.o": "6f93d458b6a4991ee00a8d815534c58451aad5b9864fff79c9ceaf0c9533fafc",
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
    "conker/src/game/generated_B21B0.c": "b6395aaea9e766c7d0779773b0be9a9948e730627b89af63e567b76b6adfef1d",
    "conker/src/game/generated_B3020.c": "6d27ddeec0aa1d0ccb55d601a7ed08aa96a591a076c2a3adccd7818b60b7f7b5",
    "conker/src/game_447B0.c": "df7b0b6f491ca5ada6e8db80c52ccde5a5899b88c94fed9f975e67a5e7ab679d",
    "conker/src/game_45B80.c": "7836725eafedce2e7103e6ce28e31dabdcd9164cebbe11683e04aff44713fb39",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
    "tools/tests/game_view_render_pass_oracle.py": "97782140d5683fada720f2bc3e01d84f21e5ea6d7b6947f1cc69fbe1886c8ee9",
    "tools/tests/test_game_actor_mask_scan_match.py": "644176e60e13e93faf846e022b679380f0721e214507986cfa877d18da63e41c",
    "tools/tests/test_game_effect_owner_ray.py": "62376c5022f50db9a53b0ec8b9517a63bc9f298dff8c7a3047963ed216a0555f"
}
TYPES = '#include "structs.h"\n'
GLOBALS = 'extern struct127 D_800CC2D0[26];\nextern u8 D_800D18A8;\n'
DECLARATIONS = GLOBALS + 'void func_15085710(s16, s32, s32);\n'
SELECTED = '''/* Publish each selected player's current health to its status record. */
void func_15085ABC(s16 mask) {
    s32 slot;

    if (!D_800D18A8) {
        for (slot = 0; slot < 4; slot++) {
            if ((1 << slot) & mask) {
                func_15085710((s16)slot, 5, D_800CC2D0[slot].health);
            }
        }
    }
}'''
RAW_SHA256 = '2933bafae376c06d981bf0e15d46afc5af43b2608481dc196819a202f33654ac'
BINDINGS = {44: [('R_MIPS_HI16', 'D_800D18A8')], 48: [('R_MIPS_LO16', 'D_800D18A8')],
            68: [('R_MIPS_HI16', 'D_800CC2D0')], 72: [('R_MIPS_LO16', 'D_800CC2D0')],
            124: [('R_MIPS_26', 'func_15085710')]}


def checked_payload(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Changed four-record health dispatch words/bindings')


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Four-record health dispatch historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    data = (root / OBJECT).read_bytes() if not old.exists() else old.read_bytes()
    if digest(data) != BEFORE_OBJECT_SHA:
        raise ValueError('Four-record-dispatch padded predecessor changed')
    if not old.exists():
        old.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Four-record health dispatch predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Four-record health dispatch snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15085ABC() {\n    return 0;\n}':
        raise ValueError('Unknown four-record-health-dispatch source predecessor')
    result = (before[:lo] + SELECTED + before[hi:])
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown four-record-health-dispatch include anchor')
    return result.replace(anchor, anchor + TYPES + '\n' + GLOBALS + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero four-record-health-dispatch alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def typed_caller(before):
    marker = '#include "functions.h"\n'
    if before.count(marker) != 1 or PROTOTYPE in before:
        raise ValueError('Unknown health-dispatch caller declaration predecessor')
    return before.replace(marker, marker + PROTOTYPE, 1)


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('MotionOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-four-record-health-dispatch',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + TYPES + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Four-record health dispatch compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    checked_payload(raw, bindings)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or sum(map(len, bindings.values())) != 5 or payload(after) != (raw, bindings):
        raise ValueError('Four-record health dispatch direct C differs from retail/whole owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Four-record health dispatch independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Four-record health dispatch raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_B21B0.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown four-record-health-dispatch padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Four-record health dispatch predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Four-record health dispatch padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Four-record health dispatch padded neighbors/pools changed')
    caller_before, da = compile_owner(root, output, values[CALLER_SOURCE].decode(), 'caller-before')
    caller_after, db = compile_owner(root, output, typed_caller(values[CALLER_SOURCE].decode()), 'caller-typed')
    caller_functions = same_functions(caller_before, caller_after, ())
    if (caller_functions != 16 or diagnostics(da) != diagnostics(db) or
            normalized_pools(caller_before) != normalized_pools(caller_after) or
            link_owner(root, output, caller_before, 'game_45B80') != link_owner(root, output, caller_after, 'game_45B80')):
        raise ValueError('Typed health-dispatch caller changed code, bindings, pools or diagnostics')
    (output / 'proposed-caller.c').write_text(typed_caller(values[CALLER_SOURCE].decode()))
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=44, frame=48, differences=0, relocations=5, new_guards=0,
        slot_words=45, alignment_words=1, alignment_bytes_preserved=True,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE,
        typed_caller_ABI='void(s16)', caller_functions_preserved=caller_functions,
        caller_diagnostics_unchanged=True)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Four-record health dispatch shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_B21B0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected four-record-health-dispatch Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game/generated_B21B0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown four-record-health-dispatch Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Four-record health dispatch Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Four-record health dispatch Make changed the normal compiler profile')
    if len(commands) != 3 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Four-record health dispatch actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Four-record health dispatch actual Make padding/metadata differs')
    report = dict(actual_Make_commands=3, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Four-record health dispatch strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Four-record health dispatch symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Four-record health dispatch image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_B21B0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown four-record-health-dispatch link input')
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
                    typed_caller(old.decode()).encode() if name == CALLER_SOURCE else
                    (output / 'qualified-padded.o').read_bytes() if name == OBJECT else
                    wanted if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != expected:
            raise ValueError('Four-record health dispatch installed input differs: ' + name)
    return values, wanted


def audit(root, output):
    values, wanted = audit_inputs(root, output)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Four-record health dispatch independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Four-record health dispatch changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Four-record health dispatch protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=44, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
