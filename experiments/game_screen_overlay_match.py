"""Screen overlay: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_151ED1E0','generated_215960'
ENTRY,ROM,BODY,SIZE=0x151ED1E0,0x21A690,188,188
SOURCE='conker/src/game/generated_215960.c'
OBJECT='conker/build/src/game/generated_215960.c.o'
ASM='conker/asm/215960.s'
BUILD='conker/build/game-screen-overlay-match'
RAW_SHA="756925b0c28243ecd139ec9a5128afb499ca92c678403f00cd8b5ee20632751c"
SNAPSHOT_SHA="46237908e01fef7b1eb6b34febb9360a0f2184c37b8e0de29da07bef0b771c28"
BEFORE_ELF_SHA="b160a355f28b36f0a7e432e9f44183b400a5f35735adc98de33a65a232fd3ce6"
TRUTH_SHA="eab58a038f764be99c6a4e7dd8a30306f5aa0154304bbb3695f5806c1ff73d85"
AUX_SOURCE='conker/src/game_45B80.c'
AUX_OBJECT='conker/build/src/game_45B80.c.o'
CALLER,HELPER=0x151E84B0,0x1501A6CC
GATE,WIDTH,HEIGHT=0x800E0B96,0x800BE620,0x800BE624
BINDINGS={4:[('R_MIPS_HI16','D_800E0B96')],8:[('R_MIPS_LO16','D_800E0B96')],144:[('R_MIPS_HI16','D_800BE624')],148:[('R_MIPS_LO16','D_800BE624')],152:[('R_MIPS_HI16','D_800BE620')],156:[('R_MIPS_LO16','D_800BE620')],164:[('R_MIPS_26','func_1501A6CC')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern u8 D_800E0B96;\nextern s32 D_800BE620;\nextern s32 D_800BE624;\nGfx *func_1501A6CC(Gfx *, s32, s32, s32, s32);\n\n"
SELECTED="/* Append a black screen overlay using the current fade alpha and screen bounds. */\nGfx *func_151ED1E0(Gfx *commands) {\n    if (D_800E0B96 == 0) {\n        return commands;\n    }\n    gDPPipeSync(commands++);\n    /* Preserve the retail reserved blend-mask bits. */\n    gDPSetOtherMode(commands++, G_CYC_1CYCLE | G_TP_PERSP | G_TF_BILERP |\n        G_TC_FILT | G_CD_MAGICSQ | G_AD_DISABLE | (0xF << G_MDSFT_BLENDMASK),\n        G_AC_NONE | G_ZS_PIXEL | G_RM_CLD_SURF | G_RM_CLD_SURF2);\n    gDPSetCombineLERP(commands++, 0, 0, 0, ENVIRONMENT, 0, 0, 0, ENVIRONMENT,\n        0, 0, 0, ENVIRONMENT, 0, 0, 0, ENVIRONMENT);\n    gDPSetEnvColor(commands++, 0, 0, 0, D_800E0B96);\n    return func_1501A6CC(commands, 0, 0, D_800BE620, D_800BE624);\n}"
OLD_PARENT="s32 func_151E84B0(void) {\n    /* Retain retail's local-slot gap under IDO's debug layout. */\n    s32 stack_pad;\n    s32 result;\n    s32 index = 0;\n    s32 (*callback)(s32);\n\n    D_8003C8E0 = 0x09000001;\n    result = func_151ED1E0();\n    callback = D_8008FFF4[D_800E0B94];\n    if (callback != NULL) {\n        result = callback(result);\n    }\n\n    if (D_80000300 != 0) {\n        if ((D_800BE616 != 0) && (D_8008FD90 >= 2)) {\n            if ((D_800BE740 & 0xF) == 0) {\n                if (D_800E0BD3 == 1) {\n                    index = 0x33;\n                } else if (D_800E0BD3 == 2) {\n                    index = 0x16;\n                }\n            }\n        } else if ((D_800BE740 & 1) == 0) {\n            if (D_800E0BD3 == 1) {\n                index = 0x32;\n            } else if (D_800E0BD3 == 2) {\n                index = 0x15;\n            }\n        }\n    }\n\n    if (index != 0) {\n        func_1504332C(0xFF, 0xFF, 0xFF, 0xFF);\n        func_15042D94(0x94, 0xC8, 0x81, D_800E0BD8[index]);\n    }\n\n    D_8003C8E0 = 0;\n    return result;\n}"
PARENT="Gfx *func_151E84B0(Gfx *commands) {\n    /* Retain retail's local-slot gap under IDO's debug layout. */\n    s32 stack_pad;\n    Gfx *result;\n    s32 index = 0;\n    Gfx *(*callback)(Gfx *);\n\n    D_8003C8E0 = 0x09000001;\n    result = func_151ED1E0(commands);\n    callback = D_8008FFF4[D_800E0B94];\n    if (callback != NULL) {\n        result = callback(result);\n    }\n\n    if (D_80000300 != 0) {\n        if ((D_800BE616 != 0) && (D_8008FD90 >= 2)) {\n            if ((D_800BE740 & 0xF) == 0) {\n                if (D_800E0BD3 == 1) {\n                    index = 0x33;\n                } else if (D_800E0BD3 == 2) {\n                    index = 0x16;\n                }\n            }\n        } else if ((D_800BE740 & 1) == 0) {\n            if (D_800E0BD3 == 1) {\n                index = 0x32;\n            } else if (D_800E0BD3 == 2) {\n                index = 0x15;\n            }\n        }\n    }\n\n    if (index != 0) {\n        func_1504332C(0xFF, 0xFF, 0xFF, 0xFF);\n        func_15042D94(0x94, 0xC8, 0x81, D_800E0BD8[index]);\n    }\n\n    D_8003C8E0 = 0;\n    return result;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Screen overlay body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151ED1E0() {'+chr(10)+'    return 0;'+chr(10)+'}'
    changes=(('s32 func_151ED1E0(void);','Gfx *func_151ED1E0(Gfx *);'),('extern s32 (*D_8008FFF4[])(s32);','extern Gfx *(*D_8008FFF4[])(Gfx *);'),(OLD_PARENT,PARENT),(stub,DECLARATIONS+SELECTED))
    for old,new in changes:
        if before.count(old)!=1:raise ValueError('Screen overlay source shape changed')
        before=before.replace(old,new,1)
    return before

def recovered_aux(before):
    for old,new in(('s32 func_151E84B0(s32);','Gfx *func_151E84B0(Gfx *);'),('(Gfx *)func_151E84B0((s32)D_800BE9D0)','func_151E84B0(D_800BE9D0)')):
        if before.count(old)!=1:raise ValueError('Screen overlay upper caller changed')
        before=before.replace(old,new,1)
    return before

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Screen overlay snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Screen overlay frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Screen overlay predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={AUX_SOURCE:recovered_aux(values[AUX_SOURCE].decode()).encode(),AUX_OBJECT:(output/'aux-after-make/src/game_45B80.c.o').read_bytes(),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Screen overlay live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Screen overlay strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Screen overlay original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Screen overlay image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Screen overlay named ELF definitions changed')

ARTIFACTS=["before-padded.o","qualified-padded.o","proposed-owner.c","proposed-aux.c","selected.o","original-func_151ED1E0.o","first-linked.elf","aux-before-make/src/game_45B80.c.o","aux-after-make/src/game_45B80.c.o"]
EVIDENCE=["before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","before-aux.c","before-aux-processed.c","before-aux.o","before-aux-diagnostics.txt","after-aux.c","after-aux-processed.c","after-aux.o","after-aux-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_215960.c","make-shadow/src/game/generated_215960.c.o","make-shadow/src/game/generated_215960.c.o.compact","make-shadow/src/game/generated_215960.c.o.padded.s","aux-before-make-plan.txt","aux-before-make-commands.json","aux-before-make-diagnostics.txt","aux-before-make/src/game_45B80.c.o","aux-before-make/src/game_45B80.c.o.compact","aux-before-make/src/game_45B80.c.o.padded.s","aux-after-make-plan.txt","aux-after-make-commands.json","aux-after-make-diagnostics.txt","aux-after-make/src/game_45B80.c.o","aux-after-make/src/game_45B80.c.o.compact","aux-after-make/src/game_45B80.c.o.padded.s"]

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Screen overlay artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Screen overlay artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Screen overlay raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Screen overlay evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Screen overlay Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Screen overlay expected empty diagnostics')
    before_aux=(output/'aux-before-make-diagnostics.txt').read_text();after_aux=(output/'aux-after-make-diagnostics.txt').read_text()
    if before_aux.count('Warning 712:')!=3 or before_aux.replace('before-aux.c','proposed-aux.c')!=after_aux:raise ValueError('Existing auxiliary diagnostics changed')
    for name in('aux-before-make/src/game_45B80.c.o','aux-after-make/src/game_45B80.c.o'):
        if(output/name).read_bytes()!=snapshot(output)[AUX_OBJECT]:raise ValueError('Auxiliary padded object changed')
    if(output/'make-shadow/src/game/generated_215960.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Screen overlay Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Screen overlay private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Screen overlay changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Screen overlay protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
