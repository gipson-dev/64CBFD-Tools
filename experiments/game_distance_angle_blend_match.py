"""Distance angle blend: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1512C068','generated_157840'
ENTRY,ROM,BODY,SIZE=0x1512C068,0x159518,232,232
SOURCE='conker/src/game/generated_157840.c'
OBJECT='conker/build/src/game/generated_157840.c.o'
ASM='conker/asm/157840.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-distance-angle-blend-1512C068-match'
RODATA_SYMBOL=None
RAW_SHA='c7d8999758f9df554a75c2230d81be9ac21c42a702fb628d96283d1133c88a7d'
SNAPSHOT_SHA='d0e9166abba350bd1f367ae6ec4579465007b3d642070ad7682b6f562d098470'
BEFORE_ELF_SHA='3b36f423f4d83be4236dca0c6a4496441460fe07a199c8b3448fcd16920ec5f6'
TRUTH_SHA='d4b3a1720f6eb924ea10f06dc671a939128b718225d0df5d318980428030849f'
BINDINGS={184: [('R_MIPS_26', 'func_15123A54')], 208: [('R_MIPS_26', 'func_1512C150')]}
ORIGINAL_BINDINGS={184: [('R_MIPS_26', 'func_15123A54')], 208: [('R_MIPS_26', 'func_1512C150')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nf32 sqrtf(f32);\n/* Keep the current provider return declaration; this caller ignores it. */\ns32 func_15123A54(struct108 *);\nvoid func_1512C150(struct108 *);\n\n'
DECLARATIONS=''
SELECTED='/* Start a near-target angle blend, then advance the current blend. */\nvoid func_1512C068(struct108 *actor) {\n    f32 direction;\n    f32 x;\n    f32 z;\n    f32 distance;\n\n    if (actor->unk390 < 180.0f) {\n        direction = 2.0f;\n    } else {\n        direction = -2.0f;\n    }\n    if (actor->unk2C != 0x80 && actor->unk2C != 0x40) {\n        x = actor->unk2F8 - actor->unk2BC;\n        z = actor->unk300 - actor->unk2C4;\n        distance = sqrtf(x * x + z * z);\n        *(f32 *)actor->pad370 = distance;\n        if (distance < 42.0f) {\n            actor->unk384 = actor->unk37C - 45.0f * direction;\n            actor->unk5CC = 0.0f;\n            func_15123A54(actor);\n            actor->unk240 |= 2;\n        }\n    }\n    func_1512C150(actor);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner value payload diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Distance angle blend body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_1512C068() {\n    return 0;\n}':raise ValueError('Distance angle placeholder changed')
 result=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n#include "structs.h"\n'
 if not result.startswith(prefix):raise ValueError('Distance angle owner includes changed')
 return HEADERS+result[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Distance angle blend snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Distance angle blend frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Distance angle blend predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Distance angle blend live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Distance angle blend named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Distance angle blend symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Distance angle blend metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Distance angle blend frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Distance angle blend original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Distance angle blend strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Distance angle blend named definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Distance angle blend scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1512C068.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_157840.c.o', 'make-shadow/src/game/generated_157840.c.o.compact', 'make-shadow/src/game/generated_157840.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Distance angle blend artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Distance angle blend artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Distance angle blend raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Distance angle blend evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Distance angle blend Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_157840.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Distance angle blend Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Distance angle blend private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Distance angle blend changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Distance angle blend protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=57,frame=24,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='20265ddb833e3f6da7219ee138f25a1e7ab41f7d4170bc3cfaa19bf64a4b17c9'
