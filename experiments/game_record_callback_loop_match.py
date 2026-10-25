"""Live record callback loop: semantic C, derived schedule and strict image gates."""
import csv
import hashlib
import io
import json
import re
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object as ordinary_padder
from tools.experiments.game_remaining_donor_candidates import compile_owner, function_span, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION,ENTRY,ROM,SIZE='func_15013000',0x15013000,0x404B0,180
SOURCE,OWNER,ASM='conker/src/game_40490.c','game_40490','conker/asm/nonmatchings/game_40490/func_15013000.s'
OBJECT='conker/build/src/game_40490.c.o'
CALLER_SOURCE='conker/src/game_34F20.c'
CALLER_OBJECT='conker/build/src/game_34F20.c.o'
BUILD='conker/build/game-record-callback-loop-match'
INPUTS = {
  "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
  "conker/asm/data/2275E0.data.s": "9c912a5b5595b37b590fb8da13727bf91e1c495b0ff0f297231347417e7d700e",
  "conker/asm/nonmatchings/game_34F20/func_15007B3C.s": "fbe6f895bfe7849d87ef1a8b9a32bdffaaa0b6c64032c99c2e919cce9345e422",
  "conker/asm/nonmatchings/game_40490/func_15013000.s": "95975c7550133f3b9de582ad700587e462c46481e4ddeafe64a3de95ce63ba23",
  "conker/asm/nonmatchings/game_40490/func_150151D4.s": "321f4fdb5df7fbd1f14c000afbd27142a403fa5c306152aeccb94a73a29e3156",
  "conker/asm/nonmatchings/game_40490/func_15015354.s": "c8dc2fcab8ca0984d81c0232fd750f6d9bd2d4edb5d83b6f208cc119459dde0b",
  "conker/asm/nonmatchings/game_44C40/func_15017930.s": "63b82e0a5643cae83a97376e9e0940edb94694bccc2bb18422561598d3af69a8",
  "conker/build/conker.ld": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
  "conker/build/conker.us.elf": "7686274a83dae9636fc1230508a775d372ee739c17b3024e436c1f3d9593f442",
  "conker/build/src/game_34F20.c.o": "4893023e658b7838b524474c2f5d7740761db86863a6d78efcf099f040e0706f",
  "conker/build/src/game_40490.c.o": "f7791694bf224220587ba1c26dbfb1ccf76ea4c14b69726c1fc74cadf543b626",
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
  "conker/src/game/generated_10CD70.c": "0df14e155328a0b44b4effd24ce3126526f7e839fded181a4c85fc75e5d01457",
  "conker/src/game/generated_CDE80.c": "440ca60ba0044d20f8a8d8ad793bef664f258760e4fb3ca50e069a7ae615fa16",
  "conker/src/game_16EE20.c": "fc2cdab1d1d3952842fc82335c3599725171c5dad3fb4afd0e2ea31cc1c1b12a",
  "conker/src/game_34F20.c": "67bdf8b2ad041fbf891c8c83bf87e9b83398ac8d198dd5fec0ddd97ddc784d1b",
  "conker/src/game_40490.c": "391f4a610ab4bffe20b093de84a845e4664e909712ab0ae72dfd3335a1993e6c",
  "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
  "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
  "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
  "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
  "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
  "tools/check_game_data_layout.py": "98c6abbff94d29fc37df8021f530b50b42be0d2c5b5c65a598dd8070e7fde55c",
  "tools/experiments/alternative_source_draft_word_screen.py": "781792e48d99e2d57e8e99655275f0a9188b00d26b73d1d4a478c734ae8151a4",
  "tools/experiments/game_actor_state_tick_integration.py": "a2ffe4f27f70134c92ae1cd80911fd68229e2cb4c5768d5eb1ddf2d61e5725c1",
  "tools/experiments/game_remaining_donor_candidates.py": "15cec3a86a8b4e5954d5efbc900f5e9d047000672845896633fbe389874de0a1",
  "tools/match_progress.py": "46e1ebac2aa79aedb9a42ce5871a5d324fc6ca97978bc906aedf6664cb36abd3",
  "tools/pad_c_object.py": "d5e11a47650cbda9907672c381534ced6aac681d1f1333bac129038a685d9362",
  "tools/pad_generated_object.py": "ad513832cf991f3f04177faf8b22b1b434404d54168cd512e574e1921c349809",
  "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
  "tools/tests/game_owner_pool.py": "159b8c009af7b2d26ba5dce29f0c46ca0805cf14dbb27e5c682d107e551ca50e",
  "tools/tests/test_game_actor_burst_consumer_match.py": "c6a58dfbf711fbe5e49e9f6afb1a0e95e097319b7dcad4a1a74f13965e0736d5",
  "tools/tests/test_game_effect_owner_ray.py": "62376c5022f50db9a53b0ec8b9517a63bc9f298dff8c7a3047963ed216a0555f",
  "tools/tests/test_game_effect_position_payload.py": "b96faf372ff366565ec7967eb3148c04bbda539a76c1bd8498fc84f19ce5daf4",
  "tools/tests/test_game_projected_packet_draw.py": "e488215f4551d0ed97454e57edb43522c0df9d1ebe9b0303f42cbd236e0261d8",
  "tools/tests/test_game_row_destination_fill.py": "b79e64e36c55617f835d5fe7abadbba5d97272cd93d50055fb4167db8f8273fd"
}
BEFORE_OBJECT_SHA = 'f7791694bf224220587ba1c26dbfb1ccf76ea4c14b69726c1fc74cadf543b626'
RAW_SHA256 = '4d921e66bdd092a1bfbc47af6da888b536257c0615590cff3ec482a8349b8e2c'
BINDINGS = {32: [('R_MIPS_HI16', 'D_800DCDC4')], 40: [('R_MIPS_LO16', 'D_800DCDC4')], 44: [('R_MIPS_HI16', 'D_800DCD90')], 56: [('R_MIPS_LO16', 'D_800DCD90')], 24: [('R_MIPS_HI16', 'D_800D3094')], 28: [('R_MIPS_LO16', 'D_800D3094')], 60: [('R_MIPS_HI16', 'D_80082E30')], 72: [('R_MIPS_LO16', 'D_80082E30')], 64: [('R_MIPS_HI16', 'D_800D3098')], 68: [('R_MIPS_LO16', 'D_800D3098')], 128: [('R_MIPS_HI16', 'D_800D3094')], 132: [('R_MIPS_LO16', 'D_800D3094')]}
OLD_INCLUDE = '#include "variables.h"'
NEW_INCLUDE = '/* This owner reads the retail base-pointer word at D_800D3098. */\n#define D_800D3098 D_800D3098_legacy_array\n#include "variables.h"\n#undef D_800D3098\n\ntypedef struct {\n    u8 reserved[0x15];\n    u8 kindFlags;\n    u8 tail[0x1E];\n} DispatchRecord40490;\ntypedef s32 (*RecordCallback40490)(DispatchRecord40490 *);\nextern DispatchRecord40490 *D_800D3098;\nextern RecordCallback40490 D_80082E30[];'
OLD_BODY = '/* Non-matching C placeholders for asm/nonmatchings/game_40490/func_15013000.s. */\ns32 func_15013000() {\n    return 0;\n}'
NEW_BODY = "/* Reset both accumulators and dispatch each record's type callback. */\nvoid func_15013000(void) {\n    u8 kindFlags;\n    u32 index;\n    RecordCallback40490 callback;\n\n    D_800DCDC4 = 0;\n    D_800DCD90 = 0.0f;\n    for (index = 0; index < (u32)D_800D3094; index++) {\n        kindFlags = D_800D3098[index].kindFlags;\n        callback = D_80082E30[(u8)(kindFlags >> 2)];\n        if (callback != NULL) {\n            callback(&D_800D3098[index]);\n        }\n    }\n}"
SELECTED = NEW_BODY
TYPES = NEW_INCLUDE.split("#undef D_800D3098\n",1)[1]
DECLARATIONS = "extern s32 D_800D3094, D_800DCDC4;\nextern f32 D_800DCD90;\n"



