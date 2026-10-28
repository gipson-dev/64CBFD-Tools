"""Threshold effect update: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151A483C','generated_1D0840'
ENTRY,ROM,BODY,SIZE=0x151A483C,0x1D1CEC,196,196
SOURCE='conker/src/game/generated_1D0840.c'
OBJECT='conker/build/src/game/generated_1D0840.c.o'
ASM='conker/asm/1D0840.s'
BUILD='conker/build/game-threshold-effect-update-match'
RODATA_SYMBOL=None
RAW_SHA="fe9b4221c61a90a9ff546e917119a84e3442ef99fb39795426c96c624877ec9e"
SNAPSHOT_SHA="8e37aed6076263f55422b1053f1565475546d3da5aabfaf97eb11fab268bd151"
BEFORE_ELF_SHA="c7173a57ca1782fd61e4c170a0b9aa6d8429df8bb393b582bfc1cde0c0d08865"
TRUTH_SHA="9b7679467c3fb18c8a8897ba6c844f88e15b9df885d8e065d47c384a2c5b458a"
PARENT,TABLE,TICKS=0x151303EC,0x80089760,0x800BE9E4
BINDINGS={16:[('R_MIPS_HI16','D_800BE9E4')],76:[('R_MIPS_LO16','D_800BE9E4')]}
HEADERS="#include <ultra64.h>\n\n"
DECLARATIONS="extern s32 D_800BE9E4;\n\n"
SELECTED="/* Update lifetime-scaled outputs and switch to the next update callback. */\ntypedef struct {\n    u8 reserved00[0x18];\n    s16 state;\n    s16 counter;\n    u8 reserved1C[0xF];\n    u8 firstOutput;\n    u8 secondOutput;\n    u8 reserved2D[0xB];\n    f32 firstValue;\n    f32 secondValue;\n    u8 reserved40[0x30];\n    u8 firstMode;\n    u8 secondMode;\n    u8 updateSelector;\n    u8 reserved73[0x35];\n    s16 parameters[6];\n} ThresholdEffectRecord1D0840;\n\ns32 func_151A483C(ThresholdEffectRecord1D0840 *record, void *unusedContext) {\n    s16 *parameters = record->parameters;\n    s32 counter = record->counter;\n    f32 increment;\n\n    if (counter < parameters[2]) {\n        record->firstOutput = counter * parameters[3];\n    }\n    if (counter < parameters[4]) {\n        increment = (s32)((u32)parameters[5] * (u32)D_800BE9E4);\n        record->firstValue += increment;\n        record->secondValue += increment;\n        counter = record->counter;\n    }\n    if (counter < parameters[0]) {\n        record->updateSelector = 1;\n        record->firstMode = 2;\n        record->secondMode = 2;\n        record->secondOutput = counter * parameters[1];\n        record->state = 0x5203;\n    }\n    return 1;\n}"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected threshold owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Threshold effect update body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151A483C() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Threshold effect update placeholder changed')
    return before.replace(stub,SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Threshold effect update snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Threshold effect update frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Threshold effect update predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Threshold effect update live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Threshold effect update strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Threshold effect update original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Threshold effect update image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Threshold effect update named ELF definitions changed')

def derive_guards():
    # Two unsigned integer products commute; the counter read at +0x1A is
    # disjoint from both float stores at +0x38/+0x3C. Rotate only that read
    # across the unchanged arithmetic/store sequence; retain all relocations.
    sequence=(0x8483001A,0x00005012,0x448A2000,0,0x46802020,0x46003200,0x46005400,0xE4880038,0xE490003C)
    changes=[(36,0x01E30019,0x006F0019),(168,0x01A30019,0x006D0019)]
    changes.extend((92+i*4,old,new)for i,(old,new)in enumerate(zip(sequence,sequence[1:]+sequence[:1])))
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',note='Normalize threshold update commutative multiplies and independent counter reload',insert_after='',insert_after_relocations='',omit='false')for at,old,new in sorted(changes)]

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='2644438e9057a3ce98cd58c2af11503e38a2cec39164719b1e010ed07dcefd24':raise ValueError('Inherited guard bytes changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Target guards already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10)).writerows(NEW_GUARDS);return before+out.getvalue().encode()
def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);patches={int(row['offset'],0):row for row in NEW_GUARDS};out=bytearray();rels={}
    for at in range(0,len(raw),4):
        word=struct.unpack_from('>I',raw,at)[0];row=patches.get(at)
        if row:
            if word!=int(row['expected'],0)or bindings.get(at):raise ValueError('Guard word/binding changed')
            if row['omit']=='true':continue
            word=int(row['replacement'],0)
        if at in bindings:rels[len(out)]=bindings[at]
        out.extend(struct.pack('>I',word))
    return bytes(out),rels

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151A483C.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1D0840.c.o.compact","make-shadow/src/game/generated_1D0840.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1D0840.c.o","make-shadow/src/game/generated_1D0840.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Threshold effect update artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Threshold effect update artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Threshold effect update raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Threshold effect update evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Threshold effect update Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1D0840.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Threshold effect update Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=11 or q['exclusions']!=0:raise ValueError('Threshold effect update private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Threshold effect update changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Threshold effect update protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=0,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=11,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
