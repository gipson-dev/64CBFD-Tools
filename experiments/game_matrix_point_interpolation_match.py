"""Matrix-bound point interpolation: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1519E304','generated_1CA420'
ENTRY,ROM,BODY,SIZE=0x1519E304,0x1CB7B4,184,184
SOURCE='conker/src/game/generated_1CA420.c'
OBJECT='conker/build/src/game/generated_1CA420.c.o'
ASM='conker/asm/1CA420.s'
BUILD='conker/build/game-matrix-point-interpolation-match'
RAW_SHA='d3f708ca17f13cefc7214b251ba71b56b9cc335e29197ece8a3898a4bcd6d6bf'
SNAPSHOT_SHA='bebc1127c05478cf77dc67dd9616bebfdda8b8603a246d810966fb72d91d955a'
BEFORE_ELF_SHA='53f02cac34ee5d56ed2f09b86f5e4b09ed5e0f9d9e098c1d453db5567dac10e1'
TRUTH_SHA='1f03c3b51b7adc6c83c8612492f67e2f33a76765ffb22d7f85d9a135e40b3de3'
HELPER,HELPER_ROM,HELPER_SIZE=0x15143134,0x1705E4,392
CALLS=(0x1519D190,0x1519D4E8,0x1519D560)
BINDINGS={76:[('R_MIPS_26','func_15143134')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct {\n    u8 *owner;\n    u8 reserved4;\n    u8 matrixIndex;\n    u8 reserved6[2];\n    f32 point[3];\n} MatrixPointBinding;\nvoid func_15143134(f32 *, f32 *, u8 *);\n"
SELECTED="/* Transform the bound point, then interpolate each coordinate from the origin. */\ns32 func_1519E304(MatrixPointBinding *binding, f32 *output,\n                 f32 x, f32 y, f32 z, f32 amount) {\n    f32 transformed[3];\n    u8 (*matrices)[64] = *(u8 (**)[64])(binding->owner + 0x1D4);\n\n    if (matrices == NULL) {\n        return 0;\n    }\n    func_15143134(binding->point, transformed,\n                  matrices[binding->matrixIndex]);\n    output[0] = (transformed[0] - x) * amount + x;\n    output[1] = (transformed[1] - y) * amount + y;\n    output[2] = (transformed[2] - z) * amount + z;\n    return 1;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Matrix point interpolation body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1519E304() {\n    return 0;\n}'
    if before.count(stub)!=1 or 'MatrixPointBinding'in before:raise ValueError('Matrix interpolation placeholder changed')
    return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Matrix point interpolation snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Matrix point interpolation frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Matrix point interpolation predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Matrix point interpolation live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Matrix point interpolation strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Matrix point interpolation original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Matrix point interpolation image differs from the body and extent prediction')
    expected=Counter((n,f[1],184 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Matrix point interpolation named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1519E304.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_1CA420.c.o","make-shadow/src/game/generated_1CA420.c.o.compact","make-shadow/src/game/generated_1CA420.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Matrix point interpolation artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Matrix point interpolation artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Matrix point interpolation raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Matrix point interpolation evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Matrix point interpolation Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Matrix point interpolation expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_1CA420.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Matrix point interpolation Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Matrix point interpolation private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Matrix point interpolation changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Matrix point interpolation protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
