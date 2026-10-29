"""Coordinate query result: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1510F648','generated_13BB20'
ENTRY,ROM,BODY,SIZE=0x1510F648,0x13CAF8,216,216
SOURCE='conker/src/game/generated_13BB20.c'
OBJECT='conker/build/src/game/generated_13BB20.c.o'
ASM='conker/asm/13BB20.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-coordinate-query-result-match'
RODATA_SYMBOL=None
RAW_SHA='d5b9038b9b31afb6bb2992ef5fc33c79b33d21376b0427a3a4f608130ddcc516'
SNAPSHOT_SHA='8c8530d353b57e0c784daec5832a9a3134c77c01d3074c928eb5985e5af5d4b6'
BEFORE_ELF_SHA='692e7be29460a38b1ce062efad943258255441cbfd18a1e6eb116a262e59bfa8'
TRUTH_SHA='ce64c90cc755646bdceb9193bd64e7fea34ed18d9318c53f0e3fa6fce5c89090'
BINDINGS={20: [('R_MIPS_26', 'func_1510F800')], 96: [('R_MIPS_26', 'func_150A64C8')], 104: [('R_MIPS_HI16', 'D_800D3830')], 108: [('R_MIPS_LO16', 'D_800D3830')], 116: [('R_MIPS_26', 'func_150A44F0')], 124: [('R_MIPS_HI16', 'D_800D3830')], 128: [('R_MIPS_LO16', 'D_800D3830')], 140: [('R_MIPS_26', 'func_150A43E0')], 156: [('R_MIPS_HI16', 'D_800D3300')], 160: [('R_MIPS_LO16', 'D_800D3300')], 196: [('R_MIPS_HI16', 'D_800A2D98')], 200: [('R_MIPS_LO16', 'D_800A2D98')]}
ORIGINAL_BINDINGS={20: [('R_MIPS_26', 'func_1510F800')], 96: [('R_MIPS_26', 'func_150A64C8')], 104: [('R_MIPS_HI16', 'D_800D3830')], 108: [('R_MIPS_LO16', 'D_800D3830')], 116: [('R_MIPS_26', 'func_150A44F0')], 124: [('R_MIPS_HI16', 'D_800D3830')], 128: [('R_MIPS_LO16', 'D_800D3830')], 140: [('R_MIPS_26', 'func_150A43E0')], 156: [('R_MIPS_HI16', 'D_800D3300')], 160: [('R_MIPS_LO16', 'D_800D3300')], 196: [('R_MIPS_HI16', 'D_800A2D98')], 200: [('R_MIPS_LO16', 'D_800A2D98')]}
HEADERS='#include <ultra64.h>\nextern u8 D_800D3830[];\nextern s32 D_800D3300;\nextern f32 D_800A2D98;\nvoid func_1510F800(s32);\ns32 func_150A64C8(s16, s16, s32 *, s32);\nvoid func_150A44F0(s32, void *, s32);\ns32 func_150A43E0(s32, s32, s32, void *);\n\n'
DECLARATIONS='extern u8 D_800D3830[];\nextern s32 D_800D3300;\nextern f32 D_800A2D98;\nvoid func_1510F800(s32);\ns32 func_150A64C8(s16, s16, s32 *, s32);\nvoid func_150A44F0(s32, void *, s32);\ns32 func_150A43E0(s32, s32, s32, void *);\n\n'
SELECTED="/* Return the coordinate query's scaled result, or its fallback value. */\nf32 func_1510F648(f32 x, f32 y, f32 z) {\n    s32 intX, intZ, value;\n    f32 result;\n\n    func_1510F800(2);\n    intX = x;\n    intZ = z;\n    func_150A64C8(intX, intZ, &value, (s32)y);\n    func_150A44F0(value, D_800D3830, 0);\n    if (func_150A43E0(intX, intZ, value, D_800D3830)) {\n        result = D_800D3300 * (1.0f / 256.0f);\n    } else {\n        result = D_800A2D98;\n    }\n    return result;\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Coordinate query result owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('State-completion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1510F648() {\n    return 0;\n}':raise ValueError('Coordinate query result placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Coordinate query result snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Coordinate query result frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Coordinate query result predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Coordinate query result live input differs: '+name)
    return values

METADATA_GROUPS=((2859188, ('D_800A2D98', 'D_80090AD8', 'D_80090598'), (1, 2, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Coordinate query result named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Coordinate query result symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Coordinate query result metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Coordinate query result frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Coordinate query result original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Coordinate query result strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Coordinate query result named definitions changed')

NEW_GUARDS=[{'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x02C', 'expected': '0x27A60024', 'replacement': '0x27A60028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x05C', 'expected': '0xAFA2001C', 'replacement': '0xAFA20020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x064', 'expected': '0xAFA30018', 'replacement': '0xAFA3001C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x070', 'expected': '0x8FA40024', 'replacement': '0x8FA40028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x084', 'expected': '0x8FA4001C', 'replacement': '0x8FA40020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x088', 'expected': '0x8FA50018', 'replacement': '0x8FA5001C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_13BB20', 'function': 'func_1510F648', 'offset': '0x090', 'expected': '0x8FA60024', 'replacement': '0x8FA60028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed coordinate-query local slots within the unchanged frame', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='69df0bc02f824de16817dd7c82f0c129e394d4f7d31d47c8c27b0793fc2067aa':raise ValueError('Inherited guard manifest changed')
    return before+b'generated_13BB20,func_1510F648,0x02C,0x27A60024,0x27A60028,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\ngenerated_13BB20,func_1510F648,0x05C,0xAFA2001C,0xAFA20020,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\ngenerated_13BB20,func_1510F648,0x064,0xAFA30018,0xAFA3001C,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\ngenerated_13BB20,func_1510F648,0x070,0x8FA40024,0x8FA40028,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\ngenerated_13BB20,func_1510F648,0x084,0x8FA4001C,0x8FA40020,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\ngenerated_13BB20,func_1510F648,0x088,0x8FA50018,0x8FA5001C,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\ngenerated_13BB20,func_1510F648,0x090,0x8FA60024,0x8FA60028,-,-,Normalize closed coordinate-query local slots within the unchanged frame,,,false\r\n'





def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw)
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0) or at in bindings:raise ValueError('Coordinate-query guard preimage changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0))
    if sha(result)!='bed2a7438e47427c4971dca6848399734d0184fc6a23e1152ba524007028597d' or bindings!=ORIGINAL_BINDINGS:raise ValueError('Coordinate-query normalized output changed')
    return bytes(result),bindings



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1510F648.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_13BB20.c.o', 'make-shadow/src/game/generated_13BB20.c.o.compact', 'make-shadow/src/game/generated_13BB20.c.o.padded.s', 'new-guards.json', 'make-shadow/src/game/generated_13BB20.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Coordinate query result artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Coordinate query result artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Coordinate query result raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Coordinate query result evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Coordinate query result Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_13BB20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Coordinate query result Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=7 or q['exclusions']!=0:raise ValueError('Coordinate query result private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Coordinate query result changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Coordinate query result protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=48,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=7,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
