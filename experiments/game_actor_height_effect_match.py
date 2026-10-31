"""Actor height effect: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151A0A10','generated_1CC440'
ENTRY,ROM,BODY,SIZE=0x151A0A10,0x1CDEC0,232,232
SOURCE='conker/src/game/generated_1CC440.c'
OBJECT='conker/build/src/game/generated_1CC440.c.o'
ASM='conker/asm/1CC440.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-height-effect-151A0A10-match'
RODATA_SYMBOL=None
RAW_SHA='a20a3291b3a12e9ddcba946f4027788b2eadbd7227b074c67feda7b181c95647'
SNAPSHOT_SHA='73a52aafec3ad6d99244e37be9d706aadf478db987a11c3ccc826a5329355f66'
BEFORE_ELF_SHA='3ccf015d8a0ced863337d5f965f0aed5c3dcac6ba684f2194f0c57c9fdd0caa2'
TRUTH_SHA='60187998a72186cff2d0222552ea2e7eb639bf907413c042379775355d13de54'
BINDINGS={40: [('R_MIPS_HI16', 'D_800C35EA')], 44: [('R_MIPS_LO16', 'D_800C35EA')], 84: [('R_MIPS_26', 'func_1510F8CC')], 184: [('R_MIPS_26', 'func_151491F4')], 204: [('R_MIPS_26', 'memcpy')]}
ORIGINAL_BINDINGS={40: [('R_MIPS_HI16', 'D_800C35EA')], 44: [('R_MIPS_LO16', 'D_800C35EA')], 84: [('R_MIPS_26', 'func_1510F8CC')], 184: [('R_MIPS_26', 'func_151491F4')], 204: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct {\n    f32 x;\n    f32 y;\n    f32 z;\n    u8 selected;\n    u8 padD[3];\n    f32 zero;\n} ActorHeightEffectPayload;\nextern u8 D_800C35EA;\nu32 func_1510F8CC(u32);\nstruct260 *func_151491F4(s16, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n'
DECLARATIONS=''
SELECTED='/* Capture the actor position and cached height, then submit the selected effect. */\nvoid func_151A0A10(u8 *actor, s16 effect, u8 variant, s32 flags) {\n    struct260 *record;\n    ActorHeightEffectPayload payload;\n\n    if (actor != NULL) {\n        payload.x = *(f32 *)(actor + 0x14);\n        payload.z = *(f32 *)(actor + 0x1C);\n        if (D_800C35EA != 1) {\n            payload.y = *(f32 *)(actor + 0x180);\n            payload.zero = 0.0f;\n            switch (func_1510F8CC(*(u32 *)(actor + 0x184))) {\n                case 10:\n                    payload.selected = 0;\n                    break;\n                case 15:\n                case 17:\n                    payload.selected = 1;\n                    break;\n                default:\n                    payload.selected = 0;\n                    break;\n            }\n            record = func_151491F4(effect, -1, 1, 1, 0, 0x14, variant, flags);\n            if (record != NULL) {\n                memcpy((u8 *)record + 0x28, &payload, 0x14);\n            }\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor-height owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor height effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_151A0A10() {\n    return 0;\n}':raise ValueError('Actor-height placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('#include "structs.h"\n','',1)
    return before[:a]+declarations+SELECTED.rstrip()+before[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor height effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor height effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor height effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor height effect live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor height effect named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor height effect symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor height effect metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor height effect frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor height effect original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor height effect strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor height effect named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Actor height effect scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151A0A10.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1CC440.c.o', 'make-shadow/src/game/generated_1CC440.c.o.compact', 'make-shadow/src/game/generated_1CC440.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor height effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor height effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor height effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor height effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor height effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1CC440.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor height effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor height effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor height effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor height effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=80,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='ce6b37af2b9c41cca40acc4c57f7134ca1fbb0135caa2d198310898dce9b8a55'
