"""Type07 parameter record: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_151B9BF0','generated_1E6B40'
ENTRY,ROM,BODY,SIZE=0x151B9BF0,0x1E70A0,192,192
SOURCE='conker/src/game/generated_1E6B40.c'
OBJECT='conker/build/src/game/generated_1E6B40.c.o'
ASM='conker/asm/1E6B40.s'
BUILD='conker/build/game-type07-parameter-record-match'
RAW_SHA="3d489eca752b1e2bd49bfbbe31f19288ca0bb98fbd1f55f696cd76f5cd60ed21"
SNAPSHOT_SHA="04a04f459750ab0a9f0ee1e6f93c4db0eb9112e2979e3f9f12221ad804192276"
BEFORE_ELF_SHA="3987efc711a7e2d30ee9b4dbabb901846750386b38f384bb6ffdc2fbe31750c9"
TRUTH_SHA="c08a81cc88b1e35e9477230732855646f5c54c3337c73bde481c59101bdca084"
FACTORY,HEAP,INITIALIZER,LIST=0x15167A68,0x10003C6C,0x15168A4C,0x800DCE50
BINDINGS={52:[('R_MIPS_26','func_15167A68')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct {\n    u8 header[0x10];\n    u32 value;\n    u8 first;\n    u8 second;\n    s16 parameters[11];\n} Type07ParameterRecord;\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\n\n"
SELECTED="/* Create a type-7 record with two byte fields and eleven signed parameters. */\nvoid func_151B9BF0(s32 first, s32 second, s16 p0, s16 p1,\n    s16 p2, s16 p3, s16 p4, s16 p5, s16 p6, s16 p7, s16 p8, s16 p9,\n    s16 p10, u32 value, u8 view, s32 context) {\n    Type07ParameterRecord *record = func_15167A68(7, context, 0x2C, 0, view, 1);\n\n    if (record != NULL) {\n        record->first = first;\n        record->second = second;\n        record->parameters[0] = p0;\n        record->parameters[1] = p1;\n        record->parameters[2] = p2;\n        record->parameters[3] = p3;\n        record->parameters[4] = p4;\n        record->parameters[5] = p5;\n        record->parameters[6] = p6;\n        record->parameters[7] = p7;\n        record->parameters[8] = p8;\n        record->parameters[9] = p9;\n        record->parameters[10] = p10;\n        record->value = value;\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Type07 parameter record body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151B9BF0() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Type07 parameter record placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Type07 parameter record snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Type07 parameter record frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Type07 parameter record predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Type07 parameter record live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Type07 parameter record strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Type07 parameter record original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Type07 parameter record image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Type07 parameter record named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151B9BF0.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1E6B40.c.o","make-shadow/src/game/generated_1E6B40.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Type07 parameter record artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type07 parameter record artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type07 parameter record raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Type07 parameter record evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type07 parameter record Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected type-7 record owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_1E6B40.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Type07 parameter record Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Type07 parameter record private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Type07 parameter record changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Type07 parameter record protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=32,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
