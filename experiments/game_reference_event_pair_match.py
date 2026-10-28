"""Paired bound-object reference events: semantic C and symmetric-branch normalization."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
OWNER="generated_1C2C60"
SOURCE="conker/src/game/generated_1C2C60.c"
OBJECT="conker/build/src/game/generated_1C2C60.c.o"
ASM="conker/asm/1C2C60.s"
BUILD="conker/build/game-reference-event-pair-match"
SIZE=188
TARGETS={"func_15198054":{"entry":353992788,"rom":1856772,"helper":353997748,"special":8,"slot":3,"raw_sha":"5c9d83c4cb75ea2beeddfb130f66b8c6f2503ceae6751c2540789ff925724be8","truth_sha":"7611fcc46bf38bcd20c78329b0f8f688423e2454b2ffa6f0ec76dd10ebb8b348"},"func_1519986C":{"entry":353998956,"rom":1862940,"helper":353802028,"special":38,"slot":14,"raw_sha":"c6b40782092830bb26701419400c9c36021fe37a13012c9c5f3df5667252ddd3","truth_sha":"cc44784ba449b14240046ebb47cb6a9641097092fd818915196e143189b88aac"}}
FUNCTIONS=tuple(TARGETS)
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct {\n    u8 *object;\n    u8 identifier;\n    u8 reserved5[3];\n} BoundObjectReference;\nvoid func_151993B4(u8 *);\nvoid func_1516972C(u8 *);\n"
SELECTED={"func_15198054":"/* Retire a matching bound object, or update its reference after replacement. */\nvoid func_15198054(u8 *owner, s32 eventAddress, u8 command) {\n    u8 *event = (u8 *)eventAddress;\n    BoundObjectReference *reference = *(BoundObjectReference **)(owner + 0x98);\n\n    if ((command == 0) || (command == 2) || (command == 8)) {\n        if ((reference->object == *(u8 **)event) ||\n            (reference->identifier == event[4])) {\n            func_151993B4(owner);\n        }\n    } else if (command == 0x2D) {\n        u8 *object = *(u8 **)event;\n        if (object == reference->object) {\n            reference->object = *(u8 **)(event + 4);\n            reference->identifier = event[9];\n        } else if (reference->object == *(u8 **)(event + 4)) {\n            reference->object = object;\n            reference->identifier = event[8];\n        }\n    }\n}","func_1519986C":"/* Retire a matching bound object, or update its reference after replacement. */\nvoid func_1519986C(u8 *owner, s32 eventAddress, u8 command) {\n    u8 *event = (u8 *)eventAddress;\n    BoundObjectReference *reference = *(BoundObjectReference **)(owner + 0x98);\n\n    if ((command == 0) || (command == 2) || (command == 0x26)) {\n        if ((reference->object == *(u8 **)event) ||\n            (reference->identifier == event[4])) {\n            func_1516972C(owner);\n        }\n    } else if (command == 0x2D) {\n        u8 *object = *(u8 **)event;\n        if (object == reference->object) {\n            reference->object = *(u8 **)(event + 4);\n            reference->identifier = event[9];\n        } else if (reference->object == *(u8 **)(event + 4)) {\n            reference->object = object;\n            reference->identifier = event[8];\n        }\n    }\n}"}
SNAPSHOT_SHA="eb2226dbaa3914d54a9f10dba76bab4c394d2d2ed7e50c59fe75f6b8373c1f33"
BEFORE_ELF_SHA="16290cc7896c19c51ea6cc4473833d79af91be2764388a52c8cd37906b8988b5"
GUARD_SHA="aa286e5015de7d8f364278aeefebd09be69aed12986816cf4a1ae58c44a0a87e"
PARENT,PARENT_ROM,PARENT_SIZE=0x15147D1C,0x1751CC,72
TABLE,TABLE_ROM,TABLE_SIZE=0x8008A390,0x22EE50,20
sha=lambda b:hashlib.sha256(b).hexdigest()

def bindings(name):return {84:[('R_MIPS_26','func_%08X'%TARGETS[name]['helper'])]}
def payload(obj,name):return function_payload(obj,name)
def checked_payload(name,raw,rs):
    if len(raw)!=SIZE or sha(raw)!=TARGETS[name]['raw_sha']or rs!=bindings(name):raise ValueError('Reference event body or call binding changed: '+name)
    return raw,rs

def normalized(name,raw,rs):
    checked_payload(name,raw,rs);words=list(struct.unpack('>47I',raw));w=words[38]
    if w!=0x544B0005 or(w>>26,w>>21&31,w>>16&31,w&65535)!=(21,2,11,5):raise ValueError('Expected symmetric BNEL changed')
    # Equality/inequality is symmetric for every pair of 32-bit GPR values.
    # Swap only the two read operands. Opcode, likely behavior, offset and delay
    # slot are fixed; neither register nor memory is written by this branch.
    words[38]=(w&0xFC00FFFF)|((w>>16&31)<<21)|((w>>21&31)<<16)
    if words[38]!=0x55620005:raise ValueError('Unexpected symmetric branch result')
    return struct.pack('>47I',*words),dict(rs)

def guard_bytes(old,payloads):
    import csv,io
    if sha(old)!=GUARD_SHA or set(payloads)!=set(FUNCTIONS):raise ValueError('Reference event guard baseline changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:raise ValueError('Guard schema changed')
    if any(row['function']in FUNCTIONS for row in reader):raise ValueError('Reference event guards already present')
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for name in FUNCTIONS:
        raw,rs=payloads[name];fitted,updated=normalized(name,raw,rs);assert rs==updated
        writer.writerow(dict(filename=OWNER,function=name,offset='0x098',expected='0x544B0005',replacement='0x55620005',expected_relocations='-',replacement_relocations='-',note='Normalize symmetric branch-likely comparison operand order',omit='false'))
    return old+stream.getvalue().encode()

def recovered_owner(before):
    if 'BoundObjectReference'in before:raise ValueError('Reference event type already installed')
    result=before
    for i,name in enumerate(FUNCTIONS):
        stub='s32 '+name+'() {\n    return 0;\n}'
        if result.count(stub)!=1:raise ValueError('Reference event placeholder changed: '+name)
        result=result.replace(stub,(DECLARATIONS+'\n'if not i else'')+SELECTED[name]+'\n',1)
    return result

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Reference event snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Reference event frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Reference event predecessor changed')
    return values

def predicted_image(before,rom):
    if sha(before)!=BEFORE_ELF_SHA:raise ValueError('Reference event strict predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=rom[t['rom']:t['rom']+SIZE]
        if len(truth)!=SIZE or sha(truth)!=t['truth_sha']:raise ValueError('Reference event truth changed')
        at=elf_slot_offset(before,t['entry'],SIZE);result[at:at+SIZE]=truth
        rows=[p for p,n,f,_ in symbol_rows(before)if n==name and f[1:3]==(t['entry'],12)and f[3]&15==2]
        if len(rows)!=1:raise ValueError('Reference event placeholder extent changed')
        struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)

def check_image(before,actual,rom):
    if actual!=predicted_image(before,rom):raise ValueError('Reference event image differs from the two literal bodies and extents')
    expected=Counter((n,f[1],SIZE if n in TARGETS else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Reference event named ELF definitions changed')

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin']),'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes()}
    for n,b in values.items():
        if(root/n).read_bytes()!=changes.get(n,b):raise ValueError('Reference event live input changed: '+n)
    return values

ARTIFACTS=('qualified-guards.csv','before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15198054.o','original-func_1519986C.o','first-linked.elf')
EVIDENCE=('before-owner.c','before-owner-processed.c','before-owner.o','before-owner-diagnostics.txt','after-owner.c','after-owner-processed.c','after-owner.o','after-owner-diagnostics.txt','selected.c','selected-processed.c','selected.o','selected-diagnostics.txt','selected-input.c','actual-Make-plan.txt','Make-commands.json','make-shadow/src/game/generated_1C2C60.c.o','make-shadow/src/game/generated_1C2C60.c.o.compact','make-shadow/src/game/generated_1C2C60.c.o.padded.s')
def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text());extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS)or set(extra)!=set(EVIDENCE):raise ValueError('Reference event artifact set changed')
    for n,h in {**rows,**extra,**json.loads((output/'frozen-raw.json').read_text())}.items():
        if sha((output/n).read_bytes())!=h:raise ValueError('Reference event prepared artifact changed: '+n)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Reference event expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_1C2C60.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Reference event Make object changed')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete']or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Reference event private preparation changed')
    return dict(rows,**extra)

def audit(root,output):
    v=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(v['conker/build/conker.us.elf'],actual,v['conker/conker.us.bin'])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=list(FUNCTIONS):raise ValueError('Reference event changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Reference event protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-2,all_addresses_fixed=True,target_words=94,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
