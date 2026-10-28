"""Quad setup wrapper: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15171F04','generated_19F150'
ENTRY,ROM,BODY,SIZE=0x15171F04,0x19F3B4,188,188
SOURCE='conker/src/game/generated_19F150.c'
OBJECT='conker/build/src/game/generated_19F150.c.o'
ASM='conker/asm/19F150.s'
BUILD='conker/build/game-record-setup-wrapper-match'
RAW_SHA="d5b5648741e5b5c7d0eecc7d10beff2a773e4ca5d191d022ae427ee5723f4b4e"
SNAPSHOT_SHA="0d538cff548020c50a1cfd106a055a99a6d53ee6d67464488eaf6ee91e3b3dda"
BEFORE_ELF_SHA="62095f23df6993e6bdd474197951164e05d56cc37b827318dc414c1b5975e664"
TRUTH_SHA="85e3c2a6931cbe452d51248dd4b9ee1342ef67fa3ad0eff4cca7b5e470604beb"
TABLE,CONSTRUCTOR,GEOMETRY,FREE=0x8008CA4C,0x15171CA0,0x151725FC,0x1516972C
ALLOC,QUERY=0x15167A68,0x1510E388
PROVIDER_RAW=bytes.fromhex("afa40000afa50004afa60008afa7000c0000102503e0000800000000")
BINDINGS={68:[("R_MIPS_26","func_15171CA0")],112:[("R_MIPS_HI16","D_8008CA4C")],128:[("R_MIPS_LO16","D_8008CA4C")],148:[("R_MIPS_26","func_151725FC")],164:[("R_MIPS_26","func_1516972C")]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="typedef struct {\n    u8 opaque0[0x10];\n    Vtx vertices[4];\n    s16 lifetime;\n    s16 frame;\n    s16 frameStep;\n    u16 color;\n    u8 imageIndex;\n    u8 flags;\n    u8 opaque5A[6];\n} QuadEffect19F150;\n\nvoid *func_15171CA0(s16, u16, u8, s32, s32, s32, u8, s32);\nextern u8 *D_8008CA4C[];\ns32 func_151725FC(Vtx *, void *, f32, f32, f32, f32, s32, u8);\nvoid func_1516972C(struct102 *);\n\n"
SELECTED="/* Allocate an animated quad, build its vertices, and release it if geometry setup fails. */\nvoid func_15171F04(f32 x, f32 y, f32 z, void *indirectVertices,\n                   s16 lifetime, u16 color, u8 imageIndex, s32 scale,\n                   s32 flags, s32 frameStep, s32 alternate, u8 slot, s32 context) {\n    QuadEffect19F150 *record;\n\n    record = func_15171CA0(lifetime, color, imageIndex, flags,\n                          frameStep, alternate, slot, context);\n    if (record != NULL) {\n        if (func_151725FC(record->vertices, indirectVertices, x, y, z, 0.0f,\n                         scale, *(u16 *)(D_8008CA4C[record->imageIndex] + 6)) == 0) {\n            func_1516972C((struct102 *)record);\n        }\n    }\n}"
PROVIDER_STUB="s32 func_151725FC(Vtx *vertices, void *indirectVertices, f32 x, f32 y, f32 z,\n                   f32 rotation, s32 scale, u8 imageControl) {\n    return 0;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Quad setup wrapper body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15171F04() {\n    return 0;\n}'
    provider='s32 func_151725FC() {\n    return 0;\n}'
    if before.count(stub)!=1 or before.count(provider)!=1:raise ValueError('Quad setup placeholders changed')
    declarations=DECLARATIONS[DECLARATIONS.index('extern u8 *D_8008CA4C[];'):]
    return before.replace('#include <ultra64.h>','#include <ultra64.h>'+chr(10)+'#include "structs.h"',1).replace(stub,declarations+SELECTED,1).replace(provider,PROVIDER_STUB,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Quad setup wrapper snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Quad setup wrapper frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Quad setup wrapper predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Quad setup wrapper live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Quad setup wrapper strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Quad setup wrapper original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    at=elf_slot_offset(before,GEOMETRY,len(PROVIDER_RAW));result[at:at+len(PROVIDER_RAW)]=PROVIDER_RAW
    provider=[p for p,n,f,_ in symbol_rows(before)if n=='func_151725FC'and f[1:3]==(GEOMETRY,12)];assert len(provider)==1;struct.pack_into('>I',result,provider[0]+8,len(PROVIDER_RAW))
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Quad setup wrapper image differs from body and extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else 28 if n=='func_151725FC'else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Quad setup wrapper named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15171F04.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_19F150.c.o","make-shadow/src/game/generated_19F150.c.o.compact","make-shadow/src/game/generated_19F150.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Quad setup wrapper artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Quad setup wrapper artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Quad setup wrapper raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Quad setup wrapper evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Quad setup wrapper Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Quad setup wrapper expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_19F150.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Quad setup wrapper Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Quad setup wrapper private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or set(n for n in a if a[n]!=b[n])!={FUNCTION,'func_151725FC'}:raise ValueError('Quad setup wrapper changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Quad setup wrapper protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-2,all_addresses_fixed=True,target_words=47,typed_provider_stub_words=7,provider_matching_credit=0,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
