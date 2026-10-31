"""Packed attached state: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as pad
sys.modules.setdefault("pad_generated_object",pad)
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15073B38','game_981E0'
ENTRY,ROM,BODY,SIZE=(352795448, 659432, 240, 240)
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
ASM='conker/asm/nonmatchings/game_981E0/func_15073B38.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-attached-packed-state-15073B38-match'
RODATA_SYMBOL=None
RAW_SHA='ba914b4485c6f7f177ae54197741257c39f88c8457912155811fe3a34c82bef0'
SNAPSHOT_SHA='fcff840afdd65a2d6f46124e13033bc978eaf553fa0aa48850993b916b1b7ed5'
BEFORE_ELF_SHA='bef3d6471a49ce7dca68d8753c91430d64e32db7ec428a6603bb23f49cb3992a'
TRUTH_SHA='5fa9eef50dddd5a78b8343a2ee8d6f37b9469e968c14a60764f910aae330f112'
BINDINGS={0: [('R_MIPS_HI16', 'D_800D1580')], 12: [('R_MIPS_LO16', 'D_800D1580')], 4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')]}
ORIGINAL_BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 0: [('R_MIPS_HI16', 'D_800D1580')], 12: [('R_MIPS_LO16', 'D_800D1580')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern struct127 *D_800D154C;\nextern s32 D_800D1580;\ntypedef struct {\n    u8 pad[0xA8];\n    f32 value;\n    u8 mode;\n    u8 flags;\n} GameAttachedPackedState;\n'
DECLARATIONS='typedef struct {\n    u8 pad[0xA8];\n    f32 value;\n    u8 mode;\n    u8 flags;\n} GameAttachedPackedState;\n'
SELECTED='/* Decode the packed word into the currently attached object. */\nvoid func_15073B38(void) {\n    f32 value;\n    f32 mode;\n    value = (f32)(D_800D1580 & 0xFFFF);\n    ((GameAttachedPackedState *)D_800D154C->unk31C)->value = value;\n    mode = (f32)((D_800D1580 >> 16) & 0xFF);\n    ((GameAttachedPackedState *)D_800D154C->unk31C)->mode = (u8)mode;\n    ((GameAttachedPackedState *)D_800D154C->unk31C)->flags = (u8)(D_800D1580 >> 24);\n}\n'

def check_owner_diagnostics(text):
 normalize=lambda value:re.sub(r'build/[^,\n]+, line ','<owner>, line ',value)
 if normalize(text)not in DIAGNOSTIC_BASELINES:raise ValueError('Changed inherited owner diagnostics')
 if text.count('cfe: Warning')!=36:raise ValueError('Changed inherited owner warning count')
 return 36





sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=240 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packed attached state body/bindings changed')
 return raw,bindings


def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_15073B38() {\n    return 0;\n}':raise ValueError('Packed attached state placeholder changed')
 if before.count('s32 func_15073B38();')!=1:raise ValueError('Packed attached state declaration changed')
 return(before[:a]+DECLARATIONS+SELECTED.rstrip()+before[b:]).replace('s32 func_15073B38();','void func_15073B38(void);')









def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Packed attached state snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Packed attached state frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Packed attached state predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Packed attached state live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Packed attached state named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Packed attached state symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Packed attached state metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Packed attached state frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Packed attached state original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Packed attached state strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Packed attached state named definitions changed')

NEW_GUARDS=[{'filename': 'game_981E0', 'function': 'func_15073B38', 'offset': '0x0D4', 'expected': '0x8C790000', 'replacement': '0x8C680000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail register allocation in packed attached-state decoder', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_981E0', 'function': 'func_15073B38', 'offset': '0x0DC', 'expected': '0x8F28031C', 'replacement': '0x8D09031C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail register allocation in packed attached-state decoder', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_981E0', 'function': 'func_15073B38', 'offset': '0x0E0', 'expected': '0x000FC603', 'replacement': '0x000FCE03', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail register allocation in packed attached-state decoder', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_981E0', 'function': 'func_15073B38', 'offset': '0x0E4', 'expected': '0xA11800AD', 'replacement': '0xA13900AD', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed tail register allocation in packed attached-state decoder', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]
def guard_manifest(before):
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited packed attached state guards changed')
 fields=list(csv.DictReader(io.StringIO(before.decode())).fieldnames)
 stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n');writer.writerows(NEW_GUARDS)
 return before+stream.getvalue().encode()




def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Packed attached state scope changed')
 checked_payload(raw,bindings);result=bytearray(raw)
 for row in NEW_GUARDS:
  at=int(row['offset'],0);expected=int(row['expected'],0);replacement=int(row['replacement'],0)
  if int.from_bytes(raw[at:at+4],'big')!=expected or at in bindings:raise ValueError('Packed attached state allocation preimage changed')
  result[at:at+4]=replacement.to_bytes(4,'big')
 if sha(result)!=NORMALIZED_SHA:raise ValueError('Packed attached state normalized body changed')
 return bytes(result),bindings




ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15073B38.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_981E0.c.o', 'make-shadow/src/game_981E0.c.o.compact', 'make-shadow/src/game_981E0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Packed attached state artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Packed attached state artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Packed attached state raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Packed attached state evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Packed attached state Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_981E0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Packed attached state Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=4 or q['exclusions']!=0:raise ValueError('Packed attached state private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Packed attached state changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Packed attached state protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=60,reachable_words=42,frame=0,alignment_words=0,slot_words=60,strict_first_link_reproduced=True,guards=4,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='86d6b8fdc5c63ef7719c43f879ad2f80afce02ec88eb32ac64b2c05371a4a66a'

NORMALIZED_SHA='2900e76b6f4173e0b4d99a16650fbbed86a0895102039e38b27eea06ede0f482'


def schedule_proof(raw,bindings,truth,retail_bindings):
 checked_payload(raw,bindings)
 if normalized_payload(raw,bindings)!=(truth,retail_bindings):raise ValueError('Packed attached state normalized body/bindings changed')
 a=struct.unpack('>60I',raw);b=struct.unpack('>60I',truth)
 if [i for i in range(60)if a[i]!=b[i]]!=[53,55,56,57]:raise ValueError('Packed attached state allocation scope changed')
 if[a[i]for i in (53,55,56,57)]!=[0x8C790000,0x8F28031C,0x000FC603,0xA11800AD]or[b[i]for i in (53,55,56,57)]!=[0x8C680000,0x8D09031C,0x000FCE03,0xA13900AD]:raise ValueError('Packed attached state tail instructions changed')
 return dict(direct_C_match=False,words=60,bindings=4,guards=4,word_indices=[53,55,56,57],register_mapping={'T9':'T0','T0':'T1','T8':'T9'},only_closed_tail_register_allocation=True,all_other_words_and_bindings_identical=True)


DIAGNOSTIC_BASELINES=('cfe: Warning 712: <owner>, line 751: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 751: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 757: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 757: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 763: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 763: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 769: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 769: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 775: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 775: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 781: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 781: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 787: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 787: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 793: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 793: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 807: illegal combination of pointer and integer\n     if ((func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) && (func_1000F4D8((u16)D_800D1582) == 0)) {\n -----------------------^\ncfe: Warning 712: <owner>, line 807: illegal combination of pointer and integer\n     if ((func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) && (func_1000F4D8((u16)D_800D1582) == 0)) {\n -----------------------------------^\ncfe: Warning 712: <owner>, line 813: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 2) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 813: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 2) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 819: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 819: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 825: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 825: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 831: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 831: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 837: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 837: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 843: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 843: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 849: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 849: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 855: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 855: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 709: <owner>, line 1496: Incompatible pointer type assignment\n             func_151DC484(&sp4C, &sp28, 0, 0xFF, 1);\n ---------------------------------^\ncfe: Warning 709: <owner>, line 2018: Incompatible pointer type assignment\n     temp_f0 = func_1505A72C(&D_800CC2D0, D_800D154C);\n ----------------------------^\n', 'cfe: Warning 712: <owner>, line 751: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 751: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 757: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 757: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 763: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 763: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 769: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 769: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 775: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 775: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 781: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 781: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 787: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 787: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 793: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 793: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 807: illegal combination of pointer and integer\n     if ((func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) && (func_1000F4D8((u16)D_800D1582) == 0)) {\n -----------------------^\ncfe: Warning 712: <owner>, line 807: illegal combination of pointer and integer\n     if ((func_1506E46C(D_800D154C, &D_800D1580, 0) != 0) && (func_1000F4D8((u16)D_800D1582) == 0)) {\n -----------------------------------^\ncfe: Warning 712: <owner>, line 813: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 2) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 813: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 2) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 819: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 819: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 825: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 825: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 831: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 831: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 837: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 837: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 843: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 843: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 849: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 849: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 712: <owner>, line 855: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------^\ncfe: Warning 712: <owner>, line 855: illegal combination of pointer and integer\n     if (func_1506E46C(D_800D154C, &D_800D1580, 1) != 0) {\n ----------------------------------^\ncfe: Warning 709: <owner>, line 1496: Incompatible pointer type assignment\n             func_151DC484(&sp4C, &sp28, 0, 0xFF, 1);\n ---------------------------------^\ncfe: Warning 709: <owner>, line 2031: Incompatible pointer type assignment\n     temp_f0 = func_1505A72C(&D_800CC2D0, D_800D154C);\n ----------------------------^\n')
