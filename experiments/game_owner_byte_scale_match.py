"""Owner byte scale: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150C7670','generated_F4B20'
ENTRY,ROM,BODY,SIZE=0x150C7670,0xF4B20,204,204
SOURCE='conker/src/game/generated_F4B20.c'
OBJECT='conker/build/src/game/generated_F4B20.c.o'
ASM='conker/asm/F4B20.s'
BUILD='conker/build/game-owner-byte-scale-match'
RODATA_SYMBOL=None
RAW_SHA='7338d6ce91693b653f5fb7d221fa51527fd673538205683b90f21ff66a8c6219'
SNAPSHOT_SHA='1b14117ad85d7324fca6922034397f28a3c029615c993368e3d400ea116e528f'
BEFORE_ELF_SHA='1ce16ec7808c68d91ffe727a183b4099f94431b85b07209cf6c3e9a614e120b5'
TRUTH_SHA='217bd2d89fb57cc1ae6089f13274ca0af13b8176e8b64a4e58a7ae254d1ddaed'
BINDINGS={40: [('R_MIPS_HI16', 'D_800A04C0')], 44: [('R_MIPS_LO16', 'D_800A04C0')]}
HEADERS='#include <ultra64.h>\n\nextern f32 D_800A04C0;\n\n'
DECLARATIONS='extern f32 D_800A04C0;\n\n'
SELECTED="/* Scale the linked data byte into the owner's output byte. */\ns32 func_150C7670(u8 *owner) {\n    f32 value = (u32)(*(u8 **)(*(u8 **)(owner + 0x170) + 0x14))[0x2F];\n\n    owner[0x70] = (u32)(value * D_800A04C0);\n    return 1;\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner-byte-scale owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner byte scale body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150C7670() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner byte scale placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner byte scale snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner byte scale frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner byte scale predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner byte scale live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner byte scale strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Owner byte scale original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Account for the closed linker ordering change without excluding metadata.
    names=('D_800A749C','D_8009E77C');pairs=[named[n]for n in names]
    if any(len(v)!=1 for v in pairs):raise ValueError('Owner byte scale metadata names changed')
    records=[v[0]for v in pairs]
    if [v[0]for v in records]!=[2820580,2820596]:raise ValueError('Owner byte scale metadata positions changed')
    if [v[1][1]for v in records]!=[0x800A749C,0x8009E77C]:raise ValueError('Owner byte scale metadata definitions changed')
    literal=b''.join(n.encode()+b'\0'for n in names)
    if before.count(literal)!=1 or before.index(literal)!=3096928:raise ValueError('Owner byte scale metadata strings changed')
    pos=before.index(literal);result[pos:pos+len(literal)]=b''.join(n.encode()+b'\0'for n in names[::-1])
    for i,j in enumerate((1,0)):
        destination,fields=records[i];other=records[j][1]
        struct.pack_into('>IIIBBH',result,destination,fields[0],*other[1:])
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner byte scale image differs from body and extent prediction')
    expected=Counter((n,f[1],204 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner byte scale named ELF definitions changed')

def derive_guards():
    # Move the existing success-result setup earlier and retain retail's nop.
    # The only inserted non-nop is the same li v0,1 removed from the old slot.
    rows=[]
    for offset,expected,replacement,inserted in ((4,0x3C014F80,0x3C014F80,'0x24020001'),(188,0x24020001,0,'')):
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Move the existing success result before unsigned conversions and retain the retail nop',insert_after=inserted,insert_after_relocations='-'if inserted else'',omit='false'))
    return rows

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='330d53c8c054bbb18be38dc6d282becece723b8c4c11177bdd04d37bb25b9131':raise ValueError('Owner byte scale inherited guard bytes changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Owner byte scale guards already present')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings)
    if struct.unpack_from('>I',raw,4)[0]!=0x3C014F80 or struct.unpack_from('>I',raw,188)[0]!=0x24020001:raise ValueError('Owner byte scale guarded instructions changed')
    out=bytearray(raw);struct.pack_into('>I',out,188,0);out[8:8]=struct.pack('>I',0x24020001)
    result=bytes(out);relocated={at+4:value for at,value in bindings.items()}
    if len(result)!=204 or sha(result)!='2cf90d8c9259d597783d72619cfc435517ae1e96ed59766e54b9b32e6e8fd141':raise ValueError('Owner byte scale normalized payload changed')
    return result,relocated

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150C7670.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_F4B20.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_F4B20.c.o","make-shadow/src/game/generated_F4B20.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner byte scale artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner byte scale artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner byte scale raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner byte scale evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner byte scale Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_F4B20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner byte scale Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Owner byte scale private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner byte scale changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner byte scale protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=51,frame=0,alignment_words=0,slot_words=51,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
