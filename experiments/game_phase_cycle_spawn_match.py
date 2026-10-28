"""Phase cycle spawn: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150D2110','generated_FF5C0'
ENTRY,ROM,BODY,SIZE=0x150D2110,0xFF5C0,188,188
SOURCE='conker/src/game/generated_FF5C0.c'
OBJECT='conker/build/src/game/generated_FF5C0.c.o'
ASM='conker/asm/FF5C0.s'
BUILD='conker/build/game-phase-cycle-spawn-match'
RAW_SHA="209cd58271212f6448ca3b6bd02fdb4053fa6fbc81ad362e48d903d7747c9c05"
SNAPSHOT_SHA="9c096af163dd80c59631d7bd50751ac2431e8f4eb295ad9a67b0a188fae7569d"
BEFORE_ELF_SHA="ef65f9bccc08a981415cbf87a4f744c610fcb56e29622863df3d3044bb5aeef4"
TRUTH_SHA="f4e2c1b5f402ac2992d354e5f8f50b6518cd687c3f52c81d3f8c60e1d9b5b25e"
COUNTER,SPAWN,COPY=0x800D9900,0x15149130,0x10022EC0
ALLOC,ZERO=0x15167A68,0x100226F0
BINDINGS={12:[("R_MIPS_HI16","D_800D9900")],24:[("R_MIPS_LO16","D_800D9900")],144:[("R_MIPS_26","func_15149130")],164:[("R_MIPS_26","memcpy")]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="typedef struct {\n    u8 active;\n    u8 pad1[3];\n    f32 phase;\n    f32 threshold;\n    f32 inactiveDuration;\n    f32 period;\n    u8 activeColor;\n    u8 inactiveColor;\n} PhaseCycle;\n\nextern u8 D_800D9900;\n\nstruct260 *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n"
SELECTED="/* Spawn a phase cycle and copy its state, retaining the packet's original padding bytes. */\nvoid func_150D2110(s16 lifetime, f32 activeDuration, f32 inactiveDuration,\n                   u8 activeColor, u8 inactiveColor, u8 priority, s32 owner) {\n    PhaseCycle cycle;\n    struct260 *effect;\n\n    D_800D9900++;\n    cycle.threshold = activeDuration;\n    cycle.inactiveDuration = inactiveDuration;\n    cycle.period = activeDuration + inactiveDuration;\n    cycle.active = 0;\n    cycle.phase = 0.0f;\n    cycle.activeColor = activeColor;\n    cycle.inactiveColor = inactiveColor;\n    effect = func_15149130(lifetime, -1, 0x2F, 2, 1, 0x26, sizeof(PhaseCycle), priority, owner);\n    if (effect != NULL) {\n        memcpy((u8 *)effect + 0x28, &cycle, sizeof(PhaseCycle));\n    }\n}"
OLD_TYPE="/* The callback receives the common actor header followed by this local state. */\ntypedef struct {\n    u8 active;\n    u8 pad1[3];\n    f32 phase;\n    f32 threshold;\n    f32 unused;\n    f32 period;\n} PhaseCycle;\n\n"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Phase cycle spawn body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150D2110() {\n    return 0;\n}'
    if before.count(stub)!=1 or before.count(OLD_TYPE)!=1:raise ValueError('Phase cycle placeholder/type changed')
    return before.replace(OLD_TYPE,'').replace(stub,DECLARATIONS+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Phase cycle spawn snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Phase cycle spawn frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Phase cycle spawn predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Phase cycle spawn live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Phase cycle spawn strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Phase cycle spawn original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Phase cycle spawn image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Phase cycle spawn named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150D2110.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_FF5C0.c.o","make-shadow/src/game/generated_FF5C0.c.o.compact","make-shadow/src/game/generated_FF5C0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Phase cycle spawn artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Phase cycle spawn artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Phase cycle spawn raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Phase cycle spawn evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Phase cycle spawn Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Phase cycle spawn expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_FF5C0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Phase cycle spawn Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Phase cycle spawn private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Phase cycle spawn changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Phase cycle spawn protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
