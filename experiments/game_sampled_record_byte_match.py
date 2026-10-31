"""Sampled record byte: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as pad
sys.modules.setdefault("pad_generated_object",pad)
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151638E0','game_18D770'
ENTRY,ROM,BODY,SIZE=(353777888, 1641872, 240, 240)
SOURCE='conker/src/game_18D770.c'
OBJECT='conker/build/src/game_18D770.c.o'
ASM='conker/asm/nonmatchings/game_18D770/func_151638E0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-sampled-record-byte-151638E0-match'
RODATA_SYMBOL=None
RAW_SHA='bd6fe0582a1fa493a8ac3865611150cb9b04c86e93e9c3a4e70fe905f4e82294'
SNAPSHOT_SHA='e25112f37e3fef05261cde8dfe23e58ab0c4c2ab64c9072ae44990d5f890747b'
BEFORE_ELF_SHA='3da616798cc1b28cd7dc490d7a7d8cafdca9d52355072db68267f42b0c4dd6ec'
TRUTH_SHA='93716fec9a76db7df4da32bc363e514589609b7f3a40574c476f60b46b790b6d'
BINDINGS={20: [('R_MIPS_26', 'func_15187FC0')], 44: [('R_MIPS_26', 'func_15188010')]}
ORIGINAL_BINDINGS={20: [('R_MIPS_26', 'func_15187FC0')], 44: [('R_MIPS_26', 'func_15188010')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nvoid func_15187FC0(s32 index, u32 *vector);\nvoid func_15188010(s32 index, f32 *value);\ntypedef struct {\n    s32 index;\n    f32 base;\n    f32 scale;\n} GameScalarSample;\n'
DECLARATIONS='void func_15187FC0(s32 index, u32 *vector);\nvoid func_15188010(s32 index, f32 *value);\ntypedef struct {\n    s32 index;\n    f32 base;\n    f32 scale;\n} GameScalarSample;\n'
SELECTED='/* Sample the live scalar record and publish its affine byte value. */\ns32 func_151638E0(struct225 *state) {\n    GameScalarSample *record;\n    u32 vector[3];\n    /* The scalar getter writes this slot only for a valid index. */\n    f32 factor;\n    record = (GameScalarSample *)&state->unk18;\n    func_15187FC0(record->index, vector);\n    func_15188010(record->index, &factor);\n    state->unk14->unk2F = (u8)(record->base + record->scale * factor);\n    return 1;\n}\n'

def check_owner_diagnostics(text):
 normalize=lambda value:re.sub(r'build/[^,\n]+, line ','<owner>, line ',value)
 if normalize(text)not in DIAGNOSTIC_BASELINES or text.count('cfe: Warning')!=48:raise ValueError('Changed inherited sampled record diagnostics')
 return 48





sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=240 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Sampled record byte body/bindings changed')
 return raw,bindings


def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_151638E0() {\n    return 0;\n}':raise ValueError('Sampled record placeholder changed')
 if before.count('s32 func_151638E0();')!=1 or before.count(RETIRED_COMMENT)!=1:raise ValueError('Sampled record declaration/comment changed')
 after=before[:a]+DECLARATIONS+'\n'+SELECTED.rstrip()+before[b:]
 return after.replace(RETIRED_COMMENT,'',1).replace('s32 func_151638E0();','s32 func_151638E0(struct225 *state);')









def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Sampled record byte snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Sampled record byte frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Sampled record byte predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Sampled record byte live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Sampled record byte named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Sampled record byte symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Sampled record byte metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Sampled record byte frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Sampled record byte original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Sampled record byte strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Sampled record byte named definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited sampled record byte guards changed')
 return before



def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Direct sampled record byte scope changed')
 return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151638E0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_18D770.c.o', 'make-shadow/src/game_18D770.c.o.compact', 'make-shadow/src/game_18D770.c.o.padded.s', 'retired-commented-draft.txt', 'original-sampling-helpers.bin', 'original-sampling-dispatcher.bin')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Sampled record byte artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Sampled record byte artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Sampled record byte raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Sampled record byte evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Sampled record byte Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_18D770.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Sampled record byte Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Sampled record byte private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Sampled record byte changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sampled record byte protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=60,reachable_words=59,frame=48,alignment_words=0,slot_words=60,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='3f87620dde0c8ab48350b406c8d184af4cde1d57c617d916770b42d1ea501fca'

NORMALIZED_SHA='bd6fe0582a1fa493a8ac3865611150cb9b04c86e93e9c3a4e70fe905f4e82294'


def schedule_proof(raw,bindings,truth,retail_bindings):
 checked_payload(raw,bindings)
 if(raw,bindings)!=(truth,retail_bindings):raise ValueError('Direct sampled record body/bindings changed')
 return dict(direct_C_match=True,words=60,bindings=2,complete_body_and_relocations_identical=True,guards=0)


RETIRED_COMMENT='// NON-MATCHING: struct isnt quite right..\n// s32 func_151638E0(struct225 *arg0) {\n//     struct227 *temp_v1;\n//     f32 sp20[3];\n//     f32 sp1C;\n//\n//     temp_v1 = &arg0->unk18;\n//     func_15187FC0(arg0->unk18, &sp20); // missing a lw here\n//     func_15188010(temp_v1, &sp1C);\n//     arg0->unk14->unk2F = (temp_v1->unk4 + (temp_v1->unk8 * sp1C));\n//     return 1;\n// }\n\n'

DIAGNOSTIC_BASELINES=('cfe: Warning 712: <owner>, line 92: illegal combination of pointer and integer\n     sp30 = func_1515D5F8(header2->unk0, header2->unk4, header2->unk8, arg2, arg3, arg4, arg5, arg6, arg7, 0);\n ---------^\ncfe: Warning 712: <owner>, line 105: illegal combination of pointer and integer\n     struct225 *ret = func_15167A68(53, arg4, offset + 24, 1, arg3, 1);\n ---------------^\ncfe: Warning 709: <owner>, line 128: Incompatible pointer type assignment\n         func_1516972C(arg0);\n ----------------------^\ncfe: Warning 712: <owner>, line 135: illegal combination of pointer and integer\n     arg0->unk14->unk2F = func_151422DC(0, &D_800A6690, 0, 0xFF, 0xFF, &D_800A6698, 575);\n ------------------------------------------^\ncfe: Warning 712: <owner>, line 135: illegal combination of pointer and integer\n     arg0->unk14->unk2F = func_151422DC(0, &D_800A6690, 0, 0xFF, 0xFF, &D_800A6698, 575);\n ----------------------------------------------------------------------^\ncfe: Warning 709: <owner>, line 140: Incompatible pointer type assignment\n     func_15163CF8(&arg0->unk18, arg0);\n ------------------^\ncfe: Warning 709: <owner>, line 145: Incompatible pointer type assignment\n     func_15163DEC(arg0, &arg0->unk18);\n ------------------------^\ncfe: Warning 709: <owner>, line 180: Incompatible pointer type assignment\n     struct227 *temp_a1 = &arg0->unk18;\n ---------------^\ncfe: Warning 712: <owner>, line 216: illegal combination of pointer and integer\n         func_151618BC(25000, 0, 0, 0, &tmp, 500, 1500);\n --------------------------------------^\ncfe: Warning 712: <owner>, line 310: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 337: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp1), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 356: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 379: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 401: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 434: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp1), arg4, arg5);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 447: illegal combination of pointer and integer\n     func_1516944C(53, &tmp, arg1);\n ----------------------^\ncfe: Warning 709: <owner>, line 471: Incompatible pointer type assignment\n     func_15169804(arg0);\n ------------------^\ncfe: Warning 709: <owner>, line 475: Incompatible pointer type assignment\n     func_15169824(arg0);\n ------------------^\ncfe: Warning 712: <owner>, line 624: illegal combination of pointer and integer\n     tmp.unk0 = arg0;\n -------------^\ncfe: Warning 709: <owner>, line 640: Incompatible pointer type assignment\n     func_15163F50(arg0, &arg0->unk18);\n ------------------------^\ncfe: Warning 712: <owner>, line 689: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg1, arg2);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 709: Incompatible pointer type assignment\n     temp_v0 = func_15149130(300, -1, 30, -1, 0, 0, sizeof(src), 0xFF, 1);\n ------------^\ncfe: Warning 712: <owner>, line 709: illegal combination of pointer and integer\n     temp_v0 = func_15149130(300, -1, 30, -1, 0, 0, sizeof(src), 0xFF, 1);\n ---------------------------------------------------^\ncfe: Warning 712: <owner>, line 789: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg6, arg7);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 812: illegal combination of pointer and integer\n     temp_v0 = func_151602C0(header, arg1, 0, arg2, arg3, arg4, arg5, arg6, offset + sizeof(src), arg9, argA);\n ------------------------------------^\ncfe: Warning 712: <owner>, line 894: illegal combination of pointer and integer\n     temp_v0 = func_151149AC(arg0->unk48);\n ------------^\ncfe: Warning 712: <owner>, line 899: illegal combination of pointer and integer\n     func_151403A8(&sp1C, 36);\n ------------------^\ncfe: Warning 712: <owner>, line 906: illegal combination of pointer and integer\n     temp_v0 = func_151149AC(arg0->unk48);\n ------------^\ncfe: Warning 712: <owner>, line 911: illegal combination of pointer and integer\n     func_151403A8(&sp1C, 37);\n ------------------^\ncfe: Warning 712: <owner>, line 942: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg6, arg7);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 959: illegal combination of pointer and integer\n     data.unk0 = arg1;\n --------------^\ncfe: Warning 712: <owner>, line 960: illegal combination of pointer and integer\n     data.unk4 = arg2;\n --------------^\ncfe: Warning 712: <owner>, line 961: illegal combination of pointer and integer\n     data.unk8 = arg3;\n --------------^\ncfe: Warning 712: <owner>, line 1015: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg6, arg7);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 1027: Incompatible pointer type assignment\n     temp_v0 = &arg0->unk18;\n ------------^\ncfe: Warning 712: <owner>, line 1046: illegal combination of pointer and integer\n     func_1516037C(&tmp, arg0, 0, arg2, arg3);\n ------------------------^\ncfe: Warning 712: <owner>, line 1056: illegal combination of pointer and integer\n     func_1516037C(&tmp, arg0, offset, arg6, arg7);\n ------------------------^\ncfe: Warning 712: <owner>, line 1098: illegal combination of pointer and integer\n     temp_v0 = func_151149AC(arg0);  \n ------------^\ncfe: Warning 709: <owner>, line 1126: Incompatible pointer type assignment\n     if (func_1516065C(arg0) == 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 1147: illegal combination of pointer and integer\n     temp_v0 = func_15160A58(arg0, 1, &D_800A6A0C, 2, 300, 100, 0, 0xFF, 0, 0xFF, 0, 0, sizeof(src), 1, arg1, arg2);\n ------------^\ncfe: Warning 712: <owner>, line 1147: illegal combination of pointer and integer\n     temp_v0 = func_15160A58(arg0, 1, &D_800A6A0C, 2, 300, 100, 0, 0xFF, 0, 0xFF, 0, 0, sizeof(src), 1, arg1, arg2);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 1155: Incompatible pointer type assignment\n     func_15163CF8(&arg0->unk30, arg0);\n ------------------^\ncfe: Warning 709: <owner>, line 1221: Incompatible pointer type assignment\n             func_1516972C(arg0);\n --------------------------^\ncfe: Warning 712: <owner>, line 1242: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg2, arg3);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 1269: Incompatible pointer type assignment\n     tmp = &arg0->unk18;\n --------^\ncfe: Warning 712: <owner>, line 1298: illegal combination of pointer and integer\n     temp_v0 = arg0->unk20;\n ------------^\ncfe: Warning 709: <owner>, line 1300: Incompatible pointer type assignment\n     func_151644F4(arg0, &arg0->unk24, arg0->unk18, temp_v0->unk0 * temp_f0, temp_v0->unk8 * temp_f0);\n ------------------------^\ncfe: Warning 712: <owner>, line 1300: illegal combination of pointer and integer\n     func_151644F4(arg0, &arg0->unk24, arg0->unk18, temp_v0->unk0 * temp_f0, temp_v0->unk8 * temp_f0);\n ------------------------------------------^\n', 'cfe: Warning 712: <owner>, line 92: illegal combination of pointer and integer\n     sp30 = func_1515D5F8(header2->unk0, header2->unk4, header2->unk8, arg2, arg3, arg4, arg5, arg6, arg7, 0);\n ---------^\ncfe: Warning 712: <owner>, line 105: illegal combination of pointer and integer\n     struct225 *ret = func_15167A68(53, arg4, offset + 24, 1, arg3, 1);\n ---------------^\ncfe: Warning 709: <owner>, line 128: Incompatible pointer type assignment\n         func_1516972C(arg0);\n ----------------------^\ncfe: Warning 712: <owner>, line 135: illegal combination of pointer and integer\n     arg0->unk14->unk2F = func_151422DC(0, &D_800A6690, 0, 0xFF, 0xFF, &D_800A6698, 575);\n ------------------------------------------^\ncfe: Warning 712: <owner>, line 135: illegal combination of pointer and integer\n     arg0->unk14->unk2F = func_151422DC(0, &D_800A6690, 0, 0xFF, 0xFF, &D_800A6698, 575);\n ----------------------------------------------------------------------^\ncfe: Warning 709: <owner>, line 140: Incompatible pointer type assignment\n     func_15163CF8(&arg0->unk18, arg0);\n ------------------^\ncfe: Warning 709: <owner>, line 145: Incompatible pointer type assignment\n     func_15163DEC(arg0, &arg0->unk18);\n ------------------------^\ncfe: Warning 709: <owner>, line 180: Incompatible pointer type assignment\n     struct227 *temp_a1 = &arg0->unk18;\n ---------------^\ncfe: Warning 712: <owner>, line 216: illegal combination of pointer and integer\n         func_151618BC(25000, 0, 0, 0, &tmp, 500, 1500);\n --------------------------------------^\ncfe: Warning 712: <owner>, line 310: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 337: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp1), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 356: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 379: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 401: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp), arg1, arg2);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 434: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(tmp1), arg4, arg5);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 447: illegal combination of pointer and integer\n     func_1516944C(53, &tmp, arg1);\n ----------------------^\ncfe: Warning 709: <owner>, line 471: Incompatible pointer type assignment\n     func_15169804(arg0);\n ------------------^\ncfe: Warning 709: <owner>, line 475: Incompatible pointer type assignment\n     func_15169824(arg0);\n ------------------^\ncfe: Warning 712: <owner>, line 624: illegal combination of pointer and integer\n     tmp.unk0 = arg0;\n -------------^\ncfe: Warning 709: <owner>, line 640: Incompatible pointer type assignment\n     func_15163F50(arg0, &arg0->unk18);\n ------------------------^\ncfe: Warning 712: <owner>, line 689: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg1, arg2);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 709: Incompatible pointer type assignment\n     temp_v0 = func_15149130(300, -1, 30, -1, 0, 0, sizeof(src), 0xFF, 1);\n ------------^\ncfe: Warning 712: <owner>, line 709: illegal combination of pointer and integer\n     temp_v0 = func_15149130(300, -1, 30, -1, 0, 0, sizeof(src), 0xFF, 1);\n ---------------------------------------------------^\ncfe: Warning 712: <owner>, line 789: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg6, arg7);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 812: illegal combination of pointer and integer\n     temp_v0 = func_151602C0(header, arg1, 0, arg2, arg3, arg4, arg5, arg6, offset + sizeof(src), arg9, argA);\n ------------------------------------^\ncfe: Warning 712: <owner>, line 894: illegal combination of pointer and integer\n     temp_v0 = func_151149AC(arg0->unk48);\n ------------^\ncfe: Warning 712: <owner>, line 899: illegal combination of pointer and integer\n     func_151403A8(&sp1C, 36);\n ------------------^\ncfe: Warning 712: <owner>, line 906: illegal combination of pointer and integer\n     temp_v0 = func_151149AC(arg0->unk48);\n ------------^\ncfe: Warning 712: <owner>, line 911: illegal combination of pointer and integer\n     func_151403A8(&sp1C, 37);\n ------------------^\ncfe: Warning 712: <owner>, line 942: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg6, arg7);\n -------------------------------------^\ncfe: Warning 712: <owner>, line 959: illegal combination of pointer and integer\n     data.unk0 = arg1;\n --------------^\ncfe: Warning 712: <owner>, line 960: illegal combination of pointer and integer\n     data.unk4 = arg2;\n --------------^\ncfe: Warning 712: <owner>, line 961: illegal combination of pointer and integer\n     data.unk8 = arg3;\n --------------^\ncfe: Warning 712: <owner>, line 1015: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg6, arg7);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 1027: Incompatible pointer type assignment\n     temp_v0 = &arg0->unk18;\n ------------^\ncfe: Warning 712: <owner>, line 1046: illegal combination of pointer and integer\n     func_1516037C(&tmp, arg0, 0, arg2, arg3);\n ------------------------^\ncfe: Warning 712: <owner>, line 1056: illegal combination of pointer and integer\n     func_1516037C(&tmp, arg0, offset, arg6, arg7);\n ------------------------^\ncfe: Warning 712: <owner>, line 1102: illegal combination of pointer and integer\n     temp_v0 = func_151149AC(arg0);  \n ------------^\ncfe: Warning 709: <owner>, line 1130: Incompatible pointer type assignment\n     if (func_1516065C(arg0) == 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 1151: illegal combination of pointer and integer\n     temp_v0 = func_15160A58(arg0, 1, &D_800A6A0C, 2, 300, 100, 0, 0xFF, 0, 0xFF, 0, 0, sizeof(src), 1, arg1, arg2);\n ------------^\ncfe: Warning 712: <owner>, line 1151: illegal combination of pointer and integer\n     temp_v0 = func_15160A58(arg0, 1, &D_800A6A0C, 2, 300, 100, 0, 0xFF, 0, 0xFF, 0, 0, sizeof(src), 1, arg1, arg2);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 1159: Incompatible pointer type assignment\n     func_15163CF8(&arg0->unk30, arg0);\n ------------------^\ncfe: Warning 709: <owner>, line 1225: Incompatible pointer type assignment\n             func_1516972C(arg0);\n --------------------------^\ncfe: Warning 712: <owner>, line 1246: illegal combination of pointer and integer\n     temp_v0 = func_1516037C(&header, arg0, sizeof(src), arg2, arg3);\n -------------------------------------^\ncfe: Warning 709: <owner>, line 1273: Incompatible pointer type assignment\n     tmp = &arg0->unk18;\n --------^\ncfe: Warning 712: <owner>, line 1302: illegal combination of pointer and integer\n     temp_v0 = arg0->unk20;\n ------------^\ncfe: Warning 709: <owner>, line 1304: Incompatible pointer type assignment\n     func_151644F4(arg0, &arg0->unk24, arg0->unk18, temp_v0->unk0 * temp_f0, temp_v0->unk8 * temp_f0);\n ------------------------^\ncfe: Warning 712: <owner>, line 1304: illegal combination of pointer and integer\n     func_151644F4(arg0, &arg0->unk24, arg0->unk18, temp_v0->unk0 * temp_f0, temp_v0->unk8 * temp_f0);\n ------------------------------------------^\n')