def checked_payload(raw, bindings):
    if len(raw)!=SIZE or digest(raw)!=RAW_SHA256 or bindings!=BINDINGS:
        raise ValueError('Record callback loop raw words/bindings changed')

def recovered_owner(before):
    for value in (OLD_INCLUDE, OLD_BODY, 's32 func_15013000();'):
        if before.count(value)!=1:raise ValueError('Record loop predecessor anchor changed')
    return before.replace(OLD_INCLUDE,NEW_INCLUDE).replace(OLD_BODY,NEW_BODY).replace(
        's32 func_15013000();','void func_15013000(void);')

def normalized_payload(raw, bindings):
    checked_payload(raw,bindings)
    words=list(struct.unpack('>45I',raw))
    normalized=list(words); result=dict(bindings)
    schedule=(9,8,10,11,14,6,7,12,19,13,15,16,17,18)
    assert sorted(schedule)==list(range(6,20))
    for dest,src in enumerate(schedule,6):
        word=words[src]
        if src==13:
            if word>>26!=4 or src+1+(word&65535)!=38:
                raise ValueError('Record loop exit branch changed')
            word=(word&0xFFFF0000)|((38-dest-1)&65535)
        normalized[dest]=word
        result.pop(dest*4,None)
        if src*4 in bindings:result[dest*4]=bindings[src*4]
    return struct.pack('>45I',*normalized),result

