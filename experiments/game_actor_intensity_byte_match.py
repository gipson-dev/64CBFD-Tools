"""Actor intensity byte: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1511BA24','generated_142560'
ENTRY,ROM,BODY,SIZE=0x1511BA24,0x148ED4,224,224
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-intensity-byte-match'
RODATA_SYMBOL=None
RAW_SHA='a3eea0535b937a52a04ba17ee096a1dd14e106e0cde91a68d599064dc95836e6'
SNAPSHOT_SHA='46431ff41aee963a7420759b756adcfacf14651f064c2fb1e70bc2e7b46df4a6'
BEFORE_ELF_SHA='124447d9285fc55fbc7b74645e44f00586270bdf696c29ede80f7b41aee8a15b'
TRUTH_SHA='a5fb365276b8bb0ea862d5f28d718b5bcaf06b6ca9dceff48dd6a6fd4104a56f'
BINDINGS={28: [('R_MIPS_26', 'func_15188010')]}
ORIGINAL_BINDINGS={28: [('R_MIPS_26', 'func_15188010')]}
HEADERS='#include <ultra64.h>\nvoid func_15188010(s32, f32 *);\n\n'
DECLARATIONS='void func_15188010(s32, f32 *);\n\n'
SELECTED='/* Store the sampled factor scaled to a nonzero actor byte. */\nvoid func_1511BA24(u8 *actor) {\n    f32 factor = 0.0f;\n\n    func_15188010(*(s32 *)(actor + 0x3C), &factor);\n    actor[0x8A] = (u32)(factor * 255.0f);\n    if (actor[0x8A] == 0) {\n        actor[0x8A] = 1;\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner diagnostics: '+text)
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor intensity byte body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1511BA24() {\n    return 0;\n}':raise ValueError('Status actor mode placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor intensity byte snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor intensity byte frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor intensity byte predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor intensity byte live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor intensity byte named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor intensity byte symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor intensity byte metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor intensity byte frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor intensity byte original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor intensity byte strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor intensity byte named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='976f8cba35366c4984694b24e814bcf8ea3ce696b18f312bcf4e1fc5a3825750':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1511BA24.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'make-shadow/src/game/generated_142560.c.o.compact', 'make-shadow/src/game/generated_142560.c.o.padded.s', 'make-shadow/src/game/generated_142560.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor intensity byte artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor intensity byte artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor intensity byte raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor intensity byte evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor intensity byte Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_142560.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor intensity byte Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor intensity byte private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor intensity byte changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor intensity byte protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,frame=32,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
