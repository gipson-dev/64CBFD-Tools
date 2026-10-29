"""Record timer update: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150A019C','generated_CD5A0'
ENTRY,ROM,BODY,SIZE=0x150A019C,0xCD64C,200,200
SOURCE='conker/src/game/generated_CD5A0.c'
OBJECT='conker/build/src/game/generated_CD5A0.c.o'
ASM='conker/asm/CD5A0.s'
BUILD='conker/build/game-record-timer-update-match'
RODATA_SYMBOL=None
RAW_SHA='6d693f3f57972620bdb00204a56844b6bb578c32633e008b3a2ee4ff1b7295cc'
SNAPSHOT_SHA='801525150976d1e556553f11a413ab33762ac5184fab1e556ea52c21d0b5f716'
BEFORE_ELF_SHA='3207865bdc54d4a01f11b5043641e90d19191bc2d09755d6ad6ba419693ca585'
TRUTH_SHA='21aea7f2baa711c81d46743117b018df83184e2f2363094a63ca5a2f9882277f'
BINDINGS={0: [('R_MIPS_HI16', 'D_800D3010')], 36: [('R_MIPS_LO16', 'D_800D3010')], 4: [('R_MIPS_HI16', 'D_800D3010')], 32: [('R_MIPS_LO16', 'D_800D3010')], 8: [('R_MIPS_HI16', 'D_8008851C')], 28: [('R_MIPS_LO16', 'D_8008851C')], 12: [('R_MIPS_HI16', 'D_80088510')], 24: [('R_MIPS_LO16', 'D_80088510')], 16: [('R_MIPS_HI16', 'D_800BE9E4')], 20: [('R_MIPS_LO16', 'D_800BE9E4')]}
RETAIL_BINDINGS={16: [('R_MIPS_HI16', 'D_800BE9E4')], 20: [('R_MIPS_LO16', 'D_800BE9E4')], 12: [('R_MIPS_HI16', 'D_80088510')], 24: [('R_MIPS_LO16', 'D_80088510')], 8: [('R_MIPS_HI16', 'D_8008851C')], 28: [('R_MIPS_LO16', 'D_8008851C')], 4: [('R_MIPS_HI16', 'D_800D3088')], 32: [('R_MIPS_LO16', 'D_800D3088')], 0: [('R_MIPS_HI16', 'D_800D3010')], 36: [('R_MIPS_LO16', 'D_800D3010')]}
HEADERS='#include <ultra64.h>\ntypedef union {\n    struct {\n        u8 status;\n        u8 pad1[3];\n    } bytes;\n    struct {\n        u32 active:1;\n        u32 running:1;\n        u32 kind:4;\n        u32 reserved:26;\n    } timer;\n    u32 word;\n} GeneratedCD5A0Flags;\n\ntypedef struct {\n    GeneratedCD5A0Flags flags;\n    u32 value;\n    u32 unk8;\n} GeneratedCD5A0Record;\nextern GeneratedCD5A0Record D_800D3010[10];\nextern u16 D_80088510[];\nextern u16 D_8008851C[];\nextern s32 D_800BE9E4;\n'
OLD_TYPE='typedef struct {\n    u8 status;\n    u8 pad1[3];\n    s32 value;\n    s32 unk8;\n} GeneratedCD5A0Record;'
NEW_TYPE='typedef union {\n    struct {\n        u8 status;\n        u8 pad1[3];\n    } bytes;\n    struct {\n        u32 active:1;\n        u32 running:1;\n        u32 kind:4;\n        u32 reserved:26;\n    } timer;\n    u32 word;\n} GeneratedCD5A0Flags;\n\ntypedef struct {\n    GeneratedCD5A0Flags flags;\n    u32 value;\n    u32 unk8;\n} GeneratedCD5A0Record;'
DECLARATIONS='extern u16 D_80088510[];\nextern u16 D_8008851C[];\nextern s32 D_800BE9E4;\n'
SELECTED='/* Advance enabled timer records, consuming at most one period per update. */\nvoid func_150A019C(void) {\n    u32 limit;\n    GeneratedCD5A0Record *record;\n    s32 index;\n\n    for (index = 0; index < 10; index++) {\n        record = &D_800D3010[index];\n        if (record->flags.timer.active && record->flags.timer.running == 1) {\n            record->unk8 += (u32)D_800BE9E4;\n            if (record->unk8 >= D_80088510[record->flags.timer.kind]) {\n                record->unk8 -= D_80088510[record->flags.timer.kind];\n                record->value++;\n                if ((limit = D_8008851C[record->flags.timer.kind]) != 0) {\n                    record->value %= limit;\n                }\n            }\n        }\n    }\n}\n'
CALLER_SOURCE='conker/src/game_45B80.c'
CALLER_OBJECT='conker/build/src/game_45B80.c.o'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record-timer-update owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=200 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record timer update body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    if before.count(OLD_TYPE)!=1 or before.count('s32 '+FUNCTION+'() {\n    return 0;\n}')!=1:raise ValueError('Record timer placeholder/type changed')
    after=before.replace(OLD_TYPE,NEW_TYPE).replace('.status','.flags.bytes.status').replace('->status','->flags.bytes.status').replace('(*(u32 *) record >> 31)','(record->flags.word >> 31)')
    after=after.replace('/* Non-matching placeholders for the text-only asm slice asm/CD5A0.s. */','/* Packed timer records from the retail CD5A0 code slice. */')
    return after.replace('s32 '+FUNCTION+'() {\n    return 0;\n}',DECLARATIONS+'\n'+SELECTED.strip())

def recovered_caller(before):
    old='s32  func_150A019C(void);'
    if before.count(old)!=1:raise ValueError('Record timer caller declaration changed')
    return before.replace(old,'void func_150A019C(void);')


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record timer update snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record timer update frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record timer update predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),CALLER_SOURCE:recovered_caller(values[CALLER_SOURCE].decode()).encode(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record timer update live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record timer update strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Record timer update original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Closed GNU symbol/string ordering change; named definitions stay identical.
    names=('D_80088510','D_800D9910');pairs=[named[n]for n in names]
    if any(len(v)!=1 for v in pairs):raise ValueError('Timer metadata names changed')
    records=[v[0]for v in pairs]
    if [v[0]for v in records]!=[0x2A8B34,0x2A8B44]:raise ValueError('Timer metadata positions changed')
    literal=b''.join(n.encode()+b'\0'for n in names)
    if before.count(literal)!=1:raise ValueError('Timer metadata string block changed')
    pos=before.index(literal);result[pos:pos+len(literal)]=b''.join(n.encode()+b'\0'for n in names[::-1])
    for i,j in enumerate((1,0)):
        destination,fields=records[i];other=records[j][1]
        struct.pack_into('>IIIBBH',result,destination,fields[0],*other[1:])
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record timer update image differs from body and extent prediction')
    expected=Counter((n,f[1],200 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record timer update named ELF definitions changed')

NEW_GUARDS=[(4, 1007353856, 1007353856, 'R_MIPS_HI16:D_800D3010', 'R_MIPS_HI16:D_800D3088'), (32, 627769464, 627769344, 'R_MIPS_LO16:D_800D3010', 'R_MIPS_LO16:D_800D3088')]
def guard_manifest(before):
    if sha(before)!='efd6bd3f1e7efba51b4b566abfd447477133a8a52daa3804bc7550b32d273293':raise ValueError('Inherited guard bytes changed')
    rows=[]
    for offset,expected,replacement,old,new in NEW_GUARDS:
        note='Bind the ten-record one-past address to its retail end label'if offset<40 else'Preserve the independent elapsed and value store order'
        rows.append(','.join((OWNER,FUNCTION,'0x%03X'%offset,'0x%08X'%expected,'0x%08X'%replacement,old,new,note,'','','false')))
    return before+('\r\n'.join(rows)+'\r\n').encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw);rs=dict(bindings)
    for offset,expected,replacement,old,new in NEW_GUARDS:
        if struct.unpack_from('>I',raw,offset)[0]!=expected:raise ValueError('Timer normalization input changed')
        struct.pack_into('>I',result,offset,replacement)
        if new!='-':kind,symbol=new.split(':');rs[offset]=[(kind,symbol)]
    if rs!=RETAIL_BINDINGS or sha(result)!='f27cfc3e0671403e3902da4d8105db0f03ce4164b34a1ff784da3aa044c220b7':raise ValueError('Timer normalization differs from original')
    return bytes(result),rs

ARTIFACTS=('proposed-caller.c','caller-before.o','caller-after.o','caller-qualified.o','before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150A019C.o','first-linked.elf')
EVIDENCE=('caller-before.c','caller-before-processed.c','caller-before-diagnostics.txt','caller-after.c','caller-after-processed.c','caller-after-diagnostics.txt',"proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_CD5A0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_CD5A0.c.o","make-shadow/src/game/generated_CD5A0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record timer update artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record timer update artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record timer update raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record timer update evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record timer update Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_CD5A0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record timer update Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=2 or q['exclusions']!=0:raise ValueError('Record timer update private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record timer update changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record timer update protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=50,frame=0,alignment_words=0,slot_words=50,strict_first_link_reproduced=True,guards=2,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
