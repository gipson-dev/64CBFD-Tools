"""Channel timer cycle: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15080348','generated_AD6B0'
ENTRY,ROM,BODY,SIZE=0x15080348,0xAD7F8,232,232
SOURCE='conker/src/game/generated_AD6B0.c'
OBJECT='conker/build/src/game/generated_AD6B0.c.o'
ASM='conker/asm/AD6B0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-channel-timer-cycle-15080348-match'
RODATA_SYMBOL=None
RAW_SHA='aa17be61f2765ad3d1b72ae3973bd2a8171c09d5568402511196bad4b49c87bc'
SNAPSHOT_SHA='c6eb79df3f638a670002088fb50e1fec0a938871ea3735333e7c228d810ed14b'
BEFORE_ELF_SHA='bfccfe135c746cda328e3bcd0558e71f7f90003d631abbed217d2d654ee7e3be'
TRUTH_SHA='23c5ba41ab1475f01840b26137d1096a553fd679887716f3686945d699838331'
BINDINGS={8: [('R_MIPS_HI16', 'D_800D1928')], 12: [('R_MIPS_LO16', 'D_800D1928')], 40: [('R_MIPS_HI16', 'D_800427F0')], 44: [('R_MIPS_LO16', 'D_800427F0')], 84: [('R_MIPS_HI16', 'D_800D192C')], 88: [('R_MIPS_LO16', 'D_800D192C')], 36: [('R_MIPS_HI16', 'D_800427F0')], 80: [('R_MIPS_LO16', 'D_800427F0')], 100: [('R_MIPS_HI16', 'D_800BE9E4')], 108: [('R_MIPS_LO16', 'D_800BE9E4')], 128: [('R_MIPS_HI16', 'D_8009BD10')], 152: [('R_MIPS_LO16', 'D_8009BD10')], 164: [('R_MIPS_26', 'func_151EF610')], 196: [('R_MIPS_HI16', 'D_800D192C')], 204: [('R_MIPS_LO16', 'D_800D192C')], 208: [('R_MIPS_HI16', 'D_800427F0')], 212: [('R_MIPS_LO16', 'D_800427F0')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_800D1928')], 12: [('R_MIPS_LO16', 'D_800D1928')], 40: [('R_MIPS_HI16', 'D_800427F0')], 44: [('R_MIPS_LO16', 'D_800427F0')], 36: [('R_MIPS_HI16', 'D_800427F0')], 80: [('R_MIPS_LO16', 'D_800427F0')], 84: [('R_MIPS_HI16', 'D_800D192C')], 88: [('R_MIPS_LO16', 'D_800D192C')], 100: [('R_MIPS_HI16', 'D_800BE9E4')], 108: [('R_MIPS_LO16', 'D_800BE9E4')], 128: [('R_MIPS_HI16', 'D_8009BD10')], 152: [('R_MIPS_LO16', 'D_8009BD10')], 164: [('R_MIPS_26', 'func_151EF610')], 196: [('R_MIPS_HI16', 'D_800D192C')], 204: [('R_MIPS_LO16', 'D_800D192C')], 208: [('R_MIPS_HI16', 'D_800427F0')], 212: [('R_MIPS_LO16', 'D_800427F0')]}
HEADERS='#include <ultra64.h>\nextern s32 D_800D1928, D_800D192C, D_800427F0, D_800BE9E4;\nextern s32 D_8009BD10[];\ns32 func_151EF610(void);\n\n'
DECLARATIONS=''
SELECTED='/* Update the actor channel gate or advance its timed five-entry cycle. */\nvoid func_15080348(u8 *actor) {\n    s32 index;\n    s32 remaining;\n\n    if (D_800D1928 != 0 && actor != NULL) {\n        if (D_800D1928 == 1) {\n            if (D_800427F0 < 1000) {\n                actor[0x1FF] = 0;\n            } else {\n                actor[0x1FF] = 1;\n            }\n        } else {\n            index = D_800D192C;\n            if (D_800427F0 > 1000) {\n                remaining = actor[0x135];\n                remaining = (s32)((u32)remaining - (u32)D_800BE9E4);\n                index = (s32)((u32)index + 1);\n                if (remaining < 0) {\n                    if (index >= 5) {\n                        index = 0;\n                    }\n                    actor[0x134] = D_8009BD10[index];\n                    actor[0x135] = func_151EF610() % 7 + 4;\n                    D_800D192C = index;\n                }\n            }\n        }\n        D_800427F0 = 0;\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected channel timer cycle diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Channel timer cycle body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15080348() {\n    return 0;\n}':raise ValueError('Channel timer placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n'
 if not after.startswith(prefix):raise ValueError('Owner includes changed')
 declarations='extern s32 D_800427F0, D_800BE9E4;\nextern s32 D_8009BD10[];\ns32 func_151EF610(void);\n'
 return prefix+declarations+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Channel timer cycle snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Channel timer cycle frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Channel timer cycle predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Channel timer cycle live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Channel timer cycle named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Channel timer cycle symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Channel timer cycle metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Channel timer cycle frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Channel timer cycle original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Channel timer cycle strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Channel timer cycle named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Channel timer cycle scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15080348.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_AD6B0.c.o', 'make-shadow/src/game/generated_AD6B0.c.o.compact', 'make-shadow/src/game/generated_AD6B0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Channel timer cycle artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Channel timer cycle artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Channel timer cycle raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Channel timer cycle evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Channel timer cycle Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_AD6B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Channel timer cycle Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Channel timer cycle private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Channel timer cycle changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Channel timer cycle protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=32,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='45613bff55c7968e57d7c40e4fc1360786d2b9489d2b56d791d19bd75ee1e938'
