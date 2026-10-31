"""Actor phase motion: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150DE6D8','generated_10B7D0'
ENTRY,ROM,BODY,SIZE=0x150DE6D8,0x10BB88,232,232
SOURCE='conker/src/game/generated_10B7D0.c'
OBJECT='conker/build/src/game/generated_10B7D0.c.o'
ASM='conker/asm/10B7D0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-phase-motion-150DE6D8-match'
RODATA_SYMBOL=None
RAW_SHA='9eb1a7e42873c15850c1c9895662e2b6aed90ebadc03548e6e4a8e3adac39189'
SNAPSHOT_SHA='622e6f5204788477b4e31632f0c9c36113aadc6546fce08efc24ee23420acbff'
BEFORE_ELF_SHA='78034ee06d159dcf43d73cf66557aa70528a104d580e3632e95665df4fbbdf38'
TRUTH_SHA='af2f59777f65fed0115853aa086814478b6e572fb60509c6076b341619dee557'
BINDINGS={24: [('R_MIPS_26', 'func_15048A40')], 32: [('R_MIPS_HI16', 'D_800A0D48')], 36: [('R_MIPS_LO16', 'D_800A0D48')], 40: [('R_MIPS_HI16', 'D_800A0D4C')], 44: [('R_MIPS_LO16', 'D_800A0D4C')], 76: [('R_MIPS_26', 'func_15048A40')], 84: [('R_MIPS_HI16', 'D_800A0D50')], 88: [('R_MIPS_LO16', 'D_800A0D50')], 108: [('R_MIPS_26', 'func_15048A40')], 124: [('R_MIPS_HI16', 'D_800BE9E4')], 128: [('R_MIPS_LO16', 'D_800BE9E4')], 116: [('R_MIPS_HI16', 'D_800A0D54')], 120: [('R_MIPS_LO16', 'D_800A0D54')]}
ORIGINAL_BINDINGS={24: [('R_MIPS_26', 'func_15048A40')], 32: [('R_MIPS_HI16', 'D_800A0D48')], 36: [('R_MIPS_LO16', 'D_800A0D48')], 40: [('R_MIPS_HI16', 'D_800A0D4C')], 44: [('R_MIPS_LO16', 'D_800A0D4C')], 76: [('R_MIPS_26', 'func_15048A40')], 84: [('R_MIPS_HI16', 'D_800A0D50')], 88: [('R_MIPS_LO16', 'D_800A0D50')], 108: [('R_MIPS_26', 'func_15048A40')], 116: [('R_MIPS_HI16', 'D_800A0D54')], 120: [('R_MIPS_LO16', 'D_800A0D54')], 124: [('R_MIPS_HI16', 'D_800BE9E4')], 128: [('R_MIPS_LO16', 'D_800BE9E4')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    f32 x,y,z;\n    u8 reserved0C[6];\n    s16 pitch;\n    u8 reserved14[0x68];\n    u32 phaseX,phaseY,phaseZ;\n} ActorPhaseMotion;\nextern f32 D_800A0D48,D_800A0D4C,D_800A0D50,D_800A0D54;\nextern s32 D_800BE9E4;\nf32 func_15048A40(u8 angle);\n'
DECLARATIONS=''
SELECTED="/* Update the actor's oscillating pitch/position and advance three phase counters. */\nvoid func_150DE6D8(ActorPhaseMotion *actor) {\n    actor->pitch = func_15048A40((u8)((s32)actor->phaseX >> 3)) * D_800A0D48 + D_800A0D4C;\n    actor->x = func_15048A40((u8)((s32)actor->phaseY >> 3)) * D_800A0D50;\n    actor->z = func_15048A40((u8)((s32)actor->phaseZ >> 3)) * D_800A0D54;\n    actor->phaseX += (u32)D_800BE9E4 * 12;\n    actor->phaseY += (u32)D_800BE9E4 * 16;\n    actor->phaseZ += (u32)D_800BE9E4 * 24;\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor-phase owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor phase motion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_150DE6D8() {\n    return 0;\n}':raise ValueError('Actor-phase placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('#include "structs.h"\n','',1)
    return before[:a]+declarations+SELECTED.rstrip()+before[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor phase motion snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor phase motion frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor phase motion predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor phase motion live input differs: '+name)
    return values

METADATA_GROUPS=((2740836,('func_150CBCE0','D_8009ECFC'),(1,0)),(2825844,('D_800A0D50','D_800A08F0'),(1,0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor phase motion named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor phase motion symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor phase motion metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor phase motion frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor phase motion original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor phase motion strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor phase motion named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Actor phase motion scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150DE6D8.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_10B7D0.c.o', 'make-shadow/src/game/generated_10B7D0.c.o.compact', 'make-shadow/src/game/generated_10B7D0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor phase motion artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor phase motion artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor phase motion raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor phase motion evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor phase motion Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_10B7D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor phase motion Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor phase motion private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor phase motion changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor phase motion protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=32,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='387d974ab8addd2d86cc692ce5b58a55c675308022b778d301cd4fc77b574c99'
