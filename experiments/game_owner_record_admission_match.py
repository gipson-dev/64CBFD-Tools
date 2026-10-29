"""Owner record admission: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151ACA60','generated_1D92F0'
ENTRY,ROM,BODY,SIZE=0x151ACA60,0x1D9F10,216,216
SOURCE='conker/src/game/generated_1D92F0.c'
OBJECT='conker/build/src/game/generated_1D92F0.c.o'
ASM='conker/asm/1D92F0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-record-admission-match'
RODATA_SYMBOL=None
RAW_SHA='015089b6a9a3e1533d5a9cefbae2bc9a9cfb96201c4dd15da499d21f9699619d'
SNAPSHOT_SHA='e70e8f61ade5e70011e6a3c9324ea7de56c38c49d24cef57bf96b2dc7fc5bce0'
BEFORE_ELF_SHA='fb529142de5bb20ae7d9d73eb5800c01ab70c3e88b4bee5a64382fb57108229c'
TRUTH_SHA='bd6c4e873943c203641b900ba3b790464dbf46ef77ac36b2b72cf640e85bfa06'
BINDINGS={68: [('R_MIPS_26', 'func_15167A68')], 100: [('R_MIPS_26', 'func_151ACB38')], 116: [('R_MIPS_26', 'func_1516979C')], 132: [('R_MIPS_HI16', 'D_800CC2D0')], 136: [('R_MIPS_LO16', 'D_800CC2D0')]}
ORIGINAL_BINDINGS={68: [('R_MIPS_26', 'func_15167A68')], 100: [('R_MIPS_26', 'func_151ACB38')], 116: [('R_MIPS_26', 'func_1516979C')], 132: [('R_MIPS_HI16', 'D_800CC2D0')], 136: [('R_MIPS_LO16', 'D_800CC2D0')]}
HEADERS='#include <ultra64.h>\nextern u8 D_800CC2D0[];\nvoid *func_15167A68(s32, s32, s32, s32, u8, s32);\ns32 func_151ACB38(u8 *, u8 *);\nvoid func_1516979C(void *);\n\n'
DECLARATIONS='extern u8 D_800CC2D0[];\nvoid *func_15167A68(s32, s32, s32, s32, u8, s32);\ns32 func_151ACB38(u8 *, u8 *);\nvoid func_1516979C(void *);\n\n'
SELECTED='/* Allocate an admitted owner record and return its 32-bit address handle. */\ns32 func_151ACA60(u8 *owner, f32 scale, s32 payloadSize) {\n    u8 *record;\n\n    if (owner == NULL) {\n        return 0;\n    }\n    record = func_15167A68(0x30, 0, (s32)((u32)payloadSize + 0x30U), 1, 0xFF, 1);\n    if (record == NULL) {\n        return 0;\n    }\n    if (func_151ACB38(owner, record + 0x18) == 0) {\n        func_1516979C(record);\n        return 0;\n    }\n    *(u8 **)(record + 0x1C) = owner;\n    record[0x20] = owner[0x3B];\n    *(s32 *)(record + 0x24) = (s32)((u32)owner - (u32)D_800CC2D0) / 0x32C;\n    *(f32 *)(record + 0x28) = scale;\n    *(s32 *)(record + 0x10) = 1;\n    *(s32 *)(record + 0x14) = 0;\n    return (s32)record;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Owner record admission owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('State-completion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_151ACA60() {\n    return 0;\n}':raise ValueError('Owner record admission placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner record admission snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner record admission frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner record admission predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner record admission live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner record admission named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner record admission symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner record admission metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner record admission frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner record admission original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner record admission strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner record admission named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151ACA60.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1D92F0.c.o', 'make-shadow/src/game/generated_1D92F0.c.o.compact', 'make-shadow/src/game/generated_1D92F0.c.o.padded.s', 'make-shadow/src/game/generated_1D92F0.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner record admission artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner record admission artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner record admission raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner record admission evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner record admission Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1D92F0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner record admission Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner record admission private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner record admission changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner record admission protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=48,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
