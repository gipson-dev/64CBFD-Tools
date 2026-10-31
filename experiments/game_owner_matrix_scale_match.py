"""Owner matrix scale: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,csv,io
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15108D24','generated_135D00'
ENTRY,ROM,BODY,SIZE=(353406244, 1270228, 236, 236)
SOURCE='conker/src/game/generated_135D00.c'
OBJECT='conker/build/src/game/generated_135D00.c.o'
ASM='conker/asm/135D00.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-owner-matrix-scale-15108D24-match'
RODATA_SYMBOL=None
RAW_SHA='219e8e108e8722a3ff5c95edb2a8bc82847dd635d3807e85231a66fe71779bec'
SNAPSHOT_SHA='7e8662ebbaa7d316241eeaef3cb8f542462a1c019ae606488a6034bf0ee8a5ee'
BEFORE_ELF_SHA='bb0d274014310d7968ee5100f2154b94a12554dba9dd34baaff5a54c6547ca5c'
TRUTH_SHA='d953461fd56adbd8dff7b180002e31ebeff09be217804596f88fb4bb9acd90ee'
BINDINGS={48: [('R_MIPS_26', 'func_150A8050')], 56: [('R_MIPS_HI16', 'D_800A2490')], 60: [('R_MIPS_LO16', 'D_800A2490')], 168: [('R_MIPS_HI16', 'D_800BE9C0')], 176: [('R_MIPS_LO16', 'D_800BE9C0')], 208: [('R_MIPS_26', 'guMtxF2L')]}
ORIGINAL_BINDINGS={48: [('R_MIPS_26', 'func_150A8050')], 56: [('R_MIPS_HI16', 'D_800A2490')], 60: [('R_MIPS_LO16', 'D_800A2490')], 168: [('R_MIPS_HI16', 'D_800BE9C0')], 176: [('R_MIPS_LO16', 'D_800BE9C0')], 208: [('R_MIPS_26', 'guMtxF2L')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800A2490;\nextern u8 D_800BE9C0;\nvoid func_150A8050(f32 matrix[4][4],f32 x,f32 y,f32 z);\n'
DECLARATIONS='extern f32 D_800A2490;\nextern u8 D_800BE9C0;\nvoid func_150A8050(f32 matrix[4][4],f32 x,f32 y,f32 z);\n'
SELECTED="/* Scale the owner's rotation matrix, retain its height and publish the active slot. */\ns32 func_15108D24(u8 *owner, s32 view) {\n    f32 matrix[4][4];\n    u8 *state;\n    state = owner + *(s32 *)(owner + 0x50) + 0xF8;\n    func_150A8050(matrix, *(f32 *)state, 0.0f, *(f32 *)(state + 4));\n    matrix[3][1] = *(f32 *)(state + 0x10);\n    matrix[0][0] *= D_800A2490;\n    matrix[0][1] *= D_800A2490;\n    matrix[0][2] *= D_800A2490;\n    matrix[1][0] *= D_800A2490;\n    matrix[1][1] *= D_800A2490;\n    matrix[1][2] *= D_800A2490;\n    matrix[2][0] *= D_800A2490;\n    matrix[2][1] *= D_800A2490;\n    matrix[2][2] *= D_800A2490;\n    guMtxF2L(matrix, (Mtx *)(owner + ((u32)D_800BE9C0 << 6) + 0x78));\n    return 1;\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected resource-pair owner diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner matrix scale body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_15108D24() {\n    return 0;\n}':raise ValueError('Owner matrix placeholder changed')
    declarations=HEADERS.replace('#include <ultra64.h>\n','',1).replace('#include "structs.h"\n','',1)
    return before[:a]+declarations+SELECTED.rstrip()+before[b:]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner matrix scale snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner matrix scale frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner matrix scale predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner matrix scale live input differs: '+name)
    return values

METADATA_GROUPS=((2966644, ('D_800A2490', 'D_80090A00'), (1, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Owner matrix scale named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Owner matrix scale symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Owner matrix scale metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner matrix scale frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner matrix scale original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner matrix scale strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner matrix scale named definitions changed')

NEW_GUARDS=[{'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x01C', 'expected': '0x8DCF0050', 'replacement': '0x8DD80050', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x020', 'expected': '0x01EE1021', 'replacement': '0x01D81021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x0A8', 'expected': '0x3C180000', 'replacement': '0x3C080000', 'expected_relocations': 'R_MIPS_HI16:D_800BE9C0', 'replacement_relocations': 'R_MIPS_HI16:D_800BE9C0', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x0B0', 'expected': '0x93180000', 'replacement': '0x91080000', 'expected_relocations': 'R_MIPS_LO16:D_800BE9C0', 'replacement_relocations': 'R_MIPS_LO16:D_800BE9C0', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x0B4', 'expected': '0x8FA80060', 'replacement': '0x8FB90060', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x0BC', 'expected': '0x0018C980', 'replacement': '0x00084980', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_135D00', 'function': 'func_15108D24', 'offset': '0x0C0', 'expected': '0x03282821', 'replacement': '0x03292821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed state-offset, matrix-page and owner temporary register cycles', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited owner-matrix guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Owner-matrix guards already present')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Owner-matrix normalization scope changed')
    checked_payload(raw,bindings);words=list(struct.unpack('>59I',raw))
    encode=lambda rows:';'.join(kind+':'+symbol for kind,symbol in rows) if rows else '-'
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if words[at//4]!=int(row['expected'],0) or encode(bindings.get(at,[]))!=row['expected_relocations'] or row['expected_relocations']!=row['replacement_relocations']:raise ValueError('Owner-matrix preimage changed')
        words[at//4]=int(row['replacement'],0)
    result=struct.pack('>59I',*words)
    if sha(result)!=NORMALIZED_SHA or bindings!=ORIGINAL_BINDINGS:raise ValueError('Owner-matrix normalized bytes/bindings changed')
    return result,bindings


ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_15108D24.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_135D00.c.o', 'make-shadow/src/game/generated_135D00.c.o.compact', 'make-shadow/src/game/generated_135D00.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner matrix scale artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner matrix scale artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner matrix scale raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner matrix scale evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner matrix scale Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_135D00.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner matrix scale Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=7 or q['exclusions']!=0:raise ValueError('Owner matrix scale private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner matrix scale changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner matrix scale protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=59,frame=96,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=7,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='1cf5a19e76f1a00276ae96201337597cb8db3499347528e33b0d47d55660531c'

NORMALIZED_SHA='250bab8aec21969ebdb16e3587fe6d7aa4d598c5447015ab90f96231c8617a8e'
