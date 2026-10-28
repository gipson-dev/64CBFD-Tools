"""Owner-link event gate: guarded C private proposal, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_150D596C','generated_1028F0'
ENTRY,ROM,BODY,SIZE=0x150D596C,0x102E1C,192,192
SOURCE='conker/src/game/generated_1028F0.c'
OBJECT='conker/build/src/game/generated_1028F0.c.o'
ASM='conker/asm/1028F0.s'
BUILD='conker/build/game-owner-link-event-gate-match'
RAW_SHA="d4442fb858a37b234ea807400e9ce1acc999e674e2de2379a73230d283a0cc95"
SNAPSHOT_SHA="1b451ccd32ca88ccbc1d317d69f72d65615db40ea41892391478b01e1ce66e11"
BEFORE_ELF_SHA="e8a939f26b31041a250422843deea4be69cc97c004014e43e6fbfb89b522bf76"
TRUTH_SHA="80b33955280bbc2d986bf243a59fc42150c0662b459f8595a7f20026901dfe22"
PARENT,TABLE,TABLE_ROM,COUNT,INDEX=0x15149434,0x8008A8D8,0x22F398,74,40
CALLER_SOURCE='conker/src/game/done/game_1765E0.c'
CALLER_OBJECT='conker/build/src/game/done/game_1765E0.c.o'
BINDINGS={88:[('R_MIPS_26','func_1516972C')]}
NORMALIZED_BINDINGS=dict(BINDINGS)
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\ntypedef struct { u8 *owner; u8 identity; u8 opaque5[3]; } EmbeddedOwnerLink;\ntypedef struct { u8 *before; u8 *after; u8 before_identity; u8 after_identity; u8 opaqueA[2]; } OwnerLinkEvent;\nvoid func_1516972C(struct102 *);\n\n"
DECLARATIONS=''
SELECTED="/* Release matching owner links for 0/3/0x2F, or retarget them for 0x2D. */\nvoid func_150D596C(struct260 *owner, s32 eventAddress, u8 command) {\n    EmbeddedOwnerLink *link = (EmbeddedOwnerLink *)((u8 *)owner + 0x28);\n    OwnerLinkEvent *event = (OwnerLinkEvent *)eventAddress;\n\n    if (command == 0 || command == 0x2F || command == 3) {\n        u8 *first = event->before;\n        /* Retail compares byte +4: the second pointer overlaps this identity. */\n        if (first == link->owner || link->identity == ((u8 *)event)[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else if (command == 0x2D) {\n        u8 *current = link->owner;\n        if (current == event->before) {\n            link->owner = event->after;\n            /* Read the identity after the pointer store; packet/link may overlap. */\n            link->identity = event->after_identity;\n        } else if (current == event->after) {\n            link->owner = event->before;\n            link->identity = event->before_identity;\n        }\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner-link event gate body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150D596C() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Owner-link event gate placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner-link event gate snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner-link event gate frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner-link event gate predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner-link event gate live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner-link event gate strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Owner-link event gate original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner-link event gate image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner-link event gate named ELF definitions changed')

def derive_guards():
    """Exchange current/first pointer registers and commute symmetric compares."""
    expected={116:0x8C430000,120:0x8CA40000,156:0x546A0005,164:0xAC440000}
    def exchange(word,fields):
        for shift in fields:
            reg=(word>>shift)&31;word=(word&~(31<<shift))|({3:4,4:3}.get(reg,reg)<<shift)
        return word
    result={at:exchange(word,(16,)if at in(116,120,164)else(21,16))for at,word in expected.items()}
    word=result[156];a,b=(word>>21)&31,(word>>16)&31
    result[156]=(word&~((31<<21)|(31<<16)))|(b<<21)|(a<<16)
    # The first equality at +124 is invariant under exchange plus commutation.
    word=exchange(0x54640007,(21,16));a,b=(word>>21)&31,(word>>16)&31
    assert((word&~((31<<21)|(31<<16)))|(b<<21)|(a<<16))==0x54640007
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
        expected='0x%08X'%expected[at],replacement='0x%08X'%result[at],
        expected_relocations='-',replacement_relocations='-',
        note='Normalize closed owner/event pointer register exchange and symmetric comparison',
        insert_after='',insert_after_relocations='',omit='false')for at in sorted(expected)]

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='70585f37f91bfac072fa8df784c94ef782fbdb6f2d4fe295f5aed132195433bb':raise ValueError('Owner-link event inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Owner-link event guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>48I',raw));result_bindings={at:list(rs)for at,rs in bindings.items()};seen=set()
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=';'.join(k+':'+n for k,n in result_bindings.get(at,[]))or'-'
        if at in seen or words[at//4]!=int(row['expected'],0)or row['expected_relocations']!=expected:raise ValueError('Owner-link event expected word/binding changed')
        seen.add(at);words[at//4]=int(row['replacement'],0);replacement=row['replacement_relocations']
        if replacement=='-':result_bindings.pop(at,None)
        else:result_bindings[at]=[tuple(part.split(':',1))for part in replacement.split(';')]
    result=struct.pack('>48I',*words)
    if len(seen)!=4 or sha(result)!='7e7606c0922c47e7d1d66e805019056484411f8c944e0669f9acd9eb8d7583f1'or result_bindings!=NORMALIZED_BINDINGS:raise ValueError('Owner-link event normalized body/bindings changed')
    return result,result_bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150D596C.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1028F0.c.o","make-shadow/src/game/generated_1028F0.c.o.compact","make-shadow/src/game/generated_1028F0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner-link event gate artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner-link event gate artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner-link event gate raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner-link event gate evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner-link event gate Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected owner-link event owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_1028F0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner-link event gate Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=4 or q['exclusions']!=0:raise ValueError('Owner-link event gate private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner-link event gate changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner-link event gate protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=24,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=4,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
