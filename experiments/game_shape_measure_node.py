"""Shape-node sequencing, typed caller and strict direct-C image gates."""

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


FUNCTION, ENTRY, ROM, SIZE = 'func_1515F1B0', 0x1515F1B0, 0x18C660, 172
SOURCE, OWNER, ASM = 'conker/src/game/generated_18A8F0.c', 'generated_18A8F0', 'conker/asm/18A8F0.s'
BUILD = 'conker/build/game-shape-measure-node/qualified'
OBJECT = 'conker/build/src/game/generated_18A8F0.c.o'
CALLER_SOURCE, CALLER_OWNER = 'conker/src/game_40490.c', 'game_40490'
CALLER_OBJECT = 'conker/build/src/game_40490.c.o'
BEFORE_CALLER_OBJECT_SHA = 'f7791694bf224220587ba1c26dbfb1ccf76ea4c14b69726c1fc74cadf543b626'
BEFORE_OBJECT_SHA = 'c36af1a4de3c8dc8f13b77f70da46a836299232895d369b4c06f1f3d5eabfe35'
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
    "conker/build/conker.us.elf": "4be66e910d868e90ce2d6ad6955010411a527aa55229d279e0097ff9b8a30d4f",
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
    "conker/src/game/generated_18A8F0.c": "713a2c0abfca450deddfd4c4e2ae853edf3a828e2a41cd72e29f3dac2c3c25a8",
    "conker/asm/18A8F0.s": "12d3407e0c32f3fdfbce1cfefc6d31eee56ceda4cb3460684142aef32b015c90",
    "conker/src/game_40490.c": "30b49f05e4573e3ccfb4eab09a1b49e6cdb16871cb50e6abdc9400ebf4ad0000",
    "conker/src/game_16EE20.c": "7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810",
    "conker/src/init_3C40.c": "7345e09fd962a1ddde96f352e3ce0ba3f1bdcff8ad512b306e3b860fb1682bdb"
}
EXTRA_DECLARATIONS = '#include "structs.h"\ns32 func_10003C6C(s32, s32, s32, s32, s32);\nf32 func_1514462C(struct134 *);\nf32 func_15144598(struct134 *);\n\ntypedef struct ShapeMeasureNode {\n    u8 *descriptor;\n    f32 volume;\n    f32 area;\n    struct ShapeMeasureNode *next;\n} ShapeMeasureNode;\n\n'
DECLARATIONS = ''
SELECTED = '/* Allocate a linked shape record with its volume and area measurements. */\nu8 *func_1515F1B0(u8 *descriptor) {\n    ShapeMeasureNode *node = (ShapeMeasureNode *)func_10003C6C(0x10, 1, 2, 0, 1);\n\n    if (node == NULL) {\n        return NULL;\n    }\n    node->descriptor = descriptor;\n    if (descriptor != NULL) {\n        node->volume = func_1514462C((struct134 *)descriptor);\n    } else {\n        node->volume = 0.0f;\n    }\n    if (descriptor != NULL) {\n        node->area = func_15144598((struct134 *)descriptor);\n    } else {\n        node->area = 0.0f;\n    }\n    node->next = NULL;\n    return (u8 *)node;\n}'


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Shape measure node historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    data = (root / OBJECT).read_bytes() if not old.exists() else old.read_bytes()
    if digest(data) != BEFORE_OBJECT_SHA:
        raise ValueError('Shape-node padded predecessor changed')
    if not old.exists():
        old.write_bytes(data)
    caller = output / 'before-caller-padded.o'
    data = caller.read_bytes() if caller.exists() else (root / CALLER_OBJECT).read_bytes()
    if digest(data) != BEFORE_CALLER_OBJECT_SHA:
        raise ValueError('Shape-node caller predecessor changed')
    if not caller.exists():
        caller.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Shape measure node predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Shape measure node snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1515F1B0() {\n    return 0;\n}':
        raise ValueError('Unknown shape-node source predecessor')
    result = (before[:lo] + SELECTED + before[hi:])
    anchor = '#include <ultra64.h>\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown shape-node include anchor')
    return result.replace(anchor, anchor + EXTRA_DECLARATIONS + '\n', 1)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero shape-node alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def recovered_caller(before):
    result=before
    for old,new in [('struct17 *func_1515F1B0(u8 *arg0);','u8 *func_1515F1B0(u8 *arg0);'),
        ('struct17 *temp_v0 = func_1515F1B0(arg0);','u8 *temp_v0 = func_1515F1B0(arg0);'),
        ('D_800DCD90 += temp_v0->unk8;','D_800DCD90 += *(f32 *)(temp_v0 + 8);')]:
        if result.count(old)!=1:raise ValueError('Unknown shape-node caller interface')
        result=result.replace(old,new,1)
    return result



