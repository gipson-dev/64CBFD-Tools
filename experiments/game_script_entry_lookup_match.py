"""Script entry lookup: semantic C, checked normalization and literal image audit."""
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
    if asm.name!='func_1507BB28.s'or filename!='game_A28B0':raise ValueError('Script-lookup padder scope changed')
    return _emit(obj,asm.parents[3]/'retail_layout.us.txt',filename,word_patches_path=word_patches_path)

from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1507BB28','game_A28B0'
ENTRY,ROM,BODY,SIZE=0x1507BB28,0xA8FD8,236,236
SOURCE='conker/src/game_A28B0.c'
OBJECT='conker/build/src/game_A28B0.c.o'
ASM='conker/asm/nonmatchings/game_A28B0/func_1507BB28.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-script-entry-lookup-1507BB28-match'
RODATA_SYMBOL=None
RAW_SHA='6e6708dc9aa34dde6b6553b7c229d306a9faed37073c4dc7a64f75f19b191485'
SNAPSHOT_SHA='2dcd26d95f3a98d1f7e51649a9a5c63c4d0def691885bd615c12cec7758ea114'
BEFORE_ELF_SHA='c5097966846c828929e45c2f7697ec3a0e186734d0e571b4484a26fbf1ddf8ba'
TRUTH_SHA='08985e269746a31fa60158d97e04d96ee7c15c2aa1f5d667edf7bb18fec0e59c'
BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 12: [('R_MIPS_HI16', 'D_800D1588')], 28: [('R_MIPS_LO16', 'D_800D1588')], 40: [('R_MIPS_HI16', 'D_8009A120')], 48: [('R_MIPS_LO16', 'D_8009A120')], 56: [('R_MIPS_HI16', 'D_8009A120')], 72: [('R_MIPS_LO16', 'D_8009A120')], 100: [('R_MIPS_HI16', 'D_80086A88')], 104: [('R_MIPS_LO16', 'D_80086A88')]}
ORIGINAL_BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 12: [('R_MIPS_HI16', 'D_800D1588')], 28: [('R_MIPS_LO16', 'D_800D1588')], 40: [('R_MIPS_HI16', 'D_8009A120')], 48: [('R_MIPS_LO16', 'D_8009A120')], 56: [('R_MIPS_HI16', 'D_8009A120')], 72: [('R_MIPS_LO16', 'D_8009A120')], 100: [('R_MIPS_HI16', 'D_80086A88')], 104: [('R_MIPS_LO16', 'D_80086A88')], 120: [('R_MIPS_HI16', 'D_80086A88')], 132: [('R_MIPS_LO16', 'D_80086A88')]}
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct {\n    struct216 *script;\n    u8 id;\n    u8 reserved05[3];\n} ScriptLookupEntry;\nextern struct127 *D_800D154C;\nextern s32 D_800D1588[187];\nextern ScriptLookupEntry D_80086A88[];\nextern struct216 D_8009A120;\n\n'
DECLARATIONS=''
SELECTED='/* Return the script address for the requested ID, using the global fallback. */\ns32 func_1507BB28(s32 unused, s32 id) {\n    u8 *resource;\n    ScriptLookupEntry *table;\n    ScriptLookupEntry *cursor;\n    s32 index;\n\n    resource = (u8 *)D_800D1588[D_800D154C->id];\n    if (resource == NULL) {\n        return (s32)&D_8009A120;\n    }\n    table = *(ScriptLookupEntry **)(resource - 0x10);\n    if (table == NULL) {\n        return (s32)&D_8009A120;\n    }\n    index = 0;\n    cursor = table;\n    while (cursor->id != id) {\n        if (cursor->script == NULL) {\n            table = D_80086A88;\n            cursor = table;\n            index = 0;\n            while (cursor->id != id) {\n                if (table->script == NULL) {\n                    for (;;) {}\n                }\n                cursor++;\n                table++;\n                index++;\n            }\n            return (s32)D_80086A88[index].script;\n        }\n        cursor++;\n        index++;\n    }\n    return (s32)table[index].script;\n}\n'

def check_owner_diagnostics(text):
    normalized=re.sub(r'build/[^,]+, line [0-9]+','<owner>',text)
    if hashlib.sha256(normalized.encode()).hexdigest()!='65e220a166d92e78e6967ea003441928c13b4ecd72296046b653b79d4724d5d2':raise ValueError('Inherited script-lookup owner diagnostics changed')
    return 14


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=232 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Script entry lookup body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    a,b=function_span(before,FUNCTION)
    if before[a:b]!='s32 func_1507BB28() {\n    return 0;\n}':raise ValueError('Script lookup placeholder changed')
    declarations=HEADERS[HEADERS.index('typedef struct'):].replace('extern struct127 *D_800D154C;\n','').replace('extern s32 D_800D1588[187];\n','')
    after=before[:a]+declarations+SELECTED.rstrip()+before[b:]
    return after.replace('// scary loops\n','',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_A28B0/func_1507BB28.s. */\n','',1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Script entry lookup snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Script entry lookup frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Script entry lookup predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Script entry lookup live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Script entry lookup named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Script entry lookup symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Script entry lookup metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Script entry lookup frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Script entry lookup original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Script entry lookup strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Script entry lookup named definitions changed')