def guard_bytes(before, obj):
    raw,bindings=payload(obj)
    normalized,rebound=normalized_payload(raw,bindings)
    old=list(csv.DictReader(io.StringIO(before.decode())))
    if any(row['function']==FUNCTION for row in old):raise ValueError('Existing record loop guards')
    fields=next(csv.reader(io.StringIO(before.decode())))
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    fmt=lambda values:';'.join(kind+':'+symbol for kind,symbol in values) or '-'
    for at in range(0x18,0x50,4):
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset=hex(at),
          expected='0x%08X'%struct.unpack_from('>I',raw,at)[0],
          replacement='0x%08X'%struct.unpack_from('>I',normalized,at)[0],
          expected_relocations=fmt(bindings.get(at,[])),replacement_relocations=fmt(rebound.get(at,[])),
          note='Normalize closed record-dispatch opening schedule and exit-branch displacement',
          insert_after='',insert_after_relocations='',omit='false'))
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line ending')
    return before+stream.getvalue().encode()

def original(root,output):
    assembly=(root/ASM).read_text().replace('glabel '+FUNCTION,
        '.globl '+FUNCTION+'\n.type '+FUNCTION+', @function\n'+FUNCTION+':').replace(
        'endlabel '+FUNCTION,'.size '+FUNCTION+', . - '+FUNCTION)
    path=output/'original-target.s';obj=path.with_suffix('.o')
    path.write_text('.set noreorder\n.set noat\n.set mips3\n.text\n'+assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(path)],check=True,capture_output=True)
    return obj

