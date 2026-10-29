"""Motion integrator: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_150CBE88','generated_F8590'
ENTRY,ROM,BODY,SIZE=0x150CBE88,0xF9338,212,212
SOURCE='conker/src/game/generated_F8590.c'
OBJECT='conker/build/src/game/generated_F8590.c.o'
ASM='conker/asm/F8590.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-kinematic-twin-match'
RODATA_SYMBOL=None
RAW_SHA='6cd03bca92ca459514f94e7ca1c2c0f04c6bc63ee52eb7e84aadc8cf67d8ec45'
SNAPSHOT_SHA='6ce8633291239478a951101f4605056845867f6bfa8f90e60408ea16796109bc'
BEFORE_ELF_SHA='56e42aa0fc75523e052f317d878babca63343371c338d8c665dac7b4b5d541b7'
TRUTH_SHA='e96d9c06aa139d75a8b1d844eb0747ac8e0a1a29365426c2b318a5df291bba7b'
BINDINGS={0: [('R_MIPS_HI16', 'D_800BE9A4')], 4: [('R_MIPS_LO16', 'D_800BE9A4')]}
ORIGINAL_BINDINGS={0: [('R_MIPS_HI16', 'D_800BE9A4')], 4: [('R_MIPS_LO16', 'D_800BE9A4')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800BE9A4;\n'
DECLARATIONS=''
SELECTED='/* Integrate position and angles, retaining the original single-precision grouping. */\ns32 func_150CBE88(u8 *record) {\n    f32 acceleration = *(f32 *)(record + 0x5C);\n    f32 verticalVelocity = *(f32 *)(record + 0x48);\n    *(f32 *)(record + 0x38) += *(f32 *)(record + 0x44) * D_800BE9A4;\n    *(f32 *)(record + 0x3C) += verticalVelocity * D_800BE9A4\n        + acceleration * D_800BE9A4 * D_800BE9A4 * 0.5f;\n    *(f32 *)(record + 0x40) += *(f32 *)(record + 0x4C) * D_800BE9A4;\n    {\n        f32 delta = acceleration * D_800BE9A4;\n\n        *(f32 *)(record + 0x48) = verticalVelocity + delta;\n    }\n    *(f32 *)(record + 0x20) += *(f32 *)(record + 0x50) * D_800BE9A4;\n    *(f32 *)(record + 0x24) += *(f32 *)(record + 0x54) * D_800BE9A4;\n    *(f32 *)(record + 0x28) += *(f32 *)(record + 0x58) * D_800BE9A4;\n    return 1;\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected Motion integrator owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Motion integrator body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_150CBE88() {\n    return 0;\n}':raise ValueError('Motion twin placeholder changed')
    return before[:start]+SELECTED.rstrip()+before[end:]




def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Motion integrator snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Motion integrator frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Motion integrator predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Motion integrator live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Motion integrator named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Motion integrator symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Motion integrator metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Motion integrator frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Motion integrator original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Motion integrator strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Motion integrator named definitions changed')

NEW_GUARDS=[{'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x000', 'expected': '0x3C030000', 'replacement': '0x3C020000', 'expected_relocations': 'R_MIPS_HI16:D_800BE9A4', 'replacement_relocations': 'R_MIPS_HI16:D_800BE9A4', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x004', 'expected': '0x24630000', 'replacement': '0x24420000', 'expected_relocations': 'R_MIPS_LO16:D_800BE9A4', 'replacement_relocations': 'R_MIPS_LO16:D_800BE9A4', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x00C', 'expected': '0xC4660000', 'replacement': '0xC4460000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x014', 'expected': '0xC480005C', 'replacement': '0xC48C005C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x030', 'expected': '0xC46C0000', 'replacement': '0xC4400000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x034', 'expected': '0x460C0482', 'replacement': '0x46006482', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x03C', 'expected': '0x460C9102', 'replacement': '0x46009102', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x04C', 'expected': '0x460C1202', 'replacement': '0x46001202', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x060', 'expected': '0xC4680000', 'replacement': '0xC4480000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x06C', 'expected': '0xE4900040', 'replacement': '0xC4920050', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x070', 'expected': '0xC4640000', 'replacement': '0xE4900040', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x074', 'expected': '0x46040382', 'replacement': '0xC4440000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x078', 'expected': '0x460E1180', 'replacement': '0x46046182', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x07C', 'expected': '0xE4860048', 'replacement': '0xC4840020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x080', 'expected': '0xC4880050', 'replacement': '0x46061200', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x084', 'expected': '0xC4720000', 'replacement': '0xE4880048', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x088', 'expected': '0xC4900020', 'replacement': '0xC44A0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x08C', 'expected': '0xC4860054', 'replacement': '0xC4880054', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x090', 'expected': '0x46124282', 'replacement': '0x460A9402', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x094', 'expected': '0x24020001', 'replacement': '0x46102180', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x098', 'expected': '0x460A8100', 'replacement': '0xC4840024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x09C', 'expected': '0xC4900024', 'replacement': '0xE4860020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0A0', 'expected': '0xE4840020', 'replacement': '0xC4520000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0A4', 'expected': '0xC4680000', 'replacement': '0xC4860058', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0A8', 'expected': '0xC4840058', 'replacement': '0x46124282', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0AC', 'expected': '0x46083482', 'replacement': '0x460A2400', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0B0', 'expected': '0x46128280', 'replacement': '0xC4840028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0B4', 'expected': '0xC4900028', 'replacement': '0xE4900024', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0B8', 'expected': '0xE48A0024', 'replacement': '0xC4480000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0BC', 'expected': '0xC4660000', 'replacement': '0x24020001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0C0', 'expected': '0x46062202', 'replacement': '0x46083482', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0C4', 'expected': '0x46088480', 'replacement': '0x46122280', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_F8590', 'function': 'func_150CBE88', 'offset': '0x0C8', 'expected': '0xE4920028', 'replacement': '0xE48A0028', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed motion integrator register allocation and independent scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='a00df1fa60bb7763d7b035dc10a0a5e95988bb00f8d9403d2331ccea70c05adc':raise ValueError('Motion twin inherited guards changed')
    return before+b'generated_F8590,func_150CBE88,0x000,0x3C030000,0x3C020000,R_MIPS_HI16:D_800BE9A4,R_MIPS_HI16:D_800BE9A4,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x004,0x24630000,0x24420000,R_MIPS_LO16:D_800BE9A4,R_MIPS_LO16:D_800BE9A4,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x00C,0xC4660000,0xC4460000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x014,0xC480005C,0xC48C005C,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x030,0xC46C0000,0xC4400000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x034,0x460C0482,0x46006482,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x03C,0x460C9102,0x46009102,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x04C,0x460C1202,0x46001202,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x060,0xC4680000,0xC4480000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x06C,0xE4900040,0xC4920050,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x070,0xC4640000,0xE4900040,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x074,0x46040382,0xC4440000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x078,0x460E1180,0x46046182,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x07C,0xE4860048,0xC4840020,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x080,0xC4880050,0x46061200,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x084,0xC4720000,0xE4880048,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x088,0xC4900020,0xC44A0000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x08C,0xC4860054,0xC4880054,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x090,0x46124282,0x460A9402,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x094,0x24020001,0x46102180,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x098,0x460A8100,0xC4840024,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x09C,0xC4900024,0xE4860020,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0A0,0xE4840020,0xC4520000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0A4,0xC4680000,0xC4860058,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0A8,0xC4840058,0x46124282,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0AC,0x46083482,0x460A2400,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0B0,0x46128280,0xC4840028,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0B4,0xC4900028,0xE4900024,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0B8,0xE48A0024,0xC4480000,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0BC,0xC4660000,0x24020001,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0C0,0x46062202,0x46083482,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0C4,0x46088480,0x46122280,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\ngenerated_F8590,func_150CBE88,0x0C8,0xE4920028,0xE48A0028,-,-,Normalize closed motion integrator register allocation and independent scheduling,,,false\r\n'






def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw);relocations=dict(bindings)
    parse=lambda text:[]if text=='-'else[tuple(v.split(':',1))for v in text.split(';')]
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0)or bindings.get(at,[])!=parse(row['expected_relocations']):raise ValueError('Motion integrator expected word or binding changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0));relocations.pop(at,None)
        if row['replacement_relocations']!='-':relocations[at]=parse(row['replacement_relocations'])
    if sha(result)!='bd0da275969658545c939ebfeb277afa70d692bb58147a1c36ae330fbfb6165a'or relocations!=ORIGINAL_BINDINGS:raise ValueError('Motion integrator normalized body/bindings changed')
    return bytes(result),relocations



ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150CBE88.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-best-input.c","make-shadow/src/game/generated_F8590.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_F8590.c.o","make-shadow/src/game/generated_F8590.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Motion integrator artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Motion integrator artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Motion integrator raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Motion integrator evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Motion integrator Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_F8590.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Motion integrator Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=33 or q['exclusions']!=0:raise ValueError('Motion integrator private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Motion integrator changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Motion integrator protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=0,alignment_words=0,slot_words=53,strict_first_link_reproduced=True,guards=33,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
