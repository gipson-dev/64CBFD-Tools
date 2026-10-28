"""Selector payload effect: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as _pad
sys.modules.setdefault("pad_generated_object",_pad)
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1500A6D8','game_36680'
ENTRY,ROM,BODY,SIZE=0x1500A6D8,0x37B88,196,196
SOURCE='conker/src/game_36680.c'
OBJECT='conker/build/src/game_36680.c.o'
ASM='conker/asm/nonmatchings/game_36680/func_1500A6D8.s'
BUILD='conker/build/game-selector-payload-effect-match'
RODATA_SYMBOL=None
RAW_SHA="c18bf186ea8126f645e9c0af683b8171e34db8109d4f23a3c12214daedfe3d2b"
SNAPSHOT_SHA="4b8fbf17fbc9dd2d44df9346aac63df8c93368032e3cf8c2d52d7012562b4d55"
BEFORE_ELF_SHA="92e68c907aba901c0e2b87dc83601de8ff7ef7cbb25d4ffc9135d39d01403ab4"
TRUTH_SHA="562cf1ff5272e4dff3f3dcb753e52b752b3fcbfe9df67019f68526dbcc5300d1"
PARENT,TABLE,CATEGORY,IDS,LOOKUP,FACTORY,COPY=0x1500A94C,0x80082BFC,0x800BE9F0,0x80082BEC,0x150B060C,0x1516037C,0x10022EC0
BINDINGS={20:[('R_MIPS_HI16','D_80082BEC')],24:[('R_MIPS_LO16','D_80082BEC')],32:[('R_MIPS_HI16','D_800BE9F0')],56:[('R_MIPS_LO16','D_800BE9F0')],96:[('R_MIPS_26','func_150B060C')],152:[('R_MIPS_26','func_1516037C')],172:[('R_MIPS_26','memcpy')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n\n"
DECLARATIONS="typedef struct { u8 values[2][3]; } EffectSelectorTable36680;\ntypedef struct {\n    f32 unk0;\n    f32 unk4;\n    u8 *record;\n    f32 unkC;\n    f32 unk10;\n    f32 unk14;\n} UnkB060C;\nextern EffectSelectorTable36680 D_80082BEC;\nextern s32 D_800BE9F0;\ns32 func_150B060C(u8, UnkB060C *);\nstruct225 *func_1516037C(Header *, struct226 *, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n"
SELECTED="/* Select the category-specific payload for commands 0x49..0x4B and spawn it. */\nvoid func_1500A6D8(struct226 *actor, s32 command) {\n    Header header;\n    UnkB060C payload;\n    s32 variant = 0;\n    EffectSelectorTable36680 ids = D_80082BEC;\n    struct225 *effect;\n\n    if (D_800BE9F0 == 6) {\n        variant = 1;\n    } else {\n        variant = 0;\n    }\n    if (func_150B060C(ids.values[variant][command - 0x49], &payload) != 0) {\n        header.unk0 = 0;\n        header.unk1 = 23;\n        header.unk2 = 300;\n        header.unk4 = 0;\n        effect = func_1516037C(&header, actor, sizeof(payload), 255, 1);\n        if (effect != NULL) {\n            memcpy((u8 *)effect + 0x18, &payload, sizeof(payload));\n        }\n    }\n}"

def check_owner_diagnostics(text):
    codes=re.findall(r'cfe: Warning (\d+):',text)
    if Counter(codes)!=Counter({'712':5,'709':1}):raise ValueError('Unexpected owner diagnostics')
    lines=[x.strip()for x in text.splitlines()if x.startswith('     ')]
    expected=[
      'temp_v0 = func_1516295C(arg0, D_80095B48[arg1], D_80095B4C[arg1], 2, 300, 12, -1, 0, -1, 1, 1, 255, 1);',
      'temp_v0 = func_1516387C(arg0, 2, 16, 300, 0, 12, 255, 1);',
      'temp_v0 = func_1516387C(arg0, 2, 16, 300, 0, 12, 255, 1);',
      'temp_v0 = func_1516387C(arg0, 2, 16, 300, 0, 12, 255, 1);',
      'temp_v0 = func_15149130(300, -1, 45, -1, 0, 0, 48, 255, 1);',
      'temp_v0 = func_15149130(300, -1, 45, -1, 0, 0, 48, 255, 1);']
    if lines!=expected or text.count('cfe:')!=6:raise ValueError('Changed diagnostic sites')
    return 6

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Selector payload effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1500A6D8() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Selector placeholder changed')
    result=before.replace(stub,SELECTED,1).replace('/* Generated placeholder declarations. */',DECLARATIONS+'/* Generated placeholder declarations. */',1).replace('s32 func_1500A6D8();','void func_1500A6D8(struct226 *actor, s32 command);',1)
    a=result.index('// void func_1500A6D8(');b=result.index('void func_1500A79C(',a);result=result[:a]+result[b:]
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_36680/func_1500A6D8.s. */\n','',1)
    if result.count('func_1516037C(&tmp, arg0, 0, 255, 1);')!=3:raise ValueError('Legacy actor calls changed')
    return result.replace('func_1516037C(&tmp, arg0, 0, 255, 1);','func_1516037C((Header *)&tmp, (struct226 *)arg0, 0, 255, 1);')


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Selector payload effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Selector payload effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Selector payload effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Selector payload effect live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Selector payload effect strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Selector payload effect original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Selector payload effect image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Selector payload effect named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='c9f2d82d72afcd7be14278dbc076ff6b8aa1330ca0f42e11d3bcf51b76923225':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1500A6D8.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game_36680.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game_36680.c.o","make-shadow/src/game_36680.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Selector payload effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Selector payload effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Selector payload effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Selector payload effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Selector payload effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_36680.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Selector payload effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Selector payload effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Selector payload effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Selector payload effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=80,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
