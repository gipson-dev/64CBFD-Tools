"""Distance effect handle: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150E3208','generated_1104D0'
ENTRY,ROM,BODY,SIZE=0x150E3208,0x1106B8,200,200
SOURCE='conker/src/game/generated_1104D0.c'
OBJECT='conker/build/src/game/generated_1104D0.c.o'
ASM='conker/asm/1104D0.s'
BUILD='conker/build/game-distance-effect-handle-match'
RODATA_SYMBOL=None
RAW_SHA='072a85ec46680ef18bc685071b757919036858417359cd9cd93901a9d268fab0'
SNAPSHOT_SHA='26c529062a7114aa98d12d33a13e26f6a41ba45592a2ff67d8bbc0ae1d5343e4'
BEFORE_ELF_SHA='3676b6521dfc597c66c7bfb24b009cba4b2d23854e8fa8064ac6bb41f5facff7'
TRUTH_SHA='f05c57c0a55d4ca2360ba20446d4f9ce5f93f45685e9d27d1e1aae129bd0da2d'
BINDINGS={56: [('R_MIPS_26', 'func_150AD9A0')], 160: [('R_MIPS_26', 'func_150E3020')]}
HEADERS='#include <ultra64.h>\n\ns32 func_150AD9A0(s32, s32, s32);\ns32 func_150E3020(s32, s32, s32, s32, s32, s32, s32, f32,\n                 s32, f32, f32, f32, s32, s16);\n\n'
DECLARATIONS='s32 func_150AD9A0(s32, s32, s32);\ns32 func_150E3020(s32, s32, s32, s32, s32, s32, s32, f32,\n                 s32, f32, f32, f32, s32, s16);\n\n'
SELECTED='/* Create a distance-scaled effect and return its one-based slot handle. */\ns32 func_150E3208(s32 x, s32 y, s32 z, s32 targetX, s32 targetY,\n                  s32 targetZ, s32 kind, s32 duration) {\n    u8 *effect;\n    f32 step;\n\n    step = (f32)func_150AD9A0((s32)((u32)x - (u32)targetX),\n                            (s32)((u32)y - (u32)targetY),\n                            (s32)((u32)z - (u32)targetZ)) / (f32)duration;\n    effect = (u8 *)func_150E3020(x, y, z, targetX, targetY, targetZ,\n                               kind, step, 0, 0.0f, 0.0f, 0.0f, 0, -99);\n    if (effect != NULL) {\n        return effect[0x48] + 1;\n    }\n    return 0;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected distance-effect-handle owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Distance effect handle body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150E3208() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Distance effect handle placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Distance effect handle snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Distance effect handle frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Distance effect handle predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Distance effect handle live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Distance effect handle strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Distance effect handle original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Distance effect handle image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Distance effect handle named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='1678dac601e1def3df3c6438b7a8b4bb0914ce5ef73a929921f12916f7ead9f2':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150E3208.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1104D0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1104D0.c.o","make-shadow/src/game/generated_1104D0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Distance effect handle artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Distance effect handle artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Distance effect handle raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Distance effect handle evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Distance effect handle Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1104D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Distance effect handle Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Distance effect handle private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Distance effect handle changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Distance effect handle protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=64,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
