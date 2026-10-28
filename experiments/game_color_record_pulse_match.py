"""Color record pulse: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_151A5070','generated_1D0840'
ENTRY,ROM,BODY,SIZE=0x151A5070,0x1D2520,192,192
SOURCE='conker/src/game/generated_1D0840.c'
OBJECT='conker/build/src/game/generated_1D0840.c.o'
ASM='conker/asm/1D0840.s'
BUILD='conker/build/game-color-record-pulse-match'
RAW_SHA="bbc7cdbe461437db044d53b39f2781d635e535d8220a063166546906476e1ee8"
SNAPSHOT_SHA="faa1fb213aefbb1f45b1d6d34186e20ec0779d83cf0b52f936282d69869a0985"
BEFORE_ELF_SHA="770078348fa22c34f67079f94cf823adb8a7129f6ebc28e5340c0ee01d518d10"
TRUTH_SHA="c901c644a9718edc094481c76cbaff7e8513848183388903f94d9f995a9a0542"
TICKS,REGISTRY,FREE,SCAN,ADAPTER,UNLINK,MODE,MODE_GLOBAL=0x800BE9E4,0x8008B4A8,0x1516972C,0x151696DC,0x15169804,0x15168B10,0x10011FA0,0x80042770
BINDINGS={16:[('R_MIPS_HI16','D_800BE9E4')],28:[('R_MIPS_LO16','D_800BE9E4')],44:[('R_MIPS_26','func_1516972C')],80:[('R_MIPS_26','func_10011FA0')],92:[('R_MIPS_HI16','D_800BE9E4')],96:[('R_MIPS_LO16','D_800BE9E4')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="#include \"structs.h\"\ntypedef struct {\n    u8 header[0x10];\n    u32 value;\n    u8 selector;\n    u8 red;\n    u8 green;\n    u8 blue;\n    u8 state;\n    u8 callback;\n    u8 view;\n    u8 reserved[5];\n} Type5AColorRecord;\nextern s32 D_800BE9E4;\nvoid func_1516972C(struct102 *);\nvoid func_10011FA0(s32 *);\n\n"
SELECTED="/* Update a finite lifetime and pulse the record color between 0x90 and 0xFF. */\nvoid func_151A5070(struct102 *object) {\n    Type5AColorRecord *record = (Type5AColorRecord *)object;\n    s32 remaining = (s32)record->value;\n    s32 step;\n    s32 shade;\n\n    if (remaining != 0) {\n        remaining = (s32)((u32)remaining - (u32)D_800BE9E4);\n        if (remaining <= 0) {\n            func_1516972C((struct102 *)record);\n            return;\n        }\n        record->value = remaining;\n    }\n    if (record->callback == 0) {\n        func_10011FA0((s32 *)2);\n    }\n    step = (s32)((u32)D_800BE9E4 * 2U);\n    shade = record->red;\n    if (record->state == 0) {\n        shade = (s32)((u32)shade - (u32)step);\n        if (shade < 0x90) {\n            shade = 0x90;\n            record->state = 1;\n        }\n    } else {\n        shade = (s32)((u32)shade + (u32)step);\n        if (shade >= 0x100) {\n            shade = 0xFF;\n            record->state = 0;\n        }\n    }\n    record->red = shade;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Color record pulse body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151A5070() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Color record pulse placeholder changed')
    return before.replace(stub,'void func_10011FA0(s32 *);'+chr(10)+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Color record pulse snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Color record pulse frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Color record pulse predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Color record pulse live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Color record pulse strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Color record pulse original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Color record pulse image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Color record pulse named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151A5070.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1D0840.c.o","make-shadow/src/game/generated_1D0840.c.o.compact","make-shadow/src/game/generated_1D0840.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Color record pulse artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Color record pulse artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Color record pulse raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Color record pulse evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Color record pulse Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected color record owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_1D0840.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Color record pulse Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Color record pulse private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Color record pulse changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Color record pulse protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=24,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
