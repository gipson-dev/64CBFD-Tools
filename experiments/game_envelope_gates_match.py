"""Ordered signed lifetime ramps with two checked commutative multiply words."""
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

OWNER='generated_1CC440'
FUNCTION='func_151A1E34'
SOURCE='conker/src/game/generated_1CC440.c'
ASM='conker/asm/1CC440.s'
OBJECT='conker/build/src/game/generated_1CC440.c.o'
BUILD='conker/build/game-envelope-gates-match/qualified'
ENTRY,ROM,SIZE=0x151A1E34,0x1CF2E4,180
SNAPSHOT_SHA='d395f30f9ef14d1e569f22f79c8b0fc8b222926f4570d7dd03584e4c56659832'
BEFORE_OBJECT_SHA='36fb6af50cfd2658342e6f95cd0643fe5993366d088f767bc8722d65a32c1143'
BEFORE_ELF_SHA='f3a35907cc1d00c745215320d28623d4e495ae14c38ac9a8c459501e270fb0bb'
GUARD_SHA='265c18d0043ca42b473415c4e7aa7e75155fddf7948d913e182b722689368199'
RAW_SHA='d839fd0b5eb25ce4ca1bfdf6ceb98f3f8629f60b69c3326574a44b78c4bd43fb'
RETAIL_SHA='8a87379f297099c2d78e634c31bf1e85c05d438ebe7cb8033ab911e8a3d7282b'
HEADERS='#include <ultra64.h>\n'
SELECTED='''/* Later matching lifetime ramps intentionally override earlier ramps. */
void func_151A1E34(u8 *effect) {
    s16 *parameters = (s16 *)(effect + 0x50);
    s32 time = *(s16 *)(effect + 0x38);

    if (parameters[2] < time) {
        effect[0x3F] = parameters[0] * (parameters[1] - time);
    }
    if (parameters[5] < time) {
        *(s16 *)(effect + 0x34) = *(s16 *)(effect + 0x36) = parameters[3] * (parameters[4] - time);
    }
    if (time < parameters[6]) {
        effect[0x3F] = parameters[7] * time;
    }
    if (time < parameters[8]) {
        *(s16 *)(effect + 0x34) = *(s16 *)(effect + 0x36) = parameters[9] * time;
    }
}'''
TABLE,TABLE_ROM,TABLE_COUNT,TABLE_INDEX=0x8008C9C8,0x231488,22,17
WINDOWS=((0x15167E80,0x15167EC4,0x195330,0x2F,0x38,0x20),
    (0x151689D4,0x15168A08,0x195E84,0xB2,0x98,0x18))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Envelope input manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Envelope frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Envelope predecessor object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE])!=RETAIL_SHA:raise ValueError('Envelope retail body changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_151A1E34() {\n    return 0;\n}':raise ValueError('Unknown envelope placeholder')
    return before[:lo]+SELECTED+before[hi:]


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('EnvelopeOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=SIZE or digest(raw)!=RAW_SHA or bindings:
        raise ValueError('Envelope complete raw body or empty bindings changed')
    words=list(struct.unpack('>45I',raw))
    for index,roles in((30,(24,3)),(39,(9,3))):
        word=words[index]
        if(word>>26,word&63,word>>21&31,word>>16&31,word>>11&31,word>>6&31)!=(0,25,*roles,0,0):
            raise ValueError('Envelope unsigned multiply operand roles changed')
        words[index]=fields(word,rs=roles[1],rt=roles[0])
    return struct.pack('>45I',*words),{}


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Envelope guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Envelope guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Envelope guards already exist')
    fitted,_=normalized(raw,bindings);before=struct.unpack('>45I',raw);after=struct.unpack('>45I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Envelope guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for index in(30,39):
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(index*4),
            expected='0x%08X'%before[index],replacement='0x%08X'%after[index],
            expected_relocations='-',replacement_relocations='-',omit='false',
            note='Derive commutative unsigned lifetime multiply operand order'))
    return old+stream.getvalue().encode()


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('Envelope image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('Envelope predecessor symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Envelope strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else
            guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Envelope current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Envelope owner diagnostics changed')
    isolated,diag=compile_owner(root,output,HEADERS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=payload(isolated,FUNCTION);fitted=normalized(raw,bindings)
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=fitted:
        raise ValueError('Envelope isolated/owner/original payload differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={name:dict(info)for name,info in fa.items()};expected[FUNCTION]['size']=SIZE
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('Envelope owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('Envelope linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('Envelope other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('Envelope neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Envelope pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=45,slot_words=45,alignment_words=0,frame=0,bindings=0,new_guards=2,
        compiler_only=False,preserved_neighbors=neighbors,owner_diagnostics_unchanged=True,pools_identical=True,
        original_caller_windows=[17,13],preserved_global_asm=wanted.count('#pragma GLOBAL_ASM('),full_parent_C_claimed=False)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def make_shadow(root,output):
    conker=root/'conker';shadow=output/'make-shadow-target';relative=OBJECT.removeprefix('conker/build/')
    target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown envelope Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a==SOURCE.removeprefix('conker/')else
            (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown envelope redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    actual=conker/target;count=same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),())
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Envelope actual Make padded object differs')
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    processors=[a for a in commands if a[:2]==['python3','../tools/asm-processor/asm_processor.py']]
    if len(commands)!=5 or len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('Envelope Make profile changed')
    if len(processors)!=2 or sum('--post-process'in a for a in processors)!=1:raise ValueError('Envelope GLOBAL_ASM processing changed')
    if not all(all(flag in a for flag in('-O2','-g3'))for a in processors):raise ValueError('Envelope processor flags changed')
    report=dict(commands=len(commands),normal_O2_g3=True,global_asm_pre_post_processing=True,compact_functions_equal=count,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('Envelope link owner changed')
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
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Envelope independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Envelope other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Envelope protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
