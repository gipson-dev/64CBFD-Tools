"""Display-list buffer allocation: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15015E80','generated_43330'
ENTRY,ROM,BODY,SIZE=0x15015E80,0x43330,188,192
SOURCE='conker/src/game/generated_43330.c'
OBJECT='conker/build/src/game/generated_43330.c.o'
ASM='conker/asm/43330.s'
BUILD='conker/build/game-display-list-buffer-allocation-match'
RAW_SHA="fe10bd7c57a957a1ef3d7457edc21b452c0ffd3812a4d61d75be40f3557f3f62"
SNAPSHOT_SHA="5513489b1e7d2cdea167eec797bc4f6634560c43fd537ca0eb7661581d967438"
BEFORE_ELF_SHA="f87a98be9f3ecb68cd8e36e4e7075a24cb28382ab5ab67d0c4457817de91639e"
TRUTH_SHA="b3e9c0160c5af5ce7b72b7b7d1667dbf53623369c38549996ca41b2942f3a155"
CONFIG,SLOTS,LIMIT,ALLOCATOR,HEAP=0x800B0DF0,0x800BE9C8,0x800BEBA4,0x10003C40,0x10003C6C
BINDINGS={4:[('R_MIPS_HI16','D_800B0DF0')],8:[('R_MIPS_LO16','D_800B0DF0')],80:[('R_MIPS_26','allocate_memory')],88:[('R_MIPS_HI16','D_800BE9C8')],92:[('R_MIPS_LO16','D_800BE9C8')],100:[('R_MIPS_HI16','D_800B0DF0')],104:[('R_MIPS_LO16','D_800B0DF0')],128:[('R_MIPS_26','allocate_memory')],136:[('R_MIPS_HI16','D_800BE9C8')],140:[('R_MIPS_LO16','D_800BE9C8')],152:[('R_MIPS_HI16','D_800BEBA4')],168:[('R_MIPS_LO16','D_800BEBA4')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="#include \"structs.h\"\nextern struct104 *D_800B0DF0;\nextern s32 D_800BE9C8[];\nextern s32 D_800BEBA4;\ns32 allocate_memory(s32, s32, s32, s32);\n\n"
SELECTED="/* Allocate both display-list buffers and reserve 400 commands below their address gap. */\nvoid func_15015E80(void) {\n    if (*(u16 *)((u8 *)D_800B0DF0 + 0x1C) == 0) {\n        *(u16 *)((u8 *)D_800B0DF0 + 0x1C) = 8000;\n    }\n    *(u16 *)((u8 *)D_800B0DF0 + 0x1C) += 400;\n    D_800BE9C8[0] = allocate_memory(*(u16 *)((u8 *)D_800B0DF0 + 0x1C) << 3, 255, 2, 0);\n    D_800BE9C8[1] = allocate_memory(*(u16 *)((u8 *)D_800B0DF0 + 0x1C) << 3, 255, 2, 0);\n    D_800BEBA4 = ((s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0]) >> 3) - 400;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Display-list buffer allocation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15015E80() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Display-list buffer allocation placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Display-list buffer allocation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Display-list buffer allocation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Display-list buffer allocation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Display-list buffer allocation live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Display-list buffer allocation strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Display-list buffer allocation original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Display-list buffer allocation image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Display-list buffer allocation named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15015E80.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_43330.c.o","make-shadow/src/game/generated_43330.c.o.compact","make-shadow/src/game/generated_43330.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Display-list buffer allocation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Display-list buffer allocation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Display-list buffer allocation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Display-list buffer allocation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Display-list buffer allocation Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected display-list buffer owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_43330.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Display-list buffer allocation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Display-list buffer allocation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Display-list buffer allocation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Display-list buffer allocation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,frame=24,alignment_words=1,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
