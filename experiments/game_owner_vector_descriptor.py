"""Direct owner-vector descriptor and a byte-identical typed forwarding caller."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='generated_10CD70'
SOURCE,ASM,OBJECT='conker/src/game/generated_10CD70.c','conker/asm/10CD70.s','conker/build/src/game/generated_10CD70.c.o'
BUILD='conker/build/game-owner-vector-descriptor/qualified'
SNAPSHOT_SHA='e51200dd4c7c0b74d58500663b22de3cc51882c39dd019b6fb236317d1681040'
BEFORE_OBJECT_SHA='0f069a11d1865a0d042dff35f64bbbe78f6329ab9fad174e70826a9abab01e43'
BEFORE_ELF_SHA='42054ab3e2fd8c1a9768693ac80b682908bce356ed2955ca907980a028c7b615'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='''typedef struct {
    f32 x, y, z;
} OwnerVector10CD70;

typedef struct {
    u32 zero0, zero4;
    u8 ownerIdentity, reserved09[3];
    u8 *owner;
    u8 attachment, reserved11[3];
    OwnerVector10CD70 vector;
    f32 value20, value24;
    s16 duration;
    u8 flags, kind;
    s8 callback;
    u8 mode;
} OwnerVectorDescriptor10CD70;

/* Retail reads the complete 12-byte vector preset at this symbol. */
extern OwnerVector10CD70 D_800A5480;
extern f32 D_800A0FB4, D_800A0FB8;
void *func_1513418C(void *, s32, u8, s32);
'''
FUNCTION='func_150E0348'
ENTRY,ROM,SIZE=0x150E0348,0x10D7F8,176
BODY=176
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='af41e78539ddde66a66ca00e85ed1ecaec3ba1b969ff350e4b04a00f0642ef1d')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Submit the owner-linked descriptor with the shared vector preset. */
void *func_150E0348(u8 *owner, u8 selector, s32 category) {
    OwnerVectorDescriptor10CD70 descriptor;

    descriptor.zero0 = 0;
    descriptor.zero4 = 0;
    descriptor.ownerIdentity = owner[0x3B];
    descriptor.owner = owner;
    descriptor.attachment = 0;
    descriptor.vector = D_800A5480;
    descriptor.value20 = D_800A0FB4;
    descriptor.value24 = D_800A0FB8;
    descriptor.duration = 300;
    descriptor.flags = 0x1B;
    descriptor.kind = 0x0B;
    descriptor.callback = -1;
    descriptor.mode = 0;
    return func_1513418C(&descriptor, 0, selector, category);
}'''}
BINDINGS={40:[('R_MIPS_HI16','D_800A5480')],48:[('R_MIPS_LO16','D_800A5480')],
    92:[('R_MIPS_HI16','D_800A0FB4')],96:[('R_MIPS_LO16','D_800A0FB4')],
    100:[('R_MIPS_HI16','D_800A0FB8')],104:[('R_MIPS_LO16','D_800A0FB8')],
    152:[('R_MIPS_26','func_1513418C')]}
CALLER_SOURCE='conker/src/game/generated_97AA0.c'
CALLER_OBJECT='conker/build/src/game/generated_97AA0.c.o'
CALLER_ASM='conker/asm/97AA0.s'
CALLER_BODY='''/* Forward the owner preset and preserve the created-record result. */
void *func_1506A6FC(u8 *owner, s32 unused) {
    return func_150E0348(owner, 0xFF, 1);
}'''



def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Owner-vector descriptor manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Owner-vector descriptor frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Owner-vector descriptor old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Owner-vector descriptor retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before.replace('#include <ultra64.h>',HEADERS.rstrip())
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown character owner-vector descriptor placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero owner-vector descriptor alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildOwnerVectorDescriptorOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def recovered_caller(before):
    lo,hi=function_span(before,'func_1506A6FC')
    if before[lo:hi]!='s32 func_1506A6FC(s32 arg0, s32 arg1) {\n    func_150E0348(arg0, 0xFF, 1);\n}':
        raise ValueError('Owner-vector caller predecessor changed')
    after=before[:lo]+CALLER_BODY+before[hi:]
    anchor='#include "structs.h"\n'
    if after.count(anchor)!=1:raise ValueError('Owner-vector caller include anchor changed')
    return after.replace(anchor,anchor+'void *func_150E0348(u8 *, u8, s32);\n',1)


def qualify_caller(root,output,values):
    original_text=values[CALLER_SOURCE].decode();wanted=recovered_caller(original_text)
    before,da=compile_owner(root,output,original_text,'before-caller')
    after,db=compile_owner(root,output,wanted,'after-caller')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Owner-vector caller diagnostics changed')
    count=same_functions(before,after,())
    if normalized_pools(before)!=normalized_pools(after):raise ValueError('Owner-vector caller pools changed')
    padded=output/'qualified-caller-padded.s'
    padded.write_text(emit_padded_assembly(after,root/CALLER_ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename='generated_97AA0'))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    if obj.read_bytes()!=values[CALLER_OBJECT]:raise ValueError('Owner-vector complete caller object changed')
    data,fs=link_owner(root,output,obj,'generated_97AA0');info=fs['func_1506A6FC'];at=info['value']
    if data[at:at+40]!=values['conker/conker.us.bin'][0x97BAC:0x97BD4]:
        raise ValueError('Owner-vector caller retail slot changed')
    (output/'proposed-caller.c').write_text(wanted)
    report=dict(all_functions_identical=count,pools_identical=True,complete_padded_object_equal=True,
        wrapper_words=10,frame=24,typed_prototype_and_explicit_return=True,diagnostics_unchanged=True)
    (output/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('OwnerVectorDescriptor image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('OwnerVectorDescriptor predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('OwnerVectorDescriptor old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)

    rows={name:(offset,fields,location)for offset,name,fields,location in symbol_rows(before)}
    definitions={
        'D_800A0FB4':(0x800A0FB4,0,16,0,65521),
        'D_80090AD0':(0x80090AD0,0,16,0,6),
        'D_800A2D90':(0x800A2D90,0,16,0,65521),
        'D_800A0FB8':(0x800A0FB8,0,16,0,65521),
        'func_1515F10C':(0x1515F10C,100,18,0,5)}
    # Predict closed hash-bucket serialization cycles, including unequal name lengths.
    for names,new_names in (
            (('D_800A0FB4','D_80090AD0','D_800A2D90'),('D_80090AD0','D_800A2D90','D_800A0FB4')),
            (('D_800A0FB8','func_1515F10C'),('func_1515F10C','D_800A0FB8'))):
        slots=[rows[name]for name in names];start,base=slots[0][2],slots[0][1][0];cursor=0
        for i,(name,(offset,fields,location))in enumerate(zip(names,slots)):
            if (offset-slots[0][0],location-start,fields[0]-base,fields[1:])!=(16*i,cursor,cursor,definitions[name]):
                raise ValueError('Owner-vector closed symbol cycle changed')
            text=name.encode()+b'\0'
            if before[location:location+len(text)]!=text:raise ValueError('Owner-vector symbol spelling changed')
            cursor+=len(text)
        replacement=b''.join(name.encode()+b'\0'for name in new_names)
        if len(replacement)!=cursor:raise ValueError('Owner-vector string span changed')
        result[start:start+cursor]=replacement;cursor=0
        for (offset,_,_),name in zip(slots,new_names):
            other,_,_=rows[name]
            result[offset:offset+16]=before[other:other+16]
            struct.pack_into('>I',result,offset,base+cursor)
            cursor+=len(name)+1
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('OwnerVectorDescriptor strict image differs')
    expected=Counter((name,fields[1],BODY if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    observed=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner-vector named definition changed beyond target size')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  recovered_caller(before.decode()).encode()if installed and name==CALLER_SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  before)
        if(root/name).read_bytes()!=expected:raise ValueError('OwnerVectorDescriptor current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    caller=qualify_caller(root,output,values)
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('OwnerVectorDescriptor owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=BODY or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=(raw,bindings):
            raise ValueError('OwnerVectorDescriptor direct C/original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=BINDINGS:
            raise ValueError('OwnerVectorDescriptor linked words or seven bindings differ')
        rows[name]=dict(words=44,frame=72,bindings=7,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('OwnerVectorDescriptor predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('OwnerVectorDescriptor predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('OwnerVectorDescriptor changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('OwnerVectorDescriptor neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('OwnerVectorDescriptor owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=44,slot_words=44,alignment_words=0,new_guards=0,compiler_only=True,preserved_neighbors=neighbors,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,caller=caller,
        all_owner_addresses_fixed=True,target_size_before=12,target_size_after=BODY)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';reports=[]
    for label,src,obj,proposal,raw,wanted in(
        ('target',SOURCE,OBJECT,'proposed-owner.c','after-owner.o',output/'qualified-padded.o'),
        ('caller',CALLER_SOURCE,CALLER_OBJECT,'proposed-caller.c','after-caller.o',output/'qualified-caller-padded.o')):
        shadow=output/('make-shadow-'+label);relative=obj.removeprefix('conker/build/')
        target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
            cwd=conker,capture_output=True,text=True,check=True)
        (output/('make-shadow-'+label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
                raise ValueError('Unexpected owner-vector descriptor Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown owner-vector descriptor redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
            if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):
                raise ValueError(p.stdout+p.stderr)
            if redirect is not None:redirect.write_text(p.stdout)
            commands.append(args)
        actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        expected_commands=3 if label=='target'else 5
        processors=[a for a in commands if a[0]=='python3'and a[1]=='../tools/asm-processor/asm_processor.py']
        if(len(commands)!=expected_commands or len(compilers)!=1 or len(processors)!=(0 if label=='target'else 2)
                or not all(f in compilers[0]for f in('-O2','-g3'))):
            raise ValueError('OwnerVectorDescriptor normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('OwnerVectorDescriptor actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    if sum(x['actual_Make_commands']for x in reports)!=8:raise ValueError('Owner-vector Make command total changed')
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_10CD70.c.o'
    if script.count(old)!=1:raise ValueError('OwnerVectorDescriptor link owner changed')
    link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()))
    elf=output/'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt',
        '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
        '--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],
        cwd=root/'conker',capture_output=True,check=True)
    before,actual=values['conker/build/conker.us.elf'],elf.read_bytes();bodies=truths(values);check_image(before,actual,bodies)
    changed=sum(a!=b for a,b in zip(before,actual));code=0
    for name,t in TARGETS.items():
        at=elf_slot_offset(before,t['entry'],176);code+=sum(a!=b for a,b in zip(before[at:at+176],bodies[name]))
    report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=changed,code_bytes_changed=code,
        metadata_bytes_changed=changed-code,metadata_exclusions=0)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root,output):
    if (root/CALLER_OBJECT).read_bytes()!=(output/'qualified-caller-padded.o').read_bytes():raise ValueError('Owner-vector installed caller object differs')
    values=check_inputs(root,output,installed=True);expected=predicted_image(values['conker/build/conker.us.elf'],truths(values))
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():
        raise ValueError('OwnerVectorDescriptor independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('OwnerVectorDescriptor changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('OwnerVectorDescriptor protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
