"""Linked actor request: semantic C, checked normalization and literal image audit."""
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
    if asm.name!='func_150626EC.s'or filename!='game_83300':raise ValueError('Linked actor request padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150626EC','game_83300'
ENTRY,ROM,BODY,SIZE=0x150626EC,0x8FB9C,232,232
SOURCE='conker/src/game_83300.c'
OBJECT='conker/build/src/game_83300.c.o'
ASM='conker/asm/nonmatchings/game_83300/func_150626EC.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-linked-actor-request-150626EC-match'
RODATA_SYMBOL=None
RAW_SHA='605bf4b58074594e16bc3333d485636ecf4758dfd83835440e312f7d1f69d5af'
SNAPSHOT_SHA='5986d8ee00fadd95ad912ac851ab9b21b978ebc1578675066bff017e206748a3'
BEFORE_ELF_SHA='66463002e6a5a923ce7a2e3062ced67466ebfb74765c74dbef2961da4ac11a53'
TRUTH_SHA='11f0f5c82dfc46dec80af8208126d314ecaf9a4f3653ff7d5a60a0d2ff7f87fa'
BINDINGS={44: [('R_MIPS_HI16', 'D_800CC2D0')], 64: [('R_MIPS_LO16', 'D_800CC2D0')], 48: [('R_MIPS_HI16', 'D_800CC2D0')], 60: [('R_MIPS_LO16', 'D_800CC2D0')], 52: [('R_MIPS_HI16', 'D_800CC2D0')], 56: [('R_MIPS_LO16', 'D_800CC2D0')], 172: [('R_MIPS_26', 'func_15060F28')]}
ORIGINAL_BINDINGS={52: [('R_MIPS_HI16', 'D_800CC2D0')], 56: [('R_MIPS_LO16', 'D_800CC2D0')], 48: [('R_MIPS_HI16', 'D_800D121C')], 60: [('R_MIPS_LO16', 'D_800D121C')], 44: [('R_MIPS_HI16', 'D_800CC2D0')], 64: [('R_MIPS_LO16', 'D_800CC2D0')], 172: [('R_MIPS_26', 'func_15060F28')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\nextern s32 D_800D121C;\nvoid func_15060F28(struct127 *, s32);\n\n'
DECLARATIONS=''
SELECTED='/* Submit the request to active actors attached to the selected owner slot. */\nvoid func_150626EC(struct127 *owner, s32 request) {\n    s32 index;\n    struct127 *record;\n\n    for (index = 0; index < 25; index++) {\n        record = &D_800CC2D0[index];\n        if (record->interaction_state != 0 &&\n            record->unk65 == (s32)((u32)owner - (u32)D_800CC2D0) / (s32)sizeof(struct127) + 1 &&\n            record->unk127 == 255) {\n            func_15060F28(record, request);\n        }\n    }\n}\n'

OWNER_DIAGNOSTICS_NORMALIZED='cfe: Warning 712: OWNER.c, line 68: illegal combination of pointer and integer\n         temp_v1 = D_800D2104[arg0->unk13F];\n ----------------^\ncfe: Warning 712: OWNER.c, line 532: illegal combination of pointer and integer\n             func_15059C84(arg0);\n --------------------------^\ncfe: Warning 712: OWNER.c, line 533: illegal combination of pointer and integer\n             func_1505A770(arg0);\n --------------------------^\ncfe: Warning 712: OWNER.c, line 536: illegal combination of pointer and integer\n     func_1505D6F0(arg0, D_800C3E78);\n ------------------^\ncfe: Warning 712: OWNER.c, line 537: illegal combination of pointer and integer\n     func_15055E50(arg0, arg0->unk1E4);\n ------------------^\ncfe: Warning 712: OWNER.c, line 566: illegal combination of pointer and integer\n         func_15056B08(arg0);\n ----------------------^\ncfe: Warning 712: OWNER.c, line 646: illegal combination of pointer and integer\n         func_150611E8(arg0, sp1C);\n ----------------------^\ncfe: Warning 712: OWNER.c, line 806: illegal combination of pointer and integer\n         ret = *temp_v1;\n ------------^\n'
def check_owner_diagnostics(text):
 normalized=re.sub(r'[^ \n]+\.c(?=, line)','OWNER.c',text)
 if normalized!=OWNER_DIAGNOSTICS_NORMALIZED:raise ValueError('Inherited owner warnings changed')
 return 8

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Linked actor request body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_150626EC() {\n    return 0;\n}'or before.count('s32 func_150626EC();')!=1:raise ValueError('Actor request placeholder changed')
 result=before[:a]+SELECTED.rstrip()+before[b:]
 return result.replace('s32 func_150626EC();','void func_150626EC(struct127 *, s32);',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_150626EC.s. */\n','',1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Linked actor request snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Linked actor request frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Linked actor request predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Linked actor request live input differs: '+name)
    return values

def validate_alias(symbols):
 if symbols['D_800D121C']!=symbols['D_800CC2D0']+25*0x32C:raise ValueError('Actor pool endpoint alias changed')
 return True

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Linked actor request named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Linked actor request symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Linked actor request metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Linked actor request frozen image changed')
    symbols={name:fields[1]for _,name,fields,_ in symbol_rows(before)}
    validate_alias(symbols)
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Linked actor request original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Linked actor request strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Linked actor request named definitions changed')

NEW_GUARDS=[{'filename': 'game_83300', 'function': 'func_150626EC', 'offset': '0x030', 'expected': '0x3C160000', 'replacement': '0x3C160000', 'expected_relocations': 'R_MIPS_HI16:D_800CC2D0', 'replacement_relocations': 'R_MIPS_HI16:D_800D121C', 'note': 'Preserve retail name for the 25-record pool endpoint alias', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_83300', 'function': 'func_150626EC', 'offset': '0x03C', 'expected': '0x26D64F4C', 'replacement': '0x26D60000', 'expected_relocations': 'R_MIPS_LO16:D_800CC2D0', 'replacement_relocations': 'R_MIPS_LO16:D_800D121C', 'note': 'Preserve retail name for the 25-record pool endpoint alias', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Linked actor request scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('Linked actor request preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('Linked actor request binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='e77e0bcabb479fa34b8a3a0bca3338c040ca143e2d402a9b14c0929e0e460c0b'or rs!=ORIGINAL_BINDINGS:raise ValueError('Linked actor request result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150626EC.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_83300.c.o', 'make-shadow/src/game_83300.c.o.compact', 'make-shadow/src/game_83300.c.o.padded.s', 'make-shadow/src/game_83300.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Linked actor request artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Linked actor request artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Linked actor request raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Linked actor request evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Linked actor request Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_83300.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Linked actor request Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Linked actor request private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Linked actor request changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Linked actor request protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=54,frame=56,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='5d5acf160b1ce57988c197dd86ac0c089dc196401827e86d7fc16569ec307e9c'
