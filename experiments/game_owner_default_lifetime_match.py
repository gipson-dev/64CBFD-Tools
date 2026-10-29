"""Owner default lifetime: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150B53D0','generated_E2880'
ENTRY,ROM,BODY,SIZE=0x150B53D0,0xE2880,216,216
SOURCE='conker/src/game/generated_E2880.c'
OBJECT='conker/build/src/game/generated_E2880.c.o'
ASM='conker/asm/E2880.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-default-lifetime-match'
RODATA_SYMBOL=None
RAW_SHA='838f4b217f5e786a9ed61fbe94eb16065e9d7c6ac92a8565ff30a93947519405'
SNAPSHOT_SHA='47749f94b7418940bef7065c1d32a7a44d2d9af675e2414a36d8281d12552faf'
BEFORE_ELF_SHA='ef537f6b4a72f14d8d971c2484abb3d8b2166534a48424c2f68c6822b38fd5d1'
TRUTH_SHA='339c98b9893716cf22c97ad0dc53e579f460ecc41c3b8a593289c75fcb1949bf'
BINDINGS={156: [('R_MIPS_26', 'func_15149130')], 180: [('R_MIPS_26', 'memcpy')], 188: [('R_MIPS_26', 'func_151D2AB0')]}
ORIGINAL_BINDINGS={156: [('R_MIPS_26', 'func_15149130')], 180: [('R_MIPS_26', 'memcpy')], 188: [('R_MIPS_26', 'func_151D2AB0')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    u8 *owner;\n    u8 ownerId;\n    f32 value0;\n    f32 value1;\n} OwnerDefaultLifetimePayload;\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\nvoid func_151D2AB0(s32);\n\n'
DECLARATIONS='typedef struct {\n    u8 *owner;\n    u8 ownerId;\n    f32 value0;\n    f32 value1;\n} OwnerDefaultLifetimePayload;\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\nvoid func_151D2AB0(s32);\n\n'
SELECTED='/* Create the owner-linked record, using 300 for the default lifetime. */\nvoid *func_150B53D0(u8 *owner, s16 lifetime, u8 priority, s32 mode) {\n    u8 *created;\n    OwnerDefaultLifetimePayload payload;\n\n    if (owner == NULL) {\n        return NULL;\n    }\n    payload.owner = owner;\n    payload.ownerId = owner[0x3B];\n    payload.value0 = 0.0f;\n    payload.value1 = 0.0f;\n    created = func_15149130(lifetime == -1 ? 300 : lifetime, -1, 0x24, -1,\n                           lifetime == -1 ? 0 : 1, 0x23, sizeof(payload), priority, mode);\n    if (created != NULL) {\n        memcpy(created + 0x28, &payload, sizeof(payload));\n        func_151D2AB0(6);\n    }\n    return created;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Owner default lifetime owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('State-completion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150B53D0() {\n    return 0;\n}':raise ValueError('Owner default lifetime placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner default lifetime snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner default lifetime frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner default lifetime predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner default lifetime live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner default lifetime named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner default lifetime symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner default lifetime metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner default lifetime frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner default lifetime original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner default lifetime strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner default lifetime named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='69df0bc02f824de16817dd7c82f0c129e394d4f7d31d47c8c27b0793fc2067aa':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150B53D0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_E2880.c.o', 'make-shadow/src/game/generated_E2880.c.o.compact', 'make-shadow/src/game/generated_E2880.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner default lifetime artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner default lifetime artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner default lifetime raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner default lifetime evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner default lifetime Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_E2880.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner default lifetime Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner default lifetime private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner default lifetime changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner default lifetime protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=80,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
