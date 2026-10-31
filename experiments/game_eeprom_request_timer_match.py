"""EEPROM request timer: semantic C, checked normalization and literal image audit."""
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
FUNCTION,OWNER='func_151DCEF0','generated_20A3A0'
ENTRY,ROM,BODY,SIZE=0x151DCEF0,0x20A3A0,232,232
SOURCE='conker/src/game/generated_20A3A0.c'
OBJECT='conker/build/src/game/generated_20A3A0.c.o'
ASM='conker/asm/20A3A0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-eeprom-request-timer-151DCEF0-match'
RODATA_SYMBOL=None
RAW_SHA='909077782d5b7404e0e012d7a0dbe04922b60491619d8ad2117f79ae7097e969'
SNAPSHOT_SHA='93299f12631cf880117a7824c817c01fae31570634b95d1909228a7ba74725e9'
BEFORE_ELF_SHA='fa76db5c79433c9fa27238794dfdcfd76a6fe3f3bc2031ed75107b78de90a76b'
TRUTH_SHA='fffb51e0bdc1cb5deb7caee59f4c36ac0d29025dddde6201298f89f7ea2ba3fc'
BINDINGS={24: [('R_MIPS_26', 'func_151DCFD8')], 40: [('R_MIPS_26', 'func_151DCFD8')], 64: [('R_MIPS_HI16', 'D_800E0A20')], 68: [('R_MIPS_LO16', 'D_800E0A20')], 76: [('R_MIPS_HI16', 'D_800E0A24')], 80: [('R_MIPS_LO16', 'D_800E0A24')], 84: [('R_MIPS_HI16', 'D_800E0A28')], 92: [('R_MIPS_LO16', 'D_800E0A28')], 96: [('R_MIPS_HI16', 'D_800E0A2C')], 128: [('R_MIPS_LO16', 'D_800E0A2C')], 100: [('R_MIPS_HI16', 'D_8002BD10')], 112: [('R_MIPS_LO16', 'D_8002BD10')], 104: [('R_MIPS_HI16', 'D_8002BD10')], 108: [('R_MIPS_LO16', 'D_8002BD10')], 124: [('R_MIPS_26', '__ll_mul')], 148: [('R_MIPS_26', '__ull_div')], 172: [('R_MIPS_HI16', 'D_80042A58')], 192: [('R_MIPS_LO16', 'D_80042A58')], 156: [('R_MIPS_HI16', '__osEepromTimerQ')], 168: [('R_MIPS_LO16', '__osEepromTimerQ')], 160: [('R_MIPS_HI16', 'D_80042A90')], 164: [('R_MIPS_LO16', 'D_80042A90')], 208: [('R_MIPS_26', 'osSetTimer')]}
ORIGINAL_BINDINGS={24: [('R_MIPS_26', 'func_151DCFD8')], 40: [('R_MIPS_26', 'func_151DCFD8')], 64: [('R_MIPS_HI16', 'D_800E0A20')], 68: [('R_MIPS_LO16', 'D_800E0A20')], 76: [('R_MIPS_HI16', 'D_800E0A24')], 80: [('R_MIPS_LO16', 'D_800E0A24')], 84: [('R_MIPS_HI16', 'D_800E0A28')], 92: [('R_MIPS_LO16', 'D_800E0A28')], 104: [('R_MIPS_HI16', 'D_8002BD14')], 108: [('R_MIPS_LO16', 'D_8002BD14')], 100: [('R_MIPS_HI16', 'D_8002BD10')], 112: [('R_MIPS_LO16', 'D_8002BD10')], 124: [('R_MIPS_26', '__ll_mul')], 96: [('R_MIPS_HI16', 'D_800E0A2C')], 128: [('R_MIPS_LO16', 'D_800E0A2C')], 148: [('R_MIPS_26', '__ull_div')], 160: [('R_MIPS_HI16', 'D_80042A90')], 164: [('R_MIPS_LO16', 'D_80042A90')], 156: [('R_MIPS_HI16', '__osEepromTimerQ')], 168: [('R_MIPS_LO16', '__osEepromTimerQ')], 172: [('R_MIPS_HI16', 'D_80042A58')], 192: [('R_MIPS_LO16', 'D_80042A58')], 208: [('R_MIPS_26', 'osSetTimer')]}
HEADERS='#include <ultra64.h>\nextern OSMesgQueue *D_800E0A20;\nextern u8 D_800E0A24;\nextern u8 *D_800E0A28;\nextern s32 D_800E0A2C;\nextern u64 D_8002BD10;\nextern OSTimer D_80042A58;\nextern OSMesg D_80042A90;\nextern OSMesgQueue __osEepromTimerQ;\ns32 func_151DCFD8(s32 mode);\n\n'
DECLARATIONS=''
SELECTED='/* Drain pending EEPROM work, publish the request, then arm its timer. */\ns32 func_151DCEF0(OSMesgQueue *queue, s32 address, void *buffer, s32 length) {\n    while (func_151DCFD8(1) != 0) {\n    }\n    D_800E0A20 = queue;\n    D_800E0A24 = (u8)address;\n    D_800E0A28 = buffer;\n    D_800E0A2C = length;\n    return osSetTimer(&D_80042A58, (12000ULL * D_8002BD10) / 1000000ULL,\n               0, &__osEepromTimerQ, &D_80042A90);\n}\n'

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected EEPROM request timer diagnostics')
    return 0


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('EEPROM request timer body/bindings changed')
    return raw,bindings

