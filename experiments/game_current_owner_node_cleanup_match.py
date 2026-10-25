"""Current-owner cleanup: direct C, owner preservation, and strict linked-image gates."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import shlex
import struct
import subprocess
from unittest.mock import patch
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION, ENTRY, ROM, SIZE = 'func_150AFDB0', 0x150AFDB0, 0xDD260, 180
SOURCE, OWNER, ASM = 'conker/src/game/generated_DC6B0.c', 'generated_DC6B0', 'conker/asm/DC6B0.s'
BUILD = 'conker/build/game-current-owner-node-cleanup-match'
OBJECT = 'conker/build/src/game/generated_DC6B0.c.o'
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/DC6B0.s": "9ee777cf5cc3eae491c12279eca2a9119c97f790329d2d4094cdd4c4ce0ac1c9",
    "conker/asm/nonmatchings/game_981E0/func_1506DE84.s": "e2cfb7adb31422b51fcb0ea75175e260a158c37c8cde7bc07f86c629cccc0bd6",
    "conker/build/conker.us.elf": "81efe331ccd0c1502e0f94b33f884a8111dae4a86dd2d59e42d732b2a8aeba96",
    "conker/build/src/game/generated_DC6B0.c.o": "d987d7d979956855e8e1cda4787a4a8d80c09c9ae84ee856b7d09f3b5eb470e7",
    "conker/build/src/game_1944C0.c.o": "7e254b6a13ec7b5034e6e7389cbdb2b8d511f0c4f921b9de246a826d65ac4b7c",
    "conker/build/src/game_981E0.c.o": "531788b1a1b6a2c819beb3eca9ec72a2742e6bcc47cfe57760c7eae0cffbe029",
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
    "conker/src/game/generated_DC6B0.c": "d8d58fb1eebbd30edeee2937b06734a94378be10467337e5301120ad585a8f77",
    "conker/src/game_1944C0.c": "28ebe25c59fe01dc61aaea0c8949fa15ba61103e5b9a8aa6e170a6da1f98b5bf",
    "conker/src/game_981E0.c": "20b9d1cad179f7d470686d38b008f175a034642ad6df508cd5334bffb7aa6f04",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "tools/experiments/game_actor_child_cleanup.py": "85b21fd74ae6dcee12c990f69303bcf11c567b80aa32f1c5270a208cde762510",
    "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
    "tools/tests/game_view_render_pass_oracle.py": "97782140d5683fada720f2bc3e01d84f21e5ea6d7b6947f1cc69fbe1886c8ee9",
    "tools/tests/test_game_actor_child_cleanup.py": "074572a09eba207cc852675b0d578a86034eaf7150ebf334d286ec7d925deb9b",
    "tools/tests/test_game_effect_owner_ray.py": "62376c5022f50db9a53b0ec8b9517a63bc9f298dff8c7a3047963ed216a0555f"
}
DECLARATIONS = '''#include "structs.h"
extern s8 D_800DD190;
extern struct102 *D_800DCE94;
extern void *D_800DD198[];
extern u8 D_800C3E78;
void func_1516972C(struct102 *);
'''
SELECTED = '''/* Release list nodes owned by the current object, preserving nested iterators. */
void func_150AFDB0(void) {
    struct102 *node;

    D_800DD190++;
    node = D_800DCE94;
    while (node != NULL) {
        D_800DD198[D_800DD190] = (struct102 *)node->unk8;
        if (D_800C3E78 == node->pad3E[1]) {
            func_1516972C(node);
        }
        node = D_800DD198[D_800DD190];
    }
    D_800DD190--;
}'''
RAW_SHA256 = '483ed4239082edc00e7a45e6d3b03f4bfe18a2adcd567f3b454da7986942a523'
BINDINGS = {12: [('R_MIPS_HI16', 'D_800DD190')], 16: [('R_MIPS_LO16', 'D_800DD190')],
    20: [('R_MIPS_HI16', 'D_800DCE94')], 24: [('R_MIPS_LO16', 'D_800DCE94')],
    28: [('R_MIPS_HI16', 'D_800DD190')], 40: [('R_MIPS_LO16', 'D_800DD190')],
    52: [('R_MIPS_HI16', 'D_800DD198')], 56: [('R_MIPS_LO16', 'D_800DD198')],
    64: [('R_MIPS_HI16', 'D_800C3E78')], 68: [('R_MIPS_LO16', 'D_800C3E78')],
    100: [('R_MIPS_26', 'func_1516972C')],
    108: [('R_MIPS_HI16', 'D_800DD190')], 112: [('R_MIPS_LO16', 'D_800DD190')],
    116: [('R_MIPS_HI16', 'D_800DD198')], 120: [('R_MIPS_LO16', 'D_800DD198')],
    144: [('R_MIPS_HI16', 'D_800DD190')], 148: [('R_MIPS_LO16', 'D_800DD190')],
    152: [('R_MIPS_HI16', 'D_800DD190')], 164: [('R_MIPS_LO16', 'D_800DD190')]}
SERIALIZATION = ((('D_80095BC0', 'D_8009EFC0'), (1, 0),
    ((0x80095BC0, 0, 16, 0, 65521), (0x8009EFC0, 0, 16, 0, 6))),)


def apply_symbol_serialization(expected):
    from tools.tests import test_game_actor_burst_packet_match as serializer
    before = Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(expected))
    with patch.object(serializer, 'SERIALIZATION', SERIALIZATION):
        serializer.apply_burst_symbol_serialization(expected)
    after = Counter((name, *fields[1:]) for _, name, fields, _ in symbol_rows(expected))
    if before != after:
        raise ValueError('Cleanup symbol serialization changed a named definition')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Current-owner cleanup historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    values = snapshot(output)
    for name, old in values.items():
        if (root / name).read_bytes() != old:
            raise ValueError('Current-owner cleanup predecessor changed: ' + name)
    if (output / 'before-padded.o').read_bytes() != values[OBJECT]:
        raise ValueError('Current-owner cleanup padded predecessor changed')
    return values


def recovered_owner(before):
    marker = '#include <ultra64.h>\n'
    if before.count(marker) != 1:
        raise ValueError('Unknown cleanup owner include anchor')
    result = before.replace(marker, marker + DECLARATIONS, 1)
    marker = 'func_1516972C(*(s32 volatile *)(temp_a1 + 0x170));'
    if result.count(marker) != 1:
        raise ValueError('Unknown neighboring cleanup call')
    result = result.replace(marker, 'func_1516972C((struct102 *)*(s32 volatile *)(temp_a1 + 0x170));', 1)
    lo, hi = function_span(result, FUNCTION)
    if result[lo:hi] != 's32 func_150AFDB0() {\n    return 0;\n}':
        raise ValueError('Unknown current-owner cleanup placeholder')
    return result[:lo] + SELECTED + result[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero current-owner cleanup alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
        if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def checked_payload(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Changed current-owner cleanup words/bindings')


def original(root, output, name=FUNCTION, asm=ASM):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('PlaneOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / asm).read_text(), name)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Current-owner cleanup compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    checked_payload(raw, bindings)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or payload(after) != (raw, bindings):
        raise ValueError('Current-owner cleanup direct C differs from retail/owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Current-owner cleanup independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Current-owner cleanup raw neighbors/pools changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown current-owner cleanup predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Current-owner cleanup predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Current-owner cleanup padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Current-owner cleanup padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=45, frame=32, differences=0, relocations=19, new_guards=0,
        alignment_words=0, owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        existing_GLOBAL_ASM_neighbors_preserved=1, shared_headers_unchanged=True,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Current-owner cleanup shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_DC6B0.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected current-owner cleanup Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
            if a == 'src/game/generated_DC6B0.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown current-owner cleanup Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected):
            raise ValueError('Current-owner cleanup Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2', '-g3')) or any('-loopunroll' in f for f in compilers[0]):
        raise ValueError('Current-owner cleanup Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Current-owner cleanup actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Current-owner cleanup actual Make padding differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        original_GLOBAL_ASM_preprocessing_and_postprocessing=True,
        padded_code_and_metadata_equal=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Current-owner cleanup strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
        if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Current-owner cleanup symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    apply_symbol_serialization(result)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Current-owner cleanup image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_DC6B0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown current-owner cleanup link input')
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
        closed_symbol_string_permutations=1, named_definitions_preserved_except_target_extent=True)
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
            raise ValueError('Current-owner cleanup installed input differs: ' + name)
    return values, wanted


def audit(root, output):
    values, wanted = audit_inputs(root, output)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Current-owner cleanup independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Current-owner cleanup changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Current-owner cleanup protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=45, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
