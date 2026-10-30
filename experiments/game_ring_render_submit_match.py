"""Ring render submit: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151668B8','generated_193430'
ENTRY,ROM,BODY,SIZE=0x151668B8,0x193D68,224,232
SOURCE='conker/src/game/generated_193430.c'
OBJECT='conker/build/src/game/generated_193430.c.o'
ASM='conker/asm/193430.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-ring-render-submit-151668B8-match'
RODATA_SYMBOL=None
RAW_SHA='35e7308321d47e65c72da8bef3cb0870f78e7a1a823496b93667053c181fbc1a'
SNAPSHOT_SHA='b4b8ca281c29aebb0ddbab1c73770099e7091bb728b382c80e2111467bc8325c'
BEFORE_ELF_SHA='37015d725a53decd1dd3d5d0d04a96d76ee6811bc507d393161fcdcc3946b052'
TRUTH_SHA='63c62361a074575c8540e0673954e5cd65acbb41b6dbc4114b3bd6b99a45d684'
BINDINGS={4: [('R_MIPS_HI16', 'D_800DCE40')], 24: [('R_MIPS_LO16', 'D_800DCE40')], 8: [('R_MIPS_HI16', 'D_800DD228')], 20: [('R_MIPS_LO16', 'D_800DD228')], 12: [('R_MIPS_HI16', 'D_800DD220')], 16: [('R_MIPS_LO16', 'D_800DD220')], 48: [('R_MIPS_HI16', 'D_800903F4')], 52: [('R_MIPS_LO16', 'D_800903F4')], 96: [('R_MIPS_HI16', 'D_800DD224')], 100: [('R_MIPS_LO16', 'D_800DD224')], 108: [('R_MIPS_HI16', 'D_800DD230')], 124: [('R_MIPS_LO16', 'D_800DD230')], 148: [('R_MIPS_26', 'func_15094F70')], 156: [('R_MIPS_HI16', 'D_800A4AC8')], 168: [('R_MIPS_LO16', 'D_800A4AC8')], 160: [('R_MIPS_HI16', 'D_800D2C9C')], 164: [('R_MIPS_LO16', 'D_800D2C9C')], 200: [('R_MIPS_26', 'func_15142FBC')]}
ORIGINAL_BINDINGS={12: [('R_MIPS_HI16', 'D_800DD220')], 16: [('R_MIPS_LO16', 'D_800DD220')], 8: [('R_MIPS_HI16', 'D_800DD228')], 20: [('R_MIPS_LO16', 'D_800DD228')], 4: [('R_MIPS_HI16', 'D_800DCE40')], 24: [('R_MIPS_LO16', 'D_800DCE40')], 48: [('R_MIPS_HI16', 'D_800903F4')], 52: [('R_MIPS_LO16', 'D_800903F4')], 96: [('R_MIPS_HI16', 'D_800DD224')], 100: [('R_MIPS_LO16', 'D_800DD224')], 108: [('R_MIPS_HI16', 'D_800DD230')], 124: [('R_MIPS_LO16', 'D_800DD230')], 148: [('R_MIPS_26', 'func_15094F70')], 160: [('R_MIPS_HI16', 'D_800D2C9C')], 164: [('R_MIPS_LO16', 'D_800D2C9C')], 156: [('R_MIPS_HI16', 'D_800A4AC8')], 168: [('R_MIPS_LO16', 'D_800A4AC8')], 200: [('R_MIPS_26', 'func_15142FBC')]}
HEADERS='#include <ultra64.h>\ntypedef struct {\n    u32 unk0;\n    u8 unk4;\n    u8 pad5;\n    u16 unk6;\n    u16 unk8;\n    u8 unkA;\n    u8 unkB;\n} structC1D70Source;\nextern s16 D_800DCE40;\nextern s32 D_800DD220, D_800DD224;\nextern u8 *D_800DD228;\nextern u8 D_800DD230[], D_800903F4[];\nextern u32 D_800D2C9C, D_800A4AC8[];\ns32 func_15094F70(s32, structC1D70Source *, s32, u8 *, s32, s32, s32, s32, s32);\nGfx *func_15142FBC(Gfx *, u32, u32, u8 *);\n\n'
DECLARATIONS=''
SELECTED='/* Advance the signed ring offset and submit its display-list packet. */\nGfx *func_151668B8(Gfx *commands, s32 unusedIndex, s32 unusedPacked, s32 unusedHighHalf) {\n    u8 sync;\n\n    D_800DD228 = D_800903F4;\n    D_800DD220 = D_800DCE40;\n    D_800DCE40 += 0x80;\n    sync = 1;\n    if (D_800DCE40 >= 0x500) {\n        D_800DCE40 = 0;\n    }\n    D_800DD224 = 1;\n    commands = (Gfx *)func_15094F70((s32)commands, (structC1D70Source *)D_800DD228,\n                                  D_800DD220, D_800DD230, 0, 0, 0, D_800DD224, 3);\n    return func_15142FBC(commands, D_800D2C9C | 0x80000 | 0x2CA0,\n                         D_800A4AC8[7] | D_800A4AC8[6], &sync);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected ring render submit diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Ring render submit body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_151668B8() {\n    return 0;\n}':raise ValueError('Ring render placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n'
 if not after.startswith(prefix):raise ValueError('Ring render owner includes changed')
 return HEADERS+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Ring render submit snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Ring render submit frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Ring render submit predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Ring render submit live input differs: '+name)
    return values

METADATA_GROUPS=((2915556, ('D_800DCE40', 'D_8008F890'), (1, 0)),)
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Ring render submit named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Ring render submit symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Ring render submit metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Ring render submit frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Ring render submit original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Ring render submit strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Ring render submit named definitions changed')

NEW_GUARDS=[{'filename': 'generated_193430', 'function': 'func_151668B8', 'offset': '0x0AC', 'expected': '0x8C6F0018', 'replacement': '0x8C6A001C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed render-mode register roles and independent table reads', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_151668B8', 'offset': '0x0B0', 'expected': '0x8C78001C', 'replacement': '0x8C6B0018', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed render-mode register roles and independent table reads', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_151668B8', 'offset': '0x0B8', 'expected': '0x00A16825', 'replacement': '0x00A1C025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed render-mode register roles and independent table reads', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_151668B8', 'offset': '0x0BC', 'expected': '0x35A52CA0', 'replacement': '0x37052CA0', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed render-mode register roles and independent table reads', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_193430', 'function': 'func_151668B8', 'offset': '0x0CC', 'expected': '0x01F83025', 'replacement': '0x014B3025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed render-mode register roles and independent table reads', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    import csv,io
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited ring render guard prefix changed')
    if not before.endswith(b'\n'):raise ValueError('Inherited guard newline changed')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(NEW_GUARDS[0]),lineterminator='\n');writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()


def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('Ring render submit scope changed')
 checked_payload(raw,bindings);result=bytearray(raw);rs={a:list(v)for a,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],16)
  if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],16):raise ValueError('Ring render submit preimage changed')
  expected=';'.join(k+':'+s for k,s in rs.get(at,[]))or'-'
  if expected!=row['expected_relocations']:raise ValueError('Ring render submit binding changed')
  struct.pack_into('>I',result,at,int(row['replacement'],16));rs.pop(at,None)
  if row['replacement_relocations']!='-':rs[at]=[tuple(x.split(':',1))for x in row['replacement_relocations'].split(';')]
 if sha(result)!='2fa746b4e019496724d2ae09bb65d4c3264098e29ba58f9e37628a162ade443e'or rs!=ORIGINAL_BINDINGS:raise ValueError('Ring render submit result changed')
 return bytes(result),rs

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151668B8.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_193430.c.o', 'make-shadow/src/game/generated_193430.c.o.compact', 'make-shadow/src/game/generated_193430.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Ring render submit artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ring render submit artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ring render submit raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Ring render submit evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Ring render submit Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_193430.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Ring render submit Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=5 or q['exclusions']!=0:raise ValueError('Ring render submit private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Ring render submit changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Ring render submit protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=56,alignment_words=2,slot_words=58,strict_first_link_reproduced=True,guards=5,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='216b34dd6fde66c1e9def4a18862d37f4eccb06374340369489ccde2d4e7d831'
