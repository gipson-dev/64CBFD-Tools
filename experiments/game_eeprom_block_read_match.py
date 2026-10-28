"""EEPROM block reader: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_151DD3A0','generated_20A850'
ENTRY,ROM,BODY,SIZE=0x151DD3A0,0x20A850,180,192
SOURCE='conker/src/game/generated_20A850.c'
OBJECT='conker/build/src/game/generated_20A850.c.o'
ASM='conker/asm/20A850.s'
BUILD='conker/build/game-eeprom-block-read-match'
RAW_SHA="c5cdafd5c29304ef8a69524df3cb3a62bbb8622ae3a416fb5972fbd7b876b192"
SNAPSHOT_SHA="094693fe4b83aaa80ce0c62834381498bc1d70984d4ee6c6f1bd1019b71005dc"
BEFORE_ELF_SHA="d677fb3c7d9e215e98dacfe782aa87813510f6516715e95b6be6b1f8fdd730fe"
TRUTH_SHA="20fbda7504204bcd7cbc68767631ff8f47d0518ef7f105f04b579c8f857b1bfc"
POLL,READ=0x151DCFD8,0x151DD140
BINDINGS={52:[('R_MIPS_26','func_151DCFD8')],68:[('R_MIPS_26','func_151DCFD8')],96:[('R_MIPS_26','func_151DD140')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="s32 func_151DCFD8(s32);\ns32 func_151DD140(OSMesgQueue *, u8, u8 *);\n\n"
SELECTED="/* Drain pending EEPROM work, then read successive complete eight-byte blocks. */\ns32 func_151DD3A0(OSMesgQueue *queue, u8 address, u8 *buffer, s32 remaining) {\n    s32 result = 0;\n\n    while (func_151DCFD8(1) != 0) {\n    }\n    while (remaining > 0) {\n        result = func_151DD140(queue, address, buffer);\n        if (result != 0) {\n            return result;\n        }\n        remaining -= 8;\n        address++;\n        buffer += 8;\n    }\n    return result;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('EEPROM block reader body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151DD3A0() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('EEPROM block reader placeholder changed')
    return before.replace('/* Non-matching placeholders for the text-only asm slice asm/20A850.s. */','/* EEPROM block reader recovered from asm/20A850.s. */',1).replace(stub,DECLARATIONS+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('EEPROM block reader snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('EEPROM block reader frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('EEPROM block reader predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('EEPROM block reader live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('EEPROM block reader strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('EEPROM block reader original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('EEPROM block reader image differs from body and extent prediction')
    expected=Counter((n,f[1],180 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('EEPROM block reader named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151DD3A0.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_20A850.c.o","make-shadow/src/game/generated_20A850.c.o.compact","make-shadow/src/game/generated_20A850.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('EEPROM block reader artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('EEPROM block reader artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('EEPROM block reader raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('EEPROM block reader evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('EEPROM block reader Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected EEPROM owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_20A850.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('EEPROM block reader Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('EEPROM block reader private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('EEPROM block reader changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('EEPROM block reader protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=45,alignment_words=3,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
