"""Ring message receive: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys,csv,io
import tools.pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly as _emit
def emit_padded_assembly(obj,asm,filename,word_patches_path):
    asm=Path(asm)
    if asm.name!='func_15043CA4.s'or filename!='game_70200':raise ValueError('Script-lookup padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER=('func_15043CA4', 'game_70200')
ENTRY,ROM,BODY,SIZE=(352599204, 463188, 232, 236)
SOURCE='conker/src/game_70200.c'
OBJECT='conker/build/src/game_70200.c.o'
ASM='conker/asm/nonmatchings/game_70200/func_15043CA4.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-ring-message-receive-15043CA4-match'
RODATA_SYMBOL=None
RAW_SHA='fbdcb69c624e79ae2682643df0a890e0672eb00477cf65747dc6d53894ab9bf3'
SNAPSHOT_SHA='1a97dbaaf04f9fb52fb770d5a23a6bb7e441f560db723f2e7ea38bc38310d5db'
BEFORE_ELF_SHA='86550723432dfe6516fb3cd3a0e5712e6a38aabd2cb9e2da7faab2c31013e772'
TRUTH_SHA='7c2df8a26319c779f76eacbe7746801e8378d37cdd5dd18d10d9fcf4121893a6'
BINDINGS={80: [('R_MIPS_26', 'func_15043AC8')], 120: [('R_MIPS_26', 'func_15043AC8')], 156: [('R_MIPS_26', 'func_15043B70')], 192: [('R_MIPS_26', 'func_15043AC8')]}
ORIGINAL_BINDINGS={80: [('R_MIPS_26', 'func_15043AC8')], 120: [('R_MIPS_26', 'func_15043AC8')], 156: [('R_MIPS_26', 'func_15043B70')], 192: [('R_MIPS_26', 'func_15043AC8')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ns32 func_15043AC8(u8 *, s32, s32, u8 *, s32);\ns32 func_15043B70(s32, s32, s32, s32);\n\n'
DECLARATIONS=''
SELECTED='/* Receive one length-prefixed message; fields are ring, size, read and write cursors. */\ns32 func_15043CA4(struct105 *queue, u8 *output, s32 capacity) {\n    s32 cursor;\n    s32 messageLength;\n\n    messageLength = 0;\n    if (queue->unk8 == queue->unkC) {\n        return 0;\n    }\n    cursor = func_15043AC8((u8 *)queue->unk0, queue->unk4, queue->unk8,\n                         (u8 *)&messageLength, 4);\n    if (capacity < messageLength) {\n        capacity = (s32)((u32)capacity - 1);\n        cursor = func_15043AC8((u8 *)queue->unk0, queue->unk4, cursor,\n                             output, capacity);\n        output[capacity] = 0;\n        cursor = func_15043B70(queue->unk0, queue->unk4, cursor,\n                             (s32)((u32)messageLength - (u32)capacity));\n    } else if (messageLength != 0) {\n        cursor = func_15043AC8((u8 *)queue->unk0, queue->unk4, cursor,\n                             output, messageLength);\n    }\n    queue->unk8 = cursor;\n    return messageLength;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected ring message receive owner diagnostics')
    return 0



sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Ring message receive body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_15043CA4() {\n    return 0;\n}':raise ValueError('Receiver placeholder changed')
    after=before[:a]+SELECTED.rstrip()+before[b:]
    return after.replace('s32 func_15043CA4();','s32 func_15043CA4(struct105 *queue, u8 *output, s32 capacity);',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_70200/func_15043CA4.s. */\n','',1)




def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Ring message receive snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Ring message receive frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Ring message receive predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Ring message receive live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Ring message receive named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Ring message receive symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Ring message receive metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Ring message receive frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Ring message receive original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Ring message receive strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Ring message receive named definitions changed')

NEW_GUARDS=[{'filename': 'game_70200', 'function': 'func_15043CA4', 'offset': '0x030', 'expected': '0x8E2F000C', 'replacement': '0x8E38000C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed empty-queue temporary allocation and symmetric comparison', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_70200', 'function': 'func_15043CA4', 'offset': '0x038', 'expected': '0x55EE0004', 'replacement': '0x55D80004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed empty-queue temporary allocation and symmetric comparison', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited ring message receive guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Script-lookup guard already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Receiver normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>58I',raw))
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if at in bindings or words[at//4]!=int(row['expected'],0):raise ValueError('Receiver expected preimage changed')
        words[at//4]=int(row['replacement'],0)
    result=struct.pack('>58I',*words)
    if sha(result)!=NORMALIZED_SHA or bindings!=ORIGINAL_BINDINGS:raise ValueError('Receiver normalized bytes/bindings changed')
    return result,bindings



NORMALIZED_SHA='e3d3b9b3b96880ba35b5725f7679ee5a6e36cf067cef4f5e4277f1f3cdb9660a'

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15043CA4.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_70200.c.o', 'make-shadow/src/game_70200.c.o.compact', 'make-shadow/src/game_70200.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Ring message receive artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ring message receive artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ring message receive raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Ring message receive evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ring message receive Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_70200.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Ring message receive Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Ring message receive private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Ring message receive changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Ring message receive protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=57,frame=56,alignment_words=1,slot_words=59,strict_first_link_reproduced=True,guards=2,insertions=0,omissions=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='521e547d2780086bab10348512d8153ce8dc9588ab3a96840ec5391da0b001f4'
