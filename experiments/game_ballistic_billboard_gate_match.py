"""Ballistic billboard motion gate: direct C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_1514AF74','generated_176A00'
ENTRY,ROM,BODY,SIZE=0x1514AF74,0x178424,192,192
SOURCE='conker/src/game/generated_176A00.c'
OBJECT='conker/build/src/game/generated_176A00.c.o'
ASM='conker/asm/176A00.s'
BUILD='conker/build/game-ballistic-billboard-gate-match'
RAW_SHA="8112df3b7e4f877bf49a0a730270b565b7248c21834ec8db2c2ea5f85e095d65"
SNAPSHOT_SHA="93cf00aba109a2af8a69ab226508270f8ac39a4a3c9b7165583d3a8d8ef1ad01"
BEFORE_ELF_SHA="a901623f145f33570885caaa08107f880fb7ab95eab873ab53d16c88eebbfa9c"
TRUTH_SHA="7c91c55a5ca9b6c6a7533dab46ec22ce7d2de18219ca11cbcae58b9d18707cf3"
CALLER,TABLE,TIME,TICKS=0x1513CFE4,0x80089D60,0x800BE9A4,0x800BE9E4
BINDINGS={0:[('R_MIPS_HI16','D_800BE9A4')],4:[('R_MIPS_LO16','D_800BE9A4')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern f32 D_800BE9A4;\n\n"
SELECTED="/* Damp billboard extents and integrate position before advancing vertical velocity. */\ns32 func_1514AF74(u8 *actor) {\n    *(f32 *)(actor + 0x2C) -= *(f32 *)(actor + 0x2C) * *(f32 *)(actor + 0x150);\n    *(f32 *)(actor + 0x30) -= *(f32 *)(actor + 0x30) * *(f32 *)(actor + 0x150);\n    *(f32 *)(actor + 0x38) += *(f32 *)(actor + 0x50) * D_800BE9A4 +\n        0.5f * *(f32 *)(actor + 0x4C) * D_800BE9A4 * D_800BE9A4;\n    *(f32 *)(actor + 0x50) += *(f32 *)(actor + 0x4C) * D_800BE9A4;\n    if (*(f32 *)(actor + 0x2C) < 10.0f || *(f32 *)(actor + 0x30) < 10.0f) {\n        return 0;\n    }\n    return 1;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Ballistic billboard motion gate body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1514AF74() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Ballistic motion placeholder changed')
    return before.replace(stub,SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Ballistic billboard motion gate snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Ballistic billboard motion gate frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Ballistic billboard motion gate predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Ballistic billboard motion gate live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Ballistic billboard motion gate strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Ballistic billboard motion gate original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Ballistic billboard motion gate image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Ballistic billboard motion gate named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1514AF74.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_176A00.c","make-shadow/src/game/generated_176A00.c.o","make-shadow/src/game/generated_176A00.c.o.compact","make-shadow/src/game/generated_176A00.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Ballistic billboard motion gate artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ballistic billboard motion gate artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ballistic billboard motion gate raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Ballistic billboard motion gate evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ballistic billboard motion gate Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    diagnostics=[(output/(n+'-diagnostics.txt')).read_text()for n in('before-owner','after-owner')];normalize=lambda s:re.sub(r'[^ \n]+-owner.c, line [0-9]+:','OWNER.c, line N:',s)
    if any(x.count('Warning 712:')!=1 or 'func_1514BF50(arg0);'not in x for x in diagnostics)or normalize(diagnostics[0])!=normalize(diagnostics[1]):raise ValueError('Existing owner diagnostics changed')
    diag=(output/'actual-Make-diagnostics.txt').read_text()
    if diag.count('Warning 712:')!=1 or 'func_1514BF50(arg0);'not in diag:raise ValueError('Actual Make diagnostics changed')
    if(output/'make-shadow/src/game/generated_176A00.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Ballistic billboard motion gate Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Ballistic billboard motion gate private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Ballistic billboard motion gate changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Ballistic billboard motion gate protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
