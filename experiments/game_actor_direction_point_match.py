"""Actor direction point: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15107A20','generated_133190'
ENTRY,ROM,BODY,SIZE=0x15107A20,0x134ED0,192,192
SOURCE='conker/src/game/generated_133190.c'
OBJECT='conker/build/src/game/generated_133190.c.o'
ASM='conker/asm/133190.s'
BUILD='conker/build/game-actor-direction-point-match'
RODATA_SYMBOL='D_800A2420'
RAW_SHA="57821ffdd6ebe93f9decc67ea990a48d788c2ffd6b639d2d74174b5f6340b153"
SNAPSHOT_SHA="440e802c3df87c7e0bc1466c1c6157cafb8716ed8f4bcf8807dab38221853c77"
BEFORE_ELF_SHA="4864adb61bffe5db611326f30fbfbeb58ffeb48181776576ee3f430bc86fe712"
TRUTH_SHA="bbdeaae539f0c19dec29ab60e950ddeeb27a81b01a6cd76862504870aa791f2d"
ORIGIN,DIRECTION,TRIG=0x1515C244,0x15143794,0x151423D8
PARENTS=(0x15107700,0x15107924)
BINDINGS={40:[('R_MIPS_26','func_1515C244')],60:[('R_MIPS_26','func_15143794')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="void func_1515C244(struct127 *, struct17 *, f32 *, f32 *);\nvoid func_15143794(s16, s16, f32, vertex *);\n\n"
SELECTED="/* Apply the actor-scaled direction to its queried origin and optionally return that origin. */\nvoid func_15107A20(struct127 *actor, s16 yaw, s16 pitch, vertex *point, struct17 *originOut) {\n    struct17 origin;\n    f32 radius;\n    f32 otherScale;\n\n    func_1515C244(actor, &origin, &radius, &otherScale);\n    func_15143794(yaw, pitch, radius, point);\n    point->y *= actor->unkF0;\n    point->x += origin.unk0;\n    point->y += origin.unk4;\n    point->z += origin.unk8;\n    if (originOut != NULL) {\n        *originOut = origin;\n    }\n}"
EXPECTED_OWNER_DIAGNOSTICS="cfe: Warning 712: <owner>: illegal combination of pointer and integer\n     func_1510761C(arg0);\n ------------------^\ncfe: Warning 712: <owner>: illegal combination of pointer and integer\n     func_1510761C(arg0);\n ------------------^\n"
def check_owner_diagnostics(text):
    normalized=re.sub(r'(?m)^(cfe: Warning \d+: )[^,\n]+, line \d+: ',r'\1<owner>: ',text)
    if normalized!=EXPECTED_OWNER_DIAGNOSTICS:raise ValueError('Actor direction inherited diagnostics changed')
    return 2

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor direction point body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15107A20() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Actor direction point placeholder changed')
    return before.replace('#include <ultra64.h>'+chr(10),'#include <ultra64.h>'+chr(10)+'#include "structs.h"'+chr(10),1).replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor direction point snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor direction point frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor direction point predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor direction point live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor direction point strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor direction point original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor direction point image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor direction point named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15107A20.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_133190.c.o","make-shadow/src/game/generated_133190.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor direction point artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor direction point artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor direction point raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor direction point evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor direction point Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_133190.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor direction point Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor direction point private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor direction point changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor direction point protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=56,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
