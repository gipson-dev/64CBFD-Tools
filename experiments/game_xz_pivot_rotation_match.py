"""XZ pivot rotation: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly as _emit
def emit_padded_assembly(obj,asm,filename,word_patches_path):
    asm=Path(asm)
    if asm.name!='func_1508EF80.s'or filename!='game_BC430':raise ValueError('XZ rotation padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1508EF80','game_BC430'
ENTRY,ROM,BODY,SIZE=0x1508EF80,0xBC430,220,224
SOURCE='conker/src/game_BC430.c'
OBJECT='conker/build/src/game_BC430.c.o'
ASM='conker/asm/nonmatchings/game_BC430/func_1508EF80.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-xz-pivot-rotation-1508EF80-match'
RODATA_SYMBOL=None
RAW_SHA='20b4d2dfe724eca987d3fd7a14a1543e19335211d4bfda26ee159e1036522053'
SNAPSHOT_SHA='d9e84ddb7b91702a35f4d2d2e779e8c4da419024c4a509214e30f79a8023869a'
BEFORE_ELF_SHA='2faf8cd54e3986dd74bd4b83000e2b7c6dba397e1fb65da3b28404de003651c4'
TRUTH_SHA='cb727a2fef872548516c2516254780750daf5492dc78a886dcf985f01194601a'
BINDINGS={28: [('R_MIPS_HI16', 'D_8009DC80')], 32: [('R_MIPS_LO16', 'D_8009DC80')], 68: [('R_MIPS_26', 'cosf')], 80: [('R_MIPS_26', 'sinf')], 128: [('R_MIPS_26', 'sinf')], 140: [('R_MIPS_26', 'cosf')]}
ORIGINAL_BINDINGS={28: [('R_MIPS_HI16', 'D_8009DC80')], 36: [('R_MIPS_LO16', 'D_8009DC80')], 68: [('R_MIPS_26', 'cosf')], 80: [('R_MIPS_26', 'sinf')], 128: [('R_MIPS_26', 'sinf')], 140: [('R_MIPS_26', 'cosf')]}
HEADERS='#include <ultra64.h>\nextern f32 D_8009DC80;\nf32 cosf(f32);\nf32 sinf(f32);\n'
DECLARATIONS='extern f32 D_8009DC80;\n\n'
SELECTED='/* Rotate X/Z about the pivot, preserving the output Y coordinate. */\nvoid func_1508EF80(f32 *point, f32 *pivot, f32 degrees, f32 *output) {\n    f32 dx, dz, radians, providerValue, z, x, cachedValue;\n    dx = point[0] - pivot[0];\n    radians = degrees * D_8009DC80;\n    dz = point[2] - pivot[2];\n    cachedValue = cosf(radians);\n    providerValue = sinf(radians);\n    x = providerValue * dz + cachedValue * dx;\n    x += pivot[0];\n    cachedValue = sinf(radians);\n    providerValue = cosf(radians);\n    z = providerValue * dz + (-cachedValue) * dx;\n    z += pivot[2];\n    output[0] = x;\n    output[2] = z;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected XZ pivot rotation diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('XZ pivot rotation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 start,end=function_span(before,FUNCTION)
 if before[start:end]!='s32 func_1508EF80() {\n    return 0;\n}':raise ValueError('XZ rotation placeholder changed')
 after=before[:start]+SELECTED.rstrip()+before[end:]
 if after.count('s32 func_1508EF80();')!=1:raise ValueError('XZ rotation prototype changed')
 return after.replace('s32 func_1508EF80();','void func_1508EF80(f32 *, f32 *, f32, f32 *);',1).replace('/* Generated placeholder declarations. */',DECLARATIONS+'/* Generated placeholder declarations. */',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_BC430/func_1508EF80.s. */\n','',1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('XZ pivot rotation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('XZ pivot rotation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('XZ pivot rotation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('XZ pivot rotation live input differs: '+name)
    return values

METADATA_GROUPS=((2947764, ('D_8009DC80', 'D_80098850', 'D_8009D3D0'), (1, 2, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('XZ pivot rotation named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('XZ pivot rotation symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('XZ pivot rotation metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('XZ pivot rotation frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('XZ pivot rotation original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('XZ pivot rotation strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('XZ pivot rotation named definitions changed')

NEW_GUARDS=[{'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x20', 'expected': '0xC42A0000', 'replacement': '0x46062201', 'expected_relocations': 'R_MIPS_LO16:D_8009DC80', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x24', 'expected': '0x46062201', 'replacement': '0xC4240000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_8009DC80', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x28', 'expected': '0x460A7502', 'replacement': '0xE7A8003C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x2C', 'expected': '0xE7A8003C', 'replacement': '0x46047502', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x30', 'expected': '0xC4B20008', 'replacement': '0xC4B00008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x34', 'expected': '0xC4900008', 'replacement': '0xC48A0008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x3C', 'expected': '0x46128101', 'replacement': '0x46105481', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_BC430', 'function': 'func_1508EF80', 'offset': '0x48', 'expected': '0xE7A40038', 'replacement': '0xE7B20038', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed XZ pivot rotation opening schedule and volatile-FP allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('XZ rotation scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('XZ rotation preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('XZ rotation binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='5926c24d93ff52d68ec35f87f1c9fc90fefe25a3f1ac43500973e27aa3b2e8d7'or rs!=ORIGINAL_BINDINGS:raise ValueError('XZ rotation result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1508EF80.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_BC430.c.o', 'make-shadow/src/game_BC430.c.o.compact', 'make-shadow/src/game_BC430.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('XZ pivot rotation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('XZ pivot rotation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('XZ pivot rotation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('XZ pivot rotation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('XZ pivot rotation Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_BC430.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('XZ pivot rotation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=8 or q['exclusions']!=0:raise ValueError('XZ pivot rotation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('XZ pivot rotation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('XZ pivot rotation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,reachable_words=55,frame=64,alignment_words=1,slot_words=56,strict_first_link_reproduced=True,guards=8,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0d1b6200117db2da46587d9776ac0a8e1c7701849dd2020c6b21a92ffae6637b'
