"""Live type-2 record rebound: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150BCFB8','generated_E8C10'
ENTRY,ROM,BODY,SIZE=0x150BCFB8,0xEA468,184,184
SOURCE='conker/src/game/generated_E8C10.c'
OBJECT='conker/build/src/game/generated_E8C10.c.o'
ASM='conker/asm/E8C10.s'
BUILD='conker/build/game-record-rebound-match'
RAW_SHA='ac4efd8d1086a313e862d5a099612735fe25cf83e1b500aca3eea80111d133ed'
SNAPSHOT_SHA='2dc81b9df292bddaee95f364acbf643da0fdad45810780642000a729d066cd84'
BEFORE_ELF_SHA='6642e143d16dba8b2e9be4234878b37a5de348678e41d352d1b40ff3f9c30d89'
TRUTH_SHA='2a57ba44a2c31f0c4cabae8fc096c4d624613ef85012843acc48b0f5ae40d9d8'
PARENT,PARENT_ROM,PARENT_SIZE=0x15133894,0x160D44,320
TABLE,TABLE_ROM=0x80089934,0x22E3F4
SCALE,SCALE_ROM,SCALE_BITS=0x8009FEF8,0x2449B8,0x3F8CCCCD
PRE,GROUND=0x151337C0,0x15046C80
BINDINGS={12:[('R_MIPS_HI16','D_8009FEF8')],16:[('R_MIPS_LO16','D_8009FEF8')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct {\n    u8 reserved[0x10];\n    f32 extent;\n    f32 damping;\n    u8 reserved18[0x24];\n    f32 height;\n    f32 reserved40;\n    f32 velocity[3];\n    f32 rotationVelocity[3];\n    f32 reserved5C;\n    u32 flags;\n} ReboundRecordE8C10;\nextern f32 D_8009FEF8;\n"
SELECTED="/* Set the ground height, then stop or reflect and damp the record's motion. */\ns32 func_150BCFB8(ReboundRecordE8C10 *record, f32 x, f32 y, f32 z,\n                 f32 groundHeight, f32 *normal) {\n    record->height = record->extent * D_8009FEF8 + groundHeight;\n    if (record->velocity[1] > -2.0f) {\n        record->velocity[0] = 0.0f;\n        record->flags &= 0xFFFFFF90U;\n        record->velocity[1] = 0.0f;\n        record->velocity[2] = 0.0f;\n    } else {\n        f32 damping = record->damping;\n        record->velocity[0] *= damping;\n        record->velocity[1] = -record->velocity[1] * damping;\n        record->velocity[2] *= damping;\n        record->rotationVelocity[0] *= damping;\n        record->rotationVelocity[1] *= damping;\n        record->rotationVelocity[2] *= damping;\n    }\n    return 1;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record rebound body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150BCFB8() {\n    return 0;\n}'
    if before.count(stub)!=1 or 'ReboundRecordE8C10'in before:raise ValueError('Record rebound placeholder/declarations changed')
    return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record rebound snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record rebound frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record rebound predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record rebound live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record rebound strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record rebound original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    named={name:(pos,fields,loc)for pos,name,fields,loc in symbol_rows(before)}
    a,fa,sa=named['func_151417C4'];b,fb,sb=named['D_8009EF5C'];first=b'func_151417C4\0';second=b'D_8009EF5C\0'
    if(b-a,sb-sa,fa[1:],fb[1:])!=(16,14,(0x151417C4,84,18,0,5),(0x8009EF5C,0,16,0,6)):raise ValueError('Record rebound closed serialization predecessor changed')
    if before[sa:sb+len(second)]!=first+second or fb[0]!=fa[0]+14:raise ValueError('Record rebound predecessor names changed')
    struct.pack_into('>IIIBBH',result,a,fa[0],*fb[1:]);struct.pack_into('>IIIBBH',result,b,fa[0]+len(second),*fa[1:]);result[sa:sb+len(second)]=second+first
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record rebound image differs from the closed body/extent/serialization prediction')
    expected=Counter((n,f[1],184 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record rebound named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150BCFB8.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_E8C10.c.o","make-shadow/src/game/generated_E8C10.c.o.compact","make-shadow/src/game/generated_E8C10.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record rebound artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record rebound artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record rebound raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record rebound evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record rebound Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Record rebound expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_E8C10.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record rebound Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record rebound private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record rebound changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record rebound protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
