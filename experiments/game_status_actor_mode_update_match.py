"""Status actor mode update: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151E7DC0','generated_20AE20'
ENTRY,ROM,BODY,SIZE=0x151E7DC0,0x215270,220,220
SOURCE='conker/src/game/generated_20AE20.c'
OBJECT='conker/build/src/game/generated_20AE20.c.o'
ASM='conker/asm/20AE20.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-status-actor-mode-update-match'
RODATA_SYMBOL=None
RAW_SHA='fcf670e6ca53a6a16a44f4d7f04901a4c1fc62081384f83740c2b3f9a2862b4c'
SNAPSHOT_SHA='b3fe513a6e4fa34cbb30f13cba94acef885f9919e3120e18a86211487b938ad5'
BEFORE_ELF_SHA='fdcc4c8a0272ec3e813c819096ff8e5090960a7cfdc10add5c85458b9a34cd2f'
TRUTH_SHA='10855f3df5de7572f60c9ba391bf8dadfd3baa26f3751583708a8146e5cce83f'
BINDINGS={8: [('R_MIPS_HI16', 'D_8008FDD4')], 12: [('R_MIPS_LO16', 'D_8008FDD4')], 40: [('R_MIPS_HI16', 'D_800ABA8C')], 44: [('R_MIPS_LO16', 'D_800ABA8C')], 52: [('R_MIPS_HI16', 'D_8008FFB0')], 56: [('R_MIPS_LO16', 'D_8008FFB0')], 160: [('R_MIPS_26', 'func_151149AC')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_8008FDD4')], 12: [('R_MIPS_LO16', 'D_8008FDD4')], 40: [('R_MIPS_HI16', 'D_800ABA8C')], 44: [('R_MIPS_LO16', 'D_800ABA8C')], 52: [('R_MIPS_HI16', 'D_8008FFB0')], 56: [('R_MIPS_LO16', 'D_8008FFB0')], 160: [('R_MIPS_26', 'func_151149AC')]}
HEADERS='#include <ultra64.h>\nextern s8 *D_8008FDD4;\nextern u8 D_8008FFB0[][6];\nextern f32 D_800ABA8C;\nu8 *func_151149AC(u8);\n\n'
DECLARATIONS='extern u8 D_8008FFB0[][6];\nextern f32 D_800ABA8C;\nu8 *func_151149AC(u8);\n\n'
SELECTED='/* Mark the two status-selected actors for mode 2, using live state after each lookup. */\nvoid func_151E7DC0(void) {\n    s32 index;\n    u8 key;\n    u8 *actor;\n\n    if (*(f32 *)(D_8008FDD4 + 8) < D_800ABA8C && D_8008FDD4[0x3E] == 0) {\n        return;\n    }\n    for (index = 0; index < 2; index++) {\n        if (D_8008FDD4[0x3E] == 0) {\n            key = D_8008FFB0[index][D_8008FDD4[0x2C]];\n        } else {\n            key = D_8008FFB0[index][0];\n        }\n        actor = func_151149AC(key);\n        if (actor != NULL) {\n            *(s32 *)(actor + 0x80) = 2;\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Status actor mode update owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Status actor mode update body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_151E7DC0() {\n    return 0;\n}':raise ValueError('Status actor mode placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Status actor mode update snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Status actor mode update frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Status actor mode update predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Status actor mode update live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Status actor mode update named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Status actor mode update symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Status actor mode update metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Status actor mode update frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Status actor mode update original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Status actor mode update strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Status actor mode update named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151E7DC0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_20AE20.c.o', 'make-shadow/src/game/generated_20AE20.c.o.compact', 'make-shadow/src/game/generated_20AE20.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Status actor mode update artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Status actor mode update artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Status actor mode update raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Status actor mode update evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Status actor mode update Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_20AE20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Status actor mode update Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Status actor mode update private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Status actor mode update changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Status actor mode update protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,frame=48,alignment_words=0,slot_words=55,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
