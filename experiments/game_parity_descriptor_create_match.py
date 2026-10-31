"""Parity descriptor creation: direct semantic C and literal image audit."""
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
FUNCTION,OWNER='func_151A90C0','generated_1D4E00'
ENTRY,ROM,BODY,SIZE=0x151A90C0,0x1D6570,236,236
SOURCE='conker/src/game/generated_1D4E00.c'
OBJECT='conker/build/src/game/generated_1D4E00.c.o'
ASM='conker/asm/1D4E00.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-parity-descriptor-create-151A90C0-match'
RODATA_SYMBOL=None
RAW_SHA='13d78346f3b72d0ab84254fd0a33148105feda1b9dbffabab835698b6727397f'
SNAPSHOT_SHA='97e4af5ddd320b8c204a8f84d018fb2dcd1f3beaea7cb6e047e5fc8f24e64dac'
BEFORE_ELF_SHA='09bbb74cdc91646d5278f9f13fba388c6f867768bc18498c251633aa19e9585e'
TRUTH_SHA='54f2a411212ae6a09411830e4776d94f1836ac58fd4ef557781db98dfca6a2e0'
BINDINGS={84: [('R_MIPS_HI16', 'D_800A8F58')], 88: [('R_MIPS_LO16', 'D_800A8F58')], 40: [('R_MIPS_HI16', 'D_800A8F5C')], 100: [('R_MIPS_LO16', 'D_800A8F5C')], 128: [('R_MIPS_HI16', 'D_800A8F60')], 132: [('R_MIPS_LO16', 'D_800A8F60')], 116: [('R_MIPS_HI16', 'D_800A8F64')], 144: [('R_MIPS_LO16', 'D_800A8F64')], 192: [('R_MIPS_26', 'func_151A8B20')], 212: [('R_MIPS_26', 'memcpy')]}
ORIGINAL_BINDINGS={84: [('R_MIPS_HI16', 'D_800A8F58')], 88: [('R_MIPS_LO16', 'D_800A8F58')], 40: [('R_MIPS_HI16', 'D_800A8F5C')], 100: [('R_MIPS_LO16', 'D_800A8F5C')], 128: [('R_MIPS_HI16', 'D_800A8F60')], 132: [('R_MIPS_LO16', 'D_800A8F60')], 116: [('R_MIPS_HI16', 'D_800A8F64')], 144: [('R_MIPS_LO16', 'D_800A8F64')], 192: [('R_MIPS_26', 'func_151A8B20')], 212: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    u8 kind;\n    u8 reserved01[3];\n    u8 *owner;\n    f32 primary;\n    f32 secondary;\n    f32 zero[5];\n    u8 enabled;\n    s8 mode;\n    u8 flags;\n} ParitySpawnRequest;\nextern f32 D_800A8F58, D_800A8F5C, D_800A8F60, D_800A8F64;\n/* The unfinished allocator returns a pointer; this call supplies five arguments. */\nu8 *func_151A8B20();\n'
DECLARATIONS=''
SELECTED="/* Create a parity-selected descriptor and attach the selector's low byte. */\nvoid func_151A90C0(u8 *owner, s32 selector) {\n    ParitySpawnRequest request;\n    f32 parity = selector & 1;\n    u8 tag[1];\n    u8 *created;\n    request.kind = 2;\n    request.owner = owner;\n    request.primary = parity ? D_800A8F58 : D_800A8F5C;\n    request.secondary = parity ? D_800A8F60 : D_800A8F64;\n    request.zero[0] = 0.0f;\n    request.zero[1] = 0.0f;\n    request.zero[2] = 0.0f;\n    request.zero[3] = 0.0f;\n    request.zero[4] = 0.0f;\n    request.enabled = 1;\n    request.mode = -1;\n    request.flags = 0;\n    tag[0] = selector;\n    created = func_151A8B20(&request, -1, 1, 0xFF, 0);\n    if (created != NULL) {\n        memcpy(created + 0x80, tag, 1);\n    }\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected parity-descriptor owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Parity descriptor creation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_151A90C0() {\n    return 0;\n}':raise ValueError('Parity-descriptor placeholder changed')
    after=before[:a]+SELECTED.rstrip()+before[b:]
    at=after.index('void func_1516972C');after=after[:at]+HEADERS.replace('#include <ultra64.h>\n','',1)+after[at:]
    old='s32 func_151A8B20() {\n    return 0;\n}'
    if after.count(old)!=1:raise ValueError('Expected unfinished allocator definition')
    after=after.replace(old,'u8 *func_151A8B20() {\n    return 0;\n}')
    if after.count('extern s32 (*D_8008F984[])(u8 *, s32);')!=1 or after.count('s32 (*callback)(u8 *, s32);')!=1:raise ValueError('Expected observed callback table and local type')
    return after.replace('extern s32 (*D_8008F984[])(u8 *, s32);','extern void (*D_8008F984[])(u8 *, s32);').replace('s32 (*callback)(u8 *, s32);','void (*callback)(u8 *, s32);')



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Parity descriptor creation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Parity descriptor creation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Parity descriptor creation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Parity descriptor creation live input differs: '+name)
    return values

METADATA_GROUPS=((2825140, ('D_800A8F60', 'D_800A8B10', 'D_800A0060', 'D_8009FC60'), (1, 2, 3, 0)), (2827268, ('D_800A8F58', 'D_800A8B08', 'D_80096368', 'func_15076F78', 'D_8009BB08'), (1, 2, 3, 4, 0)), (2847604, ('D_800A8F64', 'D_800A8B14', 'D_800A82E4', 'D_800A0064', 'D_8009F774'), (1, 2, 3, 4, 0)), (2859220, ('D_800A2D98', 'D_8009E72C'), (1, 0)), (2935812, ('D_800A8F5C', 'D_800A8B0C'), (1, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Parity descriptor creation named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Parity descriptor creation symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Parity descriptor creation metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Parity descriptor creation frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Parity descriptor creation original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Parity descriptor creation strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Parity descriptor creation named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 return before

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Parity descriptor creation scope changed')
 return checked_payload(raw,bindings)

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151A90C0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_1D4E00.c.o', 'make-shadow/src/game/generated_1D4E00.c.o.compact', 'make-shadow/src/game/generated_1D4E00.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Parity descriptor creation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Parity descriptor creation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Parity descriptor creation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Parity descriptor creation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Parity descriptor creation Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1D4E00.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Parity descriptor creation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Parity descriptor creation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Parity descriptor creation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Parity descriptor creation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=88,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0e1dcd21b2871b8c63c7e128de0c89befa9870d68748dbb979f048976a5728e9'
