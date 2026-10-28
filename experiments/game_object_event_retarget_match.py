"""Object event retarget: semantic C, checked schedule guards and strict image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys,csv,io
# The legacy padder is also a CLI and imports its sibling as a top-level module.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151D324C','game_1FFF60'
ENTRY,ROM,BODY,SIZE=0x151D324C,0x2006FC,188,188
SOURCE='conker/src/game_1FFF60.c'
OBJECT='conker/build/src/game_1FFF60.c.o'
ASM='conker/asm/nonmatchings/game_1FFF60/func_151D324C.s'
BUILD='conker/build/game-object-event-retarget-match'
RAW_SHA="2eae43abbb076098ff37e7c9d0ffdb736605eceb7cc080fe39a288274f0f3535"
SNAPSHOT_SHA="d4d4d49dd09bb2c5e55b891a9f6963705630cfe920d8c3c9f96824cbfd74174d"
BEFORE_ELF_SHA="b0e7761ede773cb12b033885cf6e7f1df84e7481a13403bb589d4f5ec3c47475"
TRUTH_SHA="fb8d076590d4d8a57007732f85b17eb986e781da2913fbd0bc5473c760f3f7b4"
HELPER,TABLE=0x151D33FC,0x8008FC64
BINDINGS={36:[("R_MIPS_26","func_151D33FC")],136:[("R_MIPS_HI16","D_8008FC64")],148:[("R_MIPS_LO16","D_8008FC64")]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="#include \"structs.h\"\ntypedef void (*ObjectEventCallback)(struct224 *, struct223 *, u8);\nextern ObjectEventCallback D_8008FC64[];\nvoid func_151D33FC(struct224 *, struct223 *);\n\n"
SELECTED="/* Retarget object references, then dispatch using the selector after the release check. */\nvoid func_151D324C(struct224 *object, struct223 *event, u8 command) {\n    s32 first;\n    if (command == 0) {\n        func_151D33FC(object, event);\n    } else if (command == 0x2D) {\n        first = event->unk0;\n        if (first == object->unk10) {\n            object->unk10 = event->unk4.w;\n            object->unk14 = event->unk9;\n        } else if (event->unk4.w == object->unk10) {\n            object->unk10 = first;\n            object->unk14 = event->unk8;\n        }\n    }\n    if (D_8008FC64[((u8 *)object)[0x1D]] != NULL) {\n        D_8008FC64[((u8 *)object)[0x1D]](object, event, command);\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=184 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Object event retarget body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151D324C() {\n    return 0;\n}'
    if before.count(stub)!=1 or 'ObjectEventCallback'in before:raise ValueError('Object event placeholder changed')
    return before.replace('s32 func_151D324C();','void func_151D324C(struct224 *, struct223 *, u8);').replace('/* Non-matching C placeholders for asm/nonmatchings/game_1FFF60/func_151D324C.s. */\n'+stub,DECLARATIONS+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Object event retarget snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Object event retarget frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Object event retarget predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Object event retarget live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Object event retarget strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Object event retarget original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Object event retarget image differs from body and symbol extent prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Object event retarget named ELF definitions changed')

NEW_GUARDS=json.loads(r'''[{"filename":"game_1FFF60","function":"func_151D324C","offset":"0x014","expected":"0x14C00009","replacement":"0x14C0000A","expected_relocations":"-","replacement_relocations":"-","note":"Restore object-event command reload and selector delay schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"game_1FFF60","function":"func_151D324C","offset":"0x034","expected":"0x10000013","replacement":"0x93A60023","expected_relocations":"-","replacement_relocations":"-","note":"Restore object-event command reload and selector delay schedule","insert_after":"0x10000014","insert_after_relocations":"-","omit":"false"},{"filename":"game_1FFF60","function":"func_151D324C","offset":"0x038","expected":"0x93A60023","replacement":"0x9089001D","expected_relocations":"-","replacement_relocations":"-","note":"Restore object-event command reload and selector delay schedule","insert_after":"","insert_after_relocations":"","omit":"false"},{"filename":"game_1FFF60","function":"func_151D324C","offset":"0x070","expected":"0x54790005","replacement":"0x57230005","expected_relocations":"-","replacement_relocations":"-","note":"Retain equivalent paired-reference comparison operand order","insert_after":"","insert_after_relocations":"","omit":"false"}]''')

def guard_manifest(before):
    if sha(before)!='bc18bdc4633b2387568bc04ee6f816ede14290f391446f745a97b44027eecc59':raise ValueError('Object-event inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Object-event guard already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>46I',raw));out=[];relocs={}
    for i,word in enumerate(words):
        offset=i*4;row=next((x for x in NEW_GUARDS if int(x['offset'],0)==offset),None)
        at=len(out)*4
        if row:
            if word!=int(row['expected'],0)or bindings.get(offset,[]):raise ValueError('Object-event expected guard word/binding changed')
            word=int(row['replacement'],0)
        out.append(word)
        if offset in bindings:relocs[at]=bindings[offset]
        if row and row['insert_after']:out.append(int(row['insert_after'],0))
    return struct.pack('>47I',*out),relocs

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151D324C.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game_1FFF60.c.o","make-shadow/src/game_1FFF60.c.o.compact","make-shadow/src/game_1FFF60.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Object event retarget artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Object event retarget artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Object event retarget raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Object event retarget evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Object event retarget Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Object event retarget expected empty diagnostics')
    if(output/'make-shadow/src/game_1FFF60.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Object event retarget Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=4 or q['exclusions']!=0:raise ValueError('Object event retarget private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Object event retarget changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Object event retarget protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=4,inserted_words=1,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
