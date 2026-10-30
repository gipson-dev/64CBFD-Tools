"""Owner lifetime descriptor: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151AE7B0','generated_1D92F0'
ENTRY,ROM,BODY,SIZE=0x151AE7B0,0x1DBC60,224,224
SOURCE='conker/src/game/generated_1D92F0.c'
OBJECT='conker/build/src/game/generated_1D92F0.c.o'
ASM='conker/asm/1D92F0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-duration-descriptor-151AE7B0-match'
RODATA_SYMBOL=None
RAW_SHA='6b567d46838f59df37ef9be033469a24b4ddbeaa6c180f3dd9e7542eaefa4767'
SNAPSHOT_SHA='bc94dd2630b3c8e82e6dafc75fc585b801f442bdbc097c2dbc619ebd73bf8373'
BEFORE_ELF_SHA='3644a879a659abc0865a85770d7ab5aad6508a52af60821523bc026d6da0c314'
TRUTH_SHA='7a5a61afc29c03c41711d9aece7a0e78ee37750542b90aa715a59ffcb92e58f6'
BINDINGS={48: [('R_MIPS_26', 'func_1516962C')], 80: [('R_MIPS_HI16', 'D_800A9D80')], 84: [('R_MIPS_LO16', 'D_800A9D80')], 200: [('R_MIPS_26', 'func_1513418C')]}
ORIGINAL_BINDINGS={48: [('R_MIPS_26', 'func_1516962C')], 80: [('R_MIPS_HI16', 'D_800A9D80')], 84: [('R_MIPS_LO16', 'D_800A9D80')], 200: [('R_MIPS_26', 'func_1513418C')]}
HEADERS='#include <ultra64.h>\n\ntypedef struct {\n    u32 zero0, zero4;\n    u8 ownerIdentity, reserved09[3];\n    u8 *owner;\n    u8 attachment, reserved11[3];\n    f32 vector[3];\n    f32 value20, value24;\n    s16 duration;\n    u8 flags, kind;\n    s8 callback;\n    u8 mode;\n} OwnerEffectDescriptor1D92F0;\n\nextern f32 D_800A9DCC, D_800A9DD0;\nvoid func_1516962C(s32, void *, u8);\nvoid *func_1513418C(void *, s32, u8, s32);\n\nextern f32 D_800A9D80;\n\n'
DECLARATIONS='extern f32 D_800A9D80;\n\n'
SELECTED='/* Notify the owner, then submit an attached effect with the selected lifetime. */\nvoid *func_151AE7B0(u8 *owner, f32 scale, s16 duration, u8 selector, s32 category) {\n    void *created;\n    OwnerEffectDescriptor1D92F0 descriptor;\n\n    if (owner == NULL) {\n        return NULL;\n    }\n    func_1516962C(40, owner, 17);\n    descriptor.zero0 = 0;\n    descriptor.zero4 = 0;\n    descriptor.ownerIdentity = owner[0x3B];\n    descriptor.owner = owner;\n    descriptor.attachment = 1;\n    descriptor.vector[0] = 0.0f;\n    descriptor.vector[1] = 0.0f;\n    descriptor.vector[2] = 0.0f;\n    descriptor.value20 = D_800A9D80;\n    descriptor.value24 = scale;\n    descriptor.flags = 2;\n    if (duration != 0) {\n        descriptor.duration = duration;\n        descriptor.flags = 6;\n    } else {\n        descriptor.duration = 300;\n    }\n    descriptor.kind = 6;\n    descriptor.callback = -1;\n    descriptor.mode = 5;\n    created = func_1513418C(&descriptor, 0, selector, category);\n    return created;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected effect motion limit diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner lifetime descriptor body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 start=before.index('typedef struct {\n    u32 zero0, zero4;');end=before.index('/* Notify the owner before constructing',start);common=before[start:end]
 if 'OwnerEffectDescriptor1D92F0'not in common or 'func_1513418C'not in common:raise ValueError('Existing descriptor declaration block changed')
 base=before[:start]+before[end:];a,b=function_span(base,FUNCTION)
 if base[a:b]!='s32 func_151AE7B0() {\n    return 0;\n}':raise ValueError('Owner lifetime placeholder changed')
 return base[:a]+common+DECLARATIONS+SELECTED.rstrip()+base[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner lifetime descriptor snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner lifetime descriptor frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner lifetime descriptor predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner lifetime descriptor live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner lifetime descriptor named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner lifetime descriptor symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner lifetime descriptor metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner lifetime descriptor frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner lifetime descriptor original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner lifetime descriptor strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner lifetime descriptor named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA or NEW_GUARDS:raise ValueError('Owner lifetime guard history changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Owner lifetime scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151AE7B0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1D92F0.c.o', 'make-shadow/src/game/generated_1D92F0.c.o.compact', 'make-shadow/src/game/generated_1D92F0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner lifetime descriptor artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner lifetime descriptor artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner lifetime descriptor raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner lifetime descriptor evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner lifetime descriptor Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1D92F0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner lifetime descriptor Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Owner lifetime descriptor private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner lifetime descriptor changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner lifetime descriptor protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=80,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0c0fdc83e5c9c7e79fe0a42948f67f2687f496d3cf5989cb72a113f3429e872b'
