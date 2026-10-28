"""Actor slot refill: guarded C private proposal, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1512B53C','generated_157840'
ENTRY,ROM,BODY,SIZE=0x1512B53C,0x1589EC,192,192
SOURCE='conker/src/game/generated_157840.c'
OBJECT='conker/build/src/game/generated_157840.c.o'
ASM='conker/asm/157840.s'
BUILD='conker/build/game-actor-slot-refill-match'
RAW_SHA="c45e1ddc7099ee0da0ded42e4fadcf94560a5d86ed7f8dd20ee80c6ea1003a34"
SNAPSHOT_SHA="8ff296fe21a358abd83ade4497e5d09d356ad10991e136806f867db3866522b2"
BEFORE_ELF_SHA="cc2ca2d66d3026bb183b2eb1dc9381d86707bbeff2c972dd5f6ed9099d352a61"
TRUTH_SHA="d13b2f6391829834b46bf37cccae2e791cf709d1c59ca19a03339aefb957d19a"
GLOBAL=0x800BE628
BINDINGS={20:[('R_MIPS_HI16','D_800BE628')],32:[('R_MIPS_LO16','D_800BE628')]}
NORMALIZED_BINDINGS={4:[('R_MIPS_HI16','D_800BE628')],8:[('R_MIPS_LO16','D_800BE628')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern s32 D_800BE628;\n"
SELECTED="/* Reset each active slot marker while the actor's refresh counter is nonzero. */\ns32 func_1512B53C(u8 *actor) {\n    s32 index;\n    u32 offset;\n\n    if (*(s16 *)(actor + 0x5FC) == 0) goto inactive;\n    {\n        *(s16 *)(actor + 0x5F8) = 1;\n        index = 0;\n        offset = 0;\n        while ((f32)index < *(f32 *)((u32)D_800BE628 + actor[0x23D] * 0x180 + 4)) {\n            *(u16 *)(*(u8 **)(actor + 0x8BC) + offset) = 0xFFFC;\n            index = (s32)((u32)index + 1);\n            offset += 2;\n        }\n        *(f32 *)(actor + 0x60C) = 0.0f;\n        *(s16 *)(actor + 0x5FC) -= 1;\n        return 1;\n    }\ninactive:\n    return 0;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Actor slot refill body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1512B53C() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Actor slot refill placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Actor slot refill snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Actor slot refill frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Actor slot refill predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Actor slot refill live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Actor slot refill strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Actor slot refill original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Actor slot refill image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Actor slot refill named ELF definitions changed')

NEW_GUARDS=[{"filename":"generated_157840","function":"func_1512B53C","offset":"0x004","expected":"0x51C0002C","replacement":"0x3C050000","expected_relocations":"-","replacement_relocations":"R_MIPS_HI16:D_800BE628","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x008","expected":"0x00001025","replacement":"0x24A50000","expected_relocations":"-","replacement_relocations":"R_MIPS_LO16:D_800BE628","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x00C","expected":"0x9098023D","replacement":"0x51C0002A","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x010","expected":"0x24050180","replacement":"0x00001025","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x014","expected":"0x3C060000","replacement":"0x44800000","expected_relocations":"R_MIPS_HI16:D_800BE628","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x018","expected":"0x03050019","replacement":"0x24060180","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x01C","expected":"0x240F0001","replacement":"0x9099023D","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x020","expected":"0x24C60000","replacement":"0x240F0001","expected_relocations":"R_MIPS_LO16:D_800BE628","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x028","expected":"0x8CC80000","replacement":"0x03260019","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x02C","expected":"0x44800000","replacement":"0x8CB80000","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x03C","expected":"0x0000C812","replacement":"0x00004012","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x040","expected":"0x03284821","replacement":"0x03084821","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x054","expected":"0x849805FC","replacement":"0x849905FC","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x06C","expected":"0x908C023D","replacement":"0x908D023D","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x070","expected":"0x8CCE0000","replacement":"0x8CAC0000","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x078","expected":"0x01850019","replacement":"0x01A60019","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x080","expected":"0x00006812","replacement":"0x00007012","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x084","expected":"0x01AE7821","replacement":"0x018E7821","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x09C","expected":"0x849805FC","replacement":"0x849905FC","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x0A8","expected":"0x2719FFFF","replacement":"0x2738FFFF","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"generated_157840","function":"func_1512B53C","offset":"0x0B0","expected":"0xA49905FC","replacement":"0xA49805FC","expected_relocations":"-","replacement_relocations":"-","note":"Normalize proven actor-slot refill GPR allocation and independent opening schedule","insert_after":"","insert_after_relocations":"","omit":"false"}]
def guard_manifest(before):
    import csv,io
    if sha(before)!='7a8a7a39ff6271b22dfb93589c78def9bf0b04d022adb5795ce3afa044c226a6':raise ValueError('Actor slot inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Actor slot guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>48I',raw));result_bindings={at:list(rs)for at,rs in bindings.items()};seen=set()
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=';'.join(k+':'+n for k,n in result_bindings.get(at,[]))or'-'
        if at in seen or words[at//4]!=int(row['expected'],0)or row['expected_relocations']!=expected:raise ValueError('Actor slot expected word/binding changed')
        seen.add(at);words[at//4]=int(row['replacement'],0);replacement=row['replacement_relocations']
        if replacement=='-':result_bindings.pop(at,None)
        else:result_bindings[at]=[tuple(part.split(':',1))for part in replacement.split(';')]
    result=struct.pack('>48I',*words)
    if len(seen)!=21 or sha(result)!='4b373b113fbb96a2431777810e14e0e12093004dd21ef16ab4ff9f726b498df6'or result_bindings!=NORMALIZED_BINDINGS:raise ValueError('Actor slot normalized body/bindings changed')
    return result,result_bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1512B53C.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_157840.c.o","make-shadow/src/game/generated_157840.c.o.compact","make-shadow/src/game/generated_157840.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Actor slot refill artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor slot refill artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor slot refill raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Actor slot refill evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Actor slot refill Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected EEPROM owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_157840.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Actor slot refill Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=21 or q['exclusions']!=0:raise ValueError('Actor slot refill private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor slot refill changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor slot refill protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=0,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=21,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
