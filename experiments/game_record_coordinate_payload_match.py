"""Record coordinate payload: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
import tools.pad_generated_object as _pad
sys.modules.setdefault("pad_generated_object",_pad)
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1500A7E8','game_36680'
ENTRY,ROM,BODY,SIZE=0x1500A7E8,0x37C98,224,224
SOURCE='conker/src/game_36680.c'
OBJECT='conker/build/src/game_36680.c.o'
ASM='conker/asm/nonmatchings/game_36680/func_1500A7E8.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-point-selector-payload-1500A7E8-match'
RODATA_SYMBOL=None
RAW_SHA='fc4e6de9581b24f4916a32c7fa9e9dc9c4e27abcb0905601b518e8e0685c6b94'
SNAPSHOT_SHA='6dc4ae1062565affcd5fcfecae5189c5edef90668dace684c931ddcea51817df'
BEFORE_ELF_SHA='a93cac0ec3ca52b364e0972e6fd2a81946dd9269728ad3732a8ba5bcede75878'
TRUTH_SHA='58baa700a775668e9e06aae874d22a07584c3268e4c297733f111366a096b495'
BINDINGS={16: [('R_MIPS_HI16', 'D_80082BF4')], 20: [('R_MIPS_LO16', 'D_80082BF4')], 44: [('R_MIPS_26', 'func_151149AC')], 180: [('R_MIPS_26', 'func_1516037C')], 200: [('R_MIPS_26', 'memcpy')]}
ORIGINAL_BINDINGS={16: [('R_MIPS_HI16', 'D_80082BF4')], 20: [('R_MIPS_LO16', 'D_80082BF4')], 44: [('R_MIPS_26', 'func_151149AC')], 180: [('R_MIPS_26', 'func_1516037C')], 200: [('R_MIPS_26', 'memcpy')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct { u8 values[6]; } EffectPointIds36680;\ntypedef struct {\n    f32 unk0;\n    f32 unk4;\n    u8 *record;\n    f32 unkC;\n    f32 unk10;\n    f32 unk14;\n} UnkB060C;\nextern EffectPointIds36680 D_80082BF4;\nu8 *func_151149AC(u8);\nstruct225 *func_1516037C(Header *, struct226 *, s32, u8, s32);\nvoid *memcpy(void *, const void *, u32);\n\n'
DECLARATIONS='typedef struct { u8 values[6]; } EffectPointIds36680;\nextern EffectPointIds36680 D_80082BF4;\nu8 *func_151149AC(u8);\n\n'
SELECTED="/* Resolve commands 0x50..0x55's record and spawn its coordinate payload. */\nvoid func_1500A7E8(struct226 *actor, s32 command) {\n    Header header;\n    UnkB060C payload;\n    struct225 *effect;\n    EffectPointIds36680 ids = D_80082BF4;\n\n    payload.record = func_151149AC(ids.values[command - 0x50]);\n    if (payload.record != NULL) {\n        payload.unk0 = -400.0f;\n        payload.unk4 = 4.0f;\n        payload.unkC = (f32)*(s16 *)(payload.record + 0x10);\n        payload.unk10 = (f32)*(s16 *)(payload.record + 0x12);\n        payload.unk14 = (f32)*(s16 *)(payload.record + 0x14);\n        header.unk0 = 0;\n        header.unk1 = 23;\n        header.unk2 = 300;\n        header.unk4 = 0;\n        effect = func_1516037C(&header, actor, sizeof(payload), 255, 1);\n        if (effect != NULL) {\n            memcpy((u8 *)effect + 0x18, &payload, sizeof(payload));\n        }\n    }\n}\n"

from tools.experiments.game_selector_payload_effect_match import check_owner_diagnostics


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=224 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('State-completion body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1500A7E8() {\n    return 0;\n}':raise ValueError('Coordinate payload placeholder changed')
    after=before[:start]+SELECTED.rstrip()+before[end:]
    after=after.replace('s32 func_1500A7E8();','void func_1500A7E8(struct226 *actor, s32 command);',1).replace('/* Generated placeholder declarations. */',DECLARATIONS+'/* Generated placeholder declarations. */',1)
    start=after.index('// void func_1500A7E8(');end=after.index('void func_1500A8C8(',start)
    return(after[:start]+after[end:]).replace('/* Non-matching C placeholders for asm/nonmatchings/game_36680/func_1500A7E8.s. */\n','',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record coordinate payload snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record coordinate payload frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record coordinate payload predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record coordinate payload live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Record coordinate payload named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Record coordinate payload symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Record coordinate payload metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record coordinate payload frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record coordinate payload original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record coordinate payload strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record coordinate payload named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='f368b633dd03cd6b8ce55d5285be0ecb1884bfa06718d91b0417907bdaede5df':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1500A7E8.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-layout-best.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_36680.c.o', 'make-shadow/src/game_36680.c.o.compact', 'make-shadow/src/game_36680.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record coordinate payload artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record coordinate payload artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record coordinate payload raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record coordinate payload evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record coordinate payload Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_36680.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record coordinate payload Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Record coordinate payload private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record coordinate payload changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record coordinate payload protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=56,reachable_words=56,frame=80,alignment_words=0,slot_words=56,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
