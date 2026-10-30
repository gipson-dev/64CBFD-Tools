"""Group channel normalization: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_group_type2_actor_reset_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1501E73C','generated_49D30'
ENTRY,ROM,BODY,SIZE=0x1501E73C,0x4BBEC,224,224
SOURCE='conker/src/game/generated_49D30.c'
OBJECT='conker/build/src/game/generated_49D30.c.o'
ASM='conker/asm/49D30.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-group-actor-channel-normalize-1501E73C-match'
RODATA_SYMBOL=None
RAW_SHA='2c2bba3a77664d260aa9d4e5ed9885d4b8e7eecb71b7619a35bd37d7a2fa6358'
SNAPSHOT_SHA='ab07e44e074136f2b26b0a2387b84355b6350ae35ca9d9f313804a108e32a406'
BEFORE_ELF_SHA='8d40a1b98b135f365c61541faf5cbf914a79e4304873fabd2e3ac4b35a18dae6'
TRUTH_SHA='1d6f67e56431a9873a21b755a989633406beacb5719f9dc480e99fa5ac80740a'
BINDINGS={24: [('R_MIPS_HI16', 'D_800C363A')], 28: [('R_MIPS_LO16', 'D_800C363A')], 52: [('R_MIPS_HI16', 'D_800C35F0')], 56: [('R_MIPS_LO16', 'D_800C35F0')], 88: [('R_MIPS_26', 'func_15083E90')], 164: [('R_MIPS_26', 'func_1507EABC')]}
ORIGINAL_BINDINGS={24: [('R_MIPS_HI16', 'D_800C363A')], 28: [('R_MIPS_LO16', 'D_800C363A')], 40: [('R_MIPS_HI16', 'D_800C35F0')], 44: [('R_MIPS_LO16', 'D_800C35F0')], 88: [('R_MIPS_26', 'func_15083E90')], 164: [('R_MIPS_26', 'func_1507EABC')]}
HEADERS='#include <ultra64.h>\nextern u8 D_800C363A[];\nextern u8 *D_800C35F0[];\nu8 *func_15083E90(u8);\nvoid func_1507EABC(u8 *);\n\n'
DECLARATIONS='void func_1507EABC(u8 *);\n\n'
SELECTED='/* Normalize channel values of at least 10 on type-2 group actors. */\nvoid func_1501E73C(s32 group) {\n    s32 offset;\n    u8 **records;\n    u8 *actor;\n    u8 *record;\n\n    if (D_800C363A[group] > 0) {\n        records = &D_800C35F0[group];\n        offset = 0;\n        do {\n            record = *records + offset;\n            if (*(u16 *)record == 2) {\n                actor = func_15083E90(record[2]);\n                if (actor == NULL) goto advance;\n                {\n                    if (actor[0x6C] >= 10) {\n                        actor[0x6C] = 0;\n                        actor[0x6A] = 0;\n                    }\n                    if (actor[0x6D] >= 10) {\n                        actor[0x6D] = 0;\n                        actor[0x6B] = 0;\n                    }\n                    func_1507EABC(actor);\n                }\n            }\nadvance:\n            offset += 8;\n        } while (offset < D_800C363A[group] * 8);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected group channel normalization diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Group channel normalization body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1501E73C() {\n    return 0;\n}':raise ValueError('Group channel placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Group channel normalization snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Group channel normalization frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Group channel normalization predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Group channel normalization live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Group channel normalization named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Group channel normalization symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Group channel normalization metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Group channel normalization frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Group channel normalization original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Group channel normalization strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Group channel normalization named definitions changed')

NEW_GUARDS=[{'filename': 'generated_49D30', 'function': 'func_1501E73C', 'offset': '0x28', 'expected': '0x00008025', 'replacement': '0x3C180000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_HI16:D_800C35F0', 'note': 'Normalize closed group actor channel scan opening address and counter schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1501E73C', 'offset': '0x2c', 'expected': '0x00047880', 'replacement': '0x27180000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800C35F0', 'note': 'Normalize closed group actor channel scan opening address and counter schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1501E73C', 'offset': '0x34', 'expected': '0x3C180000', 'replacement': '0x00047880', 'expected_relocations': 'R_MIPS_HI16:D_800C35F0', 'replacement_relocations': '-', 'note': 'Normalize closed group actor channel scan opening address and counter schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1501E73C', 'offset': '0x38', 'expected': '0x27180000', 'replacement': '0x01F89021', 'expected_relocations': 'R_MIPS_LO16:D_800C35F0', 'replacement_relocations': '-', 'note': 'Normalize closed group actor channel scan opening address and counter schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_49D30', 'function': 'func_1501E73C', 'offset': '0x3c', 'expected': '0x01F89021', 'replacement': '0x00008025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed group actor channel scan opening address and counter schedule', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!='generated_49D30'or function!=FUNCTION or len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Group normalization input fingerprint/scope changed')
 result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for at,expected,replacement,newrs in((40,0x00008025,0x3C180000,[('R_MIPS_HI16','D_800C35F0')]),(44,0x00047880,0x27180000,[('R_MIPS_LO16','D_800C35F0')]),(52,0x3C180000,0x00047880,[]),(56,0x27180000,0x01F89021,[]),(60,0x01F89021,0x00008025,[])):
  if struct.unpack_from('>I',result,at)[0]!=expected:raise ValueError('Opening preimage changed')
  struct.pack_into('>I',result,at,replacement);rs.pop(at,None)
  if newrs:rs[at]=newrs
 result=bytes(result)
 if sha(result)!='8e317b30e24a06c5fbb7c57670bfbeb19e89af0e02dd133f3e49a4f5c9bcd419'or rs!=ORIGINAL_BINDINGS:raise ValueError('Normalized body/bindings differ from original')
 return result,rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1501E73C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_49D30.c.o', 'make-shadow/src/game/generated_49D30.c.o.compact', 'make-shadow/src/game/generated_49D30.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Group channel normalization artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Group channel normalization artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Group channel normalization raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Group channel normalization evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Group channel normalization Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_49D30.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Group channel normalization Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=5 or q['exclusions']!=0:raise ValueError('Group channel normalization private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Group channel normalization changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Group channel normalization protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=40,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=5,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='f368b633dd03cd6b8ce55d5285be0ecb1884bfa06718d91b0417907bdaede5df'
