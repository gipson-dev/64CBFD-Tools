"""Resource pair release: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150843AC','generated_AEB40'
ENTRY,ROM,BODY,SIZE=0x150843AC,0xB185C,220,220
SOURCE='conker/src/game/generated_AEB40.c'
OBJECT='conker/build/src/game/generated_AEB40.c.o'
ASM='conker/asm/AEB40.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-resource-pair-release-match'
RODATA_SYMBOL='jtbl_8009CC40_game'
RAW_SHA='a3e3d32f52306487f2bfb4730dec462b0c0cc320936748ecad9685c0413e3a92'
SNAPSHOT_SHA='f3ed67ecfd34298e92c00e3d3569d2e9d2ef9e78fd8966f0479f3460f9971d61'
BEFORE_ELF_SHA='24df29fd081e58586317af2740dfcc01ab1fbd403679dc639988f8c9925132c2'
TRUTH_SHA='8037c884081f49397e3e1b9fd62ccd2743630ebb7016cdebbfe669cfded973f7'
BINDINGS={76: [('R_MIPS_HI16', 'D_800D1F80')], 96: [('R_MIPS_LO16', 'D_800D1F80')], 80: [('R_MIPS_HI16', 'D_800D19A0')], 92: [('R_MIPS_LO16', 'D_800D19A0')], 140: [('R_MIPS_26', 'func_100043B4')]}
ORIGINAL_BINDINGS={76: [('R_MIPS_HI16', 'D_800D1F80')], 96: [('R_MIPS_LO16', 'D_800D1F80')], 80: [('R_MIPS_HI16', 'D_800D19A0')], 92: [('R_MIPS_LO16', 'D_800D19A0')], 140: [('R_MIPS_26', 'func_100043B4')]}
HEADERS='#include <ultra64.h>\nextern u8 *D_800D19A0[];\nextern u8 D_800D1F80[];\nvoid func_100043B4(s32 *, u32);\n\n'
DECLARATIONS='void func_100043B4(s32 *, u32);\n\n'
SELECTED='/* Release both selected resources, decrementing shared-resource references. */\nvoid func_150843AC(u8 *record, s32 slot) {\n    u8 *cursor;\n    u8 *resource;\n    s32 offset;\n    s32 identity;\n    register s32 limit;\n\n    if (*(u8 **)((s32)record + slot * 8 + 0x28C) != NULL ||\n        *(u8 **)((s32)record + slot * 8 + 0x290) != NULL) {\n        identity = (*(u8 **)(record + 0x2C4))[slot];\n        cursor = (u8 *)((s32)record + (slot << 3));\n        for (offset = 0, limit = 8; offset != limit; offset += 4, cursor += 4) {\n            resource = *(u8 **)(cursor + 0x28C);\n            if (resource != NULL) {\n                if (resource != D_800D19A0[identity]) {\n                    func_100043B4((s32 *)resource, 3);\n                } else {\n                    D_800D1F80[identity]--;\n                }\n                *(u8 **)(cursor + 0x28C) = NULL;\n            }\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner diagnostics: '+text)
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Resource pair release body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150843AC() {\n    return 0;\n}':raise ValueError('Status actor mode placeholder changed')
    result=before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]
    if result.count('s32 func_150843AC();')!=1:raise ValueError('Old forward declaration changed')
    return result.replace('s32 func_150843AC();','void func_150843AC(u8 *, s32);',1)



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Resource pair release snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Resource pair release frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Resource pair release predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Resource pair release live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Resource pair release named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Resource pair release symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Resource pair release metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Resource pair release frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Resource pair release original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Resource pair release strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Resource pair release named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150843AC.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_AEB40.c.o', 'make-shadow/src/game/generated_AEB40.c.o.compact', 'make-shadow/src/game/generated_AEB40.c.o.padded.s', 'make-shadow/src/game/generated_AEB40.c')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Resource pair release artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource pair release artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource pair release raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Resource pair release evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Resource pair release Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_AEB40.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Resource pair release Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Resource pair release private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Resource pair release changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Resource pair release protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,frame=48,alignment_words=0,slot_words=55,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
