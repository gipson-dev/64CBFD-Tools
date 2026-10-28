"""Type91 point effect: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_151DC8BC','generated_209B50'
ENTRY,ROM,BODY,SIZE=0x151DC8BC,0x209D6C,192,192
SOURCE='conker/src/game/generated_209B50.c'
OBJECT='conker/build/src/game/generated_209B50.c.o'
ASM='conker/asm/209B50.s'
BUILD='conker/build/game-type91-point-effect-match'
RODATA_SYMBOL=None
RAW_SHA="948b4f456f7fca0195f7cbdfd6488af64b4e9be2e1fb7d2b336e01f22a4065f0"
SNAPSHOT_SHA="dfd1edd4970278d92072190b6526dc8b16dcdbebee6af4808323c3d33c8f4d66"
BEFORE_ELF_SHA="a0fc94c6245861327c84b0ed12cdf8f4a7b1fad91a25045a838620ccf8a68ac5"
TRUTH_SHA="b0f1ceaec39534ef1d70ea396c281ac714f09f9d644507ef933325961688f339"
COMPANION,FACTORY,COPY=0x151DC6A0,0x15149130,0x10022EC0
PARENT,PARSER,ALLOCATOR,HEAP,INITIALIZER,BZERO=0x150265CC,0x15023BB0,0x15167A68,0x10003C6C,0x15168A4C,0x100226F0
BINDINGS={44:[('R_MIPS_26','func_151DC6A0')],148:[('R_MIPS_26','func_15149130')],168:[('R_MIPS_26','memcpy')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n#include <string.h>\n\n"
DECLARATIONS="typedef struct {\n    vertex position;\n    f32 accumulator;\n    u8 flag;\n    u8 reserved[3];\n} Type91PointPayload;\n\ns32 func_151DC6A0();\nvoid *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\n\n"
SELECTED="/* Optionally run companion effects, then attach the point and flag to a type-0x5B effect. */\nvoid func_151DC8BC(vertex *position, s16 lifetime, u8 companions, u8 flag, u8 group, s32 context) {\n    Type91PointPayload payload;\n    u8 *effect;\n\n    if (companions) {\n        func_151DC6A0(position, group, context);\n    }\n    payload.position = *position;\n    payload.accumulator = 0.0f;\n    payload.flag = flag;\n    effect = func_15149130(lifetime, -1, 0x5B, -1, 1, 0, sizeof(payload), group, context);\n    if (effect != NULL) {\n        memcpy(effect + 0x28, &payload, sizeof(payload));\n    }\n}"
def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected type91 point effect diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Type91 point effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151DC8BC() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Type91 point effect placeholder changed')
    return before.replace('#include <ultra64.h>'+chr(10),'#include <ultra64.h>'+chr(10)+'#include "structs.h"'+chr(10)+'#include <string.h>'+chr(10),1).replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Type91 point effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Type91 point effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Type91 point effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Type91 point effect live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Type91 point effect strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Type91 point effect original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Type91 point effect image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Type91 point effect named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151DC8BC.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_209B50.c.o","make-shadow/src/game/generated_209B50.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Type91 point effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type91 point effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type91 point effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Type91 point effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type91 point effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_209B50.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Type91 point effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Type91 point effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Type91 point effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Type91 point effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=72,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
