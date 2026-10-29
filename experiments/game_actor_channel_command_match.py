"""Actor channel command: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15080430','generated_AD6B0'
ENTRY,ROM,BODY,SIZE=0x15080430,0xAD8E0,204,208
SOURCE='conker/src/game/generated_AD6B0.c'
OBJECT='conker/build/src/game/generated_AD6B0.c.o'
ASM='conker/asm/AD6B0.s'
BUILD='conker/build/game-actor-channel-command-match'
RODATA_SYMBOL=None
COUNT,APPLY,PARENT,MODE=0x1507E968,0x1507E500,0x15080228,0x800D1928
RAW_SHA='d0b480ac7753315df49a2dac777552ceae02650cc32af7d501df21ac454b4f7b'
SNAPSHOT_SHA='157720f21f61cbe8d74e09ef7efcbce75ea0aadb269beee1b0aaa097f2083945'
BEFORE_ELF_SHA='00063b783ef3f0a050c6ca8e44015e9951ca90cfdf396580f62994f0caac6d64'
TRUTH_SHA='d93fd9bc518ef31f35a729e63ab4603aa8bafcf7d797c873b410db823d5d1207'
BINDINGS={24: [('R_MIPS_26', 'func_1507E968')], 56: [('R_MIPS_HI16', 'D_800D1928')], 60: [('R_MIPS_LO16', 'D_800D1928')], 76: [('R_MIPS_26', 'func_1507E500')], 108: [('R_MIPS_HI16', 'D_800D1928')], 116: [('R_MIPS_LO16', 'D_800D1928')], 152: [('R_MIPS_26', 'func_1507E500')], 172: [('R_MIPS_HI16', 'D_800D1928')], 180: [('R_MIPS_LO16', 'D_800D1928')]}
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='s32 func_1507E968(u8 *);\nvoid func_1507E500(u8 *, s32, s32);\n'
SELECTED='/* Apply a channel command and clamp its optional duration for an active actor. */\nvoid func_15080430(u8 *actor, s32 channel, s32 duration) {\n    if (actor != 0) {\n        if (func_1507E968(actor) > 0) {\n            if (channel == 0) {\n                D_800D1928 = 0;\n                *(u16 *)(actor + 0x72) = 20;\n                func_1507E500(actor, 0, 10);\n            } else {\n                *(u16 *)(actor + 0x72) = 0xFFFE;\n                if (channel == 1) {\n                    D_800D1928 = 2;\n                } else {\n                    if (duration != 0) {\n                        if (duration > 20) duration = 20;\n                        if (duration <= 0) duration = 1;\n                    }\n                    func_1507E500(actor, channel, duration);\n                }\n            }\n        } else {\n            D_800D1928 = channel != 0;\n            if (channel != 0) return;\n            actor[0x1FF] = 0;\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Actor channel command owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor channel command body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15080430() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Actor channel command placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor channel command snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor channel command frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor channel command predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor channel command live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor channel command frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor channel command original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor channel command strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor channel command named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='63822339da0c8d3c9a2f6ce9f23ca0fb69345fc4b99f9cb352d44c9f6a218615':raise ValueError('Actor channel command inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15080430.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_AD6B0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_AD6B0.c.o","make-shadow/src/game/generated_AD6B0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor channel command artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor channel command artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor channel command raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor channel command evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor channel command Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_AD6B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor channel command Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor channel command private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor channel command changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor channel command protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=24,alignment_words=1,slot_words=52,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
