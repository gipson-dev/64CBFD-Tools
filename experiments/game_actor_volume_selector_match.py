"""Actor volume selector: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150A2EE4','generated_CDE80'
ENTRY,ROM,BODY,SIZE=0x150A2EE4,0xD0394,192,192
SOURCE='conker/src/game/generated_CDE80.c'
OBJECT='conker/build/src/game/generated_CDE80.c.o'
ASM='conker/asm/CDE80.s'
BUILD='conker/build/game-actor-volume-selector-match'
RAW_SHA="3102da592480e9abbe81c272c08d148adea860fca7f985c4d5d1b163938d7754"
SNAPSHOT_SHA="72aa8c9ed43f6793543fe7c30f6b831b4e8a269db87c8aaa4fd56259f3ac2523"
BEFORE_ELF_SHA="7c7cfc7130d6a79f63f19d33843690a535dad6ff33628d1005516ff881a247e0"
TRUTH_SHA="8f5f5daa3897b38b76186df1307e83feb7c33849f1c27ad7465d57562f17c1af"
HELPER,COUNT,TABLE,ACTORS=0x150A2E4C,0x800D3094,0x800D3098,0x800CC2D0
BINDINGS={12:[("R_MIPS_HI16","D_800D3094")],16:[("R_MIPS_LO16","D_800D3094")],36:[("R_MIPS_HI16","D_800D3098")],56:[("R_MIPS_LO16","D_800D3098")],104:[("R_MIPS_HI16","D_800CC2D0")],108:[("R_MIPS_LO16","D_800CC2D0")],160:[("R_MIPS_26","func_150A2E4C")]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="typedef struct {\n    s16 origin0;\n    s16 origin1;\n    s16 origin2;\n    u8 pad6[0xF];\n    u8 flags;\n    u8 pad16;\n    u8 field17;\n    s32 field18;\n    s32 field1C;\n    s32 field20;\n    f32 coefficient0;\n    f32 scale;\n    f32 coefficient1;\n    f32 coefficient2;\n} GeneratedCDE80Record;\n\nextern GeneratedCDE80Record *D_800D3098;\nextern s32 D_800D3094;\ns32 func_150A2E4C(GeneratedCDE80Record *, f32, f32, f32);\nextern struct127 D_800CC2D0[26];\n\n"
OWNER_DECLARATIONS="extern struct127 D_800CC2D0[26];\n\n"
SELECTED="/* Test a masked volume selector against the selected actor position. */\ns32 func_150A2EE4(s32 actorIndex, s32 selector) {\n    selector &= 0xFFF;\n    if ((u32)D_800D3094 < (u32)selector) {\n        return 1;\n    }\n    if ((D_800D3098[selector].flags & 3) == 3) {\n        return func_150A2E4C(&D_800D3098[selector], D_800CC2D0[actorIndex].x_position,\n                            D_800CC2D0[actorIndex].y_position, D_800CC2D0[actorIndex].z_position);\n    }\n    return 0;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor volume selector body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150A2EE4() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Actor volume selector placeholder changed')
    return before.replace(stub,OWNER_DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor volume selector snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor volume selector frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor volume selector predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor volume selector live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor volume selector strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor volume selector original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor volume selector image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor volume selector named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150A2EE4.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_CDE80.c.o","make-shadow/src/game/generated_CDE80.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor volume selector artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor volume selector artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor volume selector raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor volume selector evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor volume selector Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected actor volume owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_CDE80.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor volume selector Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor volume selector private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor volume selector changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor volume selector protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=24,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
