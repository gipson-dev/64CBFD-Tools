"""Spawn result query: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1507E114','game_A9D90'
ENTRY,ROM,BODY,SIZE=0x1507E114,0xAB5C4,188,188
SOURCE='conker/src/game_A9D90.c'
OBJECT='conker/build/src/game_A9D90.c.o'
ASM='conker/asm/nonmatchings/game_A9D90/func_1507E114.s'
BUILD='conker/build/game-spawn-result-query-match'
RAW_SHA="0264fcb9ae20f2749c514b1f8e1818b3f8e43249939a7b60c83c4162cc3a5bdf"
SNAPSHOT_SHA="0e8c8682e832c0242a7bb711c2a77ed41e9da6ad756bc98c6eaff86b9f2de6ed"
BEFORE_ELF_SHA="dbe02a2e46395ef932bc7f16f3e5edbd4d70796f073678c41766e786de4dbd3e"
TRUTH_SHA="10be07c009c75c8f2852d94b63427d6462536a51877f06a8555af12302cc6262"
HELPER=0x15084D70
GLOBALS=(0x800D18A8,0x800BE9F4,0x800BE3DF,0x800BE3E0)
BINDINGS={12:[("R_MIPS_HI16","D_800D18A8")],16:[("R_MIPS_LO16","D_800D18A8")],20:[("R_MIPS_HI16","D_800BE9F4")],24:[("R_MIPS_LO16","D_800BE9F4")],64:[("R_MIPS_HI16","D_800BE3DF")],76:[("R_MIPS_LO16","D_800BE3DF")],80:[("R_MIPS_HI16","D_800BE3E0")],116:[("R_MIPS_LO16","D_800BE3E0")],156:[("R_MIPS_26","func_15084D70")]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="#include \"variables.h\"\n\ns32 func_15084D70(s32, s32, s32, s16 *, f32 *, u8 *, u8 *, s32 *, s32 *, s32, s32 *);\n\n"
SELECTED="/* Query the pending spawn result while preserving the legacy context word and signed byte. */\ns32 func_1507E114(s32 *unusedSelection) {\n    s32 result;\n    s16 position[3];\n    f32 rotation[3];\n    s32 flags;\n    u8 firstByte;\n    u8 secondByte;\n    s32 signedTag;\n\n    if (!D_800D18A8) {\n        return 0;\n    }\n    if (((s32)D_800BE9F4 == 0x22) || ((s32)D_800BE9F4 == 0x18)) {\n        return 0;\n    }\n    D_800BE9F4 = (u16 *)(s32)(s8)D_800BE3DF;\n    func_15084D70(0, D_800BE3E0, 1, position, rotation, &firstByte, &secondByte,\n                  &flags, &signedTag, 1, &result);\n    return result + 1;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Spawn result query body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1507E114() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Spawn query placeholder changed')
    return before.replace('s32 func_1507E114();','s32 func_1507E114(s32 *unusedSelection);').replace('/* Non-matching C placeholders for asm/nonmatchings/game_A9D90/func_1507E114.s. */\n'+stub,DECLARATIONS+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Spawn result query snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Spawn result query frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Spawn result query predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Spawn result query live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Spawn result query strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Spawn result query original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Spawn result query image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Spawn result query named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1507E114.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game_A9D90.c","make-shadow/src/game_A9D90.c.o","make-shadow/src/game_A9D90.c.o.compact","make-shadow/src/game_A9D90.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Spawn result query artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Spawn result query artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Spawn result query raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Spawn result query evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Spawn result query Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Spawn result query expected empty diagnostics')
    if(output/'make-shadow/src/game_A9D90.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Spawn result query Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Spawn result query private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Spawn result query changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Spawn result query protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
