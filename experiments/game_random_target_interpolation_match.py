"""Random target interpolation: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1518F384','generated_1BA1D0'
ENTRY,ROM,BODY,SIZE=0x1518F384,0x1BC834,216,216
SOURCE='conker/src/game/generated_1BA1D0.c'
OBJECT='conker/build/src/game/generated_1BA1D0.c.o'
ASM='conker/asm/1BA1D0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-random-target-interpolation-match'
RODATA_SYMBOL=None
RAW_SHA='f8129122162b7702b4b11f7c9fa63b817dab1130b972df1560c159cfc6d9f330'
SNAPSHOT_SHA='3b26222ab363611e3bf96d20bcf1c93db98bff85a5cb49604a351ba0ea3463cc'
BEFORE_ELF_SHA='8484ee7ad6a8d5a12e3a125b78487cd28eba1d79ea82fb2d0e5754a39d81cf17'
TRUTH_SHA='b4a46cb5a22adeb621ce79f3fb4eae865df8055d5c58815bdd07e77b9dca90ab'
BINDINGS={20: [('R_MIPS_26', 'func_150ADA68')], 88: [('R_MIPS_26', 'func_150ADA68')], 144: [('R_MIPS_HI16', 'D_800A7B74')], 148: [('R_MIPS_LO16', 'D_800A7B74')], 160: [('R_MIPS_HI16', 'D_800A7B78')], 184: [('R_MIPS_LO16', 'D_800A7B78')]}
ORIGINAL_BINDINGS={20: [('R_MIPS_26', 'func_150ADA68')], 88: [('R_MIPS_26', 'func_150ADA68')], 144: [('R_MIPS_HI16', 'D_800A7B74')], 148: [('R_MIPS_LO16', 'D_800A7B74')], 160: [('R_MIPS_HI16', 'D_800A7B78')], 184: [('R_MIPS_LO16', 'D_800A7B78')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A7B74;\nextern f32 D_800A7B78;\nf32 func_150ADA68(void);\n\ntypedef struct {\n    f32 firstUpper;\n    f32 firstLower;\n    f32 firstTarget;\n    f32 secondUpper;\n    f32 secondLower;\n    f32 reserved14;\n    f32 secondTarget;\n    s16 firstReady;\n    s16 secondReady;\n} RandomTargets1BA1D0;\n\n'
DECLARATIONS='extern f32 D_800A7B74;\nextern f32 D_800A7B78;\n\ntypedef struct {\n    f32 firstUpper;\n    f32 firstLower;\n    f32 firstTarget;\n    f32 secondUpper;\n    f32 secondLower;\n    f32 reserved14;\n    f32 secondTarget;\n    s16 firstReady;\n    s16 secondReady;\n} RandomTargets1BA1D0;\n\n'
SELECTED='/* Initialize missing random targets, then interpolate the two live coordinates. */\ns32 func_1518F384(u8 *object) {\n    RandomTargets1BA1D0 *targets = (RandomTargets1BA1D0 *)(object + 0x110);\n\n    if (targets->firstReady == 0) {\n        targets->firstTarget = func_150ADA68() *\n            (targets->firstUpper - targets->firstLower) + targets->firstLower;\n        targets->firstReady = 1;\n    }\n    if (targets->secondReady == 0) {\n        targets->secondTarget = func_150ADA68() *\n            (targets->secondUpper - targets->secondLower) + targets->secondLower;\n        targets->secondReady = 1;\n    }\n    *(f32 *)(object + 0x30) +=\n        (targets->secondTarget - *(f32 *)(object + 0x30)) * D_800A7B74;\n    *(f32 *)(object + 0x2C) +=\n        (targets->firstTarget - *(f32 *)(object + 0x2C)) * D_800A7B78;\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    import re
    normalized=re.sub(r'build/[^,]+, line [0-9]+:', 'OWNER, line N:',text)
    rows=re.findall(r'cfe: Warning 712: OWNER, line N: illegal combination of pointer and integer\n     (func_[0-9A-F]+)\(arg0\);\n -+\^\n',normalized)
    if sorted(rows)!=['func_1518E4A0','func_1518E4A0','func_15190454','func_15190454']:raise ValueError(text)
    expected=''.join(re.findall(r'cfe: Warning 712: OWNER, line N: illegal combination of pointer and integer\n     func_[0-9A-F]+\(arg0\);\n -+\^\n',normalized))
    if normalized!=expected:raise ValueError(text)
    return 4


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Random target interpolation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1518F384() {\n    return 0;\n}':raise ValueError('Random target interpolation placeholder changed')
    return before[:start]+DECLARATIONS+SELECTED.rstrip()+before[end:]



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Random target interpolation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Random target interpolation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Random target interpolation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Random target interpolation live input differs: '+name)
    return values

METADATA_GROUPS=((2891892, ('D_80099418', 'D_8009EE18'), (1, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Random target interpolation named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Random target interpolation symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Random target interpolation metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Random target interpolation frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Random target interpolation original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Random target interpolation strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Random target interpolation named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1518F384.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1BA1D0.c.o', 'make-shadow/src/game/generated_1BA1D0.c.o.compact', 'make-shadow/src/game/generated_1BA1D0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Random target interpolation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random target interpolation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random target interpolation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Random target interpolation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random target interpolation Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1BA1D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Random target interpolation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Random target interpolation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Random target interpolation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Random target interpolation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=32,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
