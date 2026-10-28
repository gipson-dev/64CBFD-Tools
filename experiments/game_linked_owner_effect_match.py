"""Linked-owner effect: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151918BC','generated_1BA1D0'
ENTRY,ROM,BODY,SIZE=0x151918BC,0x1BED6C,196,196
SOURCE='conker/src/game/generated_1BA1D0.c'
OBJECT='conker/build/src/game/generated_1BA1D0.c.o'
ASM='conker/asm/1BA1D0.s'
BUILD='conker/build/game-linked-owner-effect-match'
RODATA_SYMBOL=None
RAW_SHA="cac0c76cac792ddf27064a6fd7c44f1a36b5a6e5f9f73a3f93bda64ecab25205"
SNAPSHOT_SHA="edfe3c09b0fb25a89db433a02e1d33c06410a8224faecda0b7dd4acc69c27c85"
BEFORE_ELF_SHA="77b67000ba81892c36c0960e2ac4761e31eaf0cb6c3c7774edaf2a915e56690f"
TRUTH_SHA="5578fde1cc5e213328fe803d0c0e5bc61f0b8341093e819b542f2027b7415d6c"
HELPER,FREE,PARENT,TABLE,TICKS=0x15190770,0x1516972C,0x15149264,0x8008A4E8,0x800BE9E4
BINDINGS={152:[('R_MIPS_26','func_15190770')],172:[('R_MIPS_26','func_1516972C')]}
HEADERS="#include <ultra64.h>\n\n"
DECLARATIONS="s32 func_15190770();\ns32 func_1516972C();\n\n"
SELECTED="/* Release invalid owner links, or emit the owner payload before releasing the record. */\nvoid func_151918BC(u8 *record) {\n    /* Preserve the retail frame and the release flag spill at incoming SP - 9. */\n    s32 unused[2];\n    u8 release = 0;\n    u8 *owner = *(u8 **)(record + 0x28);\n    u8 *payload;\n\n    (void)unused;\n    if (*(s32 *)owner == 0) {\n        release = 1;\n    } else if (record[0x2C] != owner[0x3B]) {\n        release = 1;\n    }\n    if (!release && *(s32 *)(owner + 0x1D4) != 0) {\n        payload = record + 0x28;\n        release = 1;\n        if (record[0xD] & 1) {\n            payload[8] |= 1;\n            *(s16 *)(payload + 6) = *(s16 *)(record + 0xE);\n        } else {\n            *(s16 *)(payload + 6) = 300;\n        }\n        func_15190770(payload, 0, record[0xC], record[1]);\n    }\n    if (release) {\n        func_1516972C(record);\n    }\n}"

def check_owner_diagnostics(text):
    pattern=r'cfe: Warning 712: [^\n]+, line [0-9]+: illegal combination of pointer and integer\n     (func_[0-9A-F]+)\(arg0\);\n ------------------\^\n'
    names=re.findall(pattern,text)
    if names!=['func_1518E4A0','func_1518E4A0','func_15190454','func_15190454'] or re.sub(pattern,'',text):raise ValueError('Unexpected linked-owner effect owner diagnostics')
    return len(names)

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Linked-owner effect body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151918BC() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Linked-owner effect placeholder changed')
    return before.replace(stub,SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Linked-owner effect snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Linked-owner effect frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Linked-owner effect predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Linked-owner effect live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Linked-owner effect strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Linked-owner effect original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Linked-owner effect image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Linked-owner effect named ELF definitions changed')

def derive_guards():
    # Remove a repeated a0=record+0x28, then normalize independent setup and
    # flag/lifetime scheduling. Only branches crossing that word shrink by one.
    changes=((64,0x14400018,0x14400017),(80,0x13200014,0x13200013),
       (92,0x24020001,0x26040028),(96,0x26040028,0x24020001),
       (104,0x11200008,0x11200007),(112,0x26040028,0x26040028),
       (116,0x908A0008,0x908B0008),(120,0x354B0001,0x860A000E),
       (124,0xA08B0008,0x356C0001),(128,0x860C000E,0xA08C0008),
       (136,0xA48C0006,0xA48A0006))
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',note='Normalize linked-owner effect redundant address and independent field scheduling',insert_after='',insert_after_relocations='',omit='true'if at==112 else'false')for at,old,new in changes]
NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='4d5db7992914b7209e0976f4569be48fd6b3b36a850fc0b35140fc097209b840':raise ValueError('Inherited guard bytes changed')
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

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151918BC.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1BA1D0.c.o","make-shadow/src/game/generated_1BA1D0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Linked-owner effect artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Linked-owner effect artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Linked-owner effect raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Linked-owner effect evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Linked-owner effect Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1BA1D0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Linked-owner effect Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=11 or q['exclusions']!=0:raise ValueError('Linked-owner effect private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Linked-owner effect changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Linked-owner effect protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=48,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=11,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
