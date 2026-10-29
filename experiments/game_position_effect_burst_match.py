"""Position effect burst: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151D5648','generated_200930'
ENTRY,ROM,BODY,SIZE=0x151D5648,0x202AF8,204,204
SOURCE='conker/src/game/generated_200930.c'
OBJECT='conker/build/src/game/generated_200930.c.o'
ASM='conker/asm/200930.s'
BUILD='conker/build/game-position-effect-burst-match'
RODATA_SYMBOL=None
RAW_SHA='a13fdeb94700740a64eafae1c74968b287ef59601a996218f390a7f4696989c6'
SNAPSHOT_SHA='f8d58ffeed344b354ba9621a2e872858104ebba3b5b25884d8d6399e85cc0d66'
BEFORE_ELF_SHA='3af9d58526f734f4cd164f77f683c148f21367d4bb7f5f3f6c0a589f6890c7d3'
TRUTH_SHA='5b74d3322e82539b7d7bf896c45a5b6dfb7b383e79763760c46540dd83d16b57'
BINDINGS={28: [('R_MIPS_26', 'func_151D5514')], 44: [('R_MIPS_26', 'func_151D3FF4')], 52: [('R_MIPS_26', 'func_150ADA68')], 60: [('R_MIPS_26', 'func_150ADA20')], 180: [('R_MIPS_26', 'func_151541B8')]}
HEADERS='#include <ultra64.h>\nvoid func_151D5514(f32 *, u8, s32);\nvoid func_151D3FF4(f32 *, u8, s32);\nf32 func_150ADA68(void);\ns32 func_150ADA20(void);\nu8 *func_151541B8(f32 *, f32, f32, f32, f32, u8, s32);\n\n'
DECLARATIONS='void func_151D5514(f32 *, u8, s32);\nvoid func_151D3FF4(f32 *, u8, s32);\nf32 func_150ADA68(void);\ns32 func_150ADA20(void);\nu8 *func_151541B8(f32 *, f32, f32, f32, f32, u8, s32);\n\n'
SELECTED='/* Submit the paired position effects, then the randomized burst. */\nvoid func_151D5648(f32 *position, u8 kind, s32 mode) {\n    u32 randomValue;\n    f32 randomScale;\n\n    func_151D5514(position, kind, mode);\n    func_151D3FF4(position, kind, mode);\n    randomScale = func_150ADA68();\n    randomValue = (u32)func_150ADA20();\n    func_151541B8(position, randomScale * 4.0f + 12.0f, 1.6409999f,\n                 (randomValue % 56U) + 200U, 0.0f, kind, mode);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected position-effect-burst owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Position effect burst body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151D5648() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Position effect burst placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Position effect burst snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Position effect burst frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Position effect burst predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Position effect burst live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Position effect burst frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Position effect burst original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Position effect burst strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Position effect burst named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='82a037c271b5f3a9f248316290dcb31008db70397b5ec399ebc415cdd6bd8f3a':raise ValueError('Position effect burst inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151D5648.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_200930.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_200930.c.o","make-shadow/src/game/generated_200930.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Position effect burst artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position effect burst artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position effect burst raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Position effect burst evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position effect burst Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_200930.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Position effect burst Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Position effect burst private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Position effect burst changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Position effect burst protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=48,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
