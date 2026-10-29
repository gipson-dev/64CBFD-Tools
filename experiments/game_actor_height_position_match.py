"""Actor height position: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150BA930','generated_E7970'
ENTRY,ROM,BODY,SIZE=0x150BA930,0xE7DE0,208,208
SOURCE='conker/src/game/generated_E7970.c'
OBJECT='conker/build/src/game/generated_E7970.c.o'
ASM='conker/asm/E7970.s'
BUILD='conker/build/game-actor-height-position-match'
RODATA_SYMBOL=None
INITIALIZE,QUERY,PARENT,THRESHOLD=0x1504715C,0x15046C80,0x150BAA14,0x8009FE60
RAW_SHA='a79670283002b736f52c2907367bd6db00961301c8feed2dab6b26d979249bd1'
SNAPSHOT_SHA='658da5b4673c3e198de688d336d05a8f549d3b8b5d7a3d2e478688b185d0164e'
BEFORE_ELF_SHA='062730d9aef5dc979918e8c471770f0df2da59c8fc2558b8bdc9492dfe211c11'
TRUTH_SHA='706d4842ba7c59e764f24c16faafad915e31cd97afe96122472e49dbb0c129a3'
BINDINGS={32: [('R_MIPS_HI16', 'D_8009FE60')], 40: [('R_MIPS_LO16', 'D_8009FE60')], 140: [('R_MIPS_26', 'func_1504715C')], 180: [('R_MIPS_26', 'func_15046C80')]}
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='typedef struct HeightResult71820 HeightResult71820;\ntypedef struct HeightActor71820 HeightActor71820;\nextern f32 D_8009FE60;\nvoid func_1504715C(HeightResult71820 *, HeightActor71820 *);\ns32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);\n'
SELECTED='/* Copy the actor position and optionally query the vertical interval around it. */\ns32 func_150BA930(f32 *position, u8 *actor, HeightResult71820 *result, u8 unused) {\n    f32 start[3];\n\n    position[0] = *(f32 *)(actor + 0x14);\n    if (D_8009FE60 < *(f32 *)(actor + 0x180)) {\n        position[1] = *(f32 *)(actor + 0x180);\n    } else {\n        position[1] = *(f32 *)(actor + 0x18);\n    }\n    position[2] = *(f32 *)(actor + 0x1C);\n    if (result == 0) {\n        return 1;\n    }\n    start[0] = position[0];\n    start[1] = position[1] + 100.0f;\n    start[2] = position[2];\n    func_1504715C(result, (HeightActor71820 *)actor);\n    return func_15046C80(start, 0, position[1] - 100.0f, result);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Actor height position owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=208 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor height position body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150BA930() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Actor height position placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor height position snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor height position frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor height position predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor height position live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor height position frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor height position original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor height position strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor height position named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='e800c51d09743626c1f1c510d66940511b7ce848746e8add05d95be041ec4be1':raise ValueError('Actor height position inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150BA930.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_E7970.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_E7970.c.o","make-shadow/src/game/generated_E7970.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor height position artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor height position artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor height position raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor height position evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor height position Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_E7970.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor height position Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor height position private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor height position changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor height position protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=52,frame=48,alignment_words=0,slot_words=52,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
