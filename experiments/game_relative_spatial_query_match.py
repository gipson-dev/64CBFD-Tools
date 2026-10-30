"""Relative spatial query: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1510F720','generated_13BB20'
ENTRY,ROM,BODY,SIZE=0x1510F720,0x13CBD0,224,224
SOURCE='conker/src/game/generated_13BB20.c'
OBJECT='conker/build/src/game/generated_13BB20.c.o'
ASM='conker/asm/13BB20.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-relative-spatial-query-1510F720-match'
RODATA_SYMBOL=None
RAW_SHA='e272f3de532d3f4b538488a3e09c0d5f9fa00c96eb42dfb3177a1a04bccee98b'
SNAPSHOT_SHA='57cf5ab28664ab4a3ada3e298a2e7a8f390e093f48e56c3729ee217019fc5fb3'
BEFORE_ELF_SHA='c3891dca9d33bc176ac88b07f416aa043b32712995e2c59d506f8a6ca44ba2fe'
TRUTH_SHA='b57eb170a191705d7f0adfa345d14b62024243735d027c416b15549fc7ecdf69'
BINDINGS={28: [('R_MIPS_HI16', 'D_800DBE48')], 32: [('R_MIPS_LO16', 'D_800DBE48')]}
ORIGINAL_BINDINGS={28: [('R_MIPS_HI16', 'D_800DBE48')], 32: [('R_MIPS_LO16', 'D_800DBE48')]}
HEADERS='#include <ultra64.h>\nextern u8 *D_800DBE48;\n\n'
DECLARATIONS=''
SELECTED='/* Collect nearby leaf records while following signed relative record offsets. */\ns32 func_1510F720(s32 x, s32 z, s32 radius, u8 **output) {\n    u8 *node = D_800DBE48;\n    s32 count = 0;\n    s32 dx, dz, limit, absX, absZ;\n    s32 offset, child;\n\n    while (node != NULL) {\n        dx = (s32)((u32)*(s16 *)(node + 8) - (u32)x);\n        absX = dx < 0 ? (s32)(0u - (u32)dx) : dx;\n        limit = (s32)((u32)radius + *(u16 *)(node + 6));\n        if (absX < limit &&\n            (dz = (s32)((u32)*(s16 *)(node + 10) - (u32)z),\n             absZ = dz < 0 ? (s32)(0u - (u32)dz) : dz,\n             absZ < limit)) {\n            child = *(s16 *)(node + 12);\n            if (child != 0) {\n                offset = child;\n            } else {\n                *output++ = node;\n                count++;\n                offset = *(s16 *)(node + 4);\n            }\n        } else {\n            offset = *(s16 *)(node + 4);\n        }\n        node = offset != 0 ? node + offset : NULL;\n    }\n    return count;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected effect slot release diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Relative spatial query body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1510F720() {\n    return 0;\n}':raise ValueError('Spatial query placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Relative spatial query snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Relative spatial query frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Relative spatial query predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Relative spatial query live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Relative spatial query named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Relative spatial query symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Relative spatial query metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Relative spatial query frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Relative spatial query original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Relative spatial query strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Relative spatial query named definitions changed')

NEW_GUARDS=[{'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x010', 'expected': '0x00808025', 'replacement': '0x00C08025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x034', 'expected': '0x01D02023', 'replacement': '0x01C42823', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x038', 'expected': '0x04810003', 'replacement': '0x04A10003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x03C', 'expected': '0x00802825', 'replacement': '0x00A03025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x044', 'expected': '0x00042823', 'replacement': '0x00053023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x04C', 'expected': '0x01E62021', 'replacement': '0x020F2821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x050', 'expected': '0x00A4082A', 'replacement': '0x00C5082A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x058', 'expected': '0x84450004', 'replacement': '0x84460004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x060', 'expected': '0x03112823', 'replacement': '0x03113023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x064', 'expected': '0x04A10003', 'replacement': '0x04C10003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x068', 'expected': '0x00A03825', 'replacement': '0x00C03825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x070', 'expected': '0x00053823', 'replacement': '0x00063823', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x074', 'expected': '0x00E4082A', 'replacement': '0x00E5082A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x07C', 'expected': '0x84450004', 'replacement': '0x84460004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x080', 'expected': '0x8444000C', 'replacement': '0x8445000C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x084', 'expected': '0x50800004', 'replacement': '0x50A00004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x090', 'expected': '0x00802825', 'replacement': '0x00A03025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x0A4', 'expected': '0x84450004', 'replacement': '0x84460004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x0A8', 'expected': '0x84450004', 'replacement': '0x84460004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x0AC', 'expected': '0x50A00004', 'replacement': '0x50C00004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F720', 'offset': '0x0B8', 'expected': '0x00451021', 'replacement': '0x00461021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed spatial-query register allocation cycle', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
 import csv,io
 if sha(before)!=GUARD_SHA:raise ValueError('Spatial query inherited guards changed')
 fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writerows(NEW_GUARDS)
 return before+(b''if before.endswith(b'\n')else b'\n')+stream.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 from tools.pad_generated_object import parse_relocation_spec
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Spatial query scope changed')
 checked_payload(raw,bindings);rows={int(x['offset'],0):x for x in NEW_GUARDS};words=struct.unpack('>56I',raw);output=[];relocations={}
 for i,word in enumerate(words):
  at=i*4;rs=bindings.get(at,[]);row=rows.get(at)
  if row:
   if word!=int(row['expected'],0)or rs!=parse_relocation_spec(row['expected_relocations']):raise ValueError('Spatial query preimage changed')
   word=int(row['replacement'],0);rs=parse_relocation_spec(row['replacement_relocations'])
  if rs:relocations[len(output)*4]=rs
  output.append(word)
  if row and row['insert_after']:
   rs=parse_relocation_spec(row['insert_after_relocations'])
   if rs:relocations[len(output)*4]=rs
   output.append(int(row['insert_after'],0))
 result=struct.pack('>%dI'%len(output),*output)
 if len(result)!=224 or sha(result)!=ORIGINAL_SHA or relocations!=ORIGINAL_BINDINGS:raise ValueError('Spatial query normalization changed')
 return result,relocations

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1510F720.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_13BB20.c.o', 'make-shadow/src/game/generated_13BB20.c.o.compact', 'make-shadow/src/game/generated_13BB20.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Relative spatial query artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Relative spatial query artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Relative spatial query raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Relative spatial query evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Relative spatial query Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_13BB20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Relative spatial query Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=21 or q['exclusions']!=0:raise ValueError('Relative spatial query private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Relative spatial query changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Relative spatial query protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=53,frame=16,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=21,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0c0fdc83e5c9c7e79fe0a42948f67f2687f496d3cf5989cb72a113f3429e872b'

ORIGINAL_SHA='58ac6b72d797cb8f452811d62d7134d9ec008db87e4be605491d4ea19a0e4de0'
