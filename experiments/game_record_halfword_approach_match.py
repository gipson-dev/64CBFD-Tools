"""Record halfword approach: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151193F4','generated_142560'
ENTRY,ROM,BODY,SIZE=0x151193F4,0x1468A4,224,224
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-record-halfword-approach-151193F4-match'
RODATA_SYMBOL=None
RAW_SHA='75ee1936079c6e53d007dab8bf6bd8939c4d9b8bdb6d7ab937b2acb7e96b92bb'
SNAPSHOT_SHA='691c8bad3c1436b3761025dbc305ad1c1e2260f7e447bead470fe32ed322567c'
BEFORE_ELF_SHA='1c987848c0ca140b5cb53c73495df96c74011d8e17df783e296b94c6ff164c1e'
TRUTH_SHA='04f2a46ec718998596a88ba7724c6b408f323f24453b2a0c5a391c0fdeff78ad'
BINDINGS={}
ORIGINAL_BINDINGS={}
HEADERS='#include <ultra64.h>\n\n'
DECLARATIONS=''
SELECTED='/* Approach the scaled signed halfword target and mark an already reached target. */\nvoid func_151193F4(u8 *record) {\n    s32 step;\n    s32 scale;\n    s32 origin;\n    s32 rate;\n    s32 target;\n    s32 current;\n    s32 difference;\n\n    if (*(s32 *)(record + 0x84) == 0) {\n        current = *(s16 *)(record + 0x12);\n        *(s32 *)(record + 0x84) = current | 0x80000000;\n    }\n    step = *(s32 *)(record + 0x7C);\n    if (step != 0) {\n        scale = *(s32 *)(record + 0x80);\n        origin = *(s32 *)(record + 0x84);\n        origin = (s16)origin;\n        rate = (*(s32 *)(record + 0x3C) >> 16) & 0xFFFF;\n        current = *(s16 *)(record + 0x12);\n        record[0x73] &= ~3;\n        target = (s32)((u32)rate * (u32)scale) / 256 + origin;\n        if (target != current) {\n            difference = current - target;\n            if (difference < 0) {\n                if (-difference < step) {\n                    *(s16 *)(record + 0x12) = target;\n                } else {\n                    *(s16 *)(record + 0x12) = (u32)current + (u32)step;\n                }\n            } else {\n                if (difference < step) {\n                    *(s16 *)(record + 0x12) = target;\n                } else {\n                    *(s16 *)(record + 0x12) = (u32)current - (u32)step;\n                }\n            }\n            record[0x73] |= 0;\n        } else {\n            record[0x73] |= 3;\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record halfword approach diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record halfword approach body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_151193F4() {\n    return 0;\n}':raise ValueError('Record halfword placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record halfword approach snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record halfword approach frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record halfword approach predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record halfword approach live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Record halfword approach named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Record halfword approach symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Record halfword approach metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record halfword approach frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record halfword approach original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record halfword approach strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record halfword approach named definitions changed')

NEW_GUARDS=[{'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xc', 'expected': '0x84820012', 'replacement': '0x848F0012', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x14', 'expected': '0x00417825', 'replacement': '0x01E1C025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x18', 'expected': '0xAC8F0084', 'replacement': '0xAC980084', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x30', 'expected': '0x8C860084', 'replacement': '0x8C990084', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x34', 'expected': '0x00074C03', 'replacement': '0x00075C03', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x38', 'expected': '0x312AFFFF', 'replacement': '0x316CFFFF', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x3c', 'expected': '0x01450019', 'replacement': '0x01850019', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x40', 'expected': '0x908B0073', 'replacement': '0x908D0073', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x44', 'expected': '0x0006C400', 'replacement': '0x00194C00', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x4c', 'expected': '0x0018CC03', 'replacement': '0x00095403', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x54', 'expected': '0x03203025', 'replacement': '0x01403025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x58', 'expected': '0x316CFFFC', 'replacement': '0x31AEFFFC', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x5c', 'expected': '0x01403825', 'replacement': '0x01803825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x60', 'expected': '0xA08C0073', 'replacement': '0xA08E0073', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x64', 'expected': '0x00006812', 'replacement': '0x00007812', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x68', 'expected': '0x05A10003', 'replacement': '0x05E10003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x6c', 'expected': '0x000D7203', 'replacement': '0x000FC203', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x70', 'expected': '0x25A100FF', 'replacement': '0x25E100FF', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x74', 'expected': '0x00017203', 'replacement': '0x0001C203', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x78', 'expected': '0x01C64021', 'replacement': '0x03064021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x7c', 'expected': '0x10480013', 'replacement': '0x11020013', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x8c', 'expected': '0x00057823', 'replacement': '0x0005C823', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x90', 'expected': '0x01E3082A', 'replacement': '0x0323082A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0x98', 'expected': '0x0043C021', 'replacement': '0x00434821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xa8', 'expected': '0xA4980012', 'replacement': '0xA4890012', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xb0', 'expected': '0x0043C823', 'replacement': '0x00435023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xbc', 'expected': '0xA4990012', 'replacement': '0xA48A0012', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xc0', 'expected': '0x90890073', 'replacement': '0x908B0073', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xc8', 'expected': '0xA0890073', 'replacement': '0xA08B0073', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xcc', 'expected': '0x908A0073', 'replacement': '0x908C0073', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xd0', 'expected': '0x354B0003', 'replacement': '0x358D0003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_142560', 'function': 'func_151193F4', 'offset': '0xd4', 'expected': '0xA08B0073', 'replacement': '0xA08D0073', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed halfword approach compiler temporary allocation and independent schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Halfword approach scope changed')
 checked_payload(raw,bindings);result=bytearray(raw)
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16)or row['expected_relocations']!='-'or row['replacement_relocations']!='-':raise ValueError('Halfword approach preimage/binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16))
 if sha(result)!='04f2a46ec718998596a88ba7724c6b408f323f24453b2a0c5a391c0fdeff78ad':raise ValueError('Halfword approach result changed')
 return bytes(result),{}

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151193F4.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_142560.c.o', 'make-shadow/src/game/generated_142560.c.o.compact', 'make-shadow/src/game/generated_142560.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record halfword approach artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record halfword approach artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record halfword approach raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record halfword approach evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record halfword approach Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_142560.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record halfword approach Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=32 or q['exclusions']!=0:raise ValueError('Record halfword approach private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record halfword approach changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record halfword approach protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=0,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=32,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='e3ffcb41fcab4c7903a30ec4d68584061b007f8b207de97dcf52fe0d101c802a'
