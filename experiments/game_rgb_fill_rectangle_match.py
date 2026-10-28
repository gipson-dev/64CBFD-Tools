"""RGB fill rectangle: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15110544','generated_13D350'
ENTRY,ROM,BODY,SIZE=0x15110544,0x13D9F4,188,188
SOURCE='conker/src/game/generated_13D350.c'
OBJECT='conker/build/src/game/generated_13D350.c.o'
ASM='conker/asm/13D350.s'
BUILD='conker/build/game-rgb-fill-rectangle-match'
RAW_SHA='0a176986106e50f31ba0b415269d8aef7de4e0dc80779b6038b25b7d8e532e8c'
SNAPSHOT_SHA='efff697f2c0895a09d49e518836379ce13c43b98b46224d90a0d2c3b737ec075'
BEFORE_ELF_SHA='5795da319763009c6e5c780cf08f6d1d8089ae1d94a98d12b9d8dc9b83cef63d'
TRUTH_SHA='7532df75269a9c55bbeb0f702c8a48439e186bf264366b4ee9a67a7c87aff458'
COLOR_IMAGE,RECTANGLE=0x1501A680,0x1501A6CC
BINDINGS={68:[('R_MIPS_26','func_1501A680')],164:[('R_MIPS_26','func_1501A6CC')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="Gfx *func_1501A680(Gfx *commands);\nGfx *func_1501A6CC(Gfx *commands, s32 left, s32 top, s32 right, s32 bottom);\n"
SELECTED="/* Append an RGBA16 fill rectangle, with the retail legacy blend-mask bits. */\nGfx *func_15110544(Gfx *commands, s32 left, s32 top, s32 right, s32 bottom,\n                    u8 red, u8 green, u8 blue) {\n    gDPPipeSync(commands++);\n    gDPSetOtherMode(commands++, G_CYC_FILL | G_TF_BILERP | G_TC_FILT | 0xF,\n        G_AC_NONE | G_ZS_PRIM | G_RM_NOOP | G_RM_NOOP2);\n    commands = func_1501A680(commands);\n    gDPSetFillColor(commands++, ((u32)GPACK_RGBA5551(red, green, blue, 1) << 16) |\n        GPACK_RGBA5551(red, green, blue, 1));\n    return func_1501A6CC(commands, left, top, right, bottom);\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('RGB fill rectangle body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15110544() {\n    return 0;\n}'
    if before.count(stub)!=1 or 'Gfx *func_1501A680'in before:raise ValueError('RGB fill rectangle placeholder changed')
    return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('RGB fill rectangle snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('RGB fill rectangle frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('RGB fill rectangle predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('RGB fill rectangle live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('RGB fill rectangle strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('RGB fill rectangle original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('RGB fill rectangle image differs from the body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('RGB fill rectangle named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15110544.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_13D350.c.o","make-shadow/src/game/generated_13D350.c.o.compact","make-shadow/src/game/generated_13D350.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('RGB fill rectangle artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('RGB fill rectangle artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('RGB fill rectangle raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('RGB fill rectangle evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('RGB fill rectangle Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('RGB fill rectangle expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_13D350.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('RGB fill rectangle Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('RGB fill rectangle private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('RGB fill rectangle changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('RGB fill rectangle protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
