"""Owner phase pair: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15108AB4','generated_135D00'
ENTRY,ROM,BODY,SIZE=0x15108AB4,0x135F64,204,204
SOURCE='conker/src/game/generated_135D00.c'
OBJECT='conker/build/src/game/generated_135D00.c.o'
ASM='conker/asm/135D00.s'
BUILD='conker/build/game-owner-phase-pair-match'
RODATA_SYMBOL=None
RAW_SHA='e10684cfe0226bfc64fb5fc0ed076a9c9bb8dfbe80dc441b1dfc771d1ba526f5'
SNAPSHOT_SHA='4ca31625b032fc1cd12024675a91b100ea4893cb3dd8ba58e76a1639613f3261'
BEFORE_ELF_SHA='e6af63004a57758664ba2af2ea3c311eda2a1be40ec2e3582f25407415674050'
TRUTH_SHA='77dc18cf8fb38007ce8c7696d44f424c84266b3941455ab8f11474ab5d26d8b0'
BINDINGS={4: [('R_MIPS_HI16', 'D_800BE9A4')], 8: [('R_MIPS_LO16', 'D_800BE9A4')], 20: [('R_MIPS_HI16', 'D_800A2470')], 24: [('R_MIPS_LO16', 'D_800A2470')], 36: [('R_MIPS_HI16', 'D_800A2474')], 72: [('R_MIPS_LO16', 'D_800A2474')], 92: [('R_MIPS_26', 'func_15144B68')], 104: [('R_MIPS_26', 'func_15144B68')], 116: [('R_MIPS_26', 'sinf')], 124: [('R_MIPS_HI16', 'D_800A2478')], 128: [('R_MIPS_LO16', 'D_800A2478')], 140: [('R_MIPS_26', 'sinf')], 148: [('R_MIPS_HI16', 'D_800A247C')], 152: [('R_MIPS_LO16', 'D_800A247C')], 164: [('R_MIPS_26', 'func_15108B80')], 172: [('R_MIPS_26', 'func_15108BC0')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800BE9A4;\nextern f32 D_800A2470, D_800A2474, D_800A2478, D_800A247C;\nf32 func_15144B68(f32);\nf32 sinf(f32);\nvoid func_15108B80(u8 *);\nvoid func_15108BC0(u8 *);\n\n'
DECLARATIONS='extern f32 D_800BE9A4;\nextern f32 D_800A2470, D_800A2474, D_800A2478, D_800A247C;\nf32 func_15144B68(f32);\nf32 sinf(f32);\nvoid func_15108B80(u8 *);\nvoid func_15108BC0(u8 *);\n\n'
SELECTED='/* Advance the two phases and derive their sine-scaled offsets.\n * Refresh the owner timer and lookup value, then keep the callback active. */\ns32 func_15108AB4(u8 *owner) {\n    f32 *delta = &D_800BE9A4;\n    f32 *state = (f32 *)(owner + *(s32 *)(owner + 0x50) + 0xF8);\n\n    state[2] += D_800A2470 * *delta;\n    state[3] += D_800A2474 * *delta;\n    state[2] = func_15144B68(state[2]);\n    state[3] = func_15144B68(state[3]);\n    state[0] = sinf(state[2]) * D_800A2478;\n    state[1] = sinf(state[3]) * D_800A247C;\n    func_15108B80(owner);\n    func_15108BC0(owner);\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected phase-pair owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=204 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner phase pair body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15108AB4() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner phase pair placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner phase pair snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner phase pair frozen input changed: '+name)
        values[name]=b
    extra=(output/'caller-inputs.json').read_bytes()
    if sha(extra)!='1e64a7acbd74f76737aac3a914433f70b047f75acf71480a42373df12dfb1582':raise ValueError('Caller snapshot changed')
    for name,wanted in json.loads(extra).items():
        b=(output/('caller-before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted or(name in values and values[name]!=b):raise ValueError('Caller frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner phase pair predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={CALLER_SOURCE:recovered_caller(values[CALLER_SOURCE].decode()).encode(),'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner phase pair live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Phase-pair frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Phase-pair old extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # The added references swap one existing linker symbol bucket. Reconstruct
    # its exact serialized definitions and names from the checked predecessor.
    named={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    names=('D_80099814','D_8009EE64');rows=[named[n]for n in names]
    for name,(pos,fields,loc),position,location,section in zip(names,rows,(2917604,2917620),(3176542,3176553),(65521,6)):
        if pos!=position or loc!=location or fields!=(161962+11*names.index(name),int(name[2:],16),0,16,0,section) or before[loc:loc+11]!=name.encode()+b'\0':raise ValueError('Phase-pair symbol bucket changed: '+name)
    for destination,origin,name in((rows[0],rows[1],names[1]),(rows[1],rows[0],names[0])):
        result[destination[0]:destination[0]+16]=before[origin[0]:origin[0]+16]
        struct.pack_into('>I',result,destination[0],destination[1][0]);result[destination[2]:destination[2]+11]=name.encode()+b'\0'
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner phase pair strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner phase pair named definitions changed')

def derive_guards():
    expected,replacement=0x01C48021,0x008E8021
    # ADDU is commutative modulo 2^32; only rs and rt exchange places.
    assert expected&0xFC00FFFF==replacement&0xFC00FFFF==0x8021
    assert (expected>>21&31,expected>>16&31)==(replacement>>16&31,replacement>>21&31)==(14,4)
    return [dict(filename=OWNER,function=FUNCTION,offset='0x02C',expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Preserve retail operand order for commutative unsigned owner-address addition',insert_after='',insert_after_relocations='',omit='false')]

NEW_GUARDS=derive_guards()

def guard_manifest(before):
    import csv,io
    if sha(before)!='82a037c271b5f3a9f248316290dcb31008db70397b5ec399ebc415cdd6bd8f3a':raise ValueError('Inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Phase-pair already patched')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    if struct.unpack_from('>I',out,44)[0]!=0x01C48021 or 44 in bindings:raise ValueError('ADDU guard precondition changed')
    struct.pack_into('>I',out,44,0x008E8021)
    if sha(out)!='a30a36903230ad4922e395bf5e950f91d1793d8b11f01f804ab2014d8ff6e211':raise ValueError('Phase-pair normalized body changed')
    return bytes(out),bindings



ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15108AB4.o','first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'selected-input.c', 'proposed-caller.c', 'Make-commands.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'before-caller.c', 'before-caller-processed.c', 'before-caller.o', 'before-caller-diagnostics.txt', 'after-caller.c', 'after-caller-processed.c', 'after-caller.o', 'after-caller-diagnostics.txt', 'selected.c', 'selected-processed.c', 'selected.o', 'selected-diagnostics.txt', 'actual-Make-owner-plan.txt', 'actual-Make-owner-diagnostics.txt', 'make-shadow/src/game/generated_135D00.c.o', 'make-shadow/src/game/generated_135D00.c.o.compact', 'make-shadow/src/game/generated_135D00.c.o.padded.s', 'actual-Make-caller-plan.txt', 'actual-Make-caller-diagnostics.txt', 'make-shadow/src/game_168A90.c.o', 'make-shadow/src/game_168A90.c.o.compact', 'make-shadow/src/game_168A90.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner phase pair artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner phase pair artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner phase pair raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner phase pair evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner phase pair Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make-owner'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_135D00.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner phase pair Make object differs')
    if(output/'make-shadow/src/game_168A90.c.o').read_bytes()!=snapshot(output)[CALLER_OBJECT]:raise ValueError('Caller Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=1 or q['exclusions']!=0:raise ValueError('Owner phase pair private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner phase pair changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner phase pair protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=32,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=1,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

CALLER_SOURCE='conker/src/game_168A90.c'
CALLER_OBJECT='conker/build/src/game_168A90.c.o'
CALLER=0x1513B798

def recovered_caller(before):
    if before.count('extern s32 (*D_80089C18[])();')!=1 or before.count('D_80089C18[callbackIndex]()')!=1:raise ValueError('Caller interface changed')
    return before.replace('extern s32 (*D_80089C18[])();','extern s32 (*D_80089C18[])(u8 *);').replace('D_80089C18[callbackIndex]()','D_80089C18[callbackIndex](arg0)')
