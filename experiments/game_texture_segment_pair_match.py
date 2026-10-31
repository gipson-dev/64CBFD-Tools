"""Texture segment pair: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_15133EEC','generated_15F680'
ENTRY,ROM,BODY,SIZE=(353582828, 1446812, 236, 236)
SOURCE='conker/src/game/generated_15F680.c'
OBJECT='conker/build/src/game/generated_15F680.c.o'
ASM='conker/asm/15F680.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-texture-segment-pair-15133EEC-match'
RODATA_SYMBOL=None
RAW_SHA='e3f2dfc45441878a92059209fd8a76159043aa35939f16115af8a19f73533151'
SNAPSHOT_SHA='297c88336589e23d53469e088d4208a3a576a6656d23b815e415bf354184c211'
BEFORE_ELF_SHA='4061e827bfdcdeb8fdb088993a5199851e594ec1779b81441c63cef68f90a4fc'
TRUTH_SHA='1c3ab3c937db0ac9f6a7a11f395ce43c97abae35a18c01a21abf9884afbb0347'
BINDINGS={32: [('R_MIPS_HI16', 'D_80090B60')], 36: [('R_MIPS_LO16', 'D_80090B60')], 88: [('R_MIPS_26', 'func_1510D0EC')]}
ORIGINAL_BINDINGS={32: [('R_MIPS_HI16', 'D_80090B60')], 36: [('R_MIPS_LO16', 'D_80090B60')], 88: [('R_MIPS_26', 'func_1510D0EC')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    s32 *resource;\n    u8 reserved[6];\n    u8 segments;\n    u8 layout;\n} TextureSegmentRecord15F680;\nextern TextureSegmentRecord15F680 D_80090B60[];\nu32 func_1510D0EC(s32, s32 *, s32, s32);\n'
DECLARATIONS='typedef struct {\n    s32 *resource;\n    u8 reserved[6];\n    u8 segments;\n    u8 layout;\n} TextureSegmentRecord15F680;\nextern TextureSegmentRecord15F680 D_80090B60[];\nu32 func_1510D0EC(s32, s32 *, s32, s32);\n'
SELECTED='/* Load a texture resource and append its one or two segment bindings. */\nGfx *func_15133EEC(Gfx *cursor, u16 index, u8 segment, s32 priority) {\n    s32 resource;\n    u8 segments;\n    u8 layout;\n    u32 address;\n    s32 extent;\n\n    resource = *D_80090B60[index].resource;\n    segments = D_80090B60[index].segments;\n    layout = D_80090B60[index].layout;\n    address = func_1510D0EC(resource, &extent, priority, 0);\n    gSPSegment(cursor++, segment, address);\n    if (segments == 2) {\n        gSPSegment(cursor++, segment + 1,\n                   address + extent - (layout == 1 ? 0x200 : 0x20));\n    }\n    return cursor;\n}\n'

def check_owner_diagnostics(text):
    if re.sub(r'build/[^,]+, line [0-9]+','<owner>',text)!='cfe: Warning 712: <owner>: illegal combination of pointer and integer\n             func_100043B4(arg0->entries[i], 4);\n ---------------------------------------^\ncfe: Warning 712: <owner>: illegal combination of pointer and integer\n         func_100043B4(arg0->trailing, 4);\n --------------------------^\n':raise ValueError('Inherited texture owner diagnostics changed')
    return 2



sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Texture segment pair body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15133EEC() {\n    return 0;\n}':raise ValueError('Texture segment placeholder changed')
 result=before[:a]+SELECTED.rstrip()+before[b:]
 if result.count('s32 func_15133EEC();')!=1 or result.count('func_15133EEC(arg0,')!=3:raise ValueError('Texture segment caller preimage changed')
 result=result.replace('s32 func_15133EEC();',DECLARATIONS+'Gfx *func_15133EEC(Gfx *, u16, u8, s32);',1)
 return result.replace('func_15133EEC(arg0,','func_15133EEC((Gfx *)arg0,').replace('arg0 = func_15133EEC((Gfx *)arg0,','arg0 = (s32)func_15133EEC((Gfx *)arg0,')




def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Texture segment pair snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Texture segment pair frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Texture segment pair predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Texture segment pair live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Texture segment pair named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Texture segment pair symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Texture segment pair metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Texture segment pair frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Texture segment pair original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Texture segment pair strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Texture segment pair named definitions changed')

NEW_GUARDS=[]
def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Attached effect scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15133EEC.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_15F680.c.o', 'make-shadow/src/game/generated_15F680.c.o.compact', 'make-shadow/src/game/generated_15F680.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Texture segment pair artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Texture segment pair artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Texture segment pair raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Texture segment pair evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Texture segment pair Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_15F680.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Texture segment pair Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Texture segment pair private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Texture segment pair changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Texture segment pair protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=64,alignment_words=0,slot_words=57,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='74fd8cbc1df3f5a9e34d214eca652a15d6b23aa5e7eed694f83a6fee23887744'
