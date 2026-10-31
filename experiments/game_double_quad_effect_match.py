"""Double quad effect: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15166118','generated_193430'
ENTRY,ROM,BODY,SIZE=(353788184, 1652168, 236, 236)
SOURCE='conker/src/game/generated_193430.c'
OBJECT='conker/build/src/game/generated_193430.c.o'
ASM='conker/asm/193430.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-double-quad-effect-15166118-match'
RODATA_SYMBOL=None
RAW_SHA='4bc9600552b598d31f73f62238c188ceeec99b4b3dc9ae3c913730a38808ed8e'
SNAPSHOT_SHA='6d19ff9c1eec14213d558f3b2634801a821fa568047913140b404b4f2931073a'
BEFORE_ELF_SHA='62a0323d8390580412174769d2b02b39a99834e672f7f1e92ae6c48971025452'
TRUTH_SHA='69dbd77c5d3dddbb7663c0128a04f237f7250562fd26b7e5c6e74df51fa25b85'
BINDINGS={52: [('R_MIPS_26', 'func_15167A68')], 212: [('R_MIPS_26', 'func_1517E05C')]}
ORIGINAL_BINDINGS={52: [('R_MIPS_26', 'func_15167A68')], 212: [('R_MIPS_26', 'func_1517E05C')]}
HEADERS='#include <ultra64.h>\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\nvoid func_1517E05C(s32, s32, s32);\n'
DECLARATIONS='void *func_15167A68(s32, s32, s32, s32, u8, u8);\nvoid func_1517E05C(s32, s32, s32);\n'
SELECTED="/* Initialize two quads and publish the effect's world-coordinate origin. */\nvoid func_15166118(s32 first, s32 second, s32 x, s32 y, s32 z,\n                   s32 step, s32 lifetime, s32 mode, u8 selector, s32 category) {\n    u8 *created;\n    u8 *vertices;\n    s32 quad;\n\n    created = (u8 *)func_15167A68(4, category, 0xA8, 1, selector, 1);\n    if (created != NULL) {\n        created[0x95] = 2;\n        vertices = created;\n        quad = 0;\n        do {\n            quad++;\n            vertices += 0x40;\n            *(s16 *)(vertices - 0x28) = 0x2000;\n            *(s16 *)(vertices - 0x26) = 0x2000;\n            *(s16 *)(vertices - 0x18) = 0x2800;\n            *(s16 *)(vertices - 0x16) = 0x2000;\n            *(s16 *)(vertices - 0x8) = 0x2800;\n            *(s16 *)(vertices - 0x6) = 0x2800;\n            *(s16 *)(vertices + 0x8) = 0x2000;\n            *(s16 *)(vertices + 0xA) = 0x2800;\n        } while (quad != 2);\n        *(s16 *)(created + 0x9E) = 1;\n        created[0x92] = lifetime;\n        created[0x93] = lifetime;\n        *(s16 *)(created + 0x98) = x;\n        *(s16 *)(created + 0x9A) = y;\n        *(s16 *)(created + 0x9C) = z;\n        *(s16 *)(created + 0x96) = step;\n        created[0x94] = mode;\n        created[0xA0] = first;\n        created[0xA1] = second;\n        func_1517E05C(x, y, z);\n    }\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected double quad diagnostics')
    return 0




sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Double quad effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15166118() {\n    return 0;\n}':raise ValueError('Double quad placeholder changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]





def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Double quad effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Double quad effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Double quad effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Double quad effect live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Double quad effect named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Double quad effect symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Double quad effect metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Double quad effect frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Double quad effect original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Double quad effect strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Double quad effect named definitions changed')

NEW_GUARDS=[{'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x040', 'expected': '0x00403825', 'replacement': '0x00404025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x04C', 'expected': '0x00401825', 'replacement': '0x00003025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x050', 'expected': '0x00002825', 'replacement': '0x00401825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x054', 'expected': '0x24022000', 'replacement': '0x24070002', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x058', 'expected': '0x24060002', 'replacement': '0x24052800', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x05C', 'expected': '0x24042800', 'replacement': '0x24042000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x060', 'expected': '0x24A50001', 'replacement': '0x24C60001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x068', 'expected': '0xA462FFD8', 'replacement': '0xA464FFD8', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x06C', 'expected': '0xA462FFDA', 'replacement': '0xA464FFDA', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x070', 'expected': '0xA464FFE8', 'replacement': '0xA465FFE8', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x074', 'expected': '0xA462FFEA', 'replacement': '0xA464FFEA', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x078', 'expected': '0xA464FFF8', 'replacement': '0xA465FFF8', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x07C', 'expected': '0xA464FFFA', 'replacement': '0xA465FFFA', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x080', 'expected': '0xA4620008', 'replacement': '0xA4640008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x084', 'expected': '0x14A6FFF6', 'replacement': '0x14C7FFF6', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x088', 'expected': '0xA464000A', 'replacement': '0xA465000A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0A0', 'expected': '0xA4F9009E', 'replacement': '0xA519009E', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0A4', 'expected': '0xA0E20092', 'replacement': '0xA1020092', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0A8', 'expected': '0xA0E20093', 'replacement': '0xA1020093', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0AC', 'expected': '0xA4E40098', 'replacement': '0xA5040098', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0B0', 'expected': '0xA4E5009A', 'replacement': '0xA505009A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0B4', 'expected': '0xA4E6009C', 'replacement': '0xA506009C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0B8', 'expected': '0x8FA80034', 'replacement': '0x8FA90034', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0BC', 'expected': '0xA4E80096', 'replacement': '0xA5090096', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0C0', 'expected': '0x8FA9003C', 'replacement': '0x8FAA003C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0C4', 'expected': '0xA0E90094', 'replacement': '0xA10A0094', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0C8', 'expected': '0x8FAA0020', 'replacement': '0x8FAB0020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0CC', 'expected': '0xA0EA00A0', 'replacement': '0xA10B00A0', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0D0', 'expected': '0x8FAB0024', 'replacement': '0x8FAC0024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_15166118', 'offset': '0x0D8', 'expected': '0xA0EB00A1', 'replacement': '0xA10C00A1', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed allocator-result, quad-loop and parameter-store register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited double-quad guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Double-quad guards already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Double-quad normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw))
    encode=lambda rows:';'.join(kind+':'+symbol for kind,symbol in rows) if rows else '-'
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if words[at//4]!=int(row['expected'],0) or encode(bindings.get(at,[]))!=row['expected_relocations'] or row['expected_relocations']!=row['replacement_relocations']:raise ValueError('Double-quad preimage changed')
        words[at//4]=int(row['replacement'],0)
    result=struct.pack('>59I',*words)
    if sha(result)!=NORMALIZED_SHA or bindings!=ORIGINAL_BINDINGS:raise ValueError('Double-quad normalized bytes/bindings changed')
    return result,bindings


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15166118.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_193430.c.o', 'make-shadow/src/game/generated_193430.c.o.compact', 'make-shadow/src/game/generated_193430.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Double quad effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Double quad effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Double quad effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Double quad effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Double quad effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_193430.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Double quad effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=30 or q['exclusions']!=0:raise ValueError('Double quad effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Double quad effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Double quad effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=32,alignment_words=0,slot_words=57,strict_first_link_reproduced=True,guards=30,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='74fd8cbc1df3f5a9e34d214eca652a15d6b23aa5e7eed694f83a6fee23887744'

NORMALIZED_SHA='22dd5d656d0dceb2c41c6a542350ab4c7460c3f0cd084f534ca5fcacc3e0e080'


def register_proof(raw,truth):
 words=list(struct.unpack('>59I',raw));result=list(words)
 def rename(word,mapping):
  opcode=word>>26
  if opcode==3:return word
  if opcode==0:
   return (word&~0x03FFF800)|(mapping.get(word>>21&31,word>>21&31)<<21)|(mapping.get(word>>16&31,word>>16&31)<<16)|(mapping.get(word>>11&31,word>>11&31)<<11)
  if opcode not in(5,9,35,40,41):raise ValueError('Unexpected role interval instruction')
  return(word&~0x03FF0000)|(mapping.get(word>>21&31,word>>21&31)<<21)|(mapping.get(word>>16&31,word>>16&31)<<16)
 result[16]=rename(words[16],{7:8})
 loop={2:4,4:5,5:6,6:7}
 for retail,compiler in ((19,20),(21,22),(22,23),(23,21)):result[retail]=rename(words[compiler],loop)
 result[20]=words[19]
 for i in range(24,35):result[i]=rename(words[i],loop)
 for i in range(40,55):result[i]=rename(words[i],{7:8,8:9,9:10,10:11,11:12})
 if struct.pack('>59I',*result)!=truth:raise ValueError('Closed quad register intervals changed')
 return dict(closed_register_intervals=True,setup_permutation=[20,19,22,23,21],loop_interval=[24,34],store_interval=[40,54],no_immediate_control_flow_or_memory_offset_changes=True,unpassed_fourth_origin_argument_is_not_an_ABI_input=True)
