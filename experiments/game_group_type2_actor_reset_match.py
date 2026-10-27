"""Live type-2 group actor reset: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,types
from tools.experiments.game_remaining_donor_candidates import compile_owner as _compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_150222E0','generated_49D30'
ENTRY,ROM,BODY,SIZE=0x150222E0,0x4F790,184,184
SOURCE='conker/src/game/generated_49D30.c'
OBJECT='conker/build/src/game/generated_49D30.c.o'
ASM='conker/asm/49D30.s'
BUILD='conker/build/game-group-type2-actor-reset-match'
RAW_SHA='d9ffb389bc262efcf505237026ecd45a324f46ec4dbf9751c33496c71fab9ba7'
SNAPSHOT_SHA='6b9925b08ac69d5cb8371e48b10b3dd9a754b2822ca8c88c19cb91fd254b826e'
BEFORE_ELF_SHA='86c5549e999b5bb3262b5513195b892c8e3c04a153cae3e95ea4a57cc765c30d'
TRUTH_SHA='46af58f62e8406bf1b291ae779ff7d216341ee516f5799c54f2cd3da7eeafcaa'
PARENT,PARENT_ROM=0x15022848,0x4FCF8
LOOKUP,LOOKUP_ROM,RESET=0x15083E90,0xB1340,0x1507E7E4
BINDINGS={12:[('R_MIPS_HI16','D_800C35C8')],20:[('R_MIPS_LO16','D_800C35C8')],28:[('R_MIPS_HI16','D_800C35F0')],52:[('R_MIPS_LO16','D_800C35F0')],80:[('R_MIPS_26','func_15083E90')],152:[('R_MIPS_26','func_1507E7E4')]}
HEADERS="#include <ultra64.h>\n#include \"structs.h\"\n"
DECLARATIONS="extern u16 *D_800C35C8[];\nextern u8 *D_800C35F0[];\nu8 *func_15083E90(u8);\nvoid func_1507E7E4(u8 *, u8, u8, u16, s32);\n"
SELECTED="/* Reset the actor referenced by a live type-2 group record. */\nvoid func_150222E0(s32 index, s32 group) {\n    u8 *actor;\n    u8 *record;\n    if (D_800C35C8[group][index] == 0) {\n        return;\n    }\n    record = D_800C35F0[group] + (u32)index * 8;\n    if (*(u16 *)record != 2) {\n        return;\n    }\n    actor = func_15083E90(record[2]);\n    if (actor != NULL) {\n        actor[0x6C] = 0;\n        actor[0x6D] = 0;\n        actor[0x6A] = 0;\n        actor[0x6B] = 0;\n        *(u16 *)(actor + 0x282) = 0;\n        *(u16 *)(actor + 0x27A) = 0;\n        *(u16 *)(actor + 0x27C) = 0;\n        *(u16 *)(actor + 0x27E) = 0;\n        *(u16 *)(actor + 0x280) = 0;\n        func_1507E7E4(actor, 0, 3, 0xFFFF, 10);\n        actor[0x71] = 0;\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def compile_owner(root,output,text,label):
    # asm_processor does not accept -Wo. Apply the retail no-unroll option only to cc.
    def run(argv,**kwargs):
        argv=list(argv)
        if argv[0]==str(root/'ido/ido5.3_recomp/cc'):
            if '-Wo,-loopunroll,0' in argv:raise ValueError('Duplicate compiler option')
            argv.insert(argv.index('-mips2'),'-Wo,-loopunroll,0')
        return subprocess.run(argv,**kwargs)
    scoped=types.FunctionType(_compile_owner.__code__,dict(_compile_owner.__globals__,subprocess=types.SimpleNamespace(run=run)),_compile_owner.__name__,_compile_owner.__defaults__)
    return scoped(root,output,text,label)

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Group actor reset body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_150222E0() {\n    return 0;\n}'
    anchor='extern u8 *D_800C35F0[];\n'
    if before.count(stub)!=1 or before.count(anchor)!=1 or 'func_15083E90'in before or 'func_1507E7E4'in before:raise ValueError('Group actor reset placeholder/declarations changed')
    declarations='u8 *func_15083E90(u8);\nvoid func_1507E7E4(u8 *, u8, u8, u16, s32);\n'
    return before.replace(anchor,anchor+declarations,1).replace(stub,SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Group actor reset snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Group actor reset frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Group actor reset predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Group actor reset live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Group actor reset strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Group actor reset original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY);return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Group actor reset image differs from literal body/size prediction')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_150222E0.o','first-linked.elf')
EVIDENCE=('before-owner.c','before-owner-processed.c','before-owner.o','after-owner.c','after-owner-processed.c','after-owner.o','selected.c','selected-processed.c','selected.o','selected-input.c','before-owner-diagnostics.txt','after-owner-diagnostics.txt','selected-diagnostics.txt','actual-Make-plan.txt','make-shadow/src/game/generated_49D30.c.o','make-shadow/src/game/generated_49D30.c.o.compact','make-shadow/src/game/generated_49D30.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Group actor reset artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Group actor reset artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Group actor reset raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Group actor reset evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Group actor reset Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Group actor reset expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_49D30.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Group actor reset Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Group actor reset private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Group actor reset changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Group actor reset protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