def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ShapeNodeOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-shape-node',
        (root / ASM).read_text(), FUNCTION)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + EXTRA_DECLARATIONS + SELECTED, 'selected')
    if diagnostics(da) != diagnostics(db) or dc:
        raise ValueError('Shape measure node compiler diagnostics: ' + da + db + dc)
    raw, bindings = payload(isolated)
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    linked, functions = link_owner(root, output, isolated, OWNER)
    at = functions[FUNCTION]['value']
    if linked[at:at + SIZE] != truth or sum(map(len, bindings.values())) != 3 or payload(after) != (raw, bindings):
        raise ValueError('Shape measure node direct C differs from retail/whole owner')
    if payload(original(root, output)) != (raw, bindings):
        raise ValueError('Shape measure node independent GNU original differs')
    neighbors = same_functions(before, after, (FUNCTION,))
    if not neighbors or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Shape measure node raw owner pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root / 'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(padded)], check=True, capture_output=True)
    old = output / 'before-padded.o'
    if not old.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_18A8F0.c.o', old)
    a, fa = link_owner(root, output, old, OWNER)
    b, fb = link_owner(root, output, obj, OWNER)
    expected = {name: dict(info) for name, info in fa.items()}
    if expected[FUNCTION]['size'] != 12:
        raise ValueError('Unknown shape-node padded predecessor extent')
    expected[FUNCTION]['size'] = SIZE
    at = fb[FUNCTION]['value']
    slot = elf_slot_offset(values['conker/build/conker.us.elf'], ENTRY, SIZE)
    if a[at:at + SIZE] != values['conker/build/conker.us.elf'][slot:slot + SIZE]:
        raise ValueError('Shape measure node predecessor object/ELF mismatch')
    if b[at:at + SIZE] != truth or expected != fb or a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Shape measure node padding changed another body/address/extent')
    if same_functions(old, obj, (FUNCTION,)) != neighbors or normalized_pools(old) != normalized_pools(obj):
        raise ValueError('Shape measure node padded neighbors/pools changed')
    caller = recovered_caller(values[CALLER_SOURCE].decode())
    old_c, dc = compile_owner(root, output, values[CALLER_SOURCE].decode(), 'before-caller')
    new_c, dd = compile_owner(root, output, caller, 'after-caller')
    if diagnostics(dc) != diagnostics(dd) or same_functions(old_c, new_c) != 32 or normalized_pools(old_c) != normalized_pools(new_c):
        raise ValueError('Shape-node typed caller changed diagnostics/code/pools')
    (output / 'proposed-owner.c').write_text(wanted)
    (output / 'proposed-caller.c').write_text(caller)
    report = dict(words=43, frame=48, differences=0, relocations=3, new_guards=0,
        owner_diagnostics_unchanged=True, isolated_diagnostics_empty=True,
        compiler_only=True, raw_SHA256=digest(raw), preserved_neighbors=neighbors,
        all_owner_addresses_fixed=True, target_size_before=12, target_size_after=SIZE,
        caller_diagnostics_unchanged=True, preserved_caller_functions=32)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def make_shadow(root, output):
    values=freeze(root,output);conker=root/'conker';reports=[]
    for label,src,proposed,owner,total,warnings in (
        ('owner',SOURCE,'proposed-owner.c',OWNER,35,'after-owner-diagnostics.txt'),
        ('caller',CALLER_SOURCE,'proposed-caller.c',CALLER_OWNER,32,'after-caller-diagnostics.txt')):
        expected = recovered_owner(values[src].decode())if label=='owner'else recovered_caller(values[src].decode())
        if (output/proposed).read_text()!=expected:
            raise ValueError('Shape measure node shadow source changed')
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
                raise ValueError('Unknown shape-node Make command')
            args=[(output/proposed).relative_to(conker).as_posix()if a==source_relative.as_posix()else a for a in args]
            redirect=None
            if '>' in args:
                if args.count('>')!=1 or args[-2]!='>':
                    raise ValueError('Unknown shape-node Make redirect')
                redirect=(conker/args[-1]).resolve()
                redirect.relative_to(shadow.resolve())
                args=args[:-2]
            q=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            wanted=diagnostics((output/warnings).read_text())if args[0]=='../ido/ido5.3_recomp/cc'else ''
            if q.returncode or diagnostics(q.stderr+(q.stdout if redirect is None else ''))!=wanted:
                raise ValueError('Shape measure node Make command failed: '+q.stdout+q.stderr)
            if redirect is not None:redirect.write_text(q.stdout)
            commands.append(args)
        compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        if len(commands)!=5 or len(compilers)!=1 or not all(x in compilers[0]for x in ('-O2','-g3')) or any('-loopunroll'in x for x in compilers[0]):
            raise ValueError('Shape measure node actual Make profile changed')
        actual=conker/target
        if same_functions(output/('after-'+label+'.o'),Path(str(actual)+'.compact'))!=total:
            raise ValueError('Shape measure node Make raw code changed')
        if label=='owner':
            if link_owner(root,output,actual,OWNER)!=link_owner(root,output,output/'qualified-padded.o',OWNER):
                raise ValueError('Shape measure node Make padding/metadata differs')
        elif actual.read_bytes()!=(output/'before-caller-padded.o').read_bytes():
            raise ValueError('Shape measure node actual caller object changed')
        reports.append(dict(owner=owner,commands=len(commands),raw_functions=total))
    report=dict(owners=reports,actual_Make_commands=10,normal_O2_g3=True,
        owner_padding_and_metadata_equal=True,entire_caller_object_identical=True)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Shape measure node strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Shape measure node symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Shape measure node image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_18A8F0.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown shape-node link input')
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
            raise ValueError('Shape measure node installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Shape measure node independent first image changed')
    if (root / CALLER_OBJECT).read_bytes() != (output / 'before-caller-padded.o').read_bytes():
        raise ValueError('Shape-node entire caller object changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Shape measure node changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Shape measure node protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=43, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
