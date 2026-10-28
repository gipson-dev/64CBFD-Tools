"""Type46 distance record: guarded C private proposal, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150C5370','generated_F2820'
ENTRY,ROM,BODY,SIZE=0x150C5370,0xF2820,188,192
SOURCE='conker/src/game/generated_F2820.c'
OBJECT='conker/build/src/game/generated_F2820.c.o'
ASM='conker/asm/F2820.s'
BUILD='conker/build/game-type46-distance-record-match'
RAW_SHA="b8563717a8415ce49f3da1b428262c960ba486965bba16c1d0643d79bfec6f0b"
SNAPSHOT_SHA="22b640ec7cbe446405a20e3a66046cb0a8951cd03dbce55283e4d12877ce4e8e"
BEFORE_ELF_SHA="e8697a890df7767b6735d4ceca7a9260b650ad275c1db9361c2f1f2073465f3e"
TRUTH_SHA="21997deab3c52015d274c17374428641b94d4d866b248e7e6fec914a3d596f6c"
FACTORY,COPY,LENGTH,HEAP,INITIALIZER,PARENT,FINAL=0x15167A68,0x10022EC0,0x15143E64,0x10003C6C,0x15168A4C,0x1514D564,0x1514EC1C
CALLER_SOURCE='conker/src/game/generated_179F30.c'
CALLER_OBJECT='conker/build/src/game/generated_179F30.c.o'
BINDINGS={48:[('R_MIPS_26','func_15167A68')],84:[('R_MIPS_26','memcpy')],144:[('R_MIPS_26','func_15143E64')]}
NORMALIZED_BINDINGS=dict(BINDINGS)
HEADERS="#include <ultra64.h>\n#include <string.h>\n"
DECLARATIONS="typedef struct {\n    f32 first[3];\n    f32 second[3];\n    u8 attributes[12];\n} Type46DistancePayload;\n\ntypedef struct {\n    u8 header[0x10];\n    s32 active;\n    s32 state;\n    Type46DistancePayload payload;\n    u8 pad3C[0x84];\n    f32 distance;\n    u32 tail;\n} Type46DistanceRecord;\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\nf32 func_15143E64(f32 *);\n\n"
SELECTED="/* Create a type-0x46 record and cache the distance between its first two points. */\nType46DistanceRecord *func_150C5370(const Type46DistancePayload *payload, u32 extraBytes) {\n    Type46DistanceRecord *record;\n    f32 delta[3];\n\n    record = func_15167A68(0x46, 0, (s32)(extraBytes + 0xC8u), 1, 0xFF, 1);\n    if (record == NULL) {\n        return NULL;\n    }\n    memcpy(&record->payload, payload, 0x24);\n    delta[0] = record->payload.first[0] - record->payload.second[0];\n    delta[1] = record->payload.first[1] - record->payload.second[1];\n    delta[2] = record->payload.first[2] - record->payload.second[2];\n    record->distance = func_15143E64(delta);\n    record->active = 1;\n    record->state = 0;\n    return record;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Type46 distance record body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150C5370() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Type46 distance record placeholder changed')
    return before.replace('#include <ultra64.h>'+chr(10),'#include <ultra64.h>'+chr(10)+'#include <string.h>'+chr(10),1).replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Type46 distance record snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Type46 distance record frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Type46 distance record predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Type46 distance record live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Type46 distance record strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Type46 distance record original extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Type46 distance record image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Type46 distance record named ELF definitions changed')

def derive_guards():
    """Move two independent loads, rename the saved result and restore its return move."""
    expected={64:0x1000001A,96:0x27A40020,100:0xC4640018,104:0xC4660024,152:0x8FA2002C,160:0xE44000C0,164:0xAC580010,168:0xAC400014}
    result={64:expected[64]+1,96:expected[100],100:expected[104],104:expected[96]}
    for at in(152,160,164,168):
        shift=16 if at==152 else 21
        assert(expected[at]>>shift)&31==2
        result[at]=(expected[at]&~(31<<shift))|(3<<shift)
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,expected='0x%08X'%expected[at],replacement='0x%08X'%result[at],expected_relocations='-',replacement_relocations='-',note='Normalize type46 distance record independent schedule and saved result register',insert_after='0x00601025'if at==168 else'',insert_after_relocations='-'if at==168 else'',omit='false')for at in sorted(expected)]

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='20131e428c071ea6d2cbee21968f122274bc71fb167a2a356b3033ff5582f8b9':raise ValueError('Type46 inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Type46 guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=struct.unpack('>47I',raw);rows={int(r['offset'],0):r for r in NEW_GUARDS};out=[];out_bindings={}
    for i,word in enumerate(words):
        at=i*4;rs=bindings.get(at,[]);row=rows.get(at)
        if row:
            if word!=int(row['expected'],0)or rs:raise ValueError('Type46 expected word/binding changed')
            word=int(row['replacement'],0)
        if rs:out_bindings[len(out)*4]=list(rs)
        out.append(word)
        if row and row['insert_after']:out.append(int(row['insert_after'],0))
    result=struct.pack('>48I',*out)
    if len(rows)!=8 or sha(result)!='a29e54256512b8e35e0cc03c4ba8522098e08c667abf3b5ab5377eeb213a4210'or out_bindings!=NORMALIZED_BINDINGS:raise ValueError('Type46 normalized body/bindings changed')
    return result,out_bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150C5370.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_F2820.c.o","make-shadow/src/game/generated_F2820.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Type46 distance record artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type46 distance record artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type46 distance record raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Type46 distance record evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type46 distance record Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected type46 distance owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_F2820.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Type46 distance record Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=8 or q['exclusions']!=0:raise ValueError('Type46 distance record private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Type46 distance record changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Type46 distance record protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=48,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=8,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
