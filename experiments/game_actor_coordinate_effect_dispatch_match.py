"""Actor coordinate effect dispatch: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150D8A34','generated_105760'
ENTRY,ROM,BODY,SIZE=0x150D8A34,0x105EE4,216,220
SOURCE='conker/src/game/generated_105760.c'
OBJECT='conker/build/src/game/generated_105760.c.o'
ASM='conker/asm/105760.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-actor-coordinate-effect-dispatch-match'
RODATA_SYMBOL=None
RAW_SHA='de94f97757f89e29b472ea34b45193f1ac5cd052a5f828681967db75faad5fba'
SNAPSHOT_SHA='49111c14b67896ad736b5cc7b8fe093c026bf5985b5bc41c42ecadc35e955a81'
BEFORE_ELF_SHA='33e8855c8fd8e94bab70ca87049a7e38276cbba5c1e8a43b9d7b996cd0c7c4d3'
TRUTH_SHA='ce0290cea244d44277242557d13a3376ec24efe450fecb2b3fb8a59fcdb39121'
BINDINGS={40: [('R_MIPS_26', 'func_150D88E0')], 48: [('R_MIPS_HI16', 'D_800A0B30')], 52: [('R_MIPS_LO16', 'D_800A0B30')], 56: [('R_MIPS_HI16', 'D_800A0B34')], 60: [('R_MIPS_LO16', 'D_800A0B34')], 100: [('R_MIPS_26', 'func_151875E0')], 192: [('R_MIPS_26', 'func_15165F80')]}
ORIGINAL_BINDINGS={40: [('R_MIPS_26', 'func_150D88E0')], 48: [('R_MIPS_HI16', 'D_800A0B30')], 52: [('R_MIPS_LO16', 'D_800A0B30')], 56: [('R_MIPS_HI16', 'D_800A0B34')], 60: [('R_MIPS_LO16', 'D_800A0B34')], 100: [('R_MIPS_26', 'func_151875E0')], 192: [('R_MIPS_26', 'func_15165F80')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A0B30;\nextern f32 D_800A0B34;\ns32 func_150D88E0();\ns32 func_151875E0(f32, f32, f32, s32, s32, s32, f32, f32);\ns32 func_15165F80(s32, s32, s32, s32, s32, s32, s32, u8, s32);\n\n'
DECLARATIONS='extern f32 D_800A0B30;\nextern f32 D_800A0B34;\ns32 func_151875E0(f32, f32, f32, s32, s32, s32, f32, f32);\ns32 func_15165F80(s32, s32, s32, s32, s32, s32, s32, u8, s32);\n\n'
SELECTED='/* Use the callback selector byte to emit both coordinate effects. */\n/* Keep the complete three-word callback ABI, including the unused third word. */\nvoid func_150D8A34(u8 *owner, s32 selector, s32 unused) {\n    f32 position[3];\n\n    if (*(s32 *)(owner + 0x1D4) != 0) {\n        func_150D88E0(position, owner, (u8)selector);\n        func_151875E0(position[0], position[1], position[2], 30, 15, 7,\n                     D_800A0B30, D_800A0B34);\n        func_15165F80(-1, (s32)position[0],\n                     (s32)(*(f32 *)(owner + 0x180) + 4.0f),\n                     (s32)position[2], 4, 50, 0, 255, 0);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Actor coordinate effect dispatch owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor coordinate effect dispatch body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150D8A34() {\n    return 0;\n}':raise ValueError('Status actor mode placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor coordinate effect dispatch snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor coordinate effect dispatch frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor coordinate effect dispatch predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor coordinate effect dispatch live input differs: '+name)
    return values

METADATA_GROUPS=((2990772, ('D_800A0B34', 'D_800A06D4'), (1, 0)), (2993012, ('D_800A0B30', 'D_800A06D0'), (1, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Actor coordinate effect dispatch named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Actor coordinate effect dispatch symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Actor coordinate effect dispatch metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor coordinate effect dispatch frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor coordinate effect dispatch original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor coordinate effect dispatch strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor coordinate effect dispatch named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150D8A34.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_105760.c.o', 'make-shadow/src/game/generated_105760.c.o.compact', 'make-shadow/src/game/generated_105760.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor coordinate effect dispatch artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor coordinate effect dispatch artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor coordinate effect dispatch raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor coordinate effect dispatch evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor coordinate effect dispatch Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_105760.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor coordinate effect dispatch Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor coordinate effect dispatch private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor coordinate effect dispatch changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor coordinate effect dispatch protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=64,alignment_words=1,slot_words=55,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
