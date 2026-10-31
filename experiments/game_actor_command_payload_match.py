"""Actor command payload: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150D1F6C','generated_FF0E0'
ENTRY,ROM,BODY,SIZE=0x150D1F6C,0xFF41C,232,232
SOURCE='conker/src/game/generated_FF0E0.c'
OBJECT='conker/build/src/game/generated_FF0E0.c.o'
ASM='conker/asm/FF0E0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-command-payload-150D1F6C-match'
RODATA_SYMBOL=None
RAW_SHA='223da744ea8e76639471ec8ee2afdc705f09465c16965b5860460ee2a5dabe04'
SNAPSHOT_SHA='0116e8c0862d6d16155b7bed1e36616fe468dc54c923d9905a45c7940970a6b6'
BEFORE_ELF_SHA='73099a6b504962d5910b421f1ea5d84619973fa462cdd677ce73d0e553224fd7'
TRUTH_SHA='931f6189941be3451529c3dab26d92ded80ad347fc02f40c546ddef28bb064ab'
BINDINGS={152: [('R_MIPS_HI16', 'D_800A5480')], 156: [('R_MIPS_LO16', 'D_800A5480')], 200: [('R_MIPS_26', 'func_1516972C')]}
ORIGINAL_BINDINGS={160: [('R_MIPS_HI16', 'D_800A5480')], 164: [('R_MIPS_LO16', 'D_800A5480')], 208: [('R_MIPS_26', 'func_1516972C')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct { f32 x, y, z; } CommandVector;\ntypedef struct { CommandVector position; f32 value; } ActorCommandPayload;\ntypedef struct { u8 pad0[0x18]; CommandVector position; u8 pad24[0x18]; f32 value; void *owner; u8 flags; } ActorCommandState;\nextern CommandVector D_800A5480;\nvoid func_1516972C(struct102 *actor);\n\n'
DECLARATIONS=''
SELECTED='/* Apply a position payload, owner flag command, reset or actor release. */\nvoid func_150D1F6C(struct260 *actor, s32 payloadAddress, u8 command) {\n    void *payload = (void *)payloadAddress;\n    ActorCommandState *state;\n    state = (ActorCommandState *)((u8 *)actor + 0x28);\n    if (command == 0x32) {\n        state->position = ((ActorCommandPayload *)payload)->position;\n        state->value = ((ActorCommandPayload *)payload)->value;\n    } else if (command == 0x30 || command == 0x31) {\n        if (payload == state->owner) {\n            if (command == 0x30) {\n                state->flags |= 1;\n            } else {\n                state->flags &= ~1;\n            }\n        }\n    } else if (command == 0x4E) {\n        *(CommandVector *)((u8 *)actor + 0x40) = D_800A5480;\n    } else if (command == 0x4F) {\n        func_1516972C((struct102 *)actor);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor command payload diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor command payload body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_150D1F6C() {\n    return 0;\n}':raise ValueError('Actor command placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n'
 if not after.startswith(prefix):raise ValueError('Owner includes changed')
 return HEADERS+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor command payload snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor command payload frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor command payload predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor command payload live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor command payload named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor command payload symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor command payload metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor command payload frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor command payload original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor command payload strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor command payload named definitions changed')

NEW_GUARDS=[{'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x018', 'expected': '0x14C1000B', 'replacement': '0x14C1000C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x040', 'expected': '0x10000023', 'replacement': '0xE444003C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x044', 'expected': '0xE444003C', 'replacement': '0x10000025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '0x8FBF0014', 'insert_after_relocations': '-', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x054', 'expected': '0x1461000E', 'replacement': '0x1461000F', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x060', 'expected': '0x54B9001C', 'replacement': '0x54B9001D', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x078', 'expected': '0x10000015', 'replacement': '0x10000016', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x088', 'expected': '0x10000011', 'replacement': '0xA04B0044', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_FF0E0', 'function': 'func_150D1F6C', 'offset': '0x08C', 'expected': '0xA04B0044', 'replacement': '0x10000012', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore actor-command return-address reload and branch layout', 'insert_after': '0x8FBF0014', 'insert_after_relocations': '-', 'omit': 'false'}]

def guard_manifest(before):
 import csv,io
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
 if any(row['function']==FUNCTION for row in reader):raise ValueError('Target guards already installed')
 out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\n').writerows(NEW_GUARDS)
 return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Actor command scope changed')
 checked_payload(raw,bindings);rows={int(row['offset'],0):row for row in NEW_GUARDS};out=bytearray();rels={}
 for at in range(0,len(raw),4):
  word=struct.unpack_from('>I',raw,at)[0];row=rows.get(at)
  if row:
   if word!=int(row['expected'],0)or bindings.get(at):raise ValueError('Guard input changed')
   word=int(row['replacement'],0)
  if at in bindings:rels[len(out)]=bindings[at]
  out.extend(struct.pack('>I',word))
  if row and row['insert_after']:out.extend(struct.pack('>I',int(row['insert_after'],0)))
 if len(out)!=232 or sha(out)!='60819ed76446ac1a877a23490e2a2a5c0665e5095b1f5fc17a53576da5ad5dd8' or rels!=ORIGINAL_BINDINGS:raise ValueError('Normalized body/bindings changed')
 return bytes(out),rels

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150D1F6C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_FF0E0.c.o', 'make-shadow/src/game/generated_FF0E0.c.o.compact', 'make-shadow/src/game/generated_FF0E0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor command payload artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor command payload artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor command payload raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor command payload evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor command payload Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_FF0E0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor command payload Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=8 or q['exclusions']!=0:raise ValueError('Actor command payload private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor command payload changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor command payload protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=57,frame=24,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=8,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='45613bff55c7968e57d7c40e4fc1360786d2b9489d2b56d791d19bd75ee1e938'
