"""Owner lifetime descriptor: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150F6890','generated_1228D0'
ENTRY,ROM,BODY,SIZE=0x150F6890,0x123D40,204,204
SOURCE='conker/src/game/generated_1228D0.c'
OBJECT='conker/build/src/game/generated_1228D0.c.o'
ASM='conker/asm/1228D0.s'
BUILD='conker/build/game-owner-lifetime-descriptor-match'
RODATA_SYMBOL=None
RAW_SHA='cf82ae22323ed1bf78ff436da1b3a795402d0f552811cb91e32f845ad16f0403'
SNAPSHOT_SHA='3c1a3b5e31201c0cc038c994df9da79a2d2c36394e9d70598b1f045978719142'
BEFORE_ELF_SHA='ac67fd82de83fdabaca9ae2eb56c9e9454e09a709f4906a3392dd4bc152eaac0'
TRUTH_SHA='ae328ab754633ddfba8b2d6f04e9a16299b961396fcc5268de11906ad7134aa6'
BINDINGS={40: [('R_MIPS_HI16', 'D_800A1B70')], 44: [('R_MIPS_LO16', 'D_800A1B70')], 180: [('R_MIPS_26', 'func_15134DAC')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A1B70;\nvoid *func_15134DAC(s32, s32);\ntypedef struct {\n    u8 owner_id;\n    u8 pad1[3];\n    u8 *owner;\n    u8 attachmentIndex;\n    u8 pad9[3];\n    f32 zero0;\n    f32 zero1;\n    f32 zero2;\n    f32 zero3;\n    f32 value1C;\n    f32 value20;\n    u8 mode;\n    u8 pad25;\n    s16 activeFrames;\n    s16 restartDelay;\n    s16 lifetime;\n    s16 value2C;\n    s8 startCallback;\n    s8 transformCallback;\n    s8 updateCallback;\n    u8 pad31[3];\n    f32 rate;\n    u8 flags;\n    s8 finishCallback;\n} OwnerLifetimeDescriptor1228D0;\n\n'
DECLARATIONS='extern f32 D_800A1B70;\nvoid *func_15134DAC(s32, s32);\ntypedef struct {\n    u8 owner_id;\n    u8 pad1[3];\n    u8 *owner;\n    u8 attachmentIndex;\n    u8 pad9[3];\n    f32 zero0;\n    f32 zero1;\n    f32 zero2;\n    f32 zero3;\n    f32 value1C;\n    f32 value20;\n    u8 mode;\n    u8 pad25;\n    s16 activeFrames;\n    s16 restartDelay;\n    s16 lifetime;\n    s16 value2C;\n    s8 startCallback;\n    s8 transformCallback;\n    s8 updateCallback;\n    u8 pad31[3];\n    f32 rate;\n    u8 flags;\n    s8 finishCallback;\n} OwnerLifetimeDescriptor1228D0;\n\n'
SELECTED='/* Construct an owner-attached effect with a signed lifetime.\n * The two -1 callback indices disable those optional callbacks.\n * The original four-argument ABI retains the unused selector and context. */\nvoid *func_150F6890(u8 *owner, s16 lifetime, s32 unusedSelector, s32 unusedContext) {\n    OwnerLifetimeDescriptor1228D0 packet;\n    packet.owner_id = owner[0x3B];\n    packet.owner = owner;\n    packet.attachmentIndex = 3;\n    packet.zero0 = 0.0f;\n    packet.zero1 = 0.0f;\n    packet.zero2 = 0.0f;\n    packet.zero3 = 0.0f;\n    packet.value1C = D_800A1B70;\n    packet.value20 = 8.5f;\n    packet.mode = 2;\n    packet.activeFrames = 40;\n    packet.restartDelay = 16;\n    packet.lifetime = lifetime;\n    packet.startCallback = 5;\n    packet.transformCallback = 8;\n    packet.updateCallback = -1;\n    packet.rate = 1.0f;\n    packet.flags = 0;\n    packet.finishCallback = -1;\n    packet.value2C = 0;\n    return func_15134DAC((s32)&packet, 0);\n}\n'

def check_owner_diagnostics(text):
    expected=('func_150F631C','func_1514933C','func_150F631C','func_15149368','func_150F6400','func_1513CA6C','func_150F6400','func_1513CAA0','func_151411A4','func_151411C4')
    pattern=r'cfe: Warning 712: [^\n]+, line [0-9]+: illegal combination of pointer and integer\n     (func_[0-9A-F]+)\(arg0\);\n ------------------\^\n'
    if tuple(re.findall(pattern,text))!=expected or re.sub(pattern,'',text):raise ValueError('Unexpected lifetime descriptor owner diagnostics')
    return len(expected)


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner lifetime descriptor body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150F6890() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner lifetime descriptor placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner lifetime descriptor snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner lifetime descriptor frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner lifetime descriptor predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner lifetime descriptor live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner lifetime descriptor frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner lifetime descriptor original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Referencing the recovered constant rotates two existing GNU symbol buckets.
    # Validate each old definition and every serialized slot before the permutation.
    named={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    groups=((('D_800A1B70','D_800A1620','D_800A5920'),(1,2,0)),
            (('D_80099478','D_80099828','D_8009EE78'),(2,0,1)))
    for names,order in groups:
        rows=[named[n]for n in names]
        for i,(name,(pos,fields,loc))in enumerate(zip(names,rows)):
            wanted=(int(name[2:],16),0,16,0,6 if name=='D_8009EE78'else 65521)
            if fields[1:]!=wanted or before[loc:loc+11]!=name.encode()+b'\0':raise ValueError('Lifetime descriptor named symbol changed: '+name)
            if pos!=rows[0][0]+16*i or loc!=rows[0][2]+11*i or fields[0]!=rows[0][1][0]+11*i:raise ValueError('Lifetime descriptor symbol bucket layout changed')
        for destination,index in zip(rows,order):
            origin=rows[index];result[destination[0]:destination[0]+16]=before[origin[0]:origin[0]+16]
            struct.pack_into('>I',result,destination[0],destination[1][0]);result[destination[2]:destination[2]+11]=names[index].encode()+b'\0'
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner lifetime descriptor strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner lifetime descriptor named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='82a037c271b5f3a9f248316290dcb31008db70397b5ec399ebc415cdd6bd8f3a':raise ValueError('Owner lifetime descriptor inherited guards changed')
    return before

def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)


ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150F6890.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_1228D0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1228D0.c.o","make-shadow/src/game/generated_1228D0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner lifetime descriptor artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner lifetime descriptor artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner lifetime descriptor raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner lifetime descriptor evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner lifetime descriptor Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1228D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner lifetime descriptor Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner lifetime descriptor private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner lifetime descriptor changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner lifetime descriptor protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=88,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
