"""Active actor alternate-key lookup: semantic C, linked address aliases and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
from tools import pad_generated_object
sys.modules.setdefault("pad_generated_object",pad_generated_object)
from tools.pad_c_object import emit_padded_assembly as pad_root_object
def emit_padded_assembly(obj,asm,word_patches_path=None,filename=None,rodata_symbol=None):
 return pad_root_object(obj,Path(asm).parents[3]/"retail_layout.us.txt",filename,rodata_symbol=rodata_symbol,word_patches_path=word_patches_path)
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1505EFD0','game_83300'
ENTRY,ROM,BODY,SIZE=0x1505EFD0,0x8C480,220,220
SOURCE='conker/src/game_83300.c'
OBJECT='conker/build/src/game_83300.c.o'
ASM='conker/asm/nonmatchings/game_83300/func_1505EFD0.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-active-actor-secondary-key-lookup-match'
RODATA_SYMBOL=None
RAW_SHA='7556e520af3a12607fe23600e5bccc3c4fd0d54de09b059442a575c1d8fc9892'
SNAPSHOT_SHA='db2414e8cbc5185bdf6508286525483d3a9fdd675e677b52d1f9bea4a8b21086'
BEFORE_ELF_SHA='8b77b8e756c20baeb8facf090980db0a669c4d1b00f207d5003c916ca4278133'
TRUTH_SHA='7dbf3329198aad811cca558f0381f48a92ae437fc885af535b448d5d4b5e3009'
BINDINGS={0: [('R_MIPS_HI16', 'D_800CC2D0')], 4: [('R_MIPS_LO16', 'D_800CC2D0')], 20: [('R_MIPS_HI16', 'D_800CC2D0')], 24: [('R_MIPS_LO16', 'D_800CC2D0')], 28: [('R_MIPS_HI16', 'D_800CC2D0')], 44: [('R_MIPS_LO16', 'D_800CC2D0')], 8: [('R_MIPS_HI16', 'D_800CC2D0')], 12: [('R_MIPS_LO16', 'D_800CC2D0')]}
ORIGINAL_BINDINGS={0: [('R_MIPS_HI16', 'D_800CC2D0')], 4: [('R_MIPS_LO16', 'D_800CC2D0')], 8: [('R_MIPS_HI16', 'D_800CC5FC')], 12: [('R_MIPS_LO16', 'D_800CC5FC')], 20: [('R_MIPS_HI16', 'D_800CC3F7')], 24: [('R_MIPS_LO16', 'D_800CC3F7')], 28: [('R_MIPS_HI16', 'D_800CC2D0')], 44: [('R_MIPS_LO16', 'D_800CC2D0')]}
HEADERS='#include <ultra64.h>\n#include "variables.h"\n'
DECLARATIONS=''
SELECTED='/* Return the first active actor whose alternate key matches, excluding reserved slot 25. */\nstruct127 *func_1505EFD0(s32 key) {\n    struct127 *actor;\n    s32 index;\n\n    actor = D_800CC2D0;\n    for (index = 0; index < 25; actor++, index++) {\n        if (actor->interaction_state != 0 && actor->unk127 == key) {\n            return actor;\n        }\n    }\n    return NULL;\n}\n'

def check_owner_diagnostics(text):
    def norm(s):return re.sub(r'line \d+','line #',re.sub(r'[^\s:]+\.c','<unit>',s))
    before=(Path.cwd()/BUILD/'before-owner-diagnostics.txt').read_text()
    if norm(text)!=norm(before) or text.count('Warning 712:')!=8:raise ValueError('Actor lookup inherited diagnostics changed')
    return 8


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=220 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Active actor alternate-key lookup body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1505EFD0() {\n    return 0;\n}':raise ValueError('Actor lookup placeholder changed')
    result=before[:start]+SELECTED.rstrip()+before[end:]
    return result.replace('s32 func_1505EFD0();','struct127 *func_1505EFD0(s32);').replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_1505EFD0.s. */\n','')



def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Active actor alternate-key lookup snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Active actor alternate-key lookup frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Active actor alternate-key lookup predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Active actor alternate-key lookup live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Active actor alternate-key lookup named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Active actor alternate-key lookup symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Active actor alternate-key lookup metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Active actor alternate-key lookup frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Active actor alternate-key lookup original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Active actor alternate-key lookup strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Active actor alternate-key lookup named definitions changed')

NEW_GUARDS=[]

def guard_manifest(before):
    if sha(before)!='4ad9be793b0ae038d412987b239137e8666dcd4bc2cb79432c22592d53ea7cea':raise ValueError('Inherited guard manifest changed')
    return before





def normalized_payload(raw,bindings):
    return checked_payload(raw,bindings)



ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1505EFD0.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-best-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_83300.c.o', 'make-shadow/src/game_83300.c.o.compact', 'make-shadow/src/game_83300.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Active actor alternate-key lookup artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active actor alternate-key lookup artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active actor alternate-key lookup raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Active actor alternate-key lookup evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Active actor alternate-key lookup Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_83300.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Active actor alternate-key lookup Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Active actor alternate-key lookup private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Active actor alternate-key lookup changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Active actor alternate-key lookup protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=55,frame=0,alignment_words=0,slot_words=55,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
