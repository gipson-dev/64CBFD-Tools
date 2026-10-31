"""Owner state value payload: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15109410','generated_1368C0'
ENTRY,ROM,BODY,SIZE=(353408016, 1272000, 236, 236)
SOURCE='conker/src/game/generated_1368C0.c'
OBJECT='conker/build/src/game/generated_1368C0.c.o'
ASM='conker/asm/1368C0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-state-payload-15109410-match'
RODATA_SYMBOL=None
RAW_SHA='443856dd9fef2d93030bf0a00fd3b31a97485d92685d26f01f3eab6c5f9c2e76'
SNAPSHOT_SHA='c348b4bf8b9061bbdd1a70e67bf7c7e02b5d9fbdc602b754f20b3a4cf2724476'
BEFORE_ELF_SHA='9d0ddf117f5941f532908ea7e4c6bef546a5fecda308844ba2345ba73b948277'
TRUTH_SHA='e6cca43640acb520e3e7b0e93d61d49d5e198f206b7ea7c3fbb981328a1c822c'
BINDINGS={176: [('R_MIPS_26', 'func_15149130')], 204: [('R_MIPS_26', 'memcpy')]}
ORIGINAL_BINDINGS={176: [('R_MIPS_26', 'func_15149130')], 204: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nstruct260 *func_15149130(s16, s8, s8, s8, u8, u8, struct37 *, u8, s32);\nvoid *memcpy(void *, const void *, u32);\ntypedef struct {\n    u8 *owner;\n    u8 ownerId;\n    f32 zero;\n    f32 value;\n    s8 first, second;\n} OwnerStateValuePayload1368C0;\n'
DECLARATIONS='typedef struct {\n    u8 *owner;\n    u8 ownerId;\n    f32 zero;\n    f32 value;\n    s8 first, second;\n} OwnerStateValuePayload1368C0;\n'
SELECTED="/* Create a value payload with the owner's captured identity and signed settings. */\nvoid *func_15109410(u8 *owner, s16 lifetime, s8 first, s8 second, f32 value,\n                   u32 extraBytes, u8 selector, s32 category) {\n    u8 *created;\n    OwnerStateValuePayload1368C0 payload;\n    s16 duration;\n    u8 flags;\n\n    if (owner == NULL) {\n        return NULL;\n    }\n    flags = 0;\n    if (lifetime < 0) {\n        duration = 300;\n    } else {\n        flags = 1;\n        duration = lifetime;\n    }\n    payload.zero = 0.0f;\n    payload.value = value;\n    payload.first = first;\n    payload.second = second;\n    payload.owner = owner;\n    payload.ownerId = owner[0x3B];\n    created = (u8 *)func_15149130(duration, -1, 0x1A, -1, flags, 0x1A,\n                                 (struct37 *)(extraBytes + sizeof(payload)), selector, category);\n    if (created != NULL) {\n        memcpy(created + 0x28, &payload, sizeof(payload));\n    }\n    return created;\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner value payload diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner state value payload body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15109410() {\n    return 0;\n}':raise ValueError('Owner state value placeholder changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner state value payload snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner state value payload frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner state value payload predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner state value payload live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner state value payload named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner state value payload symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner state value payload metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner state value payload frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner state value payload original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner state value payload strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner state value payload named definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Attached effect scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15109410.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1368C0.c.o', 'make-shadow/src/game/generated_1368C0.c.o.compact', 'make-shadow/src/game/generated_1368C0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner state value payload artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner state value payload artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner state value payload raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner state value payload evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner state value payload Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1368C0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner state value payload Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner state value payload private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner state value payload changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner state value payload protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=80,alignment_words=0,slot_words=57,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='74fd8cbc1df3f5a9e34d214eca652a15d6b23aa5e7eed694f83a6fee23887744'
