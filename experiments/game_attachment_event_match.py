"""Attachment event callback with a closed identity-role and branch normalization."""
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

OWNER='generated_F2820'
FUNCTION='func_150C5D0C'
SOURCE='conker/src/game/generated_F2820.c'
ASM='conker/asm/F2820.s'
OBJECT='conker/build/src/game/generated_F2820.c.o'
BUILD='conker/build/game-attachment-event-match/qualified'
ENTRY,ROM,SIZE,BODY=0x150C5D0C,0xF31BC,180,172
SNAPSHOT_SHA='d3f1e5a4bbf383151d77e70996e1f0861aa66556acdbab789a84f22c9cc20b49'
BEFORE_OBJECT_SHA='8620273f145487f91ef552ca1e5cec36159df30746dd6d92fea294b1db8b4fc4'
BEFORE_ELF_SHA='902853b86424d6758316ec20095dec229d9c1bd98b334339f3b27d07b55be8c5'
GUARD_SHA='7491ffd37d1220d54d02b3f4cbc5fdb17be36c8ffcf14c5ef0e750627d82063a'
RAW_SHA='35fbff4b98bdaa7fe5279da1dcb01e4dfad42ce3c8909d88961c47f3d323950e'
RETAIL_SHA='9834a745b0f021073d9c56d1e7dfa21f240d9866adb41ba8905e476fbf23945c'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='''void func_1516972C(struct102 *);

/* Only the attachment's identity word and saved key are exposed here. */
typedef struct {
    s32 value;
    u8 key;
} AttachmentIdentityF2820;
'''
SELECTED='''/* Release a matching attachment or retarget its saved identity and key. */
void func_150C5D0C(u8 *owner, s32 eventAddress, u8 command) {
    AttachmentIdentityF2820 *state = (AttachmentIdentityF2820 *)(owner + 0xC8);
    u8 *event = (u8 *)eventAddress;
    s32 code = command;

    if (command == 0) {
        if (state->value == *(s32 *)event || state->key == event[4]) {
            func_1516972C((struct102 *)owner);
        }
    } else if (code == 0x2D) {
        s32 current = state->value;
        s32 first = *(s32 *)event;
        if (first == current) {
            state->value = *(s32 *)(event + 4);
            state->key = event[9];
        } else if (*(s32 *)(event + 4) == current) {
            state->value = first;
            state->key = event[8];
        }
    }
}'''
BINDINGS={68:[('R_MIPS_26','func_1516972C')]}


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Attachment-event manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Attachment-event frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Attachment-event old object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE])!=RETAIL_SHA:raise ValueError('Attachment-event retail slot changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150C5D0C() {\n    return 0;\n}':raise ValueError('Unknown attachment-event placeholder')
    return before[:lo]+DECLARATIONS+'\n'+SELECTED+before[hi:]


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('AttachmentEventOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=BODY or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Attachment-event complete raw body or bindings changed')
    words=list(struct.unpack('>43I',raw));out=list(words)
    # Exchange the two closed A0/V1 identity roles only inside command 0x2D.
    out[24]=fields(words[24],rt=4);out[25]=fields(words[25],rt=3)
    out[26]=fields(words[26],rs=3,rt=4)
    branch=fields(words[34],rs=4)
    if(branch>>26,branch>>21&31,branch>>16&31,branch&65535)!=(21,4,11,5):
        raise ValueError('Attachment-event commutative branch shape changed')
    out[34]=fields(branch,rs=11,rt=4);out[36]=fields(words[36],rt=3)
    return struct.pack('>43I',*out),dict(bindings)


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Attachment-event guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Attachment-event guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Attachment-event guards already exist')
    fitted,_=normalized(raw,bindings);before=struct.unpack('>43I',raw);after=struct.unpack('>43I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Attachment-event guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for i in(24,25,26,34,36):
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],
            expected_relocations='-',replacement_relocations='-',omit='false',
            note='Derive closed attachment identity register roles and commutative comparison operands'))
    return old+stream.getvalue().encode()


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('Attachment-event image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('Attachment-event old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Attachment-event strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else
            guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Attachment-event current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Attachment-event owner diagnostics changed')
    isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=payload(isolated,FUNCTION);fitted=normalized(raw,bindings)
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=fitted:
        raise ValueError('Attachment-event isolated/owner/original payload differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=BODY
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('Attachment-event owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('Attachment-event linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('Attachment-event other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('Attachment-event neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Attachment-event pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=43,slot_words=45,alignment_words=2,frame=24,bindings=1,new_guards=5,compiler_only=False,
        preserved_neighbors=neighbors,owner_diagnostics_unchanged=True,pools_identical=True,dead_duplicate_load_word=33)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';shadow=output/'make-shadow-target';relative=OBJECT.removeprefix('conker/build/')
    target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown attachment-event Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a==SOURCE.removeprefix('conker/')else
            (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown attachment-event redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    actual=conker/target;count=same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),())
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Attachment-event actual Make padded object differs')
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=3 or len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('Attachment-event Make profile changed')
    report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('Attachment-event link owner changed')
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
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Attachment-event independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Attachment-event other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Attachment-event protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
