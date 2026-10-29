"""Byte phase offset: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15131C84','generated_15D730'
ENTRY,ROM,BODY,SIZE=0x15131C84,0x15F134,200,200
SOURCE='conker/src/game/generated_15D730.c'
OBJECT='conker/build/src/game/generated_15D730.c.o'
ASM='conker/asm/15D730.s'
BUILD='conker/build/game-byte-phase-offset-match'
RODATA_SYMBOL=None
RAW_SHA='909d1483c867a7dc9c3f3de5f87bec95709180803439c490a7620c05d3689612'
SNAPSHOT_SHA='2e4d29670fc0d894d75a1136553df70bcf2e504f6f2d51947d2e5538b38f145f'
BEFORE_ELF_SHA='1ff94fdfa879efa06f48b04185843032be078ab7cf312289e8a3e347e25b4093'
TRUTH_SHA='d1e213d664f794ec9c1be945792375c3b578b5deabac87aba7601fb8c1a9a69f'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE9E4')], 12: [('R_MIPS_LO16', 'D_800BE9E4')], 100: [('R_MIPS_26', 'func_151423D8')], 152: [('R_MIPS_26', 'func_151423D8')]}
HEADERS='#include <ultra64.h>\n\nextern s32 D_800BE9E4;\nf32 func_151423D8(u8);\n\n'
DECLARATIONS=""
SELECTED='/* Advance the byte phases, then write their scaled offsets around the base. */\nvoid func_15131C84(u8 *phases, s8 *rates, f32 base, f32 *amplitudes,\n                  f32 *first, f32 *second) {\n    f32 sample;\n\n    phases[0] += rates[0] * (u32)D_800BE9E4;\n    phases[1] += rates[1] * (u32)D_800BE9E4;\n    sample = func_151423D8((u8)(phases[0] - 0x40));\n    *first = sample * amplitudes[0] + base;\n    sample = func_151423D8((u8)(phases[1] - 0x40));\n    *second = sample * amplitudes[1] + base;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected byte-phase-offset owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Byte phase offset body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15131C84() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Byte phase offset placeholder changed')
    return before.replace(stub,SELECTED.strip())



CALLER_SOURCE='conker/src/game/generated_1BF090.c'
CALLER_OBJECT='conker/build/src/game/generated_1BF090.c.o'

def recovered_caller(before):
    declaration='s32 func_15131C84(void *, void *, s32, void *, void *, void *);'
    new_declaration='void func_15131C84(u8 *, s8 *, f32, f32 *, f32 *, f32 *);'
    old_call='    func_15131C84(arg0 + 0xAC, arg0 + 0xAE, *(s32 *)(arg0 + 0xA8),\n                  arg0 + 0xB0, arg0 + 0x38, arg0 + 0x3C);'
    new_call='    func_15131C84(arg0 + 0xAC, (s8 *)(arg0 + 0xAE), *(f32 *)(arg0 + 0xA8),\n                  (f32 *)(arg0 + 0xB0), (f32 *)(arg0 + 0x38), (f32 *)(arg0 + 0x3C));'
    if before.count(declaration)!=1 or before.count(old_call)!=1:raise ValueError('Byte phase caller changed')
    return before.replace(declaration,new_declaration).replace(old_call,new_call)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Byte phase offset snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Byte phase offset frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Byte phase offset predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),CALLER_SOURCE:recovered_caller(values[CALLER_SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Byte phase offset live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Byte phase offset strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Byte phase offset original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Byte phase offset image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Byte phase offset named ELF definitions changed')

def derive_guards():
    """Swap only fs/ft on the two independently checked mul.s words."""
    rows=[]
    for at,word in ((128,0x46002182),(176,0x46008482)):
        assert word>>26==17 and (word>>21)&31==16 and word&63==2
        fs,ft=(word>>11)&31,(word>>16)&31
        replacement=(word&~((31<<11)|(31<<16)))|(fs<<16)|(ft<<11)
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,expected='0x%08X'%word,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize byte phase-offset commutative floating multiply operand order',insert_after='',insert_after_relocations='',omit='false'))
    return rows

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='1678dac601e1def3df3c6438b7a8b4bb0914ce5ef73a929921f12916f7ead9f2':raise ValueError('Byte phase inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Byte phase guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',raw,at)[0]!=int(row['expected'],0)or bindings.get(at):raise ValueError('Byte phase guarded word/binding changed')
        struct.pack_into('>I',out,at,int(row['replacement'],0))
    result=bytes(out)
    if sha(result)!='35c58ca334568ccb9993ec3ba04305fb7d3568b619fe4881f0464877021b2437':raise ValueError('Byte phase normalized body changed')
    return result,bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15131C84.o','first-linked.elf','proposed-caller.c','caller-qualified-padded.o')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_15D730.c.o","make-shadow/src/game/generated_15D730.c.o.padded.s",)

EVIDENCE += tuple(n+suffix for n in ('caller-before','caller-after') for suffix in ('.c','-processed.c','.o','-diagnostics.txt')) + ('caller-Make-plan.txt','caller-Make-commands.json','caller-Make-diagnostics.txt','caller-make-shadow/src/game/generated_1BF090.c.o','caller-make-shadow/src/game/generated_1BF090.c.o.padded.s','caller-screen-v1.json')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Byte phase offset artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Byte phase offset artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Byte phase offset raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Byte phase offset evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Byte phase offset Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_15D730.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Byte phase offset Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Byte phase offset private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Byte phase offset changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Byte phase offset protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=24,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
