"""First marked record bit: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151140C4','generated_13D350'
ENTRY,ROM,BODY,SIZE=0x151140C4,0x141574,196,196
SOURCE='conker/src/game/generated_13D350.c'
OBJECT='conker/build/src/game/generated_13D350.c.o'
ASM='conker/asm/13D350.s'
BUILD='conker/build/game-record-first-marked-bit-match'
RODATA_SYMBOL=None
RAW_SHA="590c2f8d2309a42e9b98853caa34b675ddf534e35f8857003e1aeb67b9b50fa9"
SNAPSHOT_SHA="e27bc890c276ac76672c651e1e43dad2cecad573058e7e74e5deb1690f44080d"
BEFORE_ELF_SHA="feea5868de3eb5a9938f2a171c6268d8cccf142a99567e2e793520f91c2fc7a1"
TRUTH_SHA="33416e303519bb77f9a002bddd301cdc118eb0f1ff34f157b0a3d2027cba9549"
PARENT,TABLE,LOOKUP,BASE,MASKS,COUNT=0x1509ED74,0x8009F43C,0x151149AC,0x800DBEF4,0x800DBF94,0x800DBEF0
TABLE_ROM=0x243EFC
BINDINGS={8:[('R_MIPS_HI16','D_800DBF94')],32:[('R_MIPS_LO16','D_800DBF94')],20:[('R_MIPS_HI16','D_800DBEF4')],24:[('R_MIPS_LO16','D_800DBEF4')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern u8 *D_800DBEF4;\nextern s32 *D_800DBF94;\n\n"
SELECTED="/* Return the first set record-mask bit, or zero when disabled or empty. */\ns32 func_151140C4(u8 *record) {\n    s32 index = 0;\n    s32 mask;\n    if (record[0x4F] & 0x80) {\n        mask = D_800DBF94[(record - D_800DBEF4) / 0xA0];\n        for (; index < 32; index++) {\n            if (mask & (1U << index)) {\n                return index;\n            }\n        }\n    }\n    return 0;\n}"


def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected first-marked-bit owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=196 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('First marked record bit body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151140C4() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('First marked record bit placeholder changed')
    return before.replace(stub,SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('First marked record bit snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('First marked record bit frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('First marked record bit predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('First marked record bit live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('First marked record bit strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('First marked record bit original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('First marked record bit image differs from body and extent prediction')
    expected=Counter((n,f[1],196 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('First marked record bit named ELF definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
    if sha(before)!='91cfc61697b2f874f74475c5dadac1faec1f2e3c4f2a515d593b62d15b71ba03':raise ValueError('Inherited guard bytes changed')
    return before
def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151140C4.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_13D350.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_13D350.c.o","make-shadow/src/game/generated_13D350.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('First marked record bit artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('First marked record bit artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('First marked record bit raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('First marked record bit evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('First marked record bit Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_13D350.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('First marked record bit Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('First marked record bit private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('First marked record bit changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('First marked record bit protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=0,alignment_words=0,slot_words=49,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
