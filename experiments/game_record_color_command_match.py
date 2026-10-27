"""Registered record color commands: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150FA468','generated_126F60'
ENTRY,ROM,BODY,SIZE=0x150FA468,0x127918,184,184
SOURCE='conker/src/game/generated_126F60.c'
OBJECT='conker/build/src/game/generated_126F60.c.o'
ASM='conker/asm/126F60.s'
BUILD='conker/build/game-record-color-command-match'
RAW_SHA='afaf85b67a60ad1f1817ea2d7cfbd7175ba906766d22c0c2a8c5de9615ee56ee'
SNAPSHOT_SHA='b3729c1d65035e289aa41ab748dd0a3b47125e6ffc1d744146d47b3d19638fd0'
BEFORE_ELF_SHA='69219af068e12484b842db07cfe9df8e9dbbe6fce15dea1ce808131bcb55c087'
TRUTH_SHA='245af547df9a7df9679ab5aaa580ce62ae4632a92c094fedc47ad6f9ede9dc0e'
PARENT,PARENT_ROM,PARENT_SIZE=0x15149434,0x1768E4,92
TABLE,TABLE_ROM=0x8008A8D8,0x22F398
HELPER,HELPER_ROM,HELPER_SIZE=0x1515D4D4,0x18A984,76
BINDINGS={64:[('R_MIPS_26','func_1515D4D4')],160:[('R_MIPS_26','func_1515D4D4')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="void func_1515D4D4(s32, s32, s32, u8);\n"
SELECTED="/* Set the record timer and apply the requested black or white color override. */\nvoid func_150FA468(struct260 *record, s32 eventAddress, u8 command) {\n    if (command == 0x4C) {\n        record->unk11 = -1;\n        func_1515D4D4(0, 0, 0, 255);\n    } else if (command == 0x4D) {\n        record->unk11 = 30;\n    } else if (command == 0x4E) {\n        record->unk11 = -1;\n    } else if (command == 0x4F) {\n        record->unk11 = -1;\n        func_1515D4D4(255, 255, 255, 255);\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record color command body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150FA468() {\n    return 0;\n}'
    if before.count(stub)!=1 or '#include "structs.h"'in before:raise ValueError('Record color command placeholder changed')
    return before.replace('#include <ultra64.h>','#include <ultra64.h>\n#include "structs.h"',1).replace(stub,DECLARATIONS+'\n'+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record color command snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record color command frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record color command predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record color command live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record color command strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record color command original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record color command image differs from the closed body/extent/serialization prediction')
    expected=Counter((n,f[1],184 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record color command named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150FA468.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_126F60.c.o","make-shadow/src/game/generated_126F60.c.o.compact","make-shadow/src/game/generated_126F60.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record color command artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record color command artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record color command raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record color command evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record color command Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Record color command expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_126F60.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record color command Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record color command private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record color command changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record color command protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
