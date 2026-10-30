"""Position effect chain: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150B2494','generated_DF930'
ENTRY,ROM,BODY,SIZE=0x150B2494,0xDF944,220,220
SOURCE='conker/src/game/generated_DF930.c'
OBJECT='conker/build/src/game/generated_DF930.c.o'
ASM='conker/asm/DF930.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-position-effect-chain-match'
RODATA_SYMBOL=None
RAW_SHA='e530111c8545e4f272e2f3c10d2e3b0021635b2dd80087c7cea1de29837e80e7'
SNAPSHOT_SHA='3a7212d519e9bf555a08b4cd8206438ba7c9d5bada27dee9893b00c29f197e2c'
BEFORE_ELF_SHA='397dc6c8a50e137fefddf4bd84f23fdd66a0b751edc4196367bd7240a0442b25'
TRUTH_SHA='c8da3b2105d3cddf71483e375db653dd4c3835b03eaa3a6c1937a6bf85952ff7'
BINDINGS={36: [('R_MIPS_26', 'func_150ADA20')], 120: [('R_MIPS_26', 'func_1514C678')], 180: [('R_MIPS_26', 'func_151D5404')], 196: [('R_MIPS_26', 'func_151D3FF4')]}
ORIGINAL_BINDINGS={36: [('R_MIPS_26', 'func_150ADA20')], 120: [('R_MIPS_26', 'func_1514C678')], 180: [('R_MIPS_26', 'func_151D5404')], 196: [('R_MIPS_26', 'func_151D3FF4')]}
HEADERS='#include <ultra64.h>\ns32 func_150ADA20(void);\nvoid func_1514C678(f32, f32, f32, f32, s16, s16, s16, u8, s32, f32, void *, u8);\nvoid func_151D5404(f32 *, f32, f32, f32, s32, s32, s32, s32);\nvoid func_151D3FF4(f32 *, u8, s32);\n\n'
DECLARATIONS='s32 func_150ADA20(void);\nvoid func_1514C678(f32, f32, f32, f32, s16, s16, s16, u8, s32, f32, void *, u8);\nvoid func_151D5404(f32 *, f32, f32, f32, s32, s32, s32, s32);\nvoid func_151D3FF4(f32 *, u8, s32);\n\n'
SELECTED='/* Capture the actor position before dispatching the three effects. */\n/* Retain both unused words required by the callback table interface. */\nvoid func_150B2494(u8 *actor, s32 unused1, s32 unused2) {\n    f32 position[3];\n\n    position[0] = *(f32 *)(actor + 0x14);\n    position[1] = *(f32 *)(actor + 0x180);\n    position[2] = *(f32 *)(actor + 0x1C);\n    func_1514C678(position[0], position[1], position[2], 135.0f,\n                 0, 255, (u32)func_150ADA20() % 15 + 27, 7, 0, 0.0f, 0, 255);\n    func_151D5404(position, 1502.0f, 3000.0f, 0.00033333333f, 12, 15, 255, 0);\n    func_151D3FF4(position, 255, 0);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Position effect chain owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Position effect chain body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150B2494() {\n    return 0;\n}':raise ValueError('Status actor mode placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Position effect chain snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Position effect chain frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Position effect chain predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Position effect chain live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Position effect chain named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Position effect chain symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Position effect chain metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Position effect chain frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Position effect chain original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Position effect chain strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Position effect chain named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150B2494.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_DF930.c.o', 'make-shadow/src/game/generated_DF930.c.o.compact', 'make-shadow/src/game/generated_DF930.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Position effect chain artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position effect chain artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position effect chain raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Position effect chain evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position effect chain Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_DF930.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Position effect chain Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Position effect chain private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Position effect chain changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Position effect chain protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,frame=72,alignment_words=0,slot_words=55,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
