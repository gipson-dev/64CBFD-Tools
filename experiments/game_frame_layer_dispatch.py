"""Frame-layer sequencing, typed caller and strict direct-C image gates."""

import hashlib
import json
import re
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
from unittest.mock import patch

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.tests import test_game_actor_burst_packet_match as serialization


FUNCTION, ENTRY, ROM, SIZE = 'func_151749F8', 0x151749F8, 0x1A1EA8, 172
SOURCE, OWNER, ASM = 'conker/src/game/generated_1A1E50.c', 'generated_1A1E50', 'conker/asm/1A1E50.s'
BUILD = 'conker/build/game-frame-layer-dispatch/qualified'
OBJECT = 'conker/build/src/game/generated_1A1E50.c.o'
CALLER_SOURCE, CALLER_OWNER = 'conker/src/game_45B80.c', 'game_45B80'
CALLER_OBJECT = 'conker/build/src/game_45B80.c.o'
BEFORE_CALLER_OBJECT_SHA = '6f93d458b6a4991ee00a8d815534c58451aad5b9864fff79c9ceaf0c9533fafc'
SERIALIZATION = (
    (('D_8008CD04', 'func_1517A84C'), (1, 0),
     ((0x8008CD04, 0, 16, 0, 65521), (0x1517A84C, 12, 18, 0, 5))),
)
BEFORE_OBJECT_SHA = '6509f900890cc3a372a73c162a6d8e0e84f346f39e299b131fde07a5186288de'
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/build/conker.us.elf": "87b1175d6d301c17ae6db273c2c866d7fab43237bfba0794aa2e94912f658a09",
    "conker/retail_word_patches.us.csv": "bcd49d5d0ecb38b8765efa62ce8561f5e857b8a9b42c5bd75948ffa54d6708cb",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/include/libc/stdarg.h": "759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4",
    "conker/src/game/generated_1A1E50.c": "67ba9a5c8c98be65661bf787094b85dc201a52ac2ad93c58489338ffe9436ecb",
    "conker/asm/1A1E50.s": "e9e139cbca83c15ad1f2d4147af554c6c140ae5ededc3ee0272008948e3496e9",
    "conker/src/game_45B80.c": "e1fba9f8560d35cd0106d12062df49b36d25f2b673c725b359946b157e8daf86",
    "conker/asm/nonmatchings/game_45B80/func_15019130.s": "ce3f6e240cec6e4e8ee5c74e979f0a2ce91c14e364b7a24e3f0781f77e67b619",
    "conker/asm/data/231730.rodata.s": "887c6f85ceaa241c4e55cca63b76edcb87af5dd9d04e8a2ae9d292e384421f6c",
    "conker/src/game/done/game_193420.c": "aaf20ada2fc68831e851459e8a33ae9e1103eb64c04430fbb556535caeb4940a"
}
SINE, WRAP, CLOCK = 0x15047D60, 0x15144B68, 0x800BE9A4
EXTRA_DECLARATIONS = 'typedef void (*FrameLayerCallback)(s32);\nextern FrameLayerCallback D_8008CD04[];\nextern s32 D_800B0E00[2];\nextern u8 D_800BE616;\nextern u16 D_800CBD4E;\nvoid func_15165F70(void);\nvoid func_15195FF0(s32, s32);\nvoid func_1510C8A8(void);\nvoid func_1517DE5C(void);\nvoid func_151880C0(void);\n'
DECLARATIONS = '#include "structs.h"\nextern struct104 *D_800B0DF0;\nextern s32 D_800BE9E4;\n'
SELECTED = '/* Run frame-layer callbacks and advance the wrapping phase accumulator. */\nvoid func_151749F8(s32 unused, s32 view) {\n    func_15165F70();\n    func_15195FF0(D_800B0E00[0], D_800B0E00[1]);\n    func_1510C8A8();\n    if (((u8 *)D_800B0DF0)[0xB] != 0) {\n        D_8008CD04[((u8 *)D_800B0DF0)[0xB]](view);\n    }\n    if (D_800BE616 == 0) {\n        func_1517DE5C();\n        func_151880C0();\n    }\n    D_800CBD4E += (u32)D_800BE9E4 << 6;\n}'


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Frame-layer dispatch historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    data = (root / OBJECT).read_bytes() if not old.exists() else old.read_bytes()
    if digest(data) != BEFORE_OBJECT_SHA:
        raise ValueError('Frame-layer padded predecessor changed')
    if not old.exists():
        old.write_bytes(data)
    caller = output / 'before-caller-padded.o'
    data = caller.read_bytes() if caller.exists() else (root / CALLER_OBJECT).read_bytes()
    if digest(data) != BEFORE_CALLER_OBJECT_SHA:
        raise ValueError('Frame-layer caller predecessor changed')
    if not caller.exists():
        caller.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Frame-layer dispatch predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Frame-layer dispatch snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151749F8() {\n    return 0;\n}':
        raise ValueError('Unknown frame-layer source predecessor')
    result = (before[:lo] + SELECTED + before[hi:])
    anchor = '#include "structs.h"\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown frame-layer include anchor')
    return result.replace(anchor, anchor + EXTRA_DECLARATIONS + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero frame-layer alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def recovered_caller(before):
    old = 's32 func_151749F8(s32, s32);'
    if before.count(old) != 1:
        raise ValueError('Unknown frame-layer caller prototype')
    return before.replace(old, 'void func_151749F8(s32, s32);', 1)


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('LayerOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-frame-layer',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + EXTRA_DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Frame-layer dispatch compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or sum(map(len, bindings.values())) != 17 or payload(after) != (raw, bindings):
        raise ValueError('Frame-layer dispatch direct C differs from retail/whole owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Frame-layer dispatch independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Frame-layer dispatch raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_1A1E50.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown frame-layer padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Frame-layer dispatch predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Frame-layer dispatch padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Frame-layer dispatch padded neighbors/pools changed')
    caller = recovered_caller(values[CALLER_SOURCE].decode())
    old_c, dc = compile_owner(root, output, values[CALLER_SOURCE].decode(), 'before-caller')
    new_c, dd = compile_owner(root, output, caller, 'after-caller')
    if diagnostics(dc) != diagnostics(dd) or same_functions(old_c, new_c) != 16 or normalized_pools(old_c) != normalized_pools(new_c):
        raise ValueError('Frame-layer typed caller changed diagnostics/code/pools')
    (output / 'proposed-owner.c').write_text(wanted)
    (output / 'proposed-caller.c').write_text(caller)
    report = dict(words=43, frame=24, differences=0, relocations=17, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE,
        caller_diagnostics_unchanged=True, preserved_caller_functions=16)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values=freeze(root,output);conker=root/'conker';reports=[]
    for label,src,proposed,owner,total,warnings in (
        ('owner',SOURCE,'proposed-owner.c',OWNER,4,'after-owner-diagnostics.txt'),
        ('caller',CALLER_SOURCE,'proposed-caller.c',CALLER_OWNER,16,'after-caller-diagnostics.txt')):
        expected = recovered_owner(values[src].decode())if label=='owner'else recovered_caller(values[src].decode())
        if (output/proposed).read_text()!=expected:
            raise ValueError('Frame-layer dispatch shadow source changed')
        shadow=output/('make-shadow-'+label)
        source_relative=Path(src).relative_to('conker')
        target=(shadow/source_relative).with_suffix('.c.o').relative_to(conker).as_posix()
        (conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
            cwd=conker,capture_output=True,text=True,check=True)
        (output/('make-shadow-'+label+'-plan.txt')).write_text(plan.stdout+plan.stderr)
        commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
                raise ValueError('Unknown matrix wrapper Make command')
            args=[(output/proposed).relative_to(conker).as_posix()if a==source_relative.as_posix()else a for a in args]
            q=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            wanted=diagnostics((output/warnings).read_text())if args[0]=='../ido/ido5.3_recomp/cc'else ''
            if q.returncode or diagnostics(q.stdout+q.stderr)!=wanted:
                raise ValueError('Frame-layer dispatch Make command failed: '+q.stdout+q.stderr)
            commands.append(args)
        compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        if len(commands)!=3 or len(compilers)!=1 or not all(x in compilers[0]for x in ('-O2','-g3')) or any('-loopunroll'in x for x in compilers[0]):
            raise ValueError('Frame-layer dispatch actual Make profile changed')
        actual=conker/target
        if same_functions(output/('after-'+label+'.o'),Path(str(actual)+'.compact'))!=total:
            raise ValueError('Frame-layer dispatch Make raw code changed')
        if label=='owner':
            if link_owner(root,output,actual,OWNER)!=link_owner(root,output,output/'qualified-padded.o',OWNER):
                raise ValueError('Frame-layer dispatch Make padding/metadata differs')
        elif actual.read_bytes()!=(output/'before-caller-padded.o').read_bytes():
            raise ValueError('Frame-layer dispatch actual caller object changed')
        reports.append(dict(owner=owner,commands=3,raw_functions=total))
    report=dict(owners=reports,actual_Make_commands=6,normal_O2_g3=True,
        owner_padding_and_metadata_equal=True,entire_caller_object_identical=True)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Frame-layer dispatch strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Frame-layer dispatch symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    canonical = canonical_symbols(bytes(result))
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION):
        serialization.apply_burst_symbol_serialization(result)
    if canonical_symbols(bytes(result)) != canonical:
        raise ValueError('Frame-layer symbol serialization changed canonical symbols')
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Frame-layer dispatch image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_1A1E50.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown frame-layer link input')
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
            raise ValueError('Frame-layer dispatch installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Frame-layer dispatch independent first image changed')
    if (root / CALLER_OBJECT).read_bytes() != (output / 'before-caller-padded.o').read_bytes():
        raise ValueError('Frame-layer entire caller object changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Frame-layer dispatch changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Frame-layer dispatch protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=43, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
