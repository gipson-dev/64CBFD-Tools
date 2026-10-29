"""Payload owner command: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151D4C38','generated_200930'
ENTRY,ROM,BODY,SIZE=0x151D4C38,0x2020E8,204,204
SOURCE='conker/src/game/generated_200930.c'
OBJECT='conker/build/src/game/generated_200930.c.o'
ASM='conker/asm/200930.s'
BUILD='conker/build/game-payload-owner-command-match'
RODATA_SYMBOL=None
FREE,WRAPPER,PAIR,PARENT,TABLE=0x1516972C,0x15149514,0x15169850,0x15149434,0x8008A8D8
RAW_SHA='013b3d0eea298ef9cd11f6789f6c168ae23fe8f6390bb647006c1b10f60b23ff'
SNAPSHOT_SHA='865a09519e649797216da20b8497300bc5ad6d31818dae26b357af3a5682830f'
BEFORE_ELF_SHA='7a8e4653936643e34414876dd0e08037de00fb838c7ad21567fe3fb899b134d1'
TRUTH_SHA='152ea4f34f6155e8100de19e5f29d006577619bd02900483e69ea655ed6e46a9'
BINDINGS={80:[('R_MIPS_26','func_1516972C')],172:[('R_MIPS_26','func_15149514')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='void func_1516972C(struct102 *);\nvoid func_15149514(s32, u8, s32, s32, s32);\n\n'
SELECTED='/* Release or deactivate matching owner links, otherwise dispatch the pair event. */\nvoid func_151D4C38(struct260 *owner, s32 eventAddress, u8 command) {\n    u8 *link = (u8 *)owner + 0x28;\n    u8 *event = (u8 *)eventAddress;\n\n    if (command == 60) {\n        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (command == 4) {\n        if (*(s32 *)link == *(s32 *)event || link[4] == event[4]) {\n            link[0x10] &= ~1;\n        }\n    } else {\n        func_15149514(eventAddress, command, (s32)link, (s32)(link + 4), (s32)owner);\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected payload owner command owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Payload owner command body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151D4C38() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Payload owner command placeholder changed')
    return before.replace('#include <ultra64.h>', '#include <ultra64.h>\n#include \"structs.h\"',1).replace(stub,DECLARATIONS+SELECTED.strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Payload owner command snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Payload owner command frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Payload owner command predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Payload owner command live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Payload owner command frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Payload owner command original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Payload owner command strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Payload owner command named definitions changed')

def derive_guards():
    changes=((0x48,0x5719001B,0x5719001C),(0x58,0x10000017,0x10000018),
        (0x64,0x1441000E,0x1441000F),(0x88,0x554B000B,0x554B000C),
        (0x98,0x10000006,0xA0CD0010),(0x9C,0xA0CD0010,0x10000007))
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
        expected='0x%08X'%old,replacement='0x%08X'%new,
        expected_relocations='-',replacement_relocations='-',
        note='Restore payload-owner command flag-store branch and return-address reload',
        insert_after='0x8FBF0024'if at==0x9C else'',insert_after_relocations='-'if at==0x9C else'',omit='false')for at,old,new in changes]
NEW_GUARDS=derive_guards()

def guard_manifest(before):
    import csv,io
    if sha(before)!='1e58e8b29313c9ffe2b784379c53af9fdc8eb9152c9bb3d1e1a5fb832a5d26b6':raise ValueError('Inherited guard bytes changed')
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
    if len(out)!=204 or sha(out)!='501a617cc308f7dd1f17d9445554a537f7b549fc9f42c133fa5f44f32744f8fc' or rels!={80:[('R_MIPS_26','func_1516972C')],176:[('R_MIPS_26','func_15149514')]}:raise ValueError('Normalized payload or relocation changed')
    return bytes(out),rels

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151D4C38.o','first-linked.elf')
EVIDENCE=("make-shadow/src/game/generated_200930.c","proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_200930.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_200930.c.o","make-shadow/src/game/generated_200930.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Payload owner command artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Payload owner command artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Payload owner command raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Payload owner command evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Payload owner command Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_200930.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Payload owner command Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=6 or q['exclusions']!=0:raise ValueError('Payload owner command private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Payload owner command changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Payload owner command protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=40,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=6,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
