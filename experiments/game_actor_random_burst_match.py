"""Actor random burst: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15147040','generated_173D40'
ENTRY,ROM,BODY,SIZE=0x15147040,0x1744F0,188,188
SOURCE='conker/src/game/generated_173D40.c'
OBJECT='conker/build/src/game/generated_173D40.c.o'
ASM='conker/asm/173D40.s'
BUILD='conker/build/game-actor-random-burst-match'
RAW_SHA='187ac8d12a3811348c332d914b730e53696befc1b8836bea0cc165f0a5383ccd'
SNAPSHOT_SHA='2a4872ad1246c93ca9f93d1b109960d769a0abae23212208d074c863ce20fdb6'
BEFORE_ELF_SHA='a9cb525e36f47e0e5cccd406f0082c1cefba460988ecc97cebac39d2ba776f8c'
TRUTH_SHA='dd74c20ebbaf52afc8456bcb0fb9bda6c871b37d6075fd72b6a02b3421015264'
POINT,INTEGER_RNG,FLOAT_RNG,SUBMIT=0x15146890,0x150ADA20,0x150ADA68,0x1514C678
BINDINGS={48:[('R_MIPS_26','func_15146890')],56:[('R_MIPS_26','func_150ADA20')],80:[('R_MIPS_26','func_150ADA68')],164:[('R_MIPS_26','func_1514C678')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="s32 func_15146890();\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_1514C678(f32, f32, f32, f32, s16, s16, s16, u8, s32, f32, void *, u8);\n"
SELECTED="/* Submit a randomized type-22 burst at the attached object's selected point. */\nvoid func_15147040(u8 *actor, u8 context, s32 unused) {\n    f32 position[3];\n    s16 count;\n\n    if (*(void **)(actor + 0x1D4) == NULL) {\n        return;\n    }\n    func_15146890(position, actor, 0, context);\n    count = (u32)func_150ADA20() % 11U + 5;\n    func_1514C678(position[0], position[1], position[2], func_150ADA68() * 11.0f,\n        0, 255, count, 0x16, 0, 0.0f, NULL, 255);\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor random burst body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15147040() {\n    return 0;\n}'
    if before.count(stub)!=1 or 's32 func_15146890();'in before:raise ValueError('Actor random burst placeholder changed')
    return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1).replace('/* Non-matching placeholders for the text-only asm slice asm/173D40.s. */','/* Partially recovered text-only slice asm/173D40.s. */')

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor random burst snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor random burst frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor random burst predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor random burst live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor random burst strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor random burst original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor random burst image differs from the body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor random burst named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15147040.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_173D40.c.o","make-shadow/src/game/generated_173D40.c.o.compact","make-shadow/src/game/generated_173D40.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor random burst artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor random burst artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor random burst raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor random burst evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor random burst Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Actor random burst expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_173D40.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor random burst Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor random burst private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor random burst changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor random burst protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
