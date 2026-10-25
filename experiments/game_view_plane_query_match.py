"""View/plane query: direct C, owner preservation, and strict linked-image gates."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION, ENTRY, ROM, SIZE = 'func_150A2FA4', 0x150A2FA4, 0xD0454, 180
SOURCE, OWNER, ASM = 'conker/src/game/generated_CDE80.c', 'generated_CDE80', 'conker/asm/CDE80.s'
BUILD = 'conker/build/game-view-plane-query-match'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/CD860.s": "effe6ed0a99bfe52449277989075dd96d61b4d998c104336d814f79983dcc7c3",
    "conker/asm/CDE80.s": "95904fbecd5afa084a49b575c41494f0e275754359e2eefc3e1068d5efc15ec1",
    "conker/build/conker.us.elf": "f9ac9d10164b603e7a77f0d8018f97b54ec1ef3c67211f3ad15e118b911f4e1d",
    "conker/build/src/game/generated_CD860.c.o": "b8cad9b2343890c63a3b3b5fbf7fe748ec5cd4b54cf9ec1848797398650e54eb",
    "conker/build/src/game/generated_CDE80.c.o": "34c134c851f6d24f7d2dc52032b460a0bb61df55d6c522dcf9185c416ff3428a",
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
    "conker/src/game/generated_CD860.c": "8d634d475d6c747a0c1fe907d060610877e01c3c24e3679efb1a09df91cc4842",
    "conker/src/game/generated_CDE80.c": "4b40a96cab764c53cbf5d83fad3eb380cc4c5340b991fa415de91deb23d89b47",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
    "tools/tests/game_view_render_pass_oracle.py": "97782140d5683fada720f2bc3e01d84f21e5ea6d7b6947f1cc69fbe1886c8ee9",
    "tools/tests/test_game_effect_owner_ray.py": "62376c5022f50db9a53b0ec8b9517a63bc9f298dff8c7a3047963ed216a0555f",
    "tools/tests/test_game_record_query_match.py": "ba119426bee55d1731a1bb93f2a9fc79c5661ee1e2ecd30787c72f1499120d51"
}
RECORD = '''typedef struct {
    s16 origin0;
    s16 origin1;
    s16 origin2;
    u8 pad6[0xF];
    u8 flags;
    u8 pad16;
    u8 field17;
    s32 field18;
    s32 field1C;
    s32 field20;
    f32 coefficient0;
    f32 scale;
    f32 coefficient1;
    f32 coefficient2;
} GeneratedCDE80Record;

'''
DECLARATIONS = '''#include "structs.h"
''' + RECORD + '''extern GeneratedCDE80Record *D_800D3098;
extern s32 D_800D3094;
extern struct108 *D_800DBFF0;
s32 func_150A2E4C(GeneratedCDE80Record *, f32, f32, f32);
'''
SELECTED = '''/* Test a masked volume selector against the selected view position. */
s32 func_150A2FA4(s32 viewIndex, s32 selector) {
    struct108 *view;

    view = &D_800DBFF0[viewIndex];
    selector &= 0xFFF;
    if ((u32)D_800D3094 < (u32)selector) {
        return 1;
    }
    if ((D_800D3098[selector].flags & 3) == 3) {
        return func_150A2E4C(&D_800D3098[selector], view->unk2F8, view->unk2FC, view->unk300);
    }
    return 0;
}'''
RAW_SHA256 = '260215a1c6f61fc64c84cf88317f2dd59f68379662791ae6f20cdf810c875649'
BINDINGS = {20: [('R_MIPS_HI16', 'D_800D3094')], 24: [('R_MIPS_LO16', 'D_800D3094')],
    36: [('R_MIPS_HI16', 'D_800DBFF0')], 40: [('R_MIPS_LO16', 'D_800DBFF0')],
    88: [('R_MIPS_HI16', 'D_800D3098')], 92: [('R_MIPS_LO16', 'D_800D3098')],
    144: [('R_MIPS_26', 'func_150A2E4C')]}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('View/plane query historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    values = snapshot(output)
    for name, old in values.items():
        if (root / name).read_bytes() != old:
            raise ValueError('View/plane query predecessor changed: ' + name)
    if (output / 'before-padded.o').read_bytes() != values[OBJECT]:
        raise ValueError('View/plane query padded predecessor changed')
    return values


def recovered_owner(before):
    first = before.index('typedef struct {')
    end = before.index('extern GeneratedCDE80Record')
    plane_start = before.index('typedef struct {\n    s16 origin0;')
    plane_end = before.index('} GeneratedCDE80Plane;', plane_start) + len('} GeneratedCDE80Plane;')
    result = before[:plane_start] + 'typedef GeneratedCDE80Record GeneratedCDE80Plane;' + before[plane_end:]
    result = result[:first] + RECORD + result[end:]
    for old, new in (('field0', 'origin0'), ('field2', 'origin1'), ('field4', 'origin2')):
        marker = '].' + old + ' ='
        if result.count(marker) != 1:
            raise ValueError('Unknown view/plane record setter: ' + old)
        result = result.replace(marker, '].' + new + ' =')
    marker = 'extern GeneratedCDE80Record *D_800D3098;\n'
    if result.count(marker) != 1:
        raise ValueError('Unknown view/plane record declaration')
    result = result.replace(marker, marker + 'extern s32 D_800D3094;\nextern struct108 *D_800DBFF0;\n', 1)
    lo, hi = function_span(result, FUNCTION)
    if result[lo:hi] != 's32 func_150A2FA4() {\n    return 0;\n}':
        raise ValueError('Unknown view/plane query placeholder')
    return result[:lo] + SELECTED + result[hi:]


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero view/plane query alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
        if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def checked_payload(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Changed view/plane query words/bindings')


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
        raise ValueError('View/plane query compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    checked_payload(raw, bindings)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or payload(after) != (raw, bindings):
        raise ValueError('View/plane query direct C differs from retail/owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('View/plane query independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('View/plane query raw neighbors/pools changed')
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
        raise ValueError('Unknown view/plane query predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('View/plane query predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('View/plane query padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('View/plane query padded neighbors/pools changed')
    (output / 'proposed-owner.c').write_text(wanted)
    report = dict(words=45, frame=24, differences=0, relocations=7, new_guards=0,
        alignment_words=0, owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        existing_GLOBAL_ASM_neighbors_preserved=2, shared_headers_unchanged=True,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('View/plane query shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_CDE80.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected view/plane query Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
            if a == 'src/game/generated_CDE80.c' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown view/plane query Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected):
            raise ValueError('View/plane query Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [a for a in commands if a[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(f in compilers[0] for f in ('-O2', '-g3')) or any('-loopunroll' in f for f in compilers[0]):
        raise ValueError('View/plane query Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('View/plane query actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('View/plane query actual Make padding differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        original_GLOBAL_ASM_preprocessing_and_postprocessing=True,
        padded_code_and_metadata_equal=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('View/plane query strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
        if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('View/plane query symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('View/plane query image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_CDE80.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown view/plane query link input')
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
            raise ValueError('View/plane query installed input differs: ' + name)
    return values, wanted


def audit(root, output):
    values, wanted = audit_inputs(root, output)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('View/plane query independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('View/plane query changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('View/plane query protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=45, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
