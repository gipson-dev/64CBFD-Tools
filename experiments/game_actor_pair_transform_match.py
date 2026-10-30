"""Actor pair transform: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151D5714','generated_200930'
ENTRY,ROM,BODY,SIZE=0x151D5714,0x202BC4,228,228
SOURCE='conker/src/game/generated_200930.c'
OBJECT='conker/build/src/game/generated_200930.c.o'
ASM='conker/asm/200930.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-pair-transform-151D5714-match'
RODATA_SYMBOL=None
RAW_SHA='ed1e22dea969b7b4540e08a91986f1f0ab292c91cfb909de661f3332b7dc8085'
SNAPSHOT_SHA='41a48ee79ad0ec876ebd4d908687edac0620d50cdbfe714ea721590ed1df3f96'
BEFORE_ELF_SHA='cf242df79321050b2fe148aa0057602caee2df153e8aa4ef621d0ba2ca284ef3'
TRUTH_SHA='02acd357ee611b349a79b51eed809d22e52769f7da349ba8415f59644e2cadf5'
BINDINGS={112: [('R_MIPS_26', 'func_15145EA4')], 204: [('R_MIPS_26', 'func_151D4408')]}
ORIGINAL_BINDINGS={112: [('R_MIPS_26', 'func_15145EA4')], 204: [('R_MIPS_26', 'func_151D4408')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nvoid func_15145EA4(struct17 **, struct17 **, u8 *, s32);\n/* Assembly consumer: pass the explicitly truncated selector as an ABI word. */\nvoid func_151D4408(struct17 *, struct17 *, void *, u8 *, f32, s32, s32);\n\n'
DECLARATIONS=''
SELECTED='/* Transform both points, then submit their origin and displacement. */\nvoid func_151D5714(struct127 *actor, f32 *first, f32 *second, s32 joint,\n                   f32 scale, s32 kind, s32 mode) {\n    struct17 origin;\n    struct17 direction;\n    u8 *matrix;\n    struct17 *inputs[2];\n    struct17 *outputs[2];\n\n    if (actor->unk1D4 != NULL && (actor->unk74 & 0xF) != 0xF) {\n        matrix = (u8 *)actor->unk1D4 + ((u8)joint << 6);\n        inputs[0] = (struct17 *)first;\n        inputs[1] = (struct17 *)second;\n        outputs[0] = &origin;\n        outputs[1] = &direction;\n        func_15145EA4(inputs, outputs, matrix, 2);\n        direction.unk0 -= origin.unk0;\n        direction.unk4 -= origin.unk4;\n        direction.unk8 -= origin.unk8;\n        func_151D4408(&origin, &direction, matrix, (u8 *)actor, scale, (u8)kind, mode);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor pair transform diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=228 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor pair transform body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_151D5714() {\n    return 0;\n}':raise ValueError('Actor pair placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n#include "structs.h"\n'
 if not after.startswith(prefix):raise ValueError('Actor pair owner includes changed')
 return HEADERS+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor pair transform snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor pair transform frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor pair transform predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor pair transform live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor pair transform named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor pair transform symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor pair transform metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor pair transform frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor pair transform original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor pair transform strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor pair transform named definitions changed')

NEW_GUARDS=[{'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x09C', 'expected': '0xC7AA0068', 'replacement': '0x8FA6003C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0A4', 'expected': '0x93AD006F', 'replacement': '0xE7B20044', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0A8', 'expected': '0x8FAE0070', 'replacement': '0x27A4004C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0AC', 'expected': '0x8FA6003C', 'replacement': '0x27A50040', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0B0', 'expected': '0xE7B20044', 'replacement': '0xE7A80048', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0B4', 'expected': '0xE7A80048', 'replacement': '0xC7AA0068', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0B8', 'expected': '0x27A4004C', 'replacement': '0x93AD006F', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_200930', 'function': 'func_151D5714', 'offset': '0x0BC', 'expected': '0x27A50040', 'replacement': '0x8FAE0070', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed disjoint stack-transfer and call-address schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited pair transform guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Actor pair transform scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('Actor pair transform preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('Actor pair transform binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='62f0f2b480c2db00d802a600148ba458d400911051082f7f6501e9edb03ca1f2'or rs!=ORIGINAL_BINDINGS:raise ValueError('Actor pair transform result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151D5714.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_200930.c.o', 'make-shadow/src/game/generated_200930.c.o.compact', 'make-shadow/src/game/generated_200930.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor pair transform artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor pair transform artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor pair transform raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor pair transform evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor pair transform Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_200930.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor pair transform Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=8 or q['exclusions']!=0:raise ValueError('Actor pair transform private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor pair transform changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor pair transform protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=57,reachable_words=57,frame=88,alignment_words=0,slot_words=57,strict_first_link_reproduced=True,guards=8,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='83eff6ee2618bda3f2a2777be3a4e340bfe53ec831854972a3eba9ca9f99b979'