def qualify(root,output):
    values=freeze(root,output)
    wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    isolated,dc=compile_owner(root,output,'#include <ultra64.h>\n'+DECLARATIONS+TYPES+SELECTED,'selected')
    if diagnostics(da)!=diagnostics(db) or dc:raise ValueError('Record loop diagnostics changed: '+da+db+dc)
    raw,bindings=payload(after);checked_payload(raw,bindings)
    if payload(isolated)!=(raw,bindings):raise ValueError('Record loop isolated/owner mismatch')
    normalized,rebound=normalized_payload(raw,bindings)
    if payload(original(root,output))!=(normalized,rebound):raise ValueError('Original GNU code differs from derived schedule')
    truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=31 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Raw record-loop neighbors/pools changed')
    guards=guard_bytes(values['conker/retail_word_patches.us.csv'],after)
    guard_path=output/'proposed-word-patches.csv';guard_path.write_bytes(guards)
    padded=output/'qualified-padded.s'
    padded.write_text(ordinary_padder.emit_padded_assembly(after,root/'conker/retail_layout.us.txt',OWNER,word_patches_path=guard_path))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],check=True,capture_output=True)
    old=output/'before-padded.o'
    a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={name:dict(info)for name,info in fa.items()}
    if expected[FUNCTION]['size']!=12:raise ValueError('Record loop predecessor extent changed')
    expected[FUNCTION]['size']=SIZE;at=fb[FUNCTION]['value']
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:raise ValueError('Record loop baseline object/ELF mismatch')
    if b[at:at+SIZE]!=truth or expected!=fb or a[:at]!=b[:at] or a[at+SIZE:]!=b[at+SIZE:]:
        raise ValueError('Record loop padded owner changed another body/address/extent')
    if same_functions(old,obj,(FUNCTION,))!=neighbors or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('Padded record-loop neighbors/pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(words=45,frame=40,raw_differences=14,differences=0,relocations=12,new_guards=14,
        slot_words=45,alignment_words=0,preserved_neighbors=31,owner_diagnostics_unchanged=True,
        isolated_diagnostics_empty=True,closed_opening_permutation=True,exit_branch_target_preserved=True,
        raw_SHA256=digest(raw),all_owner_addresses_fixed=True,target_size_before=12,target_size_after=180)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def diagnostics(text):
    return re.sub(r'line\s+\d+', 'line #', re.sub(r'\S+\.c', '<unit>', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Record callback loop historical input changed: ' + name)
        values[name] = data
    return values


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    old = output / 'before-padded.o'
    data = (root / OBJECT).read_bytes() if not old.exists() else old.read_bytes()
    if digest(data) != BEFORE_OBJECT_SHA:
        raise ValueError('Record loop padded predecessor changed')
    if not old.exists():
        old.write_bytes(data)
    for name, wanted in INPUTS.items():
        data = (root / name).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Record callback loop predecessor changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Record callback loop snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
    return snapshot(output)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    raw = text[info['value']:info['value'] + info['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero record callback loop alignment tail')
    relative = {at - info['value']: rows for at, rows in bindings.items()
                if info['value'] <= at < info['value'] + end * 4}
    return raw[:end * 4], relative


def make_shadow(root, output):
    values = freeze(root, output)
    if (output / 'proposed-owner.c').read_text() != recovered_owner(values[SOURCE].decode()):
        raise ValueError('Record callback loop shadow source changed')
    conker, shadow = root / 'conker', output / 'make-shadow'
    (shadow / 'src').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game_40490.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target],
        cwd=conker, capture_output=True, text=True, check=True)
    (output / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected record callback loop Make command: ' + repr(args))
        args = [(output / 'proposed-owner.c').relative_to(conker).as_posix()
                if a == 'src/game_40490.c' else a for a in args]
        args = [(output / 'proposed-word-patches.csv').relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record callback loop Make redirect')
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        process = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        expected_diagnostics = (output / 'after-owner-diagnostics.txt').read_text() if args[0] == '../ido/ido5.3_recomp/cc' else ''
        if process.returncode or diagnostics(process.stderr + (process.stdout if redirect is None else '')) != diagnostics(expected_diagnostics):
            raise ValueError('Record callback loop Make command failed: ' + process.stdout + process.stderr)
        if redirect is not None:
            redirect.write_text(process.stdout)
        commands.append(args)
    actual = conker / target
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    if len(compilers) != 1 or not all(flag in compilers[0] for flag in ('-O2', '-g3')) or any('-loopunroll' in flag for flag in compilers[0]):
        raise ValueError('Record callback loop Make changed the normal compiler profile')
    if len(commands) != 5 or same_functions(output / 'after-owner.o', Path(str(actual) + '.compact')) != len(parse_object(output / 'after-owner.o')[1]):
        raise ValueError('Record callback loop actual Make profile differs')
    if link_owner(root, output, actual, OWNER) != link_owner(root, output, output / 'qualified-padded.o', OWNER):
        raise ValueError('Record callback loop actual Make padding/metadata differs')
    report = dict(actual_Make_commands=5, normal_O2_g3=True, all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True, cleanup_skipped=True, inherited_Make_warnings=plan.stderr)
    (output / 'make-shadow.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Record callback loop strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
            if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Record callback loop symbol extent predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)


def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Record callback loop image differs from strict body/size prediction')


def predict(root, output):
    values = freeze(root, output)
    script = (root / 'conker/build/conker.ld').read_text()
    old = 'build/src/game_40490.c.o'
    if script.count(old) != 1:
        raise ValueError('Unknown record callback loop link input')
    # ld synthesizes the local FILE group from this basename. Match the real
    # production object name so an independent link preserves all metadata.
    link_object = output / 'link-input' / Path(OBJECT).name
    link_object.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output / 'qualified-padded.o', link_object)
    link = output / 'first-link.ld'
    link.write_text(script.replace(old, link_object.relative_to(root / 'conker').as_posix()))
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
        expected = (guard_bytes(old, output / 'after-owner.o') if name == 'conker/retail_word_patches.us.csv' else
                    recovered_owner(old.decode()).encode() if name == SOURCE else
                    (output / 'qualified-padded.o').read_bytes() if name == OBJECT else
                    wanted if name == 'conker/build/conker.us.elf' else old)
        if (root / name).read_bytes() != expected:
            raise ValueError('Record callback loop installed input differs: ' + name)
    return values, wanted


def audit(root, output):
    values, wanted = audit_inputs(root, output)
    if (output / 'first-linked.elf').read_bytes() != wanted:
        raise ValueError('Record callback loop independent first image changed')
    a, _, aa = load_elf_functions(str(output / 'before-conker_build_conker.us.elf'), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Record callback loop changed another body/address')
    data = audit_layout(root / 'conker/build/conker.us.elf', root / 'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Record callback loop protected Game data changed')
    report = dict(functions=len(b), other_bodies_fixed=len(b) - 1, all_addresses_fixed=True,
        target_words=45, strict_first_link_reproduced=True, game_data=data)
    (output / 'installed-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
