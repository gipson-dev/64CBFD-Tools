"""Indexed menu record: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150B76BC','generated_E4070'
ENTRY,ROM,BODY,SIZE=(353072828, 936812, 236, 236)
SOURCE='conker/src/game/generated_E4070.c'
OBJECT='conker/build/src/game/generated_E4070.c.o'
ASM='conker/asm/E4070.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-menu-indexed-record-150B76BC-match'
RODATA_SYMBOL=None
RAW_SHA='6d4593180b0f63368dd86c298ca7952f9deb6b37b1f28615de3a140a34aed6f7'
SNAPSHOT_SHA='feb35e867f022abd3505a33f9afeca1deac0f43f885c97a53040f164f3c399f2'
BEFORE_ELF_SHA='95b69ba2d22a64d2b1ca04937ad0d64c09d0e61f7ec35602123f35c883ee1edf'
TRUTH_SHA='6a9c8562115c742674758af458f427ed234f4fc5ce6f61bd5d21a734f7bce2ae'
BINDINGS={76: [('R_MIPS_HI16', 'D_800918E8')], 80: [('R_MIPS_LO16', 'D_800918E8')], 28: [('R_MIPS_HI16', 'D_800D9898')], 36: [('R_MIPS_LO16', 'D_800D9898')], 192: [('R_MIPS_26', 'func_1516972C')], 208: [('R_MIPS_26', 'func_15169968')]}
ORIGINAL_BINDINGS={28: [('R_MIPS_HI16', 'D_800D9898')], 36: [('R_MIPS_LO16', 'D_800D9898')], 76: [('R_MIPS_HI16', 'D_800918E8')], 80: [('R_MIPS_LO16', 'D_800918E8')], 192: [('R_MIPS_26', 'func_1516972C')], 208: [('R_MIPS_26', 'func_15169968')]}
HEADERS='#include <ultra64.h>\nextern u8 D_800D9898[];\nextern u8 D_800918E8[];\nextern u8 D_800D9890;\nvoid func_1516972C(void *);\nvoid *func_15169968(void *);\n\ntypedef struct {\n    u8 *asset;\n    u8 reserved04[0x10];\n    s16 field14;\n    s16 field16;\n    s16 field18;\n    u8 reserved1A[2];\n    f32 field1C;\n    f32 field20;\n    s16 field24;\n    s16 field26;\n    s16 field28;\n    s16 field2A;\n    s16 field2C;\n    s16 field2E;\n    u8 field30;\n    u8 field31;\n    u8 field32;\n    u8 field33;\n    u8 field34;\n    u8 field35;\n    u8 field36;\n    u8 field37;\n    u8 field38;\n    u8 field39;\n    u8 reserved3A[2];\n} MenuRecordDescriptorE4070;\n\n'
DECLARATIONS='extern u8 D_800918E8[];\n\n'
SELECTED='/* Replace the selected menu record using its screen-position descriptor. */\nvoid func_150B76BC(s32 x, s32 slot) {\n    MenuRecordDescriptorE4070 descriptor;\n\n    descriptor.field31 = 1;\n    descriptor.field2C = 88;\n    descriptor.field1C = (f32)x;\n    descriptor.field2E = 64;\n    descriptor.field20 = 170.0f;\n    descriptor.field30 = 6;\n    descriptor.field14 = 0;\n    descriptor.field16 = 0;\n    descriptor.field18 = 0;\n    descriptor.asset = D_800918E8;\n    descriptor.field32 = 255;\n    descriptor.field33 = 0;\n    descriptor.field34 = 0;\n    descriptor.field35 = 255;\n    descriptor.field24 = 0;\n    descriptor.field26 = 0;\n    descriptor.field39 = 0;\n    descriptor.field36 = 7;\n    descriptor.field37 = 21;\n    descriptor.field38 = 1;\n    descriptor.field28 = 81;\n    descriptor.field2A = 81;\n    if (((void **)D_800D9898)[slot] != NULL) {\n        func_1516972C(((void **)D_800D9898)[slot]);\n    }\n    ((void **)D_800D9898)[slot] = func_15169968(&descriptor);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected slot refresh diagnostics')
    return 0




sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Indexed menu record body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_150B76BC() {\n    return 0;\n}' or before.count('s32 func_150B76BC();')!=1:raise ValueError('Indexed record placeholder/prototype changed')
 return (before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]).replace('s32 func_150B76BC();','void func_150B76BC(s32 x, s32 slot);')






def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Indexed menu record snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Indexed menu record frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Indexed menu record predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Indexed menu record live input differs: '+name)
    return values

METADATA_GROUPS=((2807716, ('func_15131AFC', 'D_8009E708'), (1, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Indexed menu record named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Indexed menu record symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Indexed menu record metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Indexed menu record frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Indexed menu record original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Indexed menu record strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Indexed menu record named definitions changed')

NEW_GUARDS=[{'filename': 'generated_E4070', 'function': 'func_150B76BC', 'offset': '0x034', 'expected': '0x240E0001', 'replacement': '0x3C01432A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rotate independent AT float constant and T6/T7 descriptor constant setup', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_E4070', 'function': 'func_150B76BC', 'offset': '0x038', 'expected': '0x240F0058', 'replacement': '0x240E0001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rotate independent AT float constant and T6/T7 descriptor constant setup', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_E4070', 'function': 'func_150B76BC', 'offset': '0x03C', 'expected': '0x3C01432A', 'replacement': '0x240F0058', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rotate independent AT float constant and T6/T7 descriptor constant setup', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited indexed-menu-record guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Owner-matrix guards already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Indexed menu record normalization scope changed')
 checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw));result_bindings={at:list(rows)for at,rows in bindings.items()}
 encode=lambda rows:';'.join(kind+':'+symbol for kind,symbol in rows)if rows else '-'
 for row in NEW_GUARDS:
  at=int(row['offset'],0)
  if words[at//4]!=int(row['expected'],0)or encode(bindings.get(at,[]))!=row['expected_relocations']:raise ValueError('Indexed menu record word/binding preimage changed')
  words[at//4]=int(row['replacement'],0);replacements=row['replacement_relocations']
  if replacements=='-':result_bindings.pop(at,None)
  else:result_bindings[at]=[tuple(item.split(':',1))for item in replacements.split(';')]
 result=struct.pack('>59I',*words)
 if sha(result)!=NORMALIZED_SHA or result_bindings!=ORIGINAL_BINDINGS:raise ValueError('Indexed menu record normalized bytes/bindings changed')
 return result,result_bindings


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_150B76BC.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_E4070.c.o', 'make-shadow/src/game/generated_E4070.c.o.compact', 'make-shadow/src/game/generated_E4070.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Indexed menu record artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Indexed menu record artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Indexed menu record raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Indexed menu record evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Indexed menu record Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_E4070.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Indexed menu record Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=3 or q['exclusions']!=0:raise ValueError('Indexed menu record private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Indexed menu record changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Indexed menu record protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=96,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=3,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='5ad4ac9e398d5088b2a2097d1f49aecff4cb7fa5471add2fd7594edadfc4b6f2'

NORMALIZED_SHA='6419f9d1267ffbdda2d4b0d723fcab5dcea73e273699f4fec75918850dd02d9d'


def schedule_proof(raw,bindings,truth,retail_bindings):
 before=list(struct.unpack('>59I',raw));after=list(before)
 if before[13:16]!=[0x240E0001,0x240F0058,0x3C01432A]or any(4*i in bindings for i in(13,14,15)):raise ValueError('Independent constant setup preimage changed')
 after[13:16]=[before[15],before[13],before[14]]
 if struct.pack('>59I',*after)!=truth or bindings!=retail_bindings:raise ValueError('Indexed descriptor constant permutation changed')
 return dict(independent_setup_rotation=True,word_indices=[13,14,15],permutation=[15,13,14],independent_destinations=['AT','T6','T7'],all_relocations_unchanged=True,no_control_or_memory_access_changes=True,frame_and_stack_offsets_unchanged=True)
