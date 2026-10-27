"""Live type-2 actor transition start: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15063570','generated_90840'
ENTRY,ROM,BODY,SIZE=0x15063570,0x90A20,184,184
SOURCE='conker/src/game/generated_90840.c'
OBJECT='conker/build/src/game/generated_90840.c.o'
ASM='conker/asm/90840.s'
BUILD='conker/build/game-actor-transition-start-match'
RAW_SHA='dd042b5f73285ac02fde20b2ee9fc2c9529723e0833712bbd7cfe9122b88c478'
SNAPSHOT_SHA='f4e30148c071def73f2c4ef178f0d1a1a3b42b83a9f7815e8c7387fe838bc89d'
BEFORE_ELF_SHA='9827542129263cc9aadf4736a9c8459ef15f0d388ac22ab66beaff64ae4354b6'
TRUTH_SHA='94a5ec149e0bb269a589cbb841e1adf6e361e32fd643592abd16433f117172c7'
PARENT,PARENT_ROM,PARENT_SIZE=0x15097A8C,0xC4F3C,8584
TABLE,TABLE_ROM=0x8009DF50,0x242A10
SPAWN,ANIMATE,GET_ACTOR,OTHER=0x15083568,0x1505E650,0x1505EEF4,0x15063404
BINDINGS={4:[('R_MIPS_HI16','D_800CC2D0')],8:[('R_MIPS_LO16','D_800CC2D0')],108:[('R_MIPS_26','func_15083568')],160:[('R_MIPS_26','func_1505E650')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="extern struct127 D_800CC2D0[];\nu8 *func_15083568(u8 *, s32, f32, s32);\nvoid func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);\n"
SELECTED="/* Start the actor's transition state and its animation providers. */\nvoid func_15063570(struct127 *actor) {\n    s32 index = ((s32)actor - (s32)D_800CC2D0) / (s32)sizeof(struct127);\n    struct127 *entry = &D_800CC2D0[(u32)index];\n\n    entry->unk31C->unk78 = 0x3B;\n    entry->unk31C->unk11A = 2;\n    func_15083568((u8 *)actor, 0x89, 1.0f, 0);\n    actor->disable_jump = 20;\n    actor->disable_run = 0;\n    actor->unk83 = 0;\n    func_1505E650((u8 *)actor, 0x221, 1.0f, 0.0f, 0.0f, 0.0f, 0);\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor transition start body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15063570() {\n    return 0;\n}'
    anchor='void func_150836CC(struct127 *arg0, s32 arg1);\n'
    if before.count(stub)!=1 or before.count(anchor)!=1 or 'func_15083568'in before or 'func_1505E650'in before:raise ValueError('Actor transition start placeholder/declarations changed')
    declarations='u8 *func_15083568(u8 *, s32, f32, s32);\nvoid func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);\n'
    return before.replace(anchor,anchor+declarations,1).replace(stub,SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor transition start snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor transition start frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor transition start predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor transition start live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor transition start strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor transition start original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY);return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor transition start image differs from literal body/size prediction')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15063570.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_90840.c","make-shadow/src/game/generated_90840.c.o","make-shadow/src/game/generated_90840.c.o.compact","make-shadow/src/game/generated_90840.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor transition start artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor transition start artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor transition start raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor transition start evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor transition start Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Actor transition start expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_90840.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor transition start Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Actor transition start private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor transition start changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor transition start protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
