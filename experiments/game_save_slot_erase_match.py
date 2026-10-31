"""Save slot erase: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys,csv,io
import tools.pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly as _emit
def emit_padded_assembly(obj,asm,filename,word_patches_path):
    asm=Path(asm)
    if asm.name!='func_1500707C.s'or filename!='game_33990':raise ValueError('Script-lookup padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER=('func_1500707C', 'game_33990')
ENTRY,ROM,BODY,SIZE=(352350332, 214316, 236, 236)
SOURCE='conker/src/game_33990.c'
OBJECT='conker/build/src/game_33990.c.o'
ASM='conker/asm/nonmatchings/game_33990/func_1500707C.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-save-slot-erase-1500707C-match'
RODATA_SYMBOL=None
RAW_SHA='3f6f480b148c0303afdac7b8243f36fa47048a1517a197be3294489891be1699'
SNAPSHOT_SHA='31006043538e1b4c041910b6a7855196862d21e3aa37d09436c37227806a620c'
BEFORE_ELF_SHA='f10c39b4ba7cb66faef1adf33b9434544aae4ceca059a4e580718b583fed85d9'
TRUTH_SHA='f7df6d381dbb26d6ecebdbdc85c28c78d5d3018fa441a71fb4ace274292208db'
BINDINGS={40: [('R_MIPS_HI16', 'D_800BE358')], 44: [('R_MIPS_LO16', 'D_800BE358')], 76: [('R_MIPS_26', 'osWritebackDCacheAll')], 84: [('R_MIPS_HI16', 'D_8002AC5C')], 88: [('R_MIPS_LO16', 'D_8002AC5C')], 92: [('R_MIPS_HI16', 'D_800BE3D8')], 96: [('R_MIPS_LO16', 'D_800BE3D8')], 108: [('R_MIPS_HI16', 'D_800BE900')], 112: [('R_MIPS_LO16', 'D_800BE900')], 144: [('R_MIPS_26', 'func_151DD4E0')], 168: [('R_MIPS_26', 'func_151DD4E0')]}
ORIGINAL_BINDINGS={44: [('R_MIPS_HI16', 'D_800BE358')], 48: [('R_MIPS_LO16', 'D_800BE358')], 80: [('R_MIPS_26', 'osWritebackDCacheAll')], 88: [('R_MIPS_HI16', 'D_8002AC5C')], 92: [('R_MIPS_LO16', 'D_8002AC5C')], 96: [('R_MIPS_HI16', 'D_800BE3D8')], 100: [('R_MIPS_LO16', 'D_800BE3D8')], 112: [('R_MIPS_HI16', 'D_800BE900')], 116: [('R_MIPS_LO16', 'D_800BE900')], 152: [('R_MIPS_26', 'func_151DD4E0')], 172: [('R_MIPS_26', 'func_151DD4E0')]}
HEADERS='#include <ultra64.h>\n#include "variables.h"\nextern u8 D_8002AC5C;\nextern OSMesgQueue D_800BE900;\ns32 func_151DD4E0(OSMesgQueue *, u8, u8 *);\n\n'
DECLARATIONS=''
SELECTED='/* Erase both EEPROM blocks for every matching signed slot ID; ignore write errors. */\nvoid func_1500707C(s32 slot) {\n    s32 i;\n    s8 *entry;\n    s32 block;\n    s32 status;\n\n    for (i = 0; i < 8; i++) {\n        *((u8 *)D_800BE358 + i) = 0xFF;\n    }\n    osWritebackDCacheAll();\n    if (D_8002AC5C == 0) {\n        entry = (s8 *)&D_800BE3D8;\n        for (i = 0; i != 4; i++) {\n            if (slot == *entry) {\n                block = (i << 4) + 4;\n                status = func_151DD4E0(&D_800BE900, (u8)block, D_800BE358);\n                func_151DD4E0(&D_800BE900, (u8)(block + 1), D_800BE358);\n            }\n            entry++;\n        }\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected save-slot erase owner diagnostics')
    return 0



sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=228 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Save slot erase body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_1500707C() {\n    return 0;\n}':raise ValueError('Save-slot erase placeholder changed')
    after=before[:a]+SELECTED.rstrip()+before[b:]
    after=after.replace('s32 func_1500707C();','void func_1500707C(s32 slot);',1)
    after=after.replace('/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_1500707C.s. */\n','',1)
    return after.replace('s32 func_151DD3A0(OSMesgQueue *, u8, u8 *, s32);','s32 func_151DD3A0(OSMesgQueue *, u8, u8 *, s32);\ns32 func_151DD4E0(OSMesgQueue *, u8, u8 *);',1)



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Save slot erase snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Save slot erase frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Save slot erase predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Save slot erase live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Save slot erase named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Save slot erase symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Save slot erase metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Save slot erase frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Save slot erase original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Save slot erase strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Save slot erase named definitions changed')

NEW_GUARDS=[{'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x004', 'expected': '0xAFB60030', 'replacement': '0xAFB70030', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x008', 'expected': '0x0080B025', 'replacement': '0x0080B825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x010', 'expected': '0xAFB5002C', 'replacement': '0xAFB6002C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x014', 'expected': '0xAFB40028', 'replacement': '0xAFB50028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x018', 'expected': '0xAFB30024', 'replacement': '0xAFB40024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x01C', 'expected': '0xAFB20020', 'replacement': '0xAFB30020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x020', 'expected': '0xAFB1001C', 'replacement': '0xAFB2001C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x024', 'expected': '0xAFB00018', 'replacement': '0xAFB10018', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '0xAFB00014', 'insert_after_relocations': '-', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x06C', 'expected': '0x3C130000', 'replacement': '0x3C150000', 'expected_relocations': 'R_MIPS_HI16:D_800BE900', 'replacement_relocations': 'R_MIPS_HI16:D_800BE900', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x070', 'expected': '0x26730000', 'replacement': '0x26B50000', 'expected_relocations': 'R_MIPS_LO16:D_800BE900', 'replacement_relocations': 'R_MIPS_LO16:D_800BE900', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x074', 'expected': '0x24150004', 'replacement': '0x24160004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x07C', 'expected': '0x00108900', 'replacement': '0x00101100', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x080', 'expected': '0x26310004', 'replacement': '0x24420004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x084', 'expected': '0x16D8000A', 'replacement': '0x16F8000A', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x088', 'expected': '0x02602025', 'replacement': '0x02A02025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x08C', 'expected': '0x322500FF', 'replacement': '0x304500FF', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '0x02803025', 'insert_after_relocations': '-', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x094', 'expected': '0x02803025', 'replacement': '0x24530001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x098', 'expected': '0x26250001', 'replacement': '0x00408825', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x09C', 'expected': '0x30B900FF', 'replacement': '0x02A02025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0A0', 'expected': '0x03202825', 'replacement': '0x326500FF', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0A4', 'expected': '0x02602025', 'replacement': '0x02602025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'true'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0B4', 'expected': '0x1615FFF0', 'replacement': '0x1616FFF0', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent paired-write argument scheduling and discarded status', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0C0', 'expected': '0x8FB00018', 'replacement': '0x8FB00014', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0C4', 'expected': '0x8FB1001C', 'replacement': '0x8FB10018', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0C8', 'expected': '0x8FB20020', 'replacement': '0x8FB2001C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0CC', 'expected': '0x8FB30024', 'replacement': '0x8FB30020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0D0', 'expected': '0x8FB40028', 'replacement': '0x8FB40024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0D4', 'expected': '0x8FB5002C', 'replacement': '0x8FB50028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500707C', 'offset': '0x0D8', 'expected': '0x8FB60030', 'replacement': '0x8FB6002C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed saved-register allocation and frame spill packing', 'insert_after': '0x8FB70030', 'insert_after_relocations': '-', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited save-slot erase guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Script-lookup guard already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Save-slot erase normalization scope changed')
    checked_payload(raw,bindings);rows={int(row['offset'],0):row for row in NEW_GUARDS};out=[];rs={}
    fmt=lambda rel:';'.join(k+':'+n for k,n in rel)if rel else '-'
    for i,word in enumerate(struct.unpack('>57I',raw)):
        at=4*i;row=rows.get(at);rel=bindings.get(at,[])
        if row:
            if word!=int(row['expected'],0)or row['expected_relocations']!=fmt(rel):raise ValueError('Save-slot erase expected preimage changed')
            if row['omit']=='true':
                if rel:raise ValueError('Save-slot erase omitted binding')
                continue
            word=int(row['replacement'],0)
            if row['replacement_relocations']!=fmt(rel):raise ValueError('Save-slot erase changed named binding')
        if rel:rs[len(out)*4]=rel
        out.append(word)
        if row and row['insert_after']:out.append(int(row['insert_after'],0))
    result=struct.pack('>59I',*out)
    if sha(result)!=NORMALIZED_SHA or rs!=ORIGINAL_BINDINGS:raise ValueError('Save-slot erase normalized bytes/bindings changed')
    return result,rs


NORMALIZED_SHA='047ff116ddd5b4f0f59de2657b4c4d4becd5ff87ac154de8410627769b88d824'

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1500707C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_33990.c.o', 'make-shadow/src/game_33990.c.o.compact', 'make-shadow/src/game_33990.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Save slot erase artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save slot erase artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save slot erase raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Save slot erase evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save slot erase Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_33990.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Save slot erase Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=29 or q['exclusions']!=0:raise ValueError('Save slot erase private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Save slot erase changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Save slot erase protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=56,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=29,insertions=3,omissions=1,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='55441d597fdc57e0430768847d0437ea1d6f230e996601a488e5dcf87bec0c3f'
