"""Record initializer: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15183ACC','generated_1B0740'
ENTRY,ROM,BODY,SIZE=0x15183ACC,0x1B0F7C,216,216
SOURCE='conker/src/game/generated_1B0740.c'
OBJECT='conker/build/src/game/generated_1B0740.c.o'
ASM='conker/asm/1B0740.s'
BUILD='conker/build/game-record-initializer-match'
RODATA_SYMBOL=None
RAW_SHA="a6f62de46073312759970f68fa2893c72ebb5b7a5ea86d1f52f11a9b14fa05cb"
SNAPSHOT_SHA="2b4c0bdd13d15562275b82cb7abfd9d2d08f6b464708bcad3dab2b5d54a81bca"
BEFORE_ELF_SHA="16a6cb0868ea9ba387f9039374021609fa5450fdc9cf1470f0b6b6a6a7f8a93c"
TRUTH_SHA="030e27791e4ea9996960b35551649a686c21ae91694a965b3f49f562a27c379b"
TABLE,FLAG,VIEWS,LOAD,RESOURCE=0x800DDE80,0x800DDF68,0x800DDF78,0x1502B6BC,0x1510CE60
BINDINGS={16:[("R_MIPS_HI16","D_800DDE80")],20:[("R_MIPS_LO16","D_800DDE80")],80:[("R_MIPS_26","func_1502B6BC")],112:[("R_MIPS_HI16","D_800DDF78")],124:[("R_MIPS_LO16","D_800DDF78")],172:[("R_MIPS_26","func_1510CE60")],184:[("R_MIPS_HI16","D_800DDF68")],196:[("R_MIPS_LO16","D_800DDF68")]}
HEADERS="#include <ultra64.h>\ntypedef struct { s32 words[5]; } Record15183974;\nextern Record15183974 D_800DDE80[11];\nextern u32 D_800DDF78[];\nvoid *func_1502B6BC(s32 *size, s32 count, s32 *relocated, s32 depth, ...);\n"
DECLARATIONS="extern u8 D_800DDF68[];\ns32 func_1510CE60(void *data, s32 unresolvedOnly, s32 retain, s32 priority, s32 *output);\n\n"
SELECTED="/* Load an empty record and prepare its referenced graphics resources. */\nvoid func_15183ACC(s32 index) {\n    s32 *result;\n\n    if (D_800DDE80[index].words[0] == 0) {\n        result = func_1502B6BC(0, 0, 0, 2, 9, index + 0xAD);\n        if (result != NULL) {\n            D_800DDE80[index].words[0] = (s32)result;\n            D_800DDE80[index].words[1] = result[0];\n            D_800DDE80[index].words[2] = result[2];\n            D_800DDE80[index].words[3] = result[6];\n            D_800DDF78[index] = result[4];\n            func_1510CE60((void *)D_800DDF78[index], 0, 1, 0x3E,\n                          &D_800DDE80[index].words[4]);\n            D_800DDF68[index] = 1;\n        }\n    }\n}"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record-initializer owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=216 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record initializer body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15183ACC() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record initializer placeholder changed')
    if before.count('s32 func_15183ACC();')!=1:raise ValueError('Initializer declaration changed')
    return before.replace('s32 func_15183ACC();','void func_15183ACC(s32 index);').replace(stub,(DECLARATIONS+SELECTED).strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record initializer snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record initializer frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record initializer predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record initializer live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record initializer strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Record initializer original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record initializer image differs from body and extent prediction')
    expected=Counter((n,f[1],216 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record initializer named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='91cfc61697b2f874f74475c5dadac1faec1f2e3c4f2a515d593b62d15b71ba03':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15183ACC.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1B0740.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1B0740.c.o","make-shadow/src/game/generated_1B0740.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record initializer artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record initializer artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record initializer raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record initializer evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record initializer Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1B0740.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record initializer Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record initializer private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record initializer changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record initializer protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=54,frame=40,alignment_words=0,slot_words=54,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
