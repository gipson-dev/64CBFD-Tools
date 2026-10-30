"""Active actor update: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1502378C','generated_49D30'
ENTRY,ROM,BODY,SIZE=0x1502378C,0x50C3C,216,228
SOURCE='conker/src/game/generated_49D30.c'
OBJECT='conker/build/src/game/generated_49D30.c.o'
ASM='conker/asm/49D30.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-active-actor-update-1502378C-match'
RODATA_SYMBOL=None
RAW_SHA='4c2483c85c70abd830138f1cb4f7a0490a49fcb3baf07731a07192ec196df0d8'
SNAPSHOT_SHA='6dd3c9025ddce3d91a9ba103f87a09d8139db3dbc6e6c8f4ecc5f33cf42dde16'
BEFORE_ELF_SHA='d712b807e2feff412e14d72e437dc0e0170e0ef533df79882f4de5bf7f07a1df'
TRUTH_SHA='b79d8c8945079f304e9cb9e73313c096ad8b9b4d027d7d8be0735028050b4df2'
BINDINGS={36: [('R_MIPS_HI16', 'D_800CC2D0')], 40: [('R_MIPS_LO16', 'D_800CC2D0')], 28: [('R_MIPS_HI16', 'D_800C3654')], 32: [('R_MIPS_LO16', 'D_800C3654')], 52: [('R_MIPS_26', 'func_1504A730')], 68: [('R_MIPS_HI16', 'D_800C3E78')], 72: [('R_MIPS_LO16', 'D_800C3E78')], 100: [('R_MIPS_26', 'func_15022998')], 108: [('R_MIPS_26', 'func_1507E73C')], 116: [('R_MIPS_26', 'func_150229E4')], 136: [('R_MIPS_26', 'func_1502178C')], 144: [('R_MIPS_26', 'func_150627D4')], 152: [('R_MIPS_26', 'func_1507FEA0')], 176: [('R_MIPS_26', 'func_15061B4C')]}
ORIGINAL_BINDINGS={28: [('R_MIPS_HI16', 'D_800C3654')], 32: [('R_MIPS_LO16', 'D_800C3654')], 36: [('R_MIPS_HI16', 'D_800CC2D0')], 40: [('R_MIPS_LO16', 'D_800CC2D0')], 52: [('R_MIPS_26', 'func_1504A730')], 68: [('R_MIPS_HI16', 'D_800C3E78')], 72: [('R_MIPS_LO16', 'D_800C3E78')], 100: [('R_MIPS_26', 'func_15022998')], 108: [('R_MIPS_26', 'func_1507E73C')], 116: [('R_MIPS_26', 'func_150229E4')], 136: [('R_MIPS_26', 'func_1502178C')], 144: [('R_MIPS_26', 'func_150627D4')], 152: [('R_MIPS_26', 'func_1507FEA0')], 176: [('R_MIPS_26', 'func_15061B4C')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\n\nextern u8 D_800C3654[];\nextern u8 D_800C3E78;\nextern struct127 D_800CC2D0[];\nvoid func_1504A730(void);\nvoid func_15022998(s32 *);\nvoid func_1507E73C(struct127 *);\ns32 func_150229E4();\ns32 func_1502178C();\nvoid func_150627D4(struct127 *);\nvoid func_1507FEA0(struct127 *);\nvoid func_15061B4C(void);\n\n'
DECLARATIONS='extern u8 D_800C3E78;\nvoid func_1504A730(void);\nvoid func_1507E73C(struct127 *);\nvoid func_150627D4(struct127 *);\nvoid func_1507FEA0(struct127 *);\nvoid func_15061B4C(void);\n\n'
SELECTED='/* Update the 25 active actor slots, or dispatch the alternate update mode. */\nvoid func_1502378C(void) {\n    struct127 *actor = D_800CC2D0;\n    s32 index = 0;\n\n    if (D_800C3654[0] != 0) {\n        func_1504A730();\n    } else {\n        u8 limit = 25;\n        do {\n            if (actor->interaction_state != 0) {\n                D_800C3E78 = index;\n                func_15022998((s32 *)actor);\n                func_1507E73C(actor);\n                if (func_150229E4(actor) != 0) {\n                    func_1502178C(actor, 0, -1);\n                    func_150627D4(actor);\n                    func_1507FEA0(actor);\n                    actor->unk2FF = 1;\n                }\n            }\n            index++;\n            actor++;\n        } while (index != limit);\n        func_15061B4C();\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected active actor update diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Active actor update body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_1502378C() {\n    return 0;\n}':raise ValueError('Active actor update placeholder changed')
 return before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Active actor update snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Active actor update frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Active actor update predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Active actor update live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Active actor update named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Active actor update symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Active actor update metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Active actor update frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Active actor update original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Active actor update strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Active actor update named definitions changed')

NEW_GUARDS=[{'filename': 'generated_49D30', 'function': 'func_1502378C', 'offset': '0x04C', 'expected': '0x24120019', 'replacement': '0x24140001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent active-actor loop-limit and flag initialization schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1502378C', 'offset': '0x050', 'expected': '0x24140001', 'replacement': '0x24120019', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent active-actor loop-limit and flag initialization schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
 import csv,io
 if sha(before)!=GUARD_SHA or len(NEW_GUARDS)!=2:raise ValueError('Active actor update guard history changed')
 columns=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(NEW_GUARDS)
 return before+(b''if before.endswith(b'\n')else b'\n')+stream.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Active actor update scope changed')
 checked_payload(raw,bindings);result=bytearray(raw)
 for row in NEW_GUARDS:
  at=int(row['offset'],0)
  if at in bindings or struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0):raise ValueError('Active actor update schedule preimage changed')
  struct.pack_into('>I',result,at,int(row['replacement'],0))
 return bytes(result),bindings

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1502378C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_49D30.c.o', 'make-shadow/src/game/generated_49D30.c.o.compact', 'make-shadow/src/game/generated_49D30.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Active actor update artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active actor update artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active actor update raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Active actor update evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active actor update Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_49D30.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Active actor update Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Active actor update private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Active actor update changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Active actor update protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,reachable_words=54,frame=48,alignment_words=3,slot_words=57,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='6c2b998b9ff00696cd938da12a3b7c2f9c7f6e64e221024f5a6643da5943ae52'
