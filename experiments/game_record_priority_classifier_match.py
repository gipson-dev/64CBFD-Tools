"""Record priority classifier: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15159370','generated_185560'
ENTRY,ROM,BODY,SIZE=0x15159370,0x186820,188,188
SOURCE='conker/src/game/generated_185560.c'
OBJECT='conker/build/src/game/generated_185560.c.o'
ASM='conker/asm/185560.s'
BUILD='conker/build/game-record-priority-classifier-match'
RAW_SHA="b4177b2aad01f337f075498a905a4d4550a1cd025caa385dca76118faae1783b"
SNAPSHOT_SHA="2dff0d58e8645cc462b1208285ed2aa4b84e1286065ee6c89aed474a4fa9e393"
BEFORE_ELF_SHA="d5fed435898d94afaa98740783d38a4c2bc04c93612e540cd2d9712488dada7a"
TRUTH_SHA="f0c7c7f1e5b75206cea64aface0f75316da10f2c61fcb5fda9f0313a649d99ca"
GATE=0x800BE616
ALLOC,FREE,PARENT=0x15167A68,0x1516979C,0x15158BD0
BINDINGS={0:[("R_MIPS_HI16","D_800BE616")],4:[("R_MIPS_LO16","D_800BE616")]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern u8 D_800BE616;\n\n"
SELECTED="/* Apply each classification rule in order; later matching rules replace the output byte. */\ns32 func_15159370(u8 *record, u8 *classification) {\n    s32 matched = 0;\n\n    if (D_800BE616 != 0) {\n        *classification = 0;\n        matched = 1;\n    }\n    if (record[0x3B] == 1) {\n        *classification = 0;\n        matched = 1;\n    }\n    if ((record[5] == 5) || (record[5] == 2)) {\n        *classification = 1;\n        matched = 1;\n    }\n    switch (record[4]) {\n        case 8:\n            *classification = 2;\n            matched = 1;\n            break;\n        case 10:\n            *classification = 3;\n            matched = 1;\n            break;\n        case 0x29:\n        case 0x2A:\n            *classification = 4;\n            matched = 1;\n            break;\n    }\n    return matched;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record priority classifier body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15159370() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Record classifier placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record priority classifier snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record priority classifier frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record priority classifier predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record priority classifier live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record priority classifier strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record priority classifier original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record priority classifier image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record priority classifier named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15159370.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_185560.c","make-shadow/src/game/generated_185560.c.o","make-shadow/src/game/generated_185560.c.o.compact","make-shadow/src/game/generated_185560.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record priority classifier artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record priority classifier artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record priority classifier raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record priority classifier evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record priority classifier Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Record priority classifier expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_185560.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record priority classifier Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record priority classifier private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record priority classifier changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record priority classifier protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
