"""Save checksum load: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as _pad
sys.modules.setdefault('pad_generated_object',_pad)
from tools.pad_c_object import emit_padded_assembly as _emit
def emit_padded_assembly(obj,asm,filename,word_patches_path):
    asm=Path(asm)
    if asm.name!='func_1500727C.s'or filename!='game_33990':raise ValueError('Save checksum load padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1500727C','game_33990'
ENTRY,ROM,BODY,SIZE=0x1500727C,0x3472C,228,228
SOURCE='conker/src/game_33990.c'
OBJECT='conker/build/src/game_33990.c.o'
ASM='conker/asm/nonmatchings/game_33990/func_1500727C.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-save-checksum-load-1500727C-match'
RODATA_SYMBOL=None
RAW_SHA='14d322a6fac76024c350909f5e26a2b9541220396b973debf8c03b15918f251c'
SNAPSHOT_SHA='da6f59a08a5adac64aa584087daabaec330b610723f6f02e95e308b00f9cb7fb'
BEFORE_ELF_SHA='6a177d64e494d6059d313a8114d060a5c0d3247d2680071c9661bd81a5575572'
TRUTH_SHA='00de482d2ff948387af09e3bbca70f07e2ba85cdefea2db760dc3bc5a78e5d94'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE900')], 20: [('R_MIPS_LO16', 'D_800BE900')], 12: [('R_MIPS_HI16', 'D_800BE2F0')], 16: [('R_MIPS_LO16', 'D_800BE2F0')], 28: [('R_MIPS_26', 'func_151DD3A0')], 36: [('R_MIPS_HI16', 'D_800BE2F2')], 40: [('R_MIPS_LO16', 'D_800BE2F2')], 44: [('R_MIPS_HI16', 'D_800BE2F3')], 48: [('R_MIPS_LO16', 'D_800BE2F3')], 72: [('R_MIPS_HI16', 'D_800BE2F0')], 80: [('R_MIPS_LO16', 'D_800BE2F0')], 188: [('R_MIPS_HI16', 'D_800BE2F0')], 192: [('R_MIPS_LO16', 'D_800BE2F0')], 204: [('R_MIPS_26', 'func_15007168')]}
ORIGINAL_BINDINGS={12: [('R_MIPS_HI16', 'D_800BE2F0')], 16: [('R_MIPS_LO16', 'D_800BE2F0')], 8: [('R_MIPS_HI16', 'D_800BE900')], 20: [('R_MIPS_LO16', 'D_800BE900')], 28: [('R_MIPS_26', 'func_151DD3A0')], 36: [('R_MIPS_HI16', 'D_800BE2F2')], 40: [('R_MIPS_LO16', 'D_800BE2F2')], 44: [('R_MIPS_HI16', 'D_800BE2F3')], 48: [('R_MIPS_LO16', 'D_800BE2F3')], 72: [('R_MIPS_HI16', 'D_800BE2F4')], 76: [('R_MIPS_LO16', 'D_800BE2F4')], 188: [('R_MIPS_HI16', 'D_800BE2F0')], 192: [('R_MIPS_LO16', 'D_800BE2F0')], 204: [('R_MIPS_26', 'func_15007168')]}
HEADERS='#include <ultra64.h>\n\ntypedef union { u16 checksum; u8 bytes[0x70]; } SaveBlock33990;\nextern SaveBlock33990 D_800BE2F0;\nextern u8 D_800BE2F2, D_800BE2F3, D_800BE2F4[];\nextern OSMesgQueue D_800BE900;\ns32 func_151DD3A0(OSMesgQueue *, u8, u8 *, s32);\ns32 func_15007168();\n\n'
DECLARATIONS='s32 func_151DD3A0(OSMesgQueue *, u8, u8 *, s32);\n\n'
SELECTED='/* Read the save block and dispatch its checksum-mismatch handler. */\nvoid func_1500727C(void) {\n    u16 checksum;\n    s32 index;\n\n    func_151DD3A0(&D_800BE900, 0x44, D_800BE2F0.bytes, 0x70);\n    checksum = D_800BE2F2;\n    checksum = (checksum << 2) + 0xCC;\n    checksum += D_800BE2F3 << 3;\n    for (index = 4; index < 104; index++) {\n        checksum += D_800BE2F0.bytes[index] << (index & 3);\n    }\n    if (checksum != D_800BE2F0.checksum) {\n        func_15007168();\n    }\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected save checksum submission diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=228 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Save checksum load body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_1500727C() {\n    return 0;\n}':raise ValueError('Save checksum reader placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 if after.count('s32 func_1500727C();')!=1:raise ValueError('Save checksum reader prototype changed')
 return after.replace('s32 func_1500727C();','void func_1500727C(void);',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_1500727C.s. */\n','',1).replace('/* Generated placeholder declarations. */',DECLARATIONS+'/* Generated placeholder declarations. */',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Save checksum load snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Save checksum load frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Save checksum load predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Save checksum load live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Save checksum load named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Save checksum load symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Save checksum load metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Save checksum load frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Save checksum load original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Save checksum load strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Save checksum load named definitions changed')

NEW_GUARDS=[{'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x048', 'expected': '0x3C040000', 'replacement': '0x3C040000', 'expected_relocations': 'R_MIPS_HI16:D_800BE2F0', 'replacement_relocations': 'R_MIPS_HI16:D_800BE2F4', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x04C', 'expected': '0x01001025', 'replacement': '0x24840000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800BE2F4', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x050', 'expected': '0x24840004', 'replacement': '0x01001025', 'expected_relocations': 'R_MIPS_LO16:D_800BE2F0', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x064', 'expected': '0x246E0001', 'replacement': '0x306A0003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x068', 'expected': '0x306A0003', 'replacement': '0x246E0001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x080', 'expected': '0x24690002', 'replacement': '0x004B6021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x084', 'expected': '0x004B6021', 'replacement': '0x24690002', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x088', 'expected': '0x0198C821', 'replacement': '0x312A0003', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x08C', 'expected': '0x312A0003', 'replacement': '0x0198C821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_33990', 'function': 'func_1500727C', 'offset': '0x0C4', 'expected': '0x51390004', 'replacement': '0x53290004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed save checksum reader schedule and equivalent save-block data address', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited group guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Save checksum load scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('Save checksum load preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('Save checksum load binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='52bde2dafef420405c6840797d470a83326683bceab82172010b82880b6ec832'or rs!=ORIGINAL_BINDINGS:raise ValueError('Save checksum load result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1500727C.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_33990.c.o', 'make-shadow/src/game_33990.c.o.compact', 'make-shadow/src/game_33990.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Save checksum load artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save checksum load artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save checksum load raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Save checksum load evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Save checksum load Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_33990.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Save checksum load Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=10 or q['exclusions']!=0:raise ValueError('Save checksum load private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Save checksum load changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Save checksum load protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=57,reachable_words=57,frame=24,alignment_words=0,slot_words=57,strict_first_link_reproduced=True,guards=10,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='39ebdad6e3eaa00d89749cb454205050e791887495559b37453b9c9be3f3e200'
