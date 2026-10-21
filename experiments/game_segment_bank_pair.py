"""Direct SDK segment-bank draw pair with typed caller and complete image gates."""

import hashlib
import json
import re
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

SOURCE, OWNER, ASM = 'conker/src/game/generated_203E20.c', 'generated_203E20', 'conker/asm/203E20.s'
CALLER_SOURCE, CALLER_OWNER = 'conker/src/game/generated_126F60.c', 'generated_126F60'
BUILD = 'conker/build/game-segment-bank-pair/qualified'
OBJECT = 'conker/build/src/game/generated_203E20.c.o'
CALLER_OBJECT = 'conker/build/src/game/generated_126F60.c.o'
BEFORE_OBJECT_SHA = 'b4bf4e782f6d7e39d98c7276bd4c94b41a6ea34e1dde18df7bd1c31d1ffc0a6b'
BEFORE_CALLER_OBJECT_SHA = '7fb6083d5edb715b1465ae005cc0d098919291cff0ed1c53aa1a5cc131fda3ed'
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
    "conker/build/conker.us.elf": "05264b64f004e8e7160542e4a63deeb776559ba1554e52b4efe15218ba5fa5c3",
    "conker/retail_word_patches.us.csv": "704d9da0fe81ea2498078c8b5b2f53994ba05cf8e9e88af2ba0cb5dfd38ce71c",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/src/game/generated_203E20.c": "ba300b511190ca575314dd104abe46aac7d9c5b1770682bcb719117d6cd9e33c",
    "conker/asm/203E20.s": "f0b5e52d8974199a54ed71cdab71ce2a53cda6472592a84b522728a478309815",
    "conker/asm/data/22F850.rodata.s": "05b48f333c92281d8fcaddc9014985cfac2ead95518204cea4c7d6d0dda7da08",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/src/game/generated_126F60.c": "c3d63dca03bdb130cade3202c99dbd310cf564d00e2c52d0afe651a5d475e057",
    "conker/asm/126F60.s": "a62123cdbabf75864cfb8dddd8e8f27bb7eb8d24886c56ceda189944c4db1a76",
    "conker/src/game/generated_15F680.c": "7bdcdacebf10a75fc8c4090ac82355b45f122f1771457f47d69e61dc19d57e94",
    "conker/asm/15F680.s": "f697fe44a7ea8c4c6a7a7016236764a088a6922f559686ee4d3731d5c264413b",
    "conker/asm/data/2275E0.data.s": "9c912a5b5595b37b590fb8da13727bf91e1c495b0ff0f297231347417e7d700e",
    "conker/asm/data/234CB0.rodata.s": "0b6c12c34c9d65c1c0db82da80c7f71687ac4cfbd32111fe51d7baacd2d6a717"
}
TARGETS = {
 'func_151D710C': dict(entry=0x151D710C, rom=0x2045BC, size=160, slot_size=164,
  SHA256='81ab0b702d359aaf4bb1c0a7fed5f1a4ef3b188cde97a6fc40d307d2bfcec48c'),
}
FUNCTIONS = tuple(TARGETS)
DECLARATIONS = "extern Gfx D_80083740[], D_800838C0[];\nGfx *func_15133EEC(Gfx *, u16, u8, s32);\n"
SELECTED = {'func_151D710C': "/* Select the segment-8 bank, submit segments 6/7 and mark the draw state. */\nGfx *func_151D710C(Gfx *commands, u8 *descriptor, s32 unused2, s32 unused3, u8 *changed) {\n    if (descriptor[0x43] < 0xFF) {\n        gSPSegment(commands++, 8, D_80083740);\n    } else {\n        gSPSegment(commands++, 8, D_800838C0);\n    }\n    commands = func_15133EEC(commands, 0xC3, 6, 3);\n    commands = func_15133EEC(commands, 0xC3, 7, 3);\n    *changed = 1;\n    return commands;\n}"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Segment pair historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, frozen, wanted in ((OBJECT, 'before-padded.o', BEFORE_OBJECT_SHA),
                                 (CALLER_OBJECT, 'before-caller-padded.o', BEFORE_CALLER_OBJECT_SHA)):
        target = output / frozen
        if not target.exists():
            data = (root / name).read_bytes()
            if digest(data) != wanted:
                raise ValueError('Segment pair padded predecessor changed: ' + name)
            target.write_bytes(data)
        if digest(target.read_bytes()) != wanted:
            raise ValueError('Segment pair frozen padded object changed: ' + name)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Segment pair predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Segment pair snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def recovered_owner(before):
    anchor = '#include <ultra64.h>\n'
    if before.count(anchor) != 1:
        raise ValueError('Unknown segment pair include anchor')
    result = before.replace(anchor, anchor + DECLARATIONS + '\n', 1)
    for name in FUNCTIONS:
        lo, hi = function_span(result, name)
        if result[lo:hi] != 's32 %s() {\n    return 0;\n}' % name:
            raise ValueError('Unknown segment pair predecessor')
        result = result[:lo] + SELECTED[name] + result[hi:]
    return result


def recovered_caller(before):
    old = 's32 func_151D710C(s32, s32, s32, s32, s32);'
    call = 'arg0 = func_151D710C(arg0, arg1, arg2, arg3, arg4);'
    if before.count(old) != 1 or before.count(call) != 1:
        raise ValueError('Unknown segment pair caller anchors')
    return before.replace(old, 'Gfx *func_151D710C(Gfx *, u8 *, s32, s32, u8 *);', 1).replace(
        call, 'arg0 = (s32)func_151D710C((Gfx *)arg0, (u8 *)arg1, arg2, arg3, (u8 *)arg4);', 1)


def caller_diagnostics(before, after):
    if diagnostics(before) != diagnostics(after):
        raise ValueError('Segment pair caller diagnostics changed')
    return dict(before_warnings=before.count('Warning'), after_warnings=after.count('Warning'),
                unchanged=True)


def payload(obj, name):
    text, functions, bindings = parse_object(obj)
    info = functions[name]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor selector alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def original(root, output, name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('ActorSelectorOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-' + name,
        (root / ASM).read_text(), name)


def qualify(root, output):
    values = freeze(root, output)
    wanted = recovered_owner(values[SOURCE].decode())
    before, da = compile_owner(root, output, values[SOURCE].decode(), 'before-owner')
    after, db = compile_owner(root, output, wanted, 'after-owner')
    if diagnostics(da) != diagnostics(db):
        raise ValueError('Segment pair owner diagnostics changed')
    rows = []
    for name, target in TARGETS.items():
        isolated, dc = compile_owner(root, output, '#include <ultra64.h>\n' + DECLARATIONS + SELECTED[name], 'selected-' + name)
        raw, bindings = payload(isolated, name)
        truth = values['conker/conker.us.bin'][target['rom']:target['rom'] + target['size']]
        linked, fs = link_owner(root, output, isolated, OWNER)
        at = fs[name]['value']
        if dc or len(raw) != 160 or digest(raw) != target['SHA256'] or linked[at:at+160] != truth or sum(map(len,bindings.values())) != 6:
            raise ValueError('Segment pair isolated C differs: ' + name)
        if payload(after, name) != (raw, bindings) or payload(original(root, output, name), name) != (raw, bindings):
            raise ValueError('Segment pair whole owner/GNU original differs')
        rows.append(dict(function=name, words=40, frame=24, bindings=6, new_guards=0))
    neighbors = same_functions(before, after, FUNCTIONS)
    if neighbors != 6 or normalized_pools(before) != normalized_pools(after):
        raise ValueError('Segment pair raw owner neighbor/pool changed')
    padded = output / 'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after, root / ASM,
        word_patches_path=root/'conker/retail_word_patches.us.csv', filename=OWNER))
    obj = padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],check=True,capture_output=True)
    a, fa = link_owner(root,output,output/'before-padded.o',OWNER)
    b, fb = link_owner(root,output,obj,OWNER)
    expected = {name:dict(info)for name,info in fa.items()};spans=[]
    for name,target in TARGETS.items():
        if expected[name]['size'] != 12:
            raise ValueError('Unknown segment pair predecessor extent')
        expected[name]['size'] = 160
        at = fb[name]['value'];spans.append((at,at+160))
        slot = elf_slot_offset(values['conker/build/conker.us.elf'],target['entry'],target['slot_size'])
        if a[at:at+target['slot_size']] != values['conker/build/conker.us.elf'][slot:slot+target['slot_size']]:
            raise ValueError('Segment pair predecessor object/ELF mismatch')
        if b[at:at+target['slot_size']] != values['conker/conker.us.bin'][target['rom']:target['rom']+target['slot_size']]:
            raise ValueError('Segment pair padded body/alignment differs')
    if expected != fb or len(a)!=len(b) or any(x!=y and not any(lo<=at<hi for lo,hi in spans)for at,(x,y)in enumerate(zip(a,b))):
        raise ValueError('Segment pair changed another body/address/extent')
    if same_functions(output/'before-padded.o',obj,FUNCTIONS)!=6 or normalized_pools(output/'before-padded.o')!=normalized_pools(obj):
        raise ValueError('Segment pair padded neighbors/pools changed')
    caller = recovered_caller(values[CALLER_SOURCE].decode())
    old_c, dc = compile_owner(root,output,values[CALLER_SOURCE].decode(),'before-caller')
    new_c, dd = compile_owner(root,output,caller,'after-caller')
    diag = caller_diagnostics(dc,dd)
    if same_functions(old_c,new_c)!=18 or normalized_pools(old_c)!=normalized_pools(new_c):
        raise ValueError('Segment pair typed caller changed code/pools')
    (output/'proposed-owner.c').write_text(wanted);(output/'proposed-caller.c').write_text(caller)
    report = dict(targets=rows,total_words=40,compiler_only=True,new_guards=0,
        preserved_neighbors=6,preserved_caller_functions=18,caller_diagnostics=diag,
        all_owner_addresses_fixed=True,target_sizes_before=[12],target_sizes_after=[160],
        original_alignment_bytes=4)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def make_shadow(root, output):
    values=freeze(root,output);conker=root/'conker';reports=[]
    for label,src,proposed,owner,total,warnings in (
        ('owner',SOURCE,'proposed-owner.c',OWNER,7,'after-owner-diagnostics.txt'),
        ('caller',CALLER_SOURCE,'proposed-caller.c',CALLER_OWNER,18,'after-caller-diagnostics.txt')):
        expected = recovered_owner(values[src].decode())if label=='owner'else recovered_caller(values[src].decode())
        if (output/proposed).read_text()!=expected:
            raise ValueError('Segment pair shadow source changed')
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
                raise ValueError('Unknown segment pair Make command')
            args=[(output/proposed).relative_to(conker).as_posix()if a==source_relative.as_posix()else a for a in args]
            q=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            wanted=diagnostics((output/warnings).read_text())if args[0]=='../ido/ido5.3_recomp/cc'else ''
            if q.returncode or diagnostics(q.stdout+q.stderr)!=wanted:
                raise ValueError('Segment pair Make command failed: '+q.stdout+q.stderr)
            commands.append(args)
        compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        if len(commands)!=3 or len(compilers)!=1 or not all(x in compilers[0]for x in ('-O2','-g3')) or any('-loopunroll'in x for x in compilers[0]):
            raise ValueError('Segment pair actual Make profile changed')
        actual=conker/target
        if same_functions(output/('after-'+label+'.o'),Path(str(actual)+'.compact'))!=total:
            raise ValueError('Segment pair Make raw code changed')
        if label=='owner':
            if link_owner(root,output,actual,OWNER)!=link_owner(root,output,output/'qualified-padded.o',OWNER):
                raise ValueError('Segment pair Make padding/metadata differs')
        elif actual.read_bytes()!=(output/'before-caller-padded.o').read_bytes():
            raise ValueError('Segment pair actual caller object changed')
        reports.append(dict(owner=owner,commands=3,raw_functions=total))
    report=dict(owners=reports,actual_Make_commands=6,normal_O2_g3=True,
        owner_padding_and_metadata_equal=True,entire_caller_object_identical=True)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before, rom):
    if digest(before) != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Segment pair strict image predecessor changed')
    result = bytearray(before)
    for name, target in TARGETS.items():
        at = elf_slot_offset(before, target['entry'], target['size'])
        result[at:at + target['size']] = rom[target['rom']:target['rom'] + target['size']]
        rows = [offset for offset, symbol, fields, _ in symbol_rows(before)
                if symbol == name and fields[1:3] == (target['entry'], 12) and fields[3] & 15 == 2]
        if len(rows) != 1:
            raise ValueError('Segment pair symbol extent predecessor changed')
        struct.pack_into('>I', result, rows[0] + 8, target['size'])
    return bytes(result)


