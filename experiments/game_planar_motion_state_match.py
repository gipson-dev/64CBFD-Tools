"""Planar motion state: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
from tools import pad_generated_object as _primary_padder
sys.modules['pad_generated_object']=_primary_padder
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150C308C','game_EF410'
ENTRY,ROM,BODY,SIZE=0x150C308C,0xF053C,212,212
SOURCE='conker/src/game_EF410.c'
OBJECT='conker/build/src/game_EF410.c.o'
ASM='conker/asm/nonmatchings/game_EF410/func_150C308C.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-planar-motion-state-match'
RODATA_SYMBOL=None
RAW_SHA='3be6459c58f8bfbd767abf2ea7d6743476db85392fba865573b117498ab0a73a'
SNAPSHOT_SHA='b2e842ac7a9da81701c4ffbdc002b66dd229c5c81bad22041190b0894e33c09c'
BEFORE_ELF_SHA='22e028b94afa7a644fb598b180cc2ff698f0608def55ad2eadd9c883363fd510'
TRUTH_SHA='677d80795d7ccb46e08e313e46cda1f88abae35a81b20c40f33e59674850a3fb'
BINDINGS={20: [('R_MIPS_HI16', 'D_80082FA4')], 40: [('R_MIPS_LO16', 'D_80082FA4')], 44: [('R_MIPS_26', 'func_15144B34')], 60: [('R_MIPS_HI16', 'D_800A0310')], 68: [('R_MIPS_LO16', 'D_800A0310')], 120: [('R_MIPS_26', 'func_150484A0')], 136: [('R_MIPS_26', 'func_15144C8C')], 144: [('R_MIPS_HI16', 'D_800A0314')], 148: [('R_MIPS_LO16', 'D_800A0314')]}
HEADERS='#include <ultra64.h>\nextern s32 D_80082FA4;\nextern f32 D_800A0310, D_800A0314;\nf32 *func_15144B34(s32);\nf32 func_150484A0(f32, f32);\nf32 func_15144C8C(f32, f32);\n'
DECLARATIONS=''
SELECTED='/* Move an active actor to state five when either motion test succeeds. */\ns32 func_150C308C(u8 *actor) {\n    u8 stop = 0;\n    f32 *motion;\n    f32 x, z;\n\n    if (*(s16 *)(actor + 0x1C) >= 6) {\n        motion = func_15144B34(D_80082FA4);\n        x = motion[0];\n        z = motion[2];\n        x = x * x + z * z;\n        if (x < D_800A0310) {\n            stop = 1;\n        } else {\n            x = func_150484A0(motion[0], motion[2]);\n            x = func_15144C8C(x, *(f32 *)(actor + 0x160));\n            if (D_800A0314 < x) {\n                stop = 1;\n            }\n        }\n    }\n    if (stop != 0) {\n        *(s16 *)(actor + 0x1C) = 5;\n    }\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Planar motion state owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Planar motion state body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    marker='/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C308C.s. */'
    if before.count(marker)!=1 or before.count('s32 func_150C308C();')!=1:raise ValueError('Planar callback source anchors changed')
    start=before.index(marker);end=before.index('/* Emit the special actor texture phase',start)
    if before[start:end].count('s32 func_150C308C() {\n    return 0;\n}')!=1:raise ValueError('Planar callback placeholder changed')
    return (before[:start]+SELECTED+'\n'+before[end:]).replace('s32 func_150C308C();','s32 func_150C308C(u8 *);',1).replace('extern f32 D_800A0284;','extern f32 D_800A0284;\nf32 *func_15144B34(s32);',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Planar motion state snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Planar motion state frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Planar motion state predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Planar motion state live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Planar motion state frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Planar motion state original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Planar motion state strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Planar motion state named definitions changed')

NEW_GUARDS=[(84, 1174806528, 1174807296), (88, 1174929468, 1174954044)]

def guard_manifest(before):
    if sha(before)!='84c233dfd374f8ba8b4f66dca69b180bc2b8b3813b7a1a594d72f88130ba0306':raise ValueError('Inherited guard prefix changed')
    return before+b'game_EF410,func_150C308C,0x054,0x46062000,0x46062300,-,-,Normalize closed planar squared-length temporary from f0 to f12,,,false\r\ngame_EF410,func_150C308C,0x058,0x4608003C,0x4608603C,-,-,Normalize closed planar squared-length temporary from f0 to f12,,,false\r\n'

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings)
    result=bytearray(raw)
    for offset,expected,replacement in NEW_GUARDS:
        if struct.unpack_from('>I',result,offset)[0]!=expected:raise ValueError('Planar temporary guard preimage changed')
        struct.pack_into('>I',result,offset,replacement)
    return bytes(result),bindings


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150C308C.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game_EF410.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game_EF410.c.o","make-shadow/src/game_EF410.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Planar motion state artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Planar motion state artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Planar motion state raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Planar motion state evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Planar motion state Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_EF410.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Planar motion state Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Planar motion state private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Planar motion state changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Planar motion state protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=32,alignment_words=0,slot_words=53,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
