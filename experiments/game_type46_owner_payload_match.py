"""Type46 owner payload: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1514D564','generated_179F30'
ENTRY,ROM,BODY,SIZE=0x1514D564,0x17AA14,232,232
SOURCE='conker/src/game/generated_179F30.c'
OBJECT='conker/build/src/game/generated_179F30.c.o'
ASM='conker/asm/179F30.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-type46-owner-payload-1514D564-match'
RODATA_SYMBOL=None
RAW_SHA='7ae59b4903067b9d08e91045d0c3e8a9f93a6520a6c3adb47855b53fdccd4887'
SNAPSHOT_SHA='1c0c2b6ab8d81f6f38c59d0b0b2fdca410d21b28bad9f16de4549fb22b1d0bb4'
BEFORE_ELF_SHA='53557b80979cc40da3e39ad2db57fe828903306b255bbad53e4986d0c8974364'
TRUTH_SHA='5ee10cb65df353ce06b53bf0564c834558aabc4524f538962e784117fe93183a'
BINDINGS={36: [('R_MIPS_HI16', 'D_800A5DE4')], 40: [('R_MIPS_LO16', 'D_800A5DE4')], 44: [('R_MIPS_HI16', 'D_800A5DE8')], 48: [('R_MIPS_LO16', 'D_800A5DE8')], 52: [('R_MIPS_HI16', 'D_800A5DEC')], 60: [('R_MIPS_LO16', 'D_800A5DEC')], 112: [('R_MIPS_HI16', 'D_800A5DF0')], 116: [('R_MIPS_LO16', 'D_800A5DF0')], 160: [('R_MIPS_26', 'func_150C5370')], 192: [('R_MIPS_26', 'memcpy')], 208: [('R_MIPS_26', 'func_1514EC1C')]}
ORIGINAL_BINDINGS={36: [('R_MIPS_HI16', 'D_800A5DE4')], 40: [('R_MIPS_LO16', 'D_800A5DE4')], 44: [('R_MIPS_HI16', 'D_800A5DE8')], 48: [('R_MIPS_LO16', 'D_800A5DE8')], 52: [('R_MIPS_HI16', 'D_800A5DEC')], 60: [('R_MIPS_LO16', 'D_800A5DEC')], 112: [('R_MIPS_HI16', 'D_800A5DF0')], 116: [('R_MIPS_LO16', 'D_800A5DF0')], 160: [('R_MIPS_26', 'func_150C5370')], 192: [('R_MIPS_26', 'memcpy')], 208: [('R_MIPS_26', 'func_1514EC1C')]}
HEADERS='#include <ultra64.h>\n#include <string.h>\ntypedef struct {\n    f32 first[3];\n    f32 second[3];\n    u8 attributes[12];\n} Type46DistancePayload;\n\ntypedef struct {\n    u8 header[0x10];\n    s32 active;\n    s32 state;\n    Type46DistancePayload payload;\n    u8 pad3C[0x84];\n    f32 distance;\n    u32 tail;\n} Type46DistanceRecord;\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\nf32 func_15143E64(f32 *);\n\ntypedef struct {\n    u8 *owner;\n    u8 unique_id;\n    u8 command;\n    u8 pad6[2];\n    f32 zero;\n    f32 lower;\n    f32 upper;\n} OwnerEffectPayload;\ntypedef struct {\n    f32 first[3];\n    f32 second[3];\n    u8 enabled;\n    u8 pad19[3];\n    f32 scale;\n    u8 mode;\n    u8 tail[3];\n} OwnerEffectDescriptor;\nextern f32 D_800A5DE4, D_800A5DE8, D_800A5DEC, D_800A5DF0;\nType46DistanceRecord *func_150C5370(const Type46DistancePayload *, u32);\ns32 func_1514EC1C(s32, s32, s16);\n\n'
DECLARATIONS=''
SELECTED='/* Create a type-0x46 effect, copy captured owner data and submit command 0x15. */\nvoid func_1514D564(u8 *owner) {\n    OwnerEffectDescriptor descriptor;\n    Type46DistanceRecord *record;\n    OwnerEffectPayload payload;\n\n    payload.owner = owner;\n    payload.unique_id = owner[0x3B];\n    payload.command = 6;\n    payload.zero = 0.0f;\n    payload.lower = -180.0f;\n    payload.upper = 77.0f;\n    descriptor.enabled = 1;\n    descriptor.first[0] = D_800A5DE4;\n    descriptor.first[1] = D_800A5DE8;\n    descriptor.first[2] = D_800A5DEC;\n    descriptor.second[0] = *(f32 *)(owner + 0x14);\n    descriptor.second[1] = *(f32 *)(owner + 0x18);\n    descriptor.second[2] = *(f32 *)(owner + 0x1C);\n    descriptor.scale = D_800A5DF0;\n    descriptor.mode = 1;\n    record = func_150C5370((const Type46DistancePayload *)&descriptor, 0x14);\n    if (record != NULL) {\n        memcpy((u8 *)record + 0xC8, &payload, 0x14);\n        func_1514EC1C((s32)record, (s32)owner, 0x15);\n    }\n}\n'

def check_owner_diagnostics(text):
    normalized=re.sub(r'build/[^,]+, line [0-9]+','<owner>',text)
    if normalized!='cfe: Warning 712: <owner>: illegal combination of pointer and integer\n     func_1514EC1C(temp, arg0, 0x14);\n ------------------^\ncfe: Warning 712: <owner>: illegal combination of pointer and integer\n     func_1514EC1C(temp, arg0, 0x14);\n ------------------------^\ncfe: Warning 712: <owner>: illegal combination of pointer and integer\n         func_1514EC1C(temp_v0, arg0, 0x13);\n ----------------------^\ncfe: Warning 712: <owner>: illegal combination of pointer and integer\n         func_1514EC1C(temp_v0, arg0, 0x13);\n -------------------------------^\n':raise ValueError('Type46 owner inherited diagnostics changed')
    return 4


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Type46 owner payload body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_1514D564() {\n    return 0;\n}':raise ValueError('Type46 owner placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('#include <string.h>\n','',1)
    after=before[:a]+declarations+SELECTED.rstrip()+before[b:]
    prefix='#include <ultra64.h>\n'
    if not after.startswith(prefix):raise ValueError('Owner includes changed')
    return prefix+'#include <string.h>\n'+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Type46 owner payload snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Type46 owner payload frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Type46 owner payload predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Type46 owner payload live input differs: '+name)
    return values

METADATA_GROUPS=((0x2A1E04,('D_800A5DE8','D_800A58B8'),(1,0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Type46 owner payload named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Type46 owner payload symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Type46 owner payload metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Type46 owner payload frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Type46 owner payload original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Type46 owner payload strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Type46 owner payload named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Type46 owner payload scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1514D564.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_179F30.c.o', 'make-shadow/src/game/generated_179F30.c.o.compact', 'make-shadow/src/game/generated_179F30.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Type46 owner payload artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type46 owner payload artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type46 owner payload raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Type46 owner payload evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Type46 owner payload Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_179F30.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Type46 owner payload Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Type46 owner payload private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Type46 owner payload changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Type46 owner payload protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=88,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='aed0e4cd810ec80495d0ae68c91267510384590c4c2f64df642ba085c61aed7f'