def check_image(before, actual, rom):
    if actual != predicted_image(before, rom):
        raise ValueError('Segment pair image differs from strict three-body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game/generated_203E20.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown actor selector link input')
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, (output / 'qualified-padded.o').relative_to(root / 'conker').as_posix()))
    elf = output / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(root / 'conker').as_posix(),
        '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
        '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
        '-o', elf.relative_to(root / 'conker').as_posix()], cwd=root / 'conker', check=True, capture_output=True)
    before, actual, rom = values['conker/build/conker.us.elf'], elf.read_bytes(), values['conker/conker.us.bin']
    check_image(before, actual, rom)
    changed = sum(a != b for a, b in zip(before, actual));code = 0
    for target in TARGETS.values():
        at = elf_slot_offset(before, target['entry'], target['size'])
        code += sum(a != b for a, b in zip(before[at:at + target['size']], rom[target['rom']:target['rom'] + target['size']]))
    report = dict(exact_prediction=True, SHA256=digest(actual), changed_bytes=changed,
        code_bytes_changed=code, metadata_bytes_changed=changed-code, metadata_exclusions=0)
    (output / 'first-link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(root, output):
    values = snapshot(output)
    wanted = predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'])
    for name, old in values.items():
        expected = recovered_owner(old.decode()).encode() if name == SOURCE else recovered_caller(old.decode()).encode() if name == CALLER_SOURCE else wanted if name == 'conker/build/conker.us.elf' else old
        if (root / name).read_bytes() != expected:
            raise ValueError('Segment pair installed input differs: ' + name)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Segment pair independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or set(n for n in a if a[n] != b[n]) != set(FUNCTIONS):
        raise ValueError('Segment pair changed another body/address')
    if parse_object(root / OBJECT) != parse_object(output / 'qualified-padded.o') or normalized_pools(root / OBJECT) != normalized_pools(output / 'qualified-padded.o'):
        raise ValueError('Segment pair installed padded object changed')
    if (root/CALLER_OBJECT).read_bytes() != (output/'before-caller-padded.o').read_bytes():
        raise ValueError('Segment pair installed caller object changed')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Segment pair protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b)-1, all_addresses_fixed=True,
        target_words=40, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
