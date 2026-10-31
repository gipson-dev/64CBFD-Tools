"""Slot actor refresh: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1501DE18','generated_49D30'
ENTRY,ROM,BODY,SIZE=(352443928, 307912, 236, 236)
SOURCE='conker/src/game/generated_49D30.c'
OBJECT='conker/build/src/game/generated_49D30.c.o'
ASM='conker/asm/49D30.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-slot-actor-refresh-1501DE18-match'
RODATA_SYMBOL=None
RAW_SHA='9e59d627f5ab2ee2a1acb596ac79b423eb3745671b95e662df52828956e74408'
SNAPSHOT_SHA='90a92a2a8f7e067775925dca832cedb4aad397d18057a96c9118928d7d99d809'
BEFORE_ELF_SHA='e269ee9d742947ddf7c03f010390773904c4b44628202386fedd6878695b9821'
TRUTH_SHA='6e894a31bd748127c908c1c3b09d9e8de92dd06fd932a7b3460fdc5ca533ccce'
BINDINGS={36: [('R_MIPS_HI16', 'D_800C3640')], 52: [('R_MIPS_LO16', 'D_800C3640')], 44: [('R_MIPS_HI16', 'D_800BEA08')], 48: [('R_MIPS_LO16', 'D_800BEA08')], 56: [('R_MIPS_HI16', 'D_800C35B0')], 68: [('R_MIPS_LO16', 'D_800C35B0')], 76: [('R_MIPS_26', 'func_150242F8')], 84: [('R_MIPS_26', 'func_1501EC38')], 96: [('R_MIPS_26', 'func_150242F8')], 104: [('R_MIPS_26', 'func_15020EC4')], 112: [('R_MIPS_HI16', 'D_800CC2D0')], 120: [('R_MIPS_LO16', 'D_800CC2D0')], 116: [('R_MIPS_HI16', 'D_800C3E78')], 128: [('R_MIPS_LO16', 'D_800C3E78')], 152: [('R_MIPS_26', 'func_150229E4')], 172: [('R_MIPS_26', 'func_1502178C')], 196: [('R_MIPS_26', 'func_1501E81C')]}
ORIGINAL_BINDINGS={44: [('R_MIPS_HI16', 'D_800BEA08')], 48: [('R_MIPS_LO16', 'D_800BEA08')], 36: [('R_MIPS_HI16', 'D_800C3640')], 52: [('R_MIPS_LO16', 'D_800C3640')], 56: [('R_MIPS_HI16', 'D_800C35B0')], 68: [('R_MIPS_LO16', 'D_800C35B0')], 76: [('R_MIPS_26', 'func_150242F8')], 84: [('R_MIPS_26', 'func_1501EC38')], 96: [('R_MIPS_26', 'func_150242F8')], 104: [('R_MIPS_26', 'func_15020EC4')], 116: [('R_MIPS_HI16', 'D_800C3E78')], 120: [('R_MIPS_LO16', 'D_800C3E78')], 112: [('R_MIPS_HI16', 'D_800CC2D0')], 124: [('R_MIPS_LO16', 'D_800CC2D0')], 152: [('R_MIPS_26', 'func_150229E4')], 172: [('R_MIPS_26', 'func_1502178C')], 196: [('R_MIPS_26', 'func_1501E81C')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern s32 D_800C3640[], D_800C35B0[], D_800BEA08;\nextern struct127 D_800CC2D0[];\nextern u8 D_800C3E78;\ns32 func_150242F8();\ns32 func_1501EC38();\ns32 func_15020EC4();\ns32 func_150229E4();\ns32 func_1502178C();\ns32 func_1501E81C();\n'
DECLARATIONS='extern s32 D_800C3640[], D_800C35B0[], D_800BEA08;\nextern struct127 D_800CC2D0[];\nextern u8 D_800C3E78;\ns32 func_150242F8();\ns32 func_1501EC38();\ns32 func_15020EC4();\ns32 func_150229E4();\ns32 func_1502178C();\ns32 func_1501E81C();\n'
SELECTED='/* Advance the slot timestamp and refresh the 25 active actor records. */\nvoid func_1501DE18(s32 slot) {\n    struct127 *actor;\n    s32 index;\n    u8 limit;\n\n    D_800C35B0[slot] = (u32)D_800C3640[slot] + (u32)D_800BEA08;\n    func_150242F8(1, 0);\n    func_1501EC38(0);\n    func_150242F8(0, 0);\n    func_15020EC4(0);\n    actor = D_800CC2D0;\n    index = 0;\n    limit = 25;\n    do {\n        if (actor->interaction_state != 0) {\n            D_800C3E78 = index;\n            if (func_150229E4(actor) != 0) {\n                func_1502178C(actor, slot, -1);\n            }\n        }\n        index++;\n        actor++;\n    } while (index != limit);\n    func_1501E81C(1, slot);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected slot refresh diagnostics')
    return 0




sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Slot actor refresh body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_1501DE18() {\n    return 0;\n}':raise ValueError('Slot refresh placeholder changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]





def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Slot actor refresh snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Slot actor refresh frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Slot actor refresh predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Slot actor refresh live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Slot actor refresh named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Slot actor refresh symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Slot actor refresh metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Slot actor refresh frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Slot actor refresh original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Slot actor refresh strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Slot actor refresh named definitions changed')

NEW_GUARDS=[{'filename': 'generated_49D30', 'function': 'func_1501DE18', 'offset': '0x078', 'expected': '0x26100000', 'replacement': '0x26730000', 'expected_relocations': 'R_MIPS_LO16:D_800CC2D0', 'replacement_relocations': 'R_MIPS_LO16:D_800C3E78', 'note': 'Rotate independent actor-address, index initialization and index-address setup', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1501DE18', 'offset': '0x07C', 'expected': '0x00008825', 'replacement': '0x26100000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800CC2D0', 'note': 'Rotate independent actor-address, index initialization and index-address setup', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1501DE18', 'offset': '0x080', 'expected': '0x26730000', 'replacement': '0x00008825', 'expected_relocations': 'R_MIPS_LO16:D_800C3E78', 'replacement_relocations': '-', 'note': 'Rotate independent actor-address, index initialization and index-address setup', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited slot-refresh guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Owner-matrix guards already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Slot refresh normalization scope changed')
 checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw));result_bindings={at:list(rows)for at,rows in bindings.items()}
 encode=lambda rows:';'.join(kind+':'+symbol for kind,symbol in rows)if rows else '-'
 for row in NEW_GUARDS:
  at=int(row['offset'],0)
  if words[at//4]!=int(row['expected'],0)or encode(bindings.get(at,[]))!=row['expected_relocations']:raise ValueError('Slot refresh word/binding preimage changed')
  words[at//4]=int(row['replacement'],0);replacements=row['replacement_relocations']
  if replacements=='-':result_bindings.pop(at,None)
  else:result_bindings[at]=[tuple(item.split(':',1))for item in replacements.split(';')]
 result=struct.pack('>59I',*words)
 if sha(result)!=NORMALIZED_SHA or result_bindings!=ORIGINAL_BINDINGS:raise ValueError('Slot refresh normalized bytes/bindings changed')
 return result,result_bindings


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1501DE18.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_49D30.c.o', 'make-shadow/src/game/generated_49D30.c.o.compact', 'make-shadow/src/game/generated_49D30.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Slot actor refresh artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Slot actor refresh artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Slot actor refresh raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Slot actor refresh evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Slot actor refresh Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_49D30.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Slot actor refresh Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=3 or q['exclusions']!=0:raise ValueError('Slot actor refresh private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Slot actor refresh changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Slot actor refresh protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=48,alignment_words=0,slot_words=57,strict_first_link_reproduced=True,guards=3,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='e96aaa6510a4295c7adb0ebc9173d5b245a381a11cf32f94fa470c9b7eeae2f9'

NORMALIZED_SHA='7436b4cc63757cc52b75ce3dcf3301fad8ae7d8a94815784a74fddeb28b92228'


def schedule_proof(raw,bindings,truth,retail_bindings):
 before=list(struct.unpack('>59I',raw));after=list(before);after[30:33]=[before[32],before[30],before[31]];expected={at:list(rows)for at,rows in bindings.items()}
 for destination,original in((120,128),(124,120),(128,124)):
  if original in bindings:expected[destination]=list(bindings[original])
  else:expected.pop(destination,None)
 if struct.pack('>59I',*after)!=truth or expected!=retail_bindings:raise ValueError('Independent slot setup permutation changed')
 return dict(independent_setup_rotation=True,word_indices=[30,31,32],permutation=[32,30,31],relocated_LO16_symbols=['D_800CC2D0','D_800C3E78'],HI16_preimages_preserved=True,no_control_or_memory_access_changes=True)