NEW_GUARDS=[{'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x058', 'expected': '0x50B9001F', 'replacement': '0x50B90020', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rebase branch around restored address word', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x06C', 'expected': '0x55000015', 'replacement': '0x55000016', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rebase branch around restored address word', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x078', 'expected': '0x00C01825', 'replacement': '0x3C0A0000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_HI16:D_80086A88', 'note': 'Restore closed fallback address materialization', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x07C', 'expected': '0x00C01025', 'replacement': '0x00002025', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Restore closed fallback address materialization', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x080', 'expected': '0x10A9000B', 'replacement': '0x10A9000C', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rebase branch around restored address word', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x084', 'expected': '0x00002025', 'replacement': '0x25430000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_80086A88', 'note': 'Restore closed fallback address materialization', 'insert_after': '0x00601025', 'insert_after_relocations': '-', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x088', 'expected': '0x8C6A0000', 'replacement': '0x8C6B0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed fallback null-check register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x08C', 'expected': '0x55400004', 'replacement': '0x55600004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed fallback null-check register allocation', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x0A0', 'expected': '0x24420008', 'replacement': '0x24840001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent script index and cursor updates', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x0A4', 'expected': '0x24630008', 'replacement': '0x24420008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent script index and cursor updates', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x0AC', 'expected': '0x24840001', 'replacement': '0x24630008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent script index and cursor updates', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x0C4', 'expected': '0x24420008', 'replacement': '0x24840001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent script index and cursor updates', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x0C8', 'expected': '0x24840001', 'replacement': '0x24420008', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize independent script index and cursor updates', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507BB28', 'offset': '0x0CC', 'expected': '0x54AFFFE5', 'replacement': '0x54AFFFE4', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Rebase branch around restored address word', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited script-lookup guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Script-lookup guard already present')
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings,owner=OWNER,function=FUNCTION):
    if owner!=OWNER or function!=FUNCTION:raise ValueError('Script lookup normalization scope changed')
    checked_payload(raw,bindings);words=struct.unpack('>58I',raw);rows={int(row['offset'],0):row for row in NEW_GUARDS};out=[];rs={}
    for i,word in enumerate(words):
        at=i*4;row=rows.get(at)
        if at in bindings:rs[len(out)*4]=bindings[at]
        if row:
            if word!=int(row['expected'],0)or at in bindings:raise ValueError('Script lookup expected word/binding changed')
            word=int(row['replacement'],0)
            if row['replacement_relocations']!='-':rs[len(out)*4]=[tuple(row['replacement_relocations'].split(':',1))]
        out.append(word)
        if row and row['insert_after']:out.append(int(row['insert_after'],0))
    result=struct.pack('>59I',*out)
    if sha(result)!=NORMALIZED_SHA or rs!=ORIGINAL_BINDINGS:raise ValueError('Script lookup normalized bytes/bindings changed')
    return result,rs

NORMALIZED_SHA='0977e9c81a7e04675f954fca850a53b6c44ab7ef68edaf36d126cf62816f8197'

ARTIFACTS=('before-padded.o', 'qualified-padded.o', 'proposed-owner.c', 'selected-final.o', 'original-func_1507BB28.o', 'first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'new-guard-rows.json', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected-final.c', 'selected-final-processed.c', 'selected-final.o', 'selected-final-diagnostics.txt', 'selected-semantic-input.c', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_A28B0.c.o', 'make-shadow/src/game_A28B0.c.o.compact', 'make-shadow/src/game_A28B0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Script entry lookup artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Script entry lookup artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Script entry lookup raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Script entry lookup evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Script entry lookup Make/diagnostics evidence changed: '+name)
    if(output/'selected-final-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game_A28B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Script entry lookup Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=14 or q['exclusions']!=0:raise ValueError('Script entry lookup private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Script entry lookup changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Script entry lookup protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=59,reachable_words=55,frame=0,alignment_words=0,slot_words=59,strict_first_link_reproduced=True,guards=14,insertions=1,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

GUARD_SHA='0e1dcd21b2871b8c63c7e128de0c89befa9870d68748dbb979f048976a5728e9'
