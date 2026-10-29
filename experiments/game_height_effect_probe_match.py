"""Height effect probe: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151A99D0','generated_1D6E80'
ENTRY,ROM,BODY,SIZE=0x151A99D0,0x1D6E80,212,212
SOURCE='conker/src/game/generated_1D6E80.c'
OBJECT='conker/build/src/game/generated_1D6E80.c.o'
ASM='conker/asm/1D6E80.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-height-effect-probe-match'
RODATA_SYMBOL=None
RAW_SHA='75087c54184f587b84c8de9364b80efd9a941ac77b58815dbe0937d99b638683'
SNAPSHOT_SHA='c21c165e19563aa8a07e63f983be5eaef3f1e298c8db8937d5c4555619b41d2c'
BEFORE_ELF_SHA='b78eb6e337b9812eafa3e14a4ec40998c965ae6270022da158df5c20d34ed69f'
TRUTH_SHA='99742da01b260cb8de9f1f54a5e71356354d41f162bae5af4b462b836d8dad56'
BINDINGS={20: [('R_MIPS_HI16', 'D_800A8F74')], 24: [('R_MIPS_LO16', 'D_800A8F74')], 144: [('R_MIPS_26', 'func_15045800')], 184: [('R_MIPS_26', 'func_151ABE40')]}
ORIGINAL_BINDINGS={24: [('R_MIPS_HI16', 'D_800A8F74')], 28: [('R_MIPS_LO16', 'D_800A8F74')], 144: [('R_MIPS_26', 'func_15045800')], 184: [('R_MIPS_26', 'func_151ABE40')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A8F74;\ns32 func_15045800(f32 *, u16, f32, void *);\nvoid func_151ABE40(f32 *, void *, s32, u8, s32);\n'
DECLARATIONS='extern f32 D_800A8F74;\ns32 func_15045800(f32 *, u16, f32, void *);\nvoid func_151ABE40(f32 *, void *, s32, u8, s32);\n'
SELECTED='/* Probe below the attached actor and submit a height-aligned effect on a hit. */\nvoid func_151A99D0(u8 *input) {\n    u8 *owner = input;\n    f32 position[3];\n    u8 *actor;\n\n    actor = *(u8 **)(owner + 0x18);\n    position[0] = *(f32 *)(actor + 0x14);\n    if (D_800A8F74 < *(f32 *)(actor + 0x118)) {\n        position[1] = *(f32 *)(actor + 0x118) + 100.0f;\n    } else {\n        position[1] = *(f32 *)(actor + 0x18) + 150.0f;\n    }\n    position[2] = *(f32 *)(actor + 0x1C);\n    if (func_15045800(position, 0, position[1] - 300.0f, owner + 0x34)) {\n        position[1] = *(f32 *)(owner + 0x34);\n        func_151ABE40(position, owner + 0x34, 3, owner[0xC], owner[1]);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Height effect probe owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Height effect probe body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_151A99D0() {\n    return 0;\n}':raise ValueError('Height effect placeholder changed')
    after=before[:start]+SELECTED.rstrip()+before[end:]
    if after.count('#include "structs.h"')!=1:raise ValueError('Height effect declaration anchor changed')
    return after.replace('#include "structs.h"','#include "structs.h"\n'+DECLARATIONS,1)



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Height effect probe snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Height effect probe frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Height effect probe predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Height effect probe live input differs: '+name)
    return values

METADATA_GROUPS=((0x2CBEA4,('D_800A8F74','D_800A8B24','D_800A4124','D_800A0074','D_8009F784','D_8009BB24'),(1,2,3,4,5,0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Height-effect named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Height-effect symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Height-effect metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Height effect probe frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Height effect probe original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Height effect probe strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Height effect probe named definitions changed')

NEW_GUARDS=[{'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x014', 'expected': '0x3C010000', 'replacement': '0xC4440014', 'expected_relocations': 'R_MIPS_HI16:D_800A8F74', 'replacement_relocations': '-', 'note': 'Normalize independent height probe setup schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x018', 'expected': '0xC4260000', 'replacement': '0x3C010000', 'expected_relocations': 'R_MIPS_LO16:D_800A8F74', 'replacement_relocations': 'R_MIPS_HI16:D_800A8F74', 'note': 'Normalize independent height probe setup schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x01C', 'expected': '0xC4440014', 'replacement': '0xC4260000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800A8F74', 'note': 'Normalize independent height probe setup schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x020', 'expected': '0x3C014316', 'replacement': '0xE7A40030', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent height probe setup schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x024', 'expected': '0xE7A40030', 'replacement': '0xC4400118', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent height probe setup schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x028', 'expected': '0xC4400118', 'replacement': '0x3C014316', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent height probe setup schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x080', 'expected': '0xAFA70028', 'replacement': '0xAFA7002C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed height-result pointer spill slot', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_1D6E80', 'function': 'func_151A99D0', 'offset': '0x0A4', 'expected': '0x8FA50028', 'replacement': '0x8FA5002C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed height-result pointer spill slot', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='3f3a4015a2e3845fc8ffcf588757807a4d0f1b5a7347baabc3e279974603acf2':raise ValueError('Height effect inherited guards changed')
    return before+b'generated_1D6E80,func_151A99D0,0x014,0x3C010000,0xC4440014,R_MIPS_HI16:D_800A8F74,-,Normalize independent height probe setup schedule,,,false\r\ngenerated_1D6E80,func_151A99D0,0x018,0xC4260000,0x3C010000,R_MIPS_LO16:D_800A8F74,R_MIPS_HI16:D_800A8F74,Normalize independent height probe setup schedule,,,false\r\ngenerated_1D6E80,func_151A99D0,0x01C,0xC4440014,0xC4260000,-,R_MIPS_LO16:D_800A8F74,Normalize independent height probe setup schedule,,,false\r\ngenerated_1D6E80,func_151A99D0,0x020,0x3C014316,0xE7A40030,-,-,Normalize independent height probe setup schedule,,,false\r\ngenerated_1D6E80,func_151A99D0,0x024,0xE7A40030,0xC4400118,-,-,Normalize independent height probe setup schedule,,,false\r\ngenerated_1D6E80,func_151A99D0,0x028,0xC4400118,0x3C014316,-,-,Normalize independent height probe setup schedule,,,false\r\ngenerated_1D6E80,func_151A99D0,0x080,0xAFA70028,0xAFA7002C,-,-,Normalize closed height-result pointer spill slot,,,false\r\ngenerated_1D6E80,func_151A99D0,0x0A4,0x8FA50028,0x8FA5002C,-,-,Normalize closed height-result pointer spill slot,,,false\r\n'


def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw);relocations=dict(bindings)
    parse=lambda text:[]if text=='-'else[tuple(v.split(':',1))for v in text.split(';')]
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0)or bindings.get(at,[])!=parse(row['expected_relocations']):raise ValueError('Height effect expected word or binding changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0));relocations.pop(at,None)
        if row['replacement_relocations']!='-':relocations[at]=parse(row['replacement_relocations'])
    if sha(result)!='9c2a9c66decd1100f1a08707523b364cb59c60073da9f216daab912c37414f4e'or relocations!=ORIGINAL_BINDINGS:raise ValueError('Height effect normalized body/bindings changed')
    return bytes(result),relocations



ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151A99D0.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_1D6E80.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1D6E80.c.o","make-shadow/src/game/generated_1D6E80.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Height effect probe artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Height effect probe artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Height effect probe raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Height effect probe evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Height effect probe Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1D6E80.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Height effect probe Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=8 or q['exclusions']!=0:raise ValueError('Height effect probe private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Height effect probe changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Height effect probe protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=64,alignment_words=0,slot_words=53,strict_first_link_reproduced=True,guards=8,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