def recovered_owner(before):
 a,b=function_span(before,FUNCTION)
 if before[a:b]!='s32 func_151DCEF0() {\n    return 0;\n}':raise ValueError('Actor command placeholder changed')
 after=before[:a]+SELECTED.rstrip()+before[b:]
 prefix='#include <ultra64.h>\n'
 if not after.startswith(prefix):raise ValueError('Owner includes changed')
 headers=HEADERS.replace('s32 func_151DCFD8(s32 mode);','/* Signed mode argument is qualified against retail; poller remains pending. */\n s32 func_151DCFD8();'.replace('\n ','\n'))
 return headers+after[len(prefix):]


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('EEPROM request timer snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('EEPROM request timer frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('EEPROM request timer predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('EEPROM request timer live input differs: '+name)
    return values

METADATA_GROUPS=((2738372, ('func_15085420', 'D_8009ED80'), (1, 0)), (2795780, ('D_800E0A2C', 'D_8009921C', '.L15032B20_game_data'), (1, 2, 0)), (2846340, ('func_15103E40', 'D_8009ED6C'), (1, 0)), (2855028, ('D_800E0A28', 'D_80099218', 'D_800A3518', 'D_80089180'), (1, 2, 3, 0)), (2857236, ('D_800E0A24', 'D_80099214', 'D_800A3514', 'D_8009EC14'), (1, 2, 3, 0)), (2880660, ('D_800E0A20', 'D_80099210', 'D_800A3510'), (1, 2, 0)), (2897476, ('D_80042A90', 'D_8008F470'), (1, 0)))
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('EEPROM request timer named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('EEPROM request timer symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('EEPROM request timer metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('EEPROM request timer frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('EEPROM request timer original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('EEPROM request timer strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('EEPROM request timer named definitions changed')

NEW_GUARDS=[{'filename': 'generated_20A3A0', 'function': 'func_151DCEF0', 'offset': '0x03C', 'expected': '0x8FAF002C', 'replacement': '0x93AF002F', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize EEPROM byte-home load and low-clock alias +4', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_20A3A0', 'function': 'func_151DCEF0', 'offset': '0x068', 'expected': '0x3C070000', 'replacement': '0x3C070000', 'expected_relocations': 'R_MIPS_HI16:D_8002BD10', 'replacement_relocations': 'R_MIPS_HI16:D_8002BD14', 'note': 'Normalize EEPROM byte-home load and low-clock alias +4', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'generated_20A3A0', 'function': 'func_151DCEF0', 'offset': '0x06C', 'expected': '0x8CE70004', 'replacement': '0x8CE70000', 'expected_relocations': 'R_MIPS_LO16:D_8002BD10', 'replacement_relocations': 'R_MIPS_LO16:D_8002BD14', 'note': 'Normalize EEPROM byte-home load and low-clock alias +4', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
 import csv,io
 if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard manifest changed')
 reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
 if any(row['function']==FUNCTION for row in reader):raise ValueError('Target guards already installed')
 out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\n').writerows(NEW_GUARDS)
 return before+out.getvalue().encode()

def validate_alias(symbols):
 if symbols['D_8002BD14']!=symbols['D_8002BD10']+4:raise ValueError('Low clock alias must be +4')

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
 if owner!=OWNER or function!=FUNCTION:raise ValueError('EEPROM request scope changed')
 checked_payload(raw,bindings);out=bytearray(raw);rels={at:list(v)for at,v in bindings.items()}
 for row in NEW_GUARDS:
  at=int(row['offset'],0);er=row['expected_relocations'];rr=row['replacement_relocations'];expected=[]if er=='-'else[tuple(er.split(':',1))]
  if struct.unpack_from('>I',raw,at)[0]!=int(row['expected'],0)or bindings.get(at,[])!=expected:raise ValueError('Guard input or binding changed')
  struct.pack_into('>I',out,at,int(row['replacement'],0))
  if rr!='-':rels[at]=[tuple(rr.split(':',1))]
 if len(out)!=232 or sha(out)!=NORMALIZED_SHA or rels!=ORIGINAL_BINDINGS:raise ValueError('Normalized body/bindings changed')
 return bytes(out),rels

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_151DCEF0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game/generated_20A3A0.c.o', 'make-shadow/src/game/generated_20A3A0.c.o.compact', 'make-shadow/src/game/generated_20A3A0.c.o.padded.s', 'native-runtime.json')

def verify_prepared(output):
    for path,wanted in json.loads((output/'native-runtime.json').read_text())['files'].items():
        if sha(Path(path).read_bytes())!=wanted:raise ValueError('Prepared native runtime changed: '+path)
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('EEPROM request timer artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('EEPROM request timer artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('EEPROM request timer raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('EEPROM request timer evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('EEPROM request timer Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_20A3A0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('EEPROM request timer Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=3 or q['exclusions']!=0:raise ValueError('EEPROM request timer private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('EEPROM request timer changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('EEPROM request timer protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=58,reachable_words=58,frame=40,alignment_words=0,slot_words=58,strict_first_link_reproduced=True,guards=3,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='400275b225bf630534391a61b4095bbcb95f10744b7a3abcd6a2e5ebbc931fc1'

NORMALIZED_SHA='16850a0fffd7694ae2d957fb3b1b11fd53c94279de8ba6ff751aea404abdf656'
