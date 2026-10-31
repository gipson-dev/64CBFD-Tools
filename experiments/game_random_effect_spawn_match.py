"""Random effect spawn: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_1500F290','generated_3C740'
ENTRY,ROM,BODY,SIZE=0x1500F290,0x3C740,232,232
SOURCE='conker/src/game/generated_3C740.c'
OBJECT='conker/build/src/game/generated_3C740.c.o'
ASM='conker/asm/3C740.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-random-effect-spawn-1500F290-match'
RODATA_SYMBOL=None
RAW_SHA='952aff5ed0fcbd9d737fe89f770b0ffd5f3ccc042cacfda40825bc82255f4aac'
SNAPSHOT_SHA='739ac54c8a2ef1530cdd7629671e94ef8a0741fbf955eb58539e09d8956e6f2b'
BEFORE_ELF_SHA='70fc05b39428ac0ff6578abc95e199defeb4e1c2938845a2d1ed2526f30dbeba'
TRUTH_SHA='a4d767b565b1d290de22ef17ff79e41fb76369c2f74cade6580d35ad2e583bf5'
BINDINGS={28: [('R_MIPS_26', 'func_151EF610')], 208: [('R_MIPS_26', 'func_1513C5B0')]}
ORIGINAL_BINDINGS={28: [('R_MIPS_26', 'func_151EF610')], 208: [('R_MIPS_26', 'func_1513C5B0')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct {\n    u32 flags;\n    s16 count;\n    u8 category;\n    u8 pad7;\n    s32 zero;\n    s32 phase;\n    u8 color[6];\n    u8 pad16[2];\n    u32 mode;\n    u8 pad1C[12];\n} RandomEffectDescriptor;\ns32 func_151EF610(void);\nstruct210 *func_1513C5B0(s32, s32, u8, u8, f32, f32, f32, f32, f32, u8, u8, s32, u8, s32);\n\n'
DECLARATIONS=''
SELECTED='/* Spawn an effect with a signed random phase and fixed dimensions. */\nstruct210 *func_1500F290(f32 x, f32 y, f32 z) {\n    RandomEffectDescriptor descriptor;\n    s32 random;\n\n    descriptor.category = 0x38;\n    descriptor.zero = 0;\n    random = func_151EF610();\n    descriptor.phase = random % 0x1000 + 0x4000;\n    descriptor.flags = 0x20014;\n    descriptor.count = 1;\n    descriptor.color[0] = 255;\n    descriptor.color[1] = 255;\n    descriptor.color[2] = 0;\n    descriptor.color[3] = 0;\n    descriptor.color[4] = 0;\n    descriptor.color[5] = 255;\n    descriptor.mode = 0x30001;\n    return func_1513C5B0((s32)&descriptor, 0, 0, 0, x, y, z, 110.0f, 110.0f, 0, 0, 0, 255, 0);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected random effect spawn diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Random effect spawn body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_1500F290() {\n    return 0;\n}':raise ValueError('Ring render placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n\n'
 if not after.startswith(prefix):raise ValueError('Ring render owner includes changed')
 return HEADERS+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Random effect spawn snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Random effect spawn frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Random effect spawn predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Random effect spawn live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Random effect spawn named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Random effect spawn symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Random effect spawn metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Random effect spawn frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Random effect spawn original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Random effect spawn strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Random effect spawn named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Random effect spawn scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1500F290.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_3C740.c.o', 'make-shadow/src/game/generated_3C740.c.o.compact', 'make-shadow/src/game/generated_3C740.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Random effect spawn artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random effect spawn artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random effect spawn raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Random effect spawn evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Random effect spawn Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_3C740.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Random effect spawn Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Random effect spawn private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Random effect spawn changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Random effect spawn protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=112,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='5d5acf160b1ce57988c197dd86ac0c089dc196401827e86d7fc16569ec307e9c'
