"""Actor descriptor effect: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150F9950','generated_124920'
ENTRY,ROM,BODY,SIZE=0x150F9950,0x126E00,196,208
SOURCE='conker/src/game/generated_124920.c'
OBJECT='conker/build/src/game/generated_124920.c.o'
ASM='conker/asm/124920.s'
BUILD='conker/build/game-actor-descriptor-effect-match'
WRAPPER_SOURCE='conker/src/game/generated_12C1E0.c'
WRAPPER_OBJECT='conker/build/src/game/generated_12C1E0.c.o'
WRAPPER_SELECTED='u8 *func_150FF288(u8 *actor) {\n    return (u8 *)func_1503195C(actor, 0x82, 0);\n}'

def recovered_wrapper(before):
    old='void func_150FF288(s32 arg0) {\n    func_1503195C(arg0, 0x82, 0);\n}'
    if before.count(old)!=1 or before.count('s32 func_1503195C();')!=1:raise ValueError('Lookup wrapper baseline changed')
    return before.replace('s32 func_1503195C();','s32 func_1503195C(u8 *, s32, u32);',1).replace(old,WRAPPER_SELECTED,1)

RODATA_SYMBOL=None
LOOKUP,GEOMETRY,PRIMARY,SECONDARY,FINAL=0x150FF288,0x150FF6E0,0x151D3F14,0x151D4408,0x150FF474
RAW_SHA='97eb6f07e8b519e75e7894ce18d325914508f6e39add09cfe7dfa58752da7521'
SNAPSHOT_SHA='b4625d46244a7c07c640447bc31f29e3d937d2ec41bcf2f991f8cd43add35428'
BEFORE_ELF_SHA='b7034c6528bf4fedc75fb8c77d66a040e98a9e7a85297e6bfd4718ce7ddb347b'
TRUTH_SHA='b25128e9fe8e4f4752ecb81ecb27b89cf664302f9047172fc4c68266631cef3d'
BINDINGS={20: [('R_MIPS_26', 'func_150FF288')], 68: [('R_MIPS_26', 'func_150FF6E0')], 88: [('R_MIPS_26', 'func_151D3F14')], 152: [('R_MIPS_26', 'func_151D4408')], 172: [('R_MIPS_26', 'func_150FF474')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='u8 *func_150FF288(u8 *);\ns32 func_150FF6E0(struct17 *, struct17 *, struct17 *, struct17 *, struct17 *, u8 *, u8 *);\nvoid func_151D3F14(struct17 *, u8, s32);\nvoid func_151D4408(struct17 *, struct17 *, void *, u8 *, f32, u8, s32);\nvoid func_150FF474(struct17 *, struct17 *, u8, s32);\n'
SELECTED="/* Recover descriptor geometry and submit the actor's paired effects. */\nvoid func_150F9950(u8 *actor, u8 selector, s32 parameter) {\n    struct17 points[6];\n    struct17 origin;\n    struct17 direction;\n    struct17 velocity;\n    struct17 other;\n    u8 *descriptor;\n\n    descriptor = func_150FF288(actor);\n    if (descriptor != 0) {\n        if (func_150FF6E0(points, &origin, &direction, &velocity, &other, actor, descriptor)) {\n            func_151D3F14(&origin, selector, parameter);\n            func_151D4408(&direction, &velocity,\n                *(u8 **)(actor + 0x1D4) + descriptor[2] * 64,\n                actor, 1.0f, selector, parameter);\n            func_150FF474(&origin, points, selector, parameter);\n        }\n    }\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected actor descriptor effect owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor descriptor effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150F9950() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Actor descriptor effect placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor descriptor effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor descriptor effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor descriptor effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),WRAPPER_SOURCE:recovered_wrapper(values[WRAPPER_SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor descriptor effect live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor descriptor effect frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor descriptor effect original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor descriptor effect strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor descriptor effect named definitions changed')

def derive_guards():
    changes=((0x60,0x8FB8002C,0x8FA8002C),(0x6C,0x93190002,0x91090002),
        (0x70,0x8CEA01D4,0x8CF901D4),(0x80,0x00194180,0x00095180),
        (0x8C,0x010A3021,0x032A3021))
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
        expected='0x%08X'%old,replacement='0x%08X'%new,
        expected_relocations='-',replacement_relocations='-',
        note='Normalize one closed descriptor-index matrix-address register allocation cycle',
        insert_after='',insert_after_relocations='',omit='false')for at,old,new in changes]
NEW_GUARDS=derive_guards()

def guard_manifest(before):
    import csv,io
    if sha(before)!='63822339da0c8d3c9a2f6ce9f23ca0fb69345fc4b99f9cb352d44c9f6a218615':raise ValueError('Inherited guard bytes changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Target guards already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10)).writerows(NEW_GUARDS);return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);patches={int(row['offset'],0):row for row in NEW_GUARDS};out=bytearray();rels={}
    for at in range(0,len(raw),4):
        word=struct.unpack_from('>I',raw,at)[0];row=patches.get(at)
        if row:
            if word!=int(row['expected'],0)or bindings.get(at):raise ValueError('Guard word or binding changed')
            word=int(row['replacement'],0)
        if at in bindings:rels[len(out)]=bindings[at]
        out.extend(struct.pack('>I',word))
        if row and row['insert_after']:out.extend(struct.pack('>I',int(row['insert_after'],0)))
    if len(out)!=196 or sha(out)!='ee6218899a03c79f0f02b076ea9b5f86a0e28c83996b722f5493b3861a6bdf7f' or rels!=BINDINGS:raise ValueError('Normalized body or bindings changed')
    return bytes(out),rels

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150F9950.o','first-linked.elf','proposed-wrapper-owner.c','wrapper-after-padded.o')
EVIDENCE=('wrapper-before.c','wrapper-before-processed.c','wrapper-before.o','wrapper-before-diagnostics.txt','wrapper-after.c','wrapper-after-processed.c','wrapper-after.o','wrapper-after-diagnostics.txt','wrapper-before-padded.o','wrapper-check-v1.json', "make-shadow/src/game/generated_124920.c","proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_124920.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_124920.c.o","make-shadow/src/game/generated_124920.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor descriptor effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor descriptor effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor descriptor effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor descriptor effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor descriptor effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_124920.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor descriptor effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=5 or q['exclusions']!=0:raise ValueError('Actor descriptor effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor descriptor effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor descriptor effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=168,alignment_words=3,slot_words=52,strict_first_link_reproduced=True,guards=5,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
