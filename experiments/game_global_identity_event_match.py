"""Global identity callback with checked phase-local register roles."""
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

OWNER='generated_1CA420'
FUNCTION='func_1519E818'
SOURCE='conker/src/game/generated_1CA420.c'
ASM='conker/asm/1CA420.s'
OBJECT='conker/build/src/game/generated_1CA420.c.o'
CALLER_SOURCE='conker/src/game/done/game_1765E0.c'
CALLER_OBJECT='conker/build/src/game/done/game_1765E0.c.o'
BUILD='conker/build/game-global-identity-event-match'
ENTRY,ROM,SIZE,BODY=0x1519E818,0x1CBCC8,180,180
PARENT,TABLE,TABLE_ROM=0x15149434,0x8008A8D8,0x22F398
SNAPSHOT_SHA='8214d7575dbc820bf84a1e22fa07ed8c86eed99c306b92871f6bcee077d7edda'
BEFORE_OBJECT_SHA='1ae2dfe1cb27c83ae7c7b829c411a5d4d32fefa714a658c0ad30aa6d6406cf93'
BEFORE_ELF_SHA='f44275f52b5cf0625f28b9e08b0ba1335263a88d8a6fb2a3b3c0d6fc2b4b1cb4'
GUARD_SHA='6e5bba5f5e904d7ee919822cb96414bf00fe5038a87ef2dbe04699ea561c0456'
RAW_SHA='278254adcc7827674bc5247d93c66e98d2084a8f6051fe777802b76502ea6426'
RETAIL_SHA='71c93baf6fbe91004c66eae513b361f611578086d2d9dc804976206332c1c090'
CALLER_SHA='dcc2285633c2d0497b6bc24d71aaa3c884d25925d0282ce530e29b6d30b34b4a'
TABLE_SHA='2e141cceb4d96cca9cedaf57161088aa51ab333ff81d4c46bca9aea7f40a4de8'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
RELEASE_DECLARATION='void func_1516972C(struct102 *);\n'
DECLARATIONS='''extern u8 *D_800E0920;
typedef struct { u8 *owner; u8 identity; u8 opaque5[3]; } PayloadOwnerLink;
typedef struct { u8 *before; u8 *after; u8 before_identity; u8 after_identity; u8 opaqueA[2]; } PayloadOwnerLinkEvent;
'''
SELECTED='''/* Retarget the payload link, or release this record and clear the global. */
void func_1519E818(struct260 *owner, s32 eventAddress, u8 command) {
    PayloadOwnerLink *link = (PayloadOwnerLink *)((u8 *)owner + 0x28);
    PayloadOwnerLinkEvent *event = (PayloadOwnerLinkEvent *)eventAddress;
    s32 code = command;

    if (command == 0) {
        u8 *current = link->owner;
        u8 *first = event->before;
        if (current == first || link->identity == ((u8 *)event)[4]) {
            func_1516972C((struct102 *)owner);
            D_800E0920 = NULL;
        }
    } else if (code == 0x2D) {
        u8 *current = link->owner;
        if (current == event->before) {
            link->owner = event->after;
            link->identity = event->after_identity;
        } else if (current == event->after) {
            link->owner = event->before;
            link->identity = event->before_identity;
        }
    }
}'''
GLOBAL=0x800E0920
BINDINGS={68:[('R_MIPS_26','func_1516972C')],76:[('R_MIPS_HI16','D_800E0920')],80:[('R_MIPS_LO16','D_800E0920')]}
GUARD_WORDS=(9,10,11,13,14,15,26,27,29,30,31,32,34,35,36,38,39,40)


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Global identity-event manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Global identity-event frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Global identity-event old object changed')
    rom=values['conker/conker.us.bin']
    if digest(rom[ROM:ROM+SIZE])!=RETAIL_SHA or digest(rom[0x1768E4:0x176940])!=CALLER_SHA:
        raise ValueError('Global identity-event original target/caller changed')
    if digest(rom[TABLE_ROM:TABLE_ROM+296])!=TABLE_SHA:raise ValueError('Global identity-event registry changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1519E818() {\n    return 0;\n}':raise ValueError('Unknown record-event placeholder')
    if before.count(RELEASE_DECLARATION)!=1 or before.count('extern u8 *D_800E0920;')!=1:
        raise ValueError('Global identity-event existing release/global interface changed')
    for line in DECLARATIONS.splitlines()[1:]:
        if before.count(line)!=1:raise ValueError('Global identity-event existing payload view changed')
    return before[:lo]+SELECTED+before[hi:]


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('GlobalIdentityEventOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=BODY or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Global identity-event complete raw body or bindings changed')
    words=list(struct.unpack('>45I',raw));out=list(words)
    def roles(word,mapping,commute=False):
        if word>>26 not in(4,21,35,36,40,43):raise ValueError('Global identity-event role opcode changed')
        a,b=word>>21&31,word>>16&31
        a,b=mapping.get(a,a),mapping.get(b,b)
        if commute:
            if word>>26!=21:raise ValueError('Global identity-event equality is not BNEL')
            a,b=b,a
        return fields(word,rs=a,rt=b)
    # Release and retarget allocations have separate, non-overlapping lifetimes.
    release={3:15,4:24,15:25,24:8}
    for at in(9,10,11,13,14,15):out[at]=roles(words[at],release)
    identity={3:4,4:3,9:11,25:9,8:10,10:12}
    for at in(26,27,28,29,30,31,32,34,35,36,38,39,40):
        out[at]=roles(words[at],identity,commute=at in(28,36))
    if tuple(i for i,(a,b)in enumerate(zip(words,out))if a!=b)!=GUARD_WORDS:
        raise ValueError('Global identity-event derived guard closure changed')
    return struct.pack('>45I',*out),dict(bindings)


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Global identity-event guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Global identity-event guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Global identity-event guards already exist')
    fitted,_=normalized(raw,bindings);before=struct.unpack('>45I',raw);after=struct.unpack('>45I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Global identity-event guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for i in GUARD_WORDS:
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],
            expected_relocations='-',replacement_relocations='-',omit='false',
            note='Restore phase-local global identity callback roles and equality operand order'))
    return old+stream.getvalue().encode()


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('Global identity-event image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('Global identity-event old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Global identity-event strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            (output/'qualified-padded.o').read_bytes()if installed and name==OBJECT else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else
            guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Global identity-event current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Global identity-event owner diagnostics changed')
    isolated,diag=compile_owner(root,output,HEADERS+RELEASE_DECLARATION+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=payload(isolated,FUNCTION);fitted=normalized(raw,bindings)
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=fitted:
        raise ValueError('Global identity-event isolated/owner/original payload differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=BODY
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('Global identity-event owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('Global identity-event linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('Global identity-event other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('Global identity-event neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Global identity-event pools changed')
    before_image=values['conker/build/conker.us.elf'];rom=values['conker/conker.us.bin']
    if before_image[elf_slot_offset(before_image,PARENT,92):][:92]!=rom[0x1768E4:0x176940]:raise ValueError('Global identity-event retained caller changed')
    if before_image[elf_slot_offset(before_image,TABLE,296):][:296]!=rom[TABLE_ROM:TABLE_ROM+296]:raise ValueError('Global identity-event live registry changed')
    if(root/CALLER_OBJECT).read_bytes()!=values[CALLER_OBJECT]:raise ValueError('Global identity-event caller owner changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=45,slot_words=45,alignment_words=0,frame=24,bindings=3,new_guards=18,compiler_only=False,
        preserved_neighbors=neighbors,preserved_global_asm=values[SOURCE].count(b'#pragma GLOBAL_ASM('),
        owner_diagnostics_unchanged=True,pools_identical=True,dead_duplicate_load_word=35,
        canonical_ABI='void(struct260*,s32,u8)',existing_struct102_release_declaration_preserved=True,
        global_clear_after_release=True,no_inserted_or_omitted_words=True,
        caller_words=23,caller_preexisting_exact=True,caller_owner_object_unchanged=True,registry_entries=74,registry_index=4)
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
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Global identity-event actual Make padded object differs')
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=3 or len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('Global identity-event Make profile changed')
    report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('Global identity-event link owner changed')
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
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Global identity-event independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Global identity-event other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Global identity-event protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
