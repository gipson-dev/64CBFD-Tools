"""Record phase/lifetime: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15169988','generated_196DB0'
ENTRY,ROM,BODY,SIZE=0x15169988,0x196E38,192,192
SOURCE='conker/src/game/generated_196DB0.c'
OBJECT='conker/build/src/game/generated_196DB0.c.o'
ASM='conker/asm/196DB0.s'
BUILD='conker/build/game-record-phase-lifetime-match'
RAW_SHA="0485506ae976faa1630ca8eb6e7aeaaa657f25a8b405ab88a291f838621f6436"
SNAPSHOT_SHA="2331adf15937c54b0923c3b0a531017d94568c2140b51ac2a1e36b17d0d8a299"
BEFORE_ELF_SHA="6fc32a5f2c15d1e97cc5e7c963f7ff07c47d0c8da90b7dbc93319cba25368f1b"
TRUTH_SHA="33cf84f1acc58d8a81d0dfa068d4cd336a9c586d743c4277b2344a2c41b60599"
TICKS,TABLE,REGISTRY,FREE,SCAN,ADAPTER,UNLINK=0x800BE9E4,0x8008CA20,0x8008B4A8,0x1516972C,0x151696DC,0x15169804,0x15168B10
BINDINGS={12:[('R_MIPS_HI16','D_8008CA20')],28:[('R_MIPS_LO16','D_8008CA20')],48:[('R_MIPS_HI16','D_800BE9E4')],52:[('R_MIPS_LO16','D_800BE9E4')],156:[('R_MIPS_26','func_1516972C')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="#include \"structs.h\"\ntypedef void (*RecordPhaseCallback)(void *);\nextern RecordPhaseCallback D_8008CA20[];\nextern s32 D_800BE9E4;\nvoid func_1516972C(struct102 *);\n\n"
SELECTED="/* Run the optional record callback, advance its phase once, and expire its lifetime. */\nvoid func_15169988(u8 *record) {\n    s32 selector = *(s8 *)(record + 0x40);\n    u32 value;\n    s32 period;\n    s32 lifetime;\n\n    if (selector != 0) {\n        D_8008CA20[selector](record);\n    }\n    value = *(s16 *)(record + 0x26);\n    value += (u32)*(s16 *)(record + 0x28) * (u32)D_800BE9E4;\n    period = record[0x41] << 8;\n    if ((s32)value >= period) {\n        value = (s32)((u32)value - (u32)period);\n    } else if ((s32)value < 0) {\n        value = (s32)((u32)value + (u32)period);\n    }\n    lifetime = *(s16 *)(record + 0x24);\n    *(s16 *)(record + 0x26) = value;\n    if (lifetime != 0) {\n        lifetime = (s32)((u32)lifetime - (u32)D_800BE9E4);\n        if (lifetime <= 0) {\n            func_1516972C((struct102 *)record);\n        } else {\n            *(s16 *)(record + 0x24) = lifetime;\n        }\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record phase/lifetime body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15169988() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record phase/lifetime placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record phase/lifetime snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record phase/lifetime frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record phase/lifetime predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record phase/lifetime live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record phase/lifetime strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record phase/lifetime original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record phase/lifetime image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record phase/lifetime named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15169988.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_196DB0.c.o","make-shadow/src/game/generated_196DB0.c.o.compact","make-shadow/src/game/generated_196DB0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record phase/lifetime artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record phase/lifetime artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record phase/lifetime raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record phase/lifetime evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record phase/lifetime Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected EEPROM owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_196DB0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record phase/lifetime Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record phase/lifetime private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record phase/lifetime changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record phase/lifetime protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=24,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
