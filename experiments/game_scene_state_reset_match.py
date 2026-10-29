"""Scene state reset: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151E327C','generated_20AE20'
ENTRY,ROM,BODY,SIZE=0x151E327C,0x21072C,200,200
SOURCE='conker/src/game/generated_20AE20.c'
OBJECT='conker/build/src/game/generated_20AE20.c.o'
ASM='conker/asm/20AE20.s'
BUILD='conker/build/game-scene-state-reset-match'
RODATA_SYMBOL=None
RAW_SHA='0d9d961ab77b9360b94e2744fa4734d54a27b7ab2f100dc8c107e04b064bb66e'
SNAPSHOT_SHA='f6f64d1d83772311be2d15b346e44c895119082b99bbbc7eccd6171cd9970864'
BEFORE_ELF_SHA='75deb5dbe7476948dae75ebb12b5fb128e2842a0b7c5762d703833967ebbca95'
TRUTH_SHA='4cbe3654f97806718f6304c10b86c7c23a921aafb1eadb0141257481210e47c1'
BINDINGS={4: [('R_MIPS_HI16', 'D_80087260')], 8: [('R_MIPS_LO16', 'D_80087260')], 24: [('R_MIPS_HI16', 'D_800E9D00')], 28: [('R_MIPS_LO16', 'D_800E9D00')], 32: [('R_MIPS_HI16', 'D_80087270')], 60: [('R_MIPS_LO16', 'D_80087270')], 68: [('R_MIPS_HI16', 'D_8008FD8C')], 72: [('R_MIPS_LO16', 'D_8008FD8C')], 76: [('R_MIPS_HI16', 'D_8008FD90')], 80: [('R_MIPS_LO16', 'D_8008FD90')], 84: [('R_MIPS_HI16', 'D_8008FD94')], 88: [('R_MIPS_LO16', 'D_8008FD94')], 92: [('R_MIPS_HI16', 'D_8008FDBC')], 96: [('R_MIPS_LO16', 'D_8008FDBC')], 100: [('R_MIPS_HI16', 'D_800BE618')], 104: [('R_MIPS_LO16', 'D_800BE618')], 108: [('R_MIPS_HI16', 'D_800D23A8')], 112: [('R_MIPS_LO16', 'D_800D23A8')], 116: [('R_MIPS_HI16', 'D_800E0B94')], 120: [('R_MIPS_LO16', 'D_800E0B94')], 124: [('R_MIPS_HI16', 'D_800D2E40')], 132: [('R_MIPS_LO16', 'D_800D2E40')], 128: [('R_MIPS_HI16', 'D_800BE3E0')], 136: [('R_MIPS_LO16', 'D_800BE3E0')], 48: [('R_MIPS_HI16', 'D_800BE3DF')], 144: [('R_MIPS_LO16', 'D_800BE3DF')], 148: [('R_MIPS_26', 'func_1501C730')], 160: [('R_MIPS_HI16', 'D_800E0B99')], 164: [('R_MIPS_LO16', 'D_800E0B99')], 176: [('R_MIPS_26', 'func_151E7EF8')], 172: [('R_MIPS_HI16', 'D_800E0BB1')], 180: [('R_MIPS_LO16', 'D_800E0BB1')]}
HEADERS='#include <ultra64.h>\n\nextern s8 D_80087260, D_8008FD8C, D_8008FD90, D_800BE3DF;\nextern u8 D_80087270[], D_800BE618, D_800D23A8, D_800E0B94;\nextern u8 D_800D2E40, D_800BE3E0, D_800E0B99, D_800E0BB1;\nextern s16 D_8008FDBC;\nextern s32 D_8008FD94;\nextern u32 D_800E9D00;\nvoid func_1501C730(s32, s32, s32, s32, s32);\nvoid func_151E7EF8(void);\n\n'
DECLARATIONS='extern s8 D_80087260, D_8008FD8C, D_8008FD90, D_800BE3DF;\nextern u8 D_80087270[], D_800BE618, D_800D23A8, D_800E0B94;\nextern u8 D_800D2E40, D_800BE3E0, D_800E0B99, D_800E0BB1;\nextern s16 D_8008FDBC;\nextern s32 D_8008FD94;\nextern u32 D_800E9D00;\nvoid func_1501C730(s32, s32, s32, s32, s32);\nvoid func_151E7EF8(void);\n\n'
SELECTED='/* Reset scene flags, submit the saved transition, then run the integrity check. */\nvoid func_151E327C(void) {\n    D_80087260 = 3;\n    if (D_800E9D00 & 0x200) {\n        D_80087260 = 0x33;\n    }\n    D_80087270[0] = 0;\n    D_8008FD8C = 1;\n    D_8008FD90 = 1;\n    /* Retail changes only the first representation byte of this word. */\n    *(s8 *)&D_8008FD94 = 1;\n    D_8008FDBC = 0;\n    *(s8 *)&D_800BE618 = 1;\n    D_800D23A8 = 0;\n    D_800E0B94 = 0;\n    D_800D2E40 = 0;\n    func_1501C730(6, D_800BE3DF, D_800BE3E0, 0, 1);\n    D_800E0B99 = 1;\n    *(s8 *)&D_800E0BB1 = 1;\n    func_151E7EF8();\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected scene-state-reset owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Scene state reset body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151E327C() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Scene state reset placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Scene state reset snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Scene state reset frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Scene state reset predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Scene state reset live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Scene state reset strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Scene state reset original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Four existing definitions rotate within one closed GNU hash bucket.
    # Check both complete records and fixed-width strings; exclude no bytes.
    names=('D_800E0B99','D_80099324','D_800A3624','D_8009ED24')
    definitions=((0x800E0B99,0,16,0,65521),(0x80099324,0,16,0,65521),
                 (0x800A3624,0,16,0,65521),(0x8009ED24,0,16,0,6))
    rows={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    first=rows[names[0]]
    for i,(name,wanted)in enumerate(zip(names,definitions)):
        pos,f,loc=rows[name]
        if pos!=first[0]+16*i or loc!=first[2]+11*i or f[0]!=first[1][0]+11*i:
            raise ValueError('Scene reset symbol bucket layout changed')
        if f[1:]!=wanted or before[loc:loc+11]!=name.encode()+b'\0':
            raise ValueError('Scene reset named definition changed: '+name)
    for dest,src in zip(names,names[1:]+names[:1]):
        pos,f,loc=rows[dest];sp,sf,sl=rows[src]
        result[pos:pos+16]=before[sp:sp+16]
        struct.pack_into('>I',result,pos,f[0])
        result[loc:loc+11]=src.encode()+b'\0'
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Scene state reset image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Scene state reset named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='1678dac601e1def3df3c6438b7a8b4bb0914ce5ef73a929921f12916f7ead9f2':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151E327C.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_20AE20.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_20AE20.c.o","make-shadow/src/game/generated_20AE20.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Scene state reset artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Scene state reset artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Scene state reset raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Scene state reset evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Scene state reset Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_20AE20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Scene state reset Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Scene state reset private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Scene state reset changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Scene state reset protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=32,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
