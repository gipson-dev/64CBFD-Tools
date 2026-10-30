"""Resource bitmap: semantic C, checked normalization and literal image audit."""
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
    if asm.name!='func_15016588.s'or filename!='game_439B0':raise ValueError('Resource bitmap padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15016588','game_439B0'
ENTRY,ROM,BODY,SIZE=0x15016588,0x43A38,220,232
SOURCE='conker/src/game_439B0.c'
OBJECT='conker/build/src/game_439B0.c.o'
ASM='conker/asm/nonmatchings/game_439B0/func_15016588.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-resource-bitmap-15016588-match'
RODATA_SYMBOL=None
RAW_SHA='1a6b8c45f0b189e4d87c0c80d44d1ec9a2b01c538463d6e2c33954c3edfe5cf2'
SNAPSHOT_SHA='4097c39c4a92f66f24894169c1b18770ce338d921287b90c3c845a6c778ded35'
BEFORE_ELF_SHA='0628306859314815f346f4c3f76088aa2e897d6bddcbd85424f3ddce9569b018'
TRUTH_SHA='2ea1b01b7f4b3545138ea8874a91311c4bcba447499b007d5470bca16e7425fd'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE580')], 12: [('R_MIPS_LO16', 'D_800BE580')], 48: [('R_MIPS_26', 'bzero')], 56: [('R_MIPS_HI16', 'D_800BEAAB')], 68: [('R_MIPS_LO16', 'D_800BEAAB')], 128: [('R_MIPS_26', 'func_1502B020')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_800BE580')], 12: [('R_MIPS_LO16', 'D_800BE580')], 48: [('R_MIPS_26', 'bzero')], 56: [('R_MIPS_HI16', 'D_800BEAAB')], 64: [('R_MIPS_LO16', 'D_800BEAAB')], 128: [('R_MIPS_26', 'func_1502B020')]}
HEADERS='#include <ultra64.h>\nextern u8 D_800BE580[];\nextern u8 D_800BEAAB;\nu32 func_1502B020(u32 *, u32, ...);\n\n'
DECLARATIONS=''
SELECTED="/* Rebuild the resource-presence bits using each query's returned size. */\nvoid func_15016588(void) {\n    s32 index;\n    s32 byteIndex;\n    s32 mask;\n    u32 size;\n\n    bzero(D_800BE580, 8);\n    byteIndex = -1;\n    index = 0;\n    do {\n        if ((index & 7) == 0) {\n            mask = 1;\n            byteIndex++;\n        } else {\n            mask <<= 1;\n        }\n        func_1502B020(&size, 3, 0x1A, D_800BEAAB, index);\n        index++;\n        if (size != 0) {\n            D_800BE580[byteIndex] |= mask;\n        }\n    } while (index != 67);\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected resource bitmap diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Resource bitmap body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15016588() {\n    return 0;\n}':raise ValueError('Resource bitmap placeholder changed')
 result=before[:a]+SELECTED.rstrip()+before[b:];prefix='#include <ultra64.h>\n'
 if not result.startswith(prefix)or result.count('s32 func_15016588();')!=1:raise ValueError('Resource bitmap owner declarations changed')
 result=HEADERS+result[len(prefix):]
 return result.replace('s32 func_15016588();','void func_15016588(void);',1).replace('// grim looking loop\n','',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_439B0/func_15016588.s. */\n','',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Resource bitmap snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Resource bitmap frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Resource bitmap predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Resource bitmap live input differs: '+name)
    return values

METADATA_GROUPS=((2815988, ('D_800BE950', 'D_800BE580'), (1, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Resource bitmap named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Resource bitmap symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Resource bitmap metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Resource bitmap frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Resource bitmap original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Resource bitmap strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Resource bitmap named definitions changed')

NEW_GUARDS=[{'filename': 'game_439B0', 'function': 'func_15016588', 'offset': '0x040', 'expected': '0x00008025', 'replacement': '0x26B50000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800BEAAB', 'note': 'Normalize independent selector address and loop-index initialization schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_439B0', 'function': 'func_15016588', 'offset': '0x044', 'expected': '0x26B50000', 'replacement': '0x00008025', 'expected_relocations': 'R_MIPS_LO16:D_800BEAAB', 'replacement_relocations': '-', 'note': 'Normalize independent selector address and loop-index initialization schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Resource bitmap scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('Resource bitmap preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('Resource bitmap binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='fdf93ed61658404561a034ad518d2b35f27d22bea9d21a80c4e3149889632a37'or rs!=ORIGINAL_BINDINGS:raise ValueError('Resource bitmap result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15016588.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_439B0.c.o', 'make-shadow/src/game_439B0.c.o.compact', 'make-shadow/src/game_439B0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Resource bitmap artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource bitmap artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource bitmap raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Resource bitmap evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource bitmap Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_439B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Resource bitmap Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Resource bitmap private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Resource bitmap changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Resource bitmap protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,reachable_words=55,frame=80,alignment_words=3,slot_words=58,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='20265ddb833e3f6da7219ee138f25a1e7ab41f7d4170bc3cfaa19bf64a4b17c9'
