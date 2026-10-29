"""Menu scene choice: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151E4314','generated_20AE20'
ENTRY,ROM,BODY,SIZE=0x151E4314,0x2117C4,200,200
SOURCE='conker/src/game/generated_20AE20.c'
OBJECT='conker/build/src/game/generated_20AE20.c.o'
ASM='conker/asm/20AE20.s'
BUILD='conker/build/game-menu-scene-choice-match'
RODATA_SYMBOL=None
RAW_SHA='e1a6d62f8beceec1795871f56d834569adad0f2107e6318198a6ede9fca95d12'
SNAPSHOT_SHA='60e2496925b66ba41b481cf749585e3a4c40a0e0e032d122fd4912ddf2f1ed84'
BEFORE_ELF_SHA='3c483bc65c5f3bc93ff9bc603a3ddd6a51929554313b9be90d999d13599072ae'
TRUTH_SHA='9ea16231d0fc1760a1b23f3581bf94d3f01c439ecb774b9a47032ba7d8868076'
LAUNCH,FALLBACK=0x1501D348,0x151E2834
BINDINGS={8: [('R_MIPS_HI16', 'D_8008FDD4')], 12: [('R_MIPS_LO16', 'D_8008FDD4')], 16: [('R_MIPS_HI16', 'D_800AB692')], 52: [('R_MIPS_LO16', 'D_800AB692')], 20: [('R_MIPS_HI16', 'D_800E0C00')], 64: [('R_MIPS_LO16', 'D_800E0C00')], 84: [('R_MIPS_HI16', 'D_800AB7A4')], 88: [('R_MIPS_LO16', 'D_800AB7A4')], 68: [('R_MIPS_HI16', 'D_800AB7A4')], 72: [('R_MIPS_LO16', 'D_800AB7A4')], 120: [('R_MIPS_26', 'func_1501D348')], 132: [('R_MIPS_HI16', 'D_8008FD80')], 136: [('R_MIPS_LO16', 'D_8008FD80')], 140: [('R_MIPS_HI16', 'D_800E0B94')], 148: [('R_MIPS_LO16', 'D_800E0B94')], 156: [('R_MIPS_HI16', 'D_8008FD8C')], 160: [('R_MIPS_LO16', 'D_8008FD8C')], 164: [('R_MIPS_HI16', 'D_8008FD90')], 172: [('R_MIPS_LO16', 'D_8008FD90')], 176: [('R_MIPS_26', 'func_151E2834')]}
HEADERS='#include <ultra64.h>\nextern s8 *D_8008FDD4;\nextern s8 D_800E0C00[];\nextern u8 D_8008FD80, D_800E0B94;\nextern s8 D_8008FD8C, D_8008FD90;\nvoid func_1501D348(s32, s32, s32, s32, s32);\ns32 func_151E2834(void);\ntypedef struct {\n    s16 scene;\n    s8 sequence;\n    s8 alternateSequence;\n} MenuSceneChoice20AE20;\nextern s8 D_800AB692[];\nextern MenuSceneChoice20AE20 D_800AB7A4[];\n\n'
DECLARATIONS='typedef struct {\n    s16 scene;\n    s8 sequence;\n    s8 alternateSequence;\n} MenuSceneChoice20AE20;\nextern s8 D_800AB692[];\nextern MenuSceneChoice20AE20 D_800AB7A4[];\n\n'
SELECTED='/* Start the selected menu scene, or use the fallback transition. */\nvoid func_151E4314(void) {\n    s32 choiceIndex;\n    s32 sequence;\n    MenuSceneChoice20AE20 *choice;\n\n    choiceIndex = D_800AB692[D_8008FDD4[0x42] * 10];\n    if (choiceIndex >= 0) {\n        if (D_800E0C00[0]) {\n            choice = &D_800AB7A4[choiceIndex];\n            sequence = choice->alternateSequence;\n        } else {\n            choice = &D_800AB7A4[choiceIndex];\n            sequence = choice->sequence;\n        }\n        func_1501D348(choice->scene, sequence, 0, 0, 0);\n        D_8008FD80 = 1;\n        D_800E0B94 = 5;\n        D_8008FD8C = 1;\n        D_8008FD90 = 1;\n    } else {\n        func_151E2834();\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected menu-scene-choice owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Menu scene choice body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151E4314() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Menu scene choice placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip(),1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Menu scene choice snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Menu scene choice frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Menu scene choice predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Menu scene choice live input differs: '+name)
    return values

# GNU ld changes two closed name-order groups after the new undefined uses.
# Preserve every named definition; never exempt entire metadata sections.
METADATA_GROUPS=(
    (0x2BA144,('D_800AB7A4','func_15007360','D_8009DA04'),(1,2,0)),
    (0x2D4E84,('func_151A2A14','D_8009E7D0'),(1,0)),
)

def reorder_metadata(before,result):
    rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
    for first,names,order in METADATA_GROUPS:
        group=[rows[first+16*i]for i in range(len(names))]
        if tuple(n for n,_,_ in group)!=names:raise ValueError('Menu scene choice metadata group changed')
        strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
        if before[start:start+len(strings)]!=strings:raise ValueError('Menu scene choice name block changed')
        offset=0;name_offset=group[0][1][0]
        for slot,index in enumerate(order):
            name,fields,_=group[index];encoded=name.encode()+b'\0'
            struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:])
            result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
        if offset!=len(strings):raise ValueError('Menu scene choice metadata length changed')

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Menu scene choice strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Menu scene choice original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Menu scene choice image differs from body, extent and closed metadata prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Menu scene choice named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='efd6bd3f1e7efba51b4b566abfd447477133a8a52daa3804bc7550b32d273293':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151E4314.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_20AE20.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_20AE20.c.o","make-shadow/src/game/generated_20AE20.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Menu scene choice artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Menu scene choice artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Menu scene choice raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Menu scene choice evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Menu scene choice Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_20AE20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Menu scene choice Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Menu scene choice private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Menu scene choice changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Menu scene choice protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=32,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
