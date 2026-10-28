"""Adjacent record load: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151838B0','generated_1B0740'
ENTRY,ROM,BODY,SIZE=0x151838B0,0x1B0D60,196,196
SOURCE='conker/src/game/generated_1B0740.c'
OBJECT='conker/build/src/game/generated_1B0740.c.o'
ASM='conker/asm/1B0740.s'
BUILD='conker/build/game-adjacent-record-load-match'
RODATA_SYMBOL=None
RAW_SHA="d08b875c488e42d9a4f3fee075cd8286c63649f530091ca8b1c8b85b18d9cd72"
SNAPSHOT_SHA="2d649515e90932e0115a125c12f285e71735dfa1e0bb10b451515244431bb065"
BEFORE_ELF_SHA="4f2b9d0c0304fa7e5ce89b9d668179f2c30532a6e406b34d6614a07f729be6af"
TRUTH_SHA="eaa8b96397b1df970cbd5dac27abe6d14cf5afc58ba8967ad12105cf51876823"
PARENT,TABLE,FLAG,INITIALIZE,LOAD=0x15183290,0x800DDE80,0x800DDF69,0x15183ACC,0x1502B6BC
BINDINGS={16:[('R_MIPS_HI16','D_800DDE80')],20:[('R_MIPS_LO16','D_800DDE80')],56:[('R_MIPS_26','func_15183ACC')],112:[('R_MIPS_26','func_1502B6BC')],152:[('R_MIPS_HI16','D_800DDF69')],176:[('R_MIPS_LO16','D_800DDF69')]}
HEADERS="#include <ultra64.h>\ntypedef struct { s32 words[5]; } Record15183974;\nextern Record15183974 D_800DDE80[11];\ns32 func_15183ACC();\n"
DECLARATIONS="extern u8 D_800DDF69[];\nvoid *func_1502B6BC(s32 *size, s32 count, s32 *relocated, s32 depth, ...);\n\n"
SELECTED="/* Load the adjacent record on demand and copy its owner fields. */\nvoid func_151838B0(s32 index) {\n    s32 *result;\n\n    if (D_800DDE80[index].words[0] == 0) {\n        func_15183ACC(index);\n    }\n    if (D_800DDE80[index + 1].words[0] == 0) {\n        result = func_1502B6BC(0, 0, 0, 2, 9, index + 0xAE);\n        if (result != NULL) {\n            D_800DDE80[index + 1].words[0] = (s32)result;\n            D_800DDE80[index + 1].words[1] = result[0];\n            D_800DDE80[index + 1].words[2] = result[2];\n            D_800DDE80[index + 1].words[3] = D_800DDE80[index].words[3];\n            D_800DDE80[index + 1].words[4] = 0;\n            D_800DDF69[index] = 1;\n        }\n    }\n}"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected adjacent-record owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Adjacent record load body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151838B0() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Adjacent record load placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Adjacent record load snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Adjacent record load frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Adjacent record load predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Adjacent record load live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Adjacent record load strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Adjacent record load original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Adjacent record load image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Adjacent record load named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='91cfc61697b2f874f74475c5dadac1faec1f2e3c4f2a515d593b62d15b71ba03':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151838B0.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1B0740.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1B0740.c.o","make-shadow/src/game/generated_1B0740.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Adjacent record load artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Adjacent record load artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Adjacent record load raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Adjacent record load evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Adjacent record load Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1B0740.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Adjacent record load Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Adjacent record load private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Adjacent record load changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Adjacent record load protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=40,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
