"""Actor action dispatch: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150979CC','generated_C4DC0'
ENTRY,ROM,BODY,SIZE=0x150979CC,0xC4E7C,192,192
SOURCE='conker/src/game/generated_C4DC0.c'
OBJECT='conker/build/src/game/generated_C4DC0.c.o'
ASM='conker/asm/C4DC0.s'
BUILD='conker/build/game-actor-action-dispatch-match'
RAW_SHA="d59793c9530abb3fe2575634521231b372007ae183ec461e791387ea50119f3a"
SNAPSHOT_SHA="af092558934cef4c29b4906b11d7bffad4b2e0baef142fd9860c5b5d7a100867"
BEFORE_ELF_SHA="5ccc025d4407926820062c60ccf343e007f84751e22fddfe7a1d2088afdc52e9"
TRUTH_SHA="13395829b02e7ad9b12775c632260155e2d700a14aabcead3fdf1885c617e949"
RECORDS,COUNT,MODE,LOOKUP,ACTION,ALTERNATE,TABLE=0x800D20FC,0x800D2100,0x800D3840,0x1505EEF4,0x15060F28,0x15053430,0x8008845C
BINDINGS={12:[('R_MIPS_26','func_1505EEF4')],40:[('R_MIPS_HI16','D_800D2100')],44:[('R_MIPS_LO16','D_800D2100')],52:[('R_MIPS_HI16','D_800D20FC')],68:[('R_MIPS_LO16','D_800D20FC')],64:[('R_MIPS_HI16','D_800D3840')],92:[('R_MIPS_LO16','D_800D3840')],128:[('R_MIPS_26','func_15060F28')],144:[('R_MIPS_26','func_15053430')],160:[('R_MIPS_26','func_15060F28')]}
HEADERS="#include <ultra64.h>\n\n/* Non-matching placeholders for the text-only asm slice asm/C4DC0.s. */\n\ntypedef struct {\n    u8 reserved0[2];\n    u8 state;\n    u8 reserved3[0x2D];\n} SpawnLookupRecord;\nextern SpawnLookupRecord *D_800D20FC;\ns32 func_15083E0C(u8);\nu8 *func_15083E90(u8);\ns32 func_15082A44(SpawnLookupRecord *, s32, s32, s32, s32);\n\n"
DECLARATIONS="#include \"structs.h\"\nextern u8 D_800D2100;\nextern s32 D_800D3840;\nstruct127 *func_1505EEF4(s32);\nvoid func_15060F28(struct127 *, s32);\ns32 func_15053430(struct127 *);\n\n"
SELECTED="/* Activate a resolved actor record and dispatch its mode-dependent action. */\ns32 func_150979CC(s32 index, s32 *context) {\n    struct127 *actor = func_1505EEF4(index);\n\n    if (actor == NULL) {\n        return 0;\n    }\n    if (index < D_800D2100) {\n        D_800D20FC[index].state = 1;\n    }\n    if (D_800D3840 == 2) {\n        if (context[1] == 0) {\n            func_15060F28(actor, 0);\n        } else {\n            func_15053430(actor);\n        }\n    } else {\n        func_15060F28(actor, 0);\n    }\n    return 999999;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor action dispatch body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150979CC() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Actor action dispatch placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor action dispatch snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor action dispatch frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor action dispatch predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor action dispatch live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor action dispatch strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor action dispatch original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor action dispatch image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor action dispatch named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150979CC.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_C4DC0.c.o","make-shadow/src/game/generated_C4DC0.c.o.compact","make-shadow/src/game/generated_C4DC0.c.o.padded.s","preparation.json",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor action dispatch artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor action dispatch artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor action dispatch raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor action dispatch evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor action dispatch Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected actor action owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_C4DC0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor action dispatch Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor action dispatch private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor action dispatch changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor action dispatch protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=24,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
