"""Rotated origin: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150CEF60','generated_FC410'
ENTRY,ROM,BODY,SIZE=0x150CEF60,0xFC410,224,224
SOURCE='conker/src/game/generated_FC410.c'
OBJECT='conker/build/src/game/generated_FC410.c.o'
ASM='conker/asm/FC410.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-rotated-origin-150CEF60-match'
RODATA_SYMBOL=None
RAW_SHA='a19275841103bdb80e114783f6b17c14413ee1c947a8ecb2c131c3129744e751'
SNAPSHOT_SHA='5d78fa65a88c1fb9d6c5d6ecbe750886f684e15549bf7d85c6a98ed3315e36e5'
BEFORE_ELF_SHA='94bceedb6ee2665484ad0a9d70c1d9db2d2542c29dcf1856e5608319e8fbaacc'
TRUTH_SHA='d341201ebef9adb497404626cd733d406d8eafb8c7bf491566c42b1bd4bf2f4c'
BINDINGS={12: [('R_MIPS_26', 'func_151149AC')], 20: [('R_MIPS_HI16', 'D_800A0830')], 24: [('R_MIPS_LO16', 'D_800A0830')], 36: [('R_MIPS_26', 'func_150AD78C')], 48: [('R_MIPS_26', 'func_150AD780')], 96: [('R_MIPS_HI16', 'D_800A0834')], 144: [('R_MIPS_LO16', 'D_800A0834')], 188: [('R_MIPS_26', 'func_150A3444')], 200: [('R_MIPS_26', 'func_151749A0')]}
ORIGINAL_BINDINGS={12: [('R_MIPS_26', 'func_151149AC')], 20: [('R_MIPS_HI16', 'D_800A0830')], 24: [('R_MIPS_LO16', 'D_800A0830')], 36: [('R_MIPS_26', 'func_150AD78C')], 48: [('R_MIPS_26', 'func_150AD780')], 96: [('R_MIPS_HI16', 'D_800A0834')], 144: [('R_MIPS_LO16', 'D_800A0834')], 188: [('R_MIPS_26', 'func_150A3444')], 200: [('R_MIPS_26', 'func_151749A0')]}
HEADERS='#include <ultra64.h>\nu8 *func_151149AC(u8);\nf32 func_150AD78C(f32);\nf32 func_150AD780(f32);\nvoid func_150A3444(s32, s16, s16, s16);\nvoid func_151749A0(s32, s32);\nextern f32 D_800A0830, D_800A0834;\n\n'
DECLARATIONS='u8 *func_151149AC(u8);\nf32 func_150AD78C(f32);\nf32 func_150AD780(f32);\nvoid func_150A3444(s32, s16, s16, s16);\nvoid func_151749A0(s32, s32);\nextern f32 D_800A0830, D_800A0834;\n\n'
SELECTED='/* Rotate the marker around its fixed origin and advance the phase counter. */\nvoid func_150CEF60(s32 unused) {\n    f32 second;\n    f32 radians;\n    f32 originX, originY, pointX, pointY, dx, dy;\n    f32 first;\n    (void)unused;\n    radians = *(f32 *)(func_151149AC(4) + 8) * D_800A0830;\n    first = func_150AD78C(radians);\n    second = func_150AD780(radians);\n    originX = -1.0f;\n    originY = 44.0f;\n    pointX = 76.0f;\n    pointY = 241.0f;\n    dx = pointX - originX;\n    dy = pointY - originY;\n    func_150A3444(2, (s16)(dx * second - dy * first + originX),\n        (s16)(dx * first + dy * second + originY), (s16)D_800A0834);\n    func_151749A0(5, 3);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected rotated origin diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Rotated origin body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150CEF60() {\n    return 0;\n}':raise ValueError('Rotated origin placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Rotated origin snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Rotated origin frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Rotated origin predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Rotated origin live input differs: '+name)
    return values

METADATA_GROUPS=((2921428, ('D_800A0830', 'D_800A0460', 'D_800A4960'), (1, 2, 0)), (2924356, ('D_800A0834', 'D_800A0464', 'D_800A03A8', 'D_800A4964'), (1, 2, 3, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Rotated origin named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Rotated origin symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Rotated origin metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Rotated origin frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Rotated origin original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Rotated origin strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Rotated origin named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA or NEW_GUARDS:raise ValueError('Rotated origin guard history changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Rotated origin scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150CEF60.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_FC410.c.o', 'make-shadow/src/game/generated_FC410.c.o.compact', 'make-shadow/src/game/generated_FC410.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Rotated origin artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Rotated origin artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Rotated origin raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Rotated origin evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Rotated origin Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_FC410.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Rotated origin Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Rotated origin private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Rotated origin changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Rotated origin protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=64,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='7ff7e838acb8d1fab239942e8ec9567820b8b35f642e394cb153ccfd4f5ef836'
