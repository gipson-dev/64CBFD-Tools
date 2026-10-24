"""Extended identity events with two release commands and checked instruction roles."""
import csv
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments.game_four_head_lookup_match import digest,diagnostics,payload,fields
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='generated_11C2B0'
FUNCTION='func_150F1020'
SOURCE='conker/src/game/generated_11C2B0.c'
ASM='conker/asm/11C2B0.s'
OBJECT='conker/build/src/game/generated_11C2B0.c.o'
CALLER_SOURCE='conker/src/game/generated_15D730.c'
CALLER_OBJECT='conker/build/src/game/generated_15D730.c.o'
BUILD='conker/build/game-extended-identity-event-match/qualified'
ENTRY,ROM,SIZE,BODY=0x150F1020,0x11E4D0,180,180
PARENT,TABLE,TABLE_ROM=0x15131C2C,0x80089878,0x22E338
SNAPSHOT_SHA='3487b4f714aeac90ddda45b361b43d6459778326d465e0b171a1c142eb376912'
BEFORE_OBJECT_SHA='a475992b5e72bb2022a038374b57de3b24a03da26f9b2a535086d28cf8505652'
BEFORE_ELF_SHA='a3b0f6e3ffbf59a8f0820c12386c5fc9ed1cb25f37b50d512fa26fb7c62f8e35'
GUARD_SHA='034248938d5d2c9c597b31533f5d412892859529b36f0109ab28d57b8286e380'
RAW_SHA='3012a2a5f78935a61829aca0d5511246cdd595eef2b1e8a09f236e7b407673b5'
RETAIL_SHA='e550498c9d7ea950479f65f6cd857e731af11397ce1e239e3dbc39830ddafd79'
CALLER_SHA='0f9c9edd02a198a0416dc76b94408c401a85dd821f1989840c3d9a54023f4dec'
TABLE_SHA='1254796b212e9e1ff3f9e51dab9c2975cf48467edbc8fd32c76c8b47dde137a9'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
RELEASE_DECLARATION='void func_1516972C(struct102 *);\n'
DECLARATIONS='''/* Only the payload's identity word and saved key are exposed. */
typedef struct {
    s32 value;
    u8 key;
} IdentityEvent11C2B0;
'''
SELECTED='''/* Retarget an embedded identity, or release its owner for a matching event. */
void func_150F1020(u8 *owner, s32 eventAddress, u8 command) {
    IdentityEvent11C2B0 *state = (IdentityEvent11C2B0 *)(owner + 0xA8);
    u8 *event = (u8 *)eventAddress;
    s32 code = command;

    if (command == 0x2D) {
        s32 current = state->value;
        s32 first = *(s32 *)event;
        if (first == current) {
            state->value = *(s32 *)(event + 4);
            state->key = event[9];
        } else if (*(s32 *)(event + 4) == current) {
            state->value = first;
            state->key = event[8];
        }
    } else if (code == 0 || code == 0x43) {
        if (*(s32 *)event == state->value || state->key == event[4]) {
            func_1516972C((struct102 *)owner);
        }
    }
}'''
BINDINGS={156:[('R_MIPS_26','func_1516972C')]}
GUARD_WORDS=(10,11,12,20,22,31,32,33,35,36,37)


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Extended identity-event manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Extended identity-event frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Extended identity-event old object changed')
    rom=values['conker/conker.us.bin']
    if digest(rom[ROM:ROM+SIZE])!=RETAIL_SHA or digest(rom[0x15F0DC:0x15F134])!=CALLER_SHA:
        raise ValueError('Extended identity-event original target/caller changed')
    if digest(rom[TABLE_ROM:TABLE_ROM+56])!=TABLE_SHA:raise ValueError('Extended identity-event registry changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F1020() {\n    return 0;\n}':raise ValueError('Unknown extended identity-event placeholder')
    if before.count('void func_1516972C(struct102 *);')!=2:raise ValueError('Existing typed release interfaces changed')
    if before.count('#include "structs.h"')!=1:raise ValueError('Existing owner include changed')
    return before[:lo]+DECLARATIONS+'\n'+SELECTED+before[hi:]


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ExtendedIdentityEventOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=BODY or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Extended identity-event complete raw body or bindings changed')
    words=list(struct.unpack('>45I',raw));out=list(words)
    def roles(word,mapping,rs=False,rt=False):
        a,b=word>>21&31,word>>16&31
        return fields(word,rs=mapping.get(a,a)if rs else None,rt=mapping.get(b,b)if rt else None)
    def commute(word):
        if word>>26 not in(4,21):raise ValueError('Extended identity-event comparison shape changed')
        return fields(word,rs=word>>16&31,rt=word>>21&31)
    identity={3:4,4:3}
    for at in(10,11):
        if words[at]>>26!=35:raise ValueError('Extended identity-event identity load changed')
        out[at]=roles(words[at],identity,rt=True)
    for at in(12,20):
        if words[at]>>26!=21:raise ValueError('Extended identity-event identity comparison changed')
        out[at]=roles(words[at],identity,rs=True,rt=True)
    out[20]=commute(out[20])
    if words[22]>>26!=43:raise ValueError('Extended identity-event identity store changed')
    out[22]=roles(words[22],identity,rt=True)
    # Restore event-before-state reads without moving a branch or call binding.
    release={10:3,11:10,12:11}
    if(words[31]>>26,words[32]>>26,words[31]>>21&31,words[32]>>21&31)!=(35,35,2,5):
        raise ValueError('Extended identity-event release read pair changed')
    out[31]=roles(words[32],release,rt=True);out[32]=words[31]
    if words[33]>>26!=4:raise ValueError('Extended identity-event release comparison changed')
    out[33]=commute(roles(words[33],release,rs=True,rt=True))
    for at in(35,36):
        if words[at]>>26!=36:raise ValueError('Extended identity-event key load changed')
        out[at]=roles(words[at],release,rt=True)
    if words[37]>>26!=21:raise ValueError('Extended identity-event key comparison changed')
    out[37]=roles(words[37],release,rs=True,rt=True)
    if tuple(i for i,(a,b)in enumerate(zip(words,out))if a!=b)!=GUARD_WORDS:
        raise ValueError('Extended identity-event derived guard closure changed')
    return struct.pack('>45I',*out),dict(bindings)


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Extended identity-event guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Extended identity-event guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Extended identity-event guards already exist')
    fitted,_=normalized(raw,bindings);before=struct.unpack('>45I',raw);after=struct.unpack('>45I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Extended identity-event guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for i in GUARD_WORDS:
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],
            expected_relocations='-',replacement_relocations='-',omit='false',
            note='Derive extended identity roles, independent read order and commutative comparisons'))
    return old+stream.getvalue().encode()


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('Extended identity-event image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('Extended identity-event old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Extended identity-event strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else
            guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Extended identity-event current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Extended identity-event owner diagnostics changed')
    isolated,diag=compile_owner(root,output,HEADERS+RELEASE_DECLARATION+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=payload(isolated,FUNCTION);fitted=normalized(raw,bindings)
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=fitted:
        raise ValueError('Extended identity-event isolated/owner/original payload differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=BODY
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('Extended identity-event owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('Extended identity-event linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('Extended identity-event other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('Extended identity-event neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Extended identity-event pools changed')
    before_image=values['conker/build/conker.us.elf'];rom=values['conker/conker.us.bin']
    if before_image[elf_slot_offset(before_image,PARENT,88):][:88]!=rom[0x15F0DC:0x15F134]:raise ValueError('Extended identity-event retained caller changed')
    if before_image[elf_slot_offset(before_image,TABLE,56):][:56]!=rom[TABLE_ROM:TABLE_ROM+56]:raise ValueError('Extended identity-event live registry changed')
    if(root/CALLER_OBJECT).read_bytes()!=values[CALLER_OBJECT]:raise ValueError('Extended identity-event caller owner changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=45,slot_words=45,alignment_words=0,frame=24,bindings=1,new_guards=11,compiler_only=False,
        preserved_neighbors=neighbors,preserved_global_asm=values[SOURCE].count(b'#pragma GLOBAL_ASM('),
        owner_diagnostics_unchanged=True,pools_identical=True,dead_duplicate_load_word=19,
        canonical_ABI='void(u8*,s32,u8)',existing_struct102_release_declaration_preserved=True,
        caller_words=22,caller_preexisting_exact=True,caller_owner_object_unchanged=True,registry_entries=14,registry_index=10,
        caller_flags_mask=0x4000,selector_offset=0x75,active_bounds_clamp=False)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';shadow=output/'make-shadow-target';relative=OBJECT.removeprefix('conker/build/')
    target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown record-event Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a==SOURCE.removeprefix('conker/')else
            (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown record-event redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    actual=conker/target;count=same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),())
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Extended identity-event actual Make padded object differs')
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=3 or len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('Extended identity-event Make profile changed')
    report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('Extended identity-event link owner changed')
    link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()))
    elf=output/'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt',
        '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections',
        '--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,check=True)
    before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    check_image(before,actual,truth);changed=sum(a!=b for a,b in zip(before,actual));at=elf_slot_offset(before,ENTRY,SIZE)
    code=sum(a!=b for a,b in zip(before[at:at+SIZE],truth))
    report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=changed,code_bytes=code,metadata_bytes=changed-code,exclusions=0)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root,output):
    values=check_inputs(root,output,installed=True);expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Extended identity-event independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Extended identity-event other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Extended identity-event protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
