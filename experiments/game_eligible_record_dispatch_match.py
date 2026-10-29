"""Live record dispatch: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150A278C','generated_CDE80'
ENTRY,ROM,BODY,SIZE=0x150A278C,0xCFC3C,216,216
SOURCE='conker/src/game/generated_CDE80.c'
OBJECT='conker/build/src/game/generated_CDE80.c.o'
ASM='conker/asm/CDE80.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-live-record-dispatch-match'
RODATA_SYMBOL=None
RAW_SHA='d7f500c16bc21c9402789aecd09950fc767a71c614db71e8d0e2ec1523e0af2b'
SNAPSHOT_SHA='a0c11938669e6a3c3e5b72be8c06c5fe6d1da459f9ff532fb6a48a3768328098'
BEFORE_ELF_SHA='163ff1c51c13f9359553ac92186bdbc7c98dc4ec89dcf7123169c4cc25b11ee0'
TRUTH_SHA='13caa29706215ec25f2759c5b39ba02efdd87ee1816033eae0267f7516b24efe'
BINDINGS={40: [('R_MIPS_HI16', 'D_800D3094')], 44: [('R_MIPS_LO16', 'D_800D3094')], 76: [('R_MIPS_HI16', 'D_800D3098')], 80: [('R_MIPS_LO16', 'D_800D3098')], 116: [('R_MIPS_26', 'func_150A1DA0')], 148: [('R_MIPS_26', 'func_15172E7C')]}
ORIGINAL_BINDINGS={40: [('R_MIPS_HI16', 'D_800D3094')], 44: [('R_MIPS_LO16', 'D_800D3094')], 76: [('R_MIPS_HI16', 'D_800D3098')], 80: [('R_MIPS_LO16', 'D_800D3098')], 116: [('R_MIPS_26', 'func_150A1DA0')], 148: [('R_MIPS_26', 'func_15172E7C')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct {\n    s16 origin0;\n    s16 origin1;\n    s16 origin2;\n    u8 pad6[0xF];\n    u8 flags;\n    u8 pad16;\n    u8 field17;\n    s32 field18;\n    s32 field1C;\n    s32 field20;\n    f32 coefficient0;\n    f32 scale;\n    f32 coefficient1;\n    f32 coefficient2;\n} GeneratedCDE80Record;\n\nextern GeneratedCDE80Record *D_800D3098;\nextern s32 D_800D3094;\ns32 func_150A1DA0(struct127 *, s32, s32);\ns32 func_15172E7C(struct127 *, u8, s32);\n\n'
DECLARATIONS='s32 func_15172E7C(struct127 *, u8, s32);\n\n'
SELECTED='/* Dispatch eligible records using the live table and count after each helper. */\nvoid func_150A278C(struct127 *actor) {\n    u32 index;\n\n    if (((u8 *)actor)[0x65] == 0) {\n        for (index = 0; index < (u32)D_800D3094; index++) {\n            if ((D_800D3098[index].flags >> 2) == 8 &&\n                func_150A1DA0(actor, (s32)&D_800D3098[index], 0) == 0) {\n                func_15172E7C(actor, D_800D3098[index].field17,\n                             D_800D3098[index].field18);\n            }\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Live record dispatch owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('State-completion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150A278C() {\n    return 0;\n}':raise ValueError('Live record dispatch placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Live record dispatch snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Live record dispatch frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Live record dispatch predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Live record dispatch live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Live record dispatch named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Live record dispatch symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Live record dispatch metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Live record dispatch frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Live record dispatch original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Live record dispatch strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Live record dispatch named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150A278C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_CDE80.c.o', 'make-shadow/src/game/generated_CDE80.c.o.compact', 'make-shadow/src/game/generated_CDE80.c.o.padded.s', 'make-shadow/src/game/generated_CDE80.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Live record dispatch artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Live record dispatch artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Live record dispatch raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Live record dispatch evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Live record dispatch Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_CDE80.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Live record dispatch Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Live record dispatch private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Live record dispatch changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Live record dispatch protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=48,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
