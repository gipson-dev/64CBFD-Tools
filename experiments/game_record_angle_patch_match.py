"""Record angle patch: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150C7C90','generated_F4D20'
ENTRY,ROM,BODY,SIZE=(353139856, 1003840, 236, 236)
SOURCE='conker/src/game/generated_F4D20.c'
OBJECT='conker/build/src/game/generated_F4D20.c.o'
ASM='conker/asm/F4D20.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-record-angle-patch-150C7C90-match'
RODATA_SYMBOL=None
RAW_SHA='8c359181c969275c5cafe18e13ee91a25ac7c3701079c27700404551fad4c9e0'
SNAPSHOT_SHA='91db40893d733d2d18d39c5993fccac3d8cc2869ab030fc872b5307d4ceb6622'
BEFORE_ELF_SHA='333cd9a49306db1458dd2e90b7577b214503f2752d3144cb9f747075ecdbd0d4'
TRUTH_SHA='1920f9d8135a148f10057f5bc6b3dd3815da8706bd77b761f057c78d44dd73d4'
BINDINGS={104: [('R_MIPS_26', 'func_151149AC')]}
ORIGINAL_BINDINGS={104: [('R_MIPS_26', 'func_151149AC')]}
HEADERS='#include <ultra64.h>\nu8 *func_151149AC(u8);\n'
DECLARATIONS='u8 *func_151149AC(u8);\n\n'
SELECTED='/* Patch the sentinel record with the wrapped object-relative angle. */\nvoid func_150C7C90(u8 *actor) {\n    s32 index;\n    u8 *record;\n    s32 angle;\n\n    if (*(s32 *)(actor + 0x7C) == 0) {\n        record = *(u8 **)(actor + 0x1C);\n        index = 0;\n        while (*(s8 *)(record + (index << 3)) != -14) {\n            index++;\n        }\n        *(s32 *)(actor + 0x7C) = index;\n    }\n    index = *(s32 *)(actor + 0x7C);\n    record = *(u8 **)(actor + 0x1C) + index * 8;\n    angle = -669 - *(s16 *)(func_151149AC(*(u32 *)(actor + 0x3C) & 0xFF) + 0x12);\n    if (*(u32 *)(actor + 0x3C) & 0x8000) {\n        angle = 836 - angle;\n    }\n    while (angle < 0) {\n        angle += 1024;\n    }\n    while (angle >= 1024) {\n        angle -= 1024;\n    }\n    *(u32 *)record &= ~0xFFF;\n    *(u32 *)record |= angle;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected slot refresh diagnostics')
    return 0




sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record angle patch body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_150C7C90() {\n    return 0;\n}':raise ValueError('Angle patch placeholder changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]







def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record angle patch snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record angle patch frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record angle patch predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record angle patch live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Record angle patch named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Record angle patch symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Record angle patch metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record angle patch frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record angle patch original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record angle patch strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record angle patch named definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited angle patch guards changed')
 return before



def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Direct angle patch scope changed')
 return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150C7C90.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_F4D20.c.o', 'make-shadow/src/game/generated_F4D20.c.o.compact', 'make-shadow/src/game/generated_F4D20.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record angle patch artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record angle patch artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record angle patch raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record angle patch evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record angle patch Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_F4D20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record angle patch Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record angle patch private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record angle patch changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record angle patch protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=32,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='c0ac0ea7d44ac6fb46585874ac7522ea4067ec290ac3b1005aa374b168cb0a7c'

NORMALIZED_SHA='8c359181c969275c5cafe18e13ee91a25ac7c3701079c27700404551fad4c9e0'


def schedule_proof(raw,bindings,truth,retail_bindings):
 checked_payload(raw,bindings)
 if (raw,bindings)!=(truth,retail_bindings):raise ValueError('Direct body or relocation differs')
 return dict(direct_C_match=True,words=59,bindings=1,complete_body_and_relocations_identical=True,guards=0)
