"""Cosine height delta: direct semantic C and literal image audit."""
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
FUNCTION,OWNER='func_151162D4','generated_142560'
ENTRY,ROM,BODY,SIZE=0x151162D4,0x143784,236,236
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-cosine-height-delta-151162D4-match'
RODATA_SYMBOL=None
RAW_SHA='b946764ab1dc53d201caf0732ca44d232002a3e431ce318a71fd15546862cd3e'
SNAPSHOT_SHA='a53a2da1eda5e492f356c49e029ad981f3aa9a412d1ec0145cf61d293b28a235'
BEFORE_ELF_SHA='6c0b47cec5381a5cb0506af0572c4e9380ac1322a94b6ab37c2d89a200daca75'
TRUTH_SHA='f150a887a345ea9c21a9298ae61d1440ea5fa764a4cb94982a279a33d7b9f68d'
BINDINGS={116: [('R_MIPS_26', 'cosf')], 132: [('R_MIPS_HI16', 'D_800BE9E4')], 156: [('R_MIPS_LO16', 'D_800BE9E4')]}
ORIGINAL_BINDINGS={116: [('R_MIPS_26', 'cosf')], 132: [('R_MIPS_HI16', 'D_800BE9E4')], 156: [('R_MIPS_LO16', 'D_800BE9E4')]}
HEADERS='#include <ultra64.h>\n\ntypedef struct {\n    u8 reserved00[0x12];\n    s16 height;\n    u8 reserved14[4];\n    f32 offset;\n    u8 reserved1C[0x20];\n    s32 packed;\n    u8 reserved40[0x1C];\n    s16 delta;\n    u8 reserved5E[0x1E];\n    u32 phase;\n} CosineHeightRecord;\nextern s32 D_800BE9E4;\n\n'
DECLARATIONS=''
SELECTED='/* Advance the cosine offset and publish its change in integral height. */\nvoid func_151162D4(CosineHeightRecord *record) {\n    f32 amplitude;\n    s32 speed;\n    s16 previousHeight;\n    f32 offset;\n\n    previousHeight = (s32)((f32)record->height + record->offset);\n    amplitude = (s16)(record->packed & 0xFFFF);\n    speed = (record->packed >> 16) & 0xFFFF;\n    offset = cosf((f32)(s32)record->phase * 0.0054931640625f) * amplitude;\n    record->offset = offset;\n    record->phase += (u32)speed * (u32)D_800BE9E4;\n    record->delta = (s32)(((f32)record->height + offset) - (f32)previousHeight);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected cosine-height owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Cosine height delta body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_151162D4() {\n    return 0;\n}':raise ValueError('Cosine-height placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('#include "structs.h"\n','',1)
    after=before[:a]+declarations+SELECTED.rstrip()+before[b:]
    if after.count('func_151162D4(arg0);')!=1:raise ValueError('Expected one typed direct caller')
    return after.replace('func_151162D4(arg0);','func_151162D4((CosineHeightRecord *)arg0);')


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Cosine height delta snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Cosine height delta frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Cosine height delta predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Cosine height delta live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Cosine height delta named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Cosine height delta symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Cosine height delta metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Cosine height delta frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Cosine height delta original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Cosine height delta strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Cosine height delta named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Cosine height delta scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151162D4.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'make-shadow/src/game/generated_142560.c.o.compact', 'make-shadow/src/game/generated_142560.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Cosine height delta artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Cosine height delta artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Cosine height delta raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Cosine height delta evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Cosine height delta Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_142560.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Cosine height delta Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Cosine height delta private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Cosine height delta changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Cosine height delta protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=40,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0e1dcd21b2871b8c63c7e128de0c89befa9870d68748dbb979f048976a5728e9'
