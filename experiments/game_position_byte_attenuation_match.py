"""Position alpha attenuation: guarded C private proposal, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_1517B6E8','generated_1A89B0'
ENTRY,ROM,BODY,SIZE=0x1517B6E8,0x1A8B98,192,192
SOURCE='conker/src/game/generated_1A89B0.c'
OBJECT='conker/build/src/game/generated_1A89B0.c.o'
ASM='conker/asm/1A89B0.s'
BUILD='conker/build/game-position-byte-attenuation-match'
RAW_SHA="5239edfc21fc76a2a75b01eb389682c67d02e3918ccc2d6320d80d5b7a18623c"
SNAPSHOT_SHA="0077bb4000013e400e240f263063a64207022f0e08639bb091fd224999af5591"
BEFORE_ELF_SHA="09637b9c03ce34c02c38f08521e35fc9206900f4d25c99448849c87846e6c279"
TRUTH_SHA="ee6c15f1908be61a815e45dbe6762e925aea9eacc2207c4679ae456a02b19b6e"
REGISTRY=0x8008CEBC
BINDINGS={}
NORMALIZED_BINDINGS={}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS=""
SELECTED="/* Adjust the position and attenuate vertex alpha after the counter reaches 0x600. */\ns32 func_1517B6E8(s16 *input, s16 *output, s32 *counter, u8 *alpha) {\n    s32 current = *counter;\n    s32 scaled;\n\n    if (current >= 0x600) {\n        output[1] = (current >> 6) + input[1] - 24;\n        output[0] = input[0] + (*counter >> 8) - 6;\n        scaled = ((*alpha << 7) / ((*counter >> 6) - 23)) >> 4;\n        if (scaled < *alpha) {\n            *alpha = scaled;\n        }\n        *counter = 0x600;\n    } else {\n        output[0] = input[0];\n        output[1] = input[1];\n    }\n    output[2] = input[2];\n    return 0;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Position alpha attenuation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1517B6E8() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Position alpha attenuation placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Position alpha attenuation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Position alpha attenuation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Position alpha attenuation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Position alpha attenuation live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Position alpha attenuation strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Position alpha attenuation original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Position alpha attenuation image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Position alpha attenuation named ELF definitions changed')

NEW_GUARDS=[{"filename":"generated_1A89B0","function":"func_1517B6E8","offset":"0x010","expected":"0x848E0002","replacement":"0x848F0002","expected_relocations":"-","replacement_relocations":"-","note":"Normalize closed opening counter-shift and input-Y GPR exchange","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_1A89B0","function":"func_1517B6E8","offset":"0x014","expected":"0x00027983","replacement":"0x00027183","expected_relocations":"-","replacement_relocations":"-","note":"Normalize closed opening counter-shift and input-Y GPR exchange","insert_after":"","insert_after_relocations":"","omit":"false"}]
def guard_manifest(before):
    import csv,io
    if sha(before)!='a8af4b342808530c29b95255b79b882169fb1f59b94d3365c0e1f0da9cf9a1cf':raise ValueError('Position alpha inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Position alpha guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>48I',raw));result_bindings={at:list(rs)for at,rs in bindings.items()};seen=set()
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=';'.join(k+':'+n for k,n in result_bindings.get(at,[]))or'-'
        if at in seen or words[at//4]!=int(row['expected'],0)or row['expected_relocations']!=expected:raise ValueError('Position alpha expected word/binding changed')
        seen.add(at);words[at//4]=int(row['replacement'],0);replacement=row['replacement_relocations']
        if replacement=='-':result_bindings.pop(at,None)
        else:result_bindings[at]=[tuple(part.split(':',1))for part in replacement.split(';')]
    result=struct.pack('>48I',*words)
    if len(seen)!=2 or sha(result)!='ee6c15f1908be61a815e45dbe6762e925aea9eacc2207c4679ae456a02b19b6e'or result_bindings!=NORMALIZED_BINDINGS:raise ValueError('Position alpha normalized body/bindings changed')
    return result,result_bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1517B6E8.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1A89B0.c.o","make-shadow/src/game/generated_1A89B0.c.o.compact","make-shadow/src/game/generated_1A89B0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Position alpha attenuation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position alpha attenuation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position alpha attenuation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Position alpha attenuation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Position alpha attenuation Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected position alpha owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_1A89B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Position alpha attenuation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Position alpha attenuation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Position alpha attenuation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Position alpha attenuation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=0,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
