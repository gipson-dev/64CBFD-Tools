"""Resource status bit clear: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150A2864','generated_CDE80'
ENTRY,ROM,BODY,SIZE=0x150A2864,0xCFD14,220,220
SOURCE='conker/src/game/generated_CDE80.c'
OBJECT='conker/build/src/game/generated_CDE80.c.o'
ASM='conker/asm/CDE80.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-resource-status-bit-clear-match'
RODATA_SYMBOL=None
RAW_SHA='ea2b1dd09c88dfc58997c801eeb95ec093fc0d0b51eb6972c1a7380ba8d954f0'
SNAPSHOT_SHA='3935b10752a5cb3857afcdab18e2d981690874113d7721cca3e8d14a45c58b62'
BEFORE_ELF_SHA='a93e110f4776e19e1415de9eb0855e29dac775c0d794c8dce68cb8521b75917a'
TRUTH_SHA='130eac2e733f32cf4c99eadd299c6d9bce283a5edfcefb00446f633cbc03a14b'
BINDINGS={20: [('R_MIPS_HI16', 'D_800D3094')], 24: [('R_MIPS_LO16', 'D_800D3094')], 44: [('R_MIPS_HI16', 'D_800D3098')], 56: [('R_MIPS_LO16', 'D_800D3098')], 88: [('R_MIPS_HI16', 'D_800D30F0')], 128: [('R_MIPS_LO16', 'D_800D30F0')], 108: [('R_MIPS_HI16', 'D_800D3270')], 112: [('R_MIPS_LO16', 'D_800D3270')], 144: [('R_MIPS_26', '__ll_lshift')]}
ORIGINAL_BINDINGS={20: [('R_MIPS_HI16', 'D_800D3094')], 24: [('R_MIPS_LO16', 'D_800D3094')], 44: [('R_MIPS_HI16', 'D_800D3098')], 56: [('R_MIPS_LO16', 'D_800D3098')], 108: [('R_MIPS_HI16', 'D_800D3270')], 112: [('R_MIPS_LO16', 'D_800D3270')], 104: [('R_MIPS_HI16', 'D_800D30F0')], 116: [('R_MIPS_LO16', 'D_800D30F0')], 144: [('R_MIPS_26', '__ll_lshift')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    s16 origin0;\n    s16 origin1;\n    s16 origin2;\n    u8 pad6[0xF];\n    u8 flags;\n    u8 pad16;\n    u8 field17;\n    s32 field18;\n    s32 field1C;\n    s32 field20;\n    f32 coefficient0;\n    f32 scale;\n    f32 coefficient1;\n    f32 coefficient2;\n} GeneratedCDE80Record;\n\nextern GeneratedCDE80Record *D_800D3098;\nextern s32 D_800D3094;\nextern u64 D_800D30F0[];\nextern u64 D_800D3270[];\n\n'
DECLARATIONS='extern u64 D_800D30F0[];\nextern u64 D_800D3270[];\n\n'
SELECTED='/* Set a resource status byte and clear its bit from each active-set row. */\nvoid func_150A2864(u32 identity, s32 status) {\n    u64 *row;\n    u32 word;\n    u64 shift;\n\n    identity &= 0xFFF;\n    if (identity < (u32)D_800D3094) {\n        ((u8 *)&D_800D3098[identity])[0x14] = status;\n    }\n    if (status == 1) {\n        for (shift = identity & 0x3F, word = identity >> 6, row = D_800D30F0; ; ) {\n            row[word] = row[word] & ~(1ULL << shift);\n            row += 3;\n            if (row == D_800D3270) break;\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner diagnostics: '+text)
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Resource status bit clear body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150A2864() {\n    return 0;\n}':raise ValueError('Status actor mode placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Resource status bit clear snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Resource status bit clear frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Resource status bit clear predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Resource status bit clear live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Resource status bit clear named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Resource status bit clear symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Resource status bit clear metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Resource status bit clear frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Resource status bit clear original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Resource status bit clear strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Resource status bit clear named definitions changed')

NEW_GUARDS=[{'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x058', 'expected': '0x3C100000', 'replacement': '0x3089003F', 'expected_relocations': 'R_MIPS_HI16:D_800D30F0', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x064', 'expected': '0x3089003F', 'replacement': '0x240A0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x068', 'expected': '0x240A0000', 'replacement': '0x3C100000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_HI16:D_800D30F0', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x074', 'expected': '0xAFAA0028', 'replacement': '0x26100000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800D30F0', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x078', 'expected': '0xAFA9002C', 'replacement': '0xAFAA0028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x080', 'expected': '0x26100000', 'replacement': '0xAFA9002C', 'expected_relocations': 'R_MIPS_LO16:D_800D30F0', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x09C', 'expected': '0x8C980000', 'replacement': '0x8C8E0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x0A0', 'expected': '0x8C990004', 'replacement': '0x8C8F0004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x0A4', 'expected': '0x00407027', 'replacement': '0x0040C027', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_CDE80', 'function': 'func_150A2864', 'offset': '0x0A8', 'expected': '0x00607827', 'replacement': '0x0060C827', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent bit-clear setup and closed temporary register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before+b'generated_CDE80,func_150A2864,0x058,0x3C100000,0x3089003F,R_MIPS_HI16:D_800D30F0,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x064,0x3089003F,0x240A0000,-,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x068,0x240A0000,0x3C100000,-,R_MIPS_HI16:D_800D30F0,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x074,0xAFAA0028,0x26100000,-,R_MIPS_LO16:D_800D30F0,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x078,0xAFA9002C,0xAFAA0028,-,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x080,0x26100000,0xAFA9002C,R_MIPS_LO16:D_800D30F0,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x09C,0x8C980000,0x8C8E0000,-,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x0A0,0x8C990004,0x8C8F0004,-,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x0A4,0x00407027,0x0040C027,-,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\ngenerated_CDE80,func_150A2864,0x0A8,0x00607827,0x0060C827,-,-,Normalize independent bit-clear setup and closed temporary register allocation,,,false\r\n'





def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw);rels=dict(bindings)
    parse=lambda value:[]if value=='-'else[tuple(x.split(':',1))for x in value.split(';')]
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0)or rels.get(at,[])!=parse(row['expected_relocations']):raise ValueError('Bit-clear guard preimage changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0));rels.pop(at,None)
        if parse(row['replacement_relocations']):rels[at]=parse(row['replacement_relocations'])
    if sha(result)!='f90a4a3132ad5c01eb2084fd5c80d1f2e7ef07f339d2c0918b2c69ce12d92b61'or rels!=ORIGINAL_BINDINGS:raise ValueError('Bit-clear normalized words or bindings changed')
    return bytes(result),rels


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150A2864.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_CDE80.c.o', 'make-shadow/src/game/generated_CDE80.c.o.compact', 'make-shadow/src/game/generated_CDE80.c.o.padded.s', 'make-shadow/src/game/generated_CDE80.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Resource status bit clear artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource status bit clear artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource status bit clear raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Resource status bit clear evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource status bit clear Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_CDE80.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Resource status bit clear Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=10 or q['exclusions']!=0:raise ValueError('Resource status bit clear private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Resource status bit clear changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Resource status bit clear protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,frame=64,alignment_words=0,slot_words=55,strict_first_link_reproduced=True,guards=10,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
