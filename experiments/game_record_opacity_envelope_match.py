"""Record opacity envelope: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150F55C8','generated_1228D0'
ENTRY,ROM,BODY,SIZE=0x150F55C8,0x122A78,196,196
SOURCE='conker/src/game/generated_1228D0.c'
OBJECT='conker/build/src/game/generated_1228D0.c.o'
ASM='conker/asm/1228D0.s'
BUILD='conker/build/game-record-opacity-envelope-match'
RODATA_SYMBOL=None
RAW_SHA="1d37e31a89ff6e2172e13d21829c4b58919b1540c7231c779bf815230023aa9a"
SNAPSHOT_SHA="93f9e9b14744d5d284d8b2b6da7032d1f39b73f00b04cbf83d5b59c75df0d982"
BEFORE_ELF_SHA="16d504990da019ce31d571869191ff7813556c3d04b638d487ed91a712eb0737"
TRUTH_SHA="1d37e31a89ff6e2172e13d21829c4b58919b1540c7231c779bf815230023aa9a"
TABLE,WRAPPER,FREE,TICKS=0x8008CA20,0x150F5590,0x1516972C,0x800BE9E4
BINDINGS={}
HEADERS="#include <ultra64.h>\n\n"
SELECTED="/* Apply the record opacity envelope to its remaining lifetime. */\nvoid func_150F55C8(u8 *record) {\n    s32 duration = *(s32 *)(record + 0x1C) & 0xFFFF;\n    s32 fadeIn = *(s32 *)(record + 0x18) >> 16;\n    s32 hold = *(s32 *)(record + 0x18) & 0xFFFF;\n    s32 fadeOut = *(s32 *)(record + 0x1C) >> 16;\n    s32 boundary = duration - fadeIn;\n    s32 remaining = *(s16 *)(record + 0x24);\n\n    if (boundary < remaining) {\n        record[0x45] = ((duration - remaining) * 255) / fadeIn;\n    } else if (boundary - hold < remaining) {\n        record[0x45] = 255;\n    } else {\n        record[0x45] = (remaining * 255) / fadeOut;\n    }\n}"

def check_owner_diagnostics(text):
    pattern=r'cfe: Warning 712: [^\n]+, line [0-9]+: illegal combination of pointer and integer\n     (func_[0-9A-F]+)\(arg0\);\n ------------------\^\n'
    names=re.findall(pattern,text)
    if names!=['func_150F631C','func_1514933C','func_150F631C','func_15149368','func_150F6400','func_1513CA6C','func_150F6400','func_1513CAA0','func_151411A4','func_151411C4'] or re.sub(pattern,'',text):raise ValueError('Unexpected opacity owner diagnostics')
    return len(names)

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record opacity envelope body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150F55C8() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record opacity envelope placeholder changed')
    return before.replace('s32 func_150F55C8();','void func_150F55C8(u8 *record);',1).replace(stub,SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record opacity envelope snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record opacity envelope frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record opacity envelope predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record opacity envelope live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record opacity envelope strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record opacity envelope original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record opacity envelope image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record opacity envelope named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150F55C8.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1228D0.c.o","make-shadow/src/game/generated_1228D0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record opacity envelope artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record opacity envelope artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record opacity envelope raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record opacity envelope evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record opacity envelope Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1228D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record opacity envelope Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record opacity envelope private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record opacity envelope changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record opacity envelope protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=0,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
