"""Record range sound: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_1509F4E8','generated_CBDB0'
ENTRY,ROM,BODY,SIZE=0x1509F4E8,0xCC998,192,192
SOURCE='conker/src/game/generated_CBDB0.c'
OBJECT='conker/build/src/game/generated_CBDB0.c.o'
ASM='conker/asm/CBDB0.s'
BUILD='conker/build/game-record-range-sound-match'
RAW_SHA="8e24df1fe41a5085384d5b95e3ffe62429f204d4b132e45cf3af0a545c0efb2f"
SNAPSHOT_SHA="e79c8982850095977cec9c3c806f3f7c2e955aab7ac4c53c4d45e9e0d8b073c6"
BEFORE_ELF_SHA="d3d212c4d0df5199bf1e879e50cb841e4b9819db44b4178c6592353d6eb0493f"
TRUTH_SHA="5d06d24929cfc2d0ad6f3ddd12a27a814909fe108782d57d0c5b3b2c474ef45c"
RANDOM,SOUND,SUBMIT,TABLE=0x1000F568,0x10010F88,0x10010E78,0x800D3098
BINDINGS={24:[('R_MIPS_HI16','D_800D3098')],28:[('R_MIPS_LO16','D_800D3098')],100:[('R_MIPS_26','func_1000F568')],168:[('R_MIPS_26','func_10010F88')]}
HEADERS="#include <ultra64.h>\ns32 func_1000F568(s32, u32);\nu16 func_10010F88(s32, u16, s16, u8, s32, s16, s16, s16, s16, s16);\n"
DECLARATIONS="typedef struct {\n    s16 x, y, z, distanceLimit;\n    u8 pad8[0x2C];\n} RecordSoundEntry;\nextern RecordSoundEntry *D_800D3098;\n\n"
SELECTED="/* Select a sound and submit it at the record position with a bounded distance. */\nu16 func_1509F4E8(s32 first, s32 last, u16 volume, s32 index, u32 distance) {\n    RecordSoundEntry *record = &D_800D3098[index];\n    s32 limit = record->distanceLimit;\n    s32 selected;\n\n    if (distance >= (u32)limit) {\n        distance = limit - 1;\n    }\n    selected = func_1000F568(first, (u8)((u32)last - (u32)first + 1));\n    return func_10010F88(selected, volume, 0, 0, 0, record->x, record->y, record->z, distance, limit);\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record range sound body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1509F4E8() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record range sound placeholder changed')
    return before.replace('#include <ultra64.h>'+chr(10),HEADERS,1).replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record range sound snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record range sound frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record range sound predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record range sound live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record range sound strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record range sound original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record range sound image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record range sound named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1509F4E8.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_CBDB0.c.o","make-shadow/src/game/generated_CBDB0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record range sound artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record range sound artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record range sound raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record range sound evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record range sound Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected record sound owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_CBDB0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record range sound Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record range sound private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record range sound changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record range sound protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=56,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
