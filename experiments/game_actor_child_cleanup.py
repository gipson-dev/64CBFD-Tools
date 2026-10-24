"""Direct-C paired actor child teardown with strict owner, caller and image gates."""
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

OWNER='generated_11C2B0'
SOURCE,ASM,OBJECT='conker/src/game/generated_11C2B0.c','conker/asm/11C2B0.s','conker/build/src/game/generated_11C2B0.c.o'
CALLER_SOURCE,CALLER_OBJECT='conker/src/game_169510.c','conker/build/src/game_169510.c.o'
BUILD='conker/build/game-actor-child-cleanup/qualified'
SNAPSHOT_SHA='5da810d3de8cc0748e877500f74de621fa0f1538e355c0ca4abbe3d396df8b01'
BEFORE_OBJECT_SHA='ad260b8c4369b27ffe963c200c964008c65983962e7aa98eafa3ce561e810cac'
BEFORE_ELF_SHA='fb1c38c6c9f3125f6f410be7df90b459dac9ea3cf0af4d0179b631745e3c6198'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='''typedef struct {
    u8 opaque0[0x1C];
    struct102 *children[5];
} ChildReleaseState11C2B0;

void func_1516972C(struct102 *);
void func_1516979C(struct102 *);
void func_1513CA6C(struct210 *);
void func_1513CAA0(struct210 *);
'''
TARGETS={
 'func_150EF7B0':dict(entry=0x150EF7B0,rom=0x11CC60,release=0x1516972C,finish=0x1513CA6C,
  parent=0x1513CB58,table=0x80089EF8,table_rom=0x22E9B8,
  retail_SHA256='0a3cdd60b59fdb41e462e60a8b0baad0e1caea5de7e6879726703d549ff88366'),
 'func_150EF860':dict(entry=0x150EF860,rom=0x11CD10,release=0x1516979C,finish=0x1513CAA0,
  parent=0x1513CBA4,table=0x80089F2C,table_rom=0x22E9EC,
  retail_SHA256='96454209e43379cd34fcd73008c4935fedf1a98f96d35ebe85d630ebf788cbc0')}
FUNCTIONS=tuple(TARGETS)
SELECTED={}
for name,t in TARGETS.items():
 release='func_%08X'%t['release'];finish='func_%08X'%t['finish']
 SELECTED[name]='''/* Release the five attached children, then run the actor's base teardown. */
void NAME(struct210 *owner) {
    ChildReleaseState11C2B0 *state = (ChildReleaseState11C2B0 *)((u8 *)owner + 0x110);
    s32 index;

    for (index = 0; index < 2; index++) {
        if (state->children[index] != NULL) {
            RELEASE(state->children[index]);
        }
    }
    if (state->children[2] != NULL) {
        RELEASE(state->children[2]);
    }
    if (state->children[3] != NULL) {
        RELEASE(state->children[3]);
    }
    if (state->children[4] != NULL) {
        RELEASE(state->children[4]);
    }
    FINISH(owner);
}'''.replace('NAME',name).replace('RELEASE',release).replace('FINISH',finish)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'\S+\.c','<unit>',text)


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Child cleanup manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Child cleanup frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Child cleanup old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Child cleanup retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown child cleanup placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def recovered_caller(before):
    result=before
    for table in('D_80089EF8','D_80089F2C'):
        old=table+'[idx]();'
        if result.count(old)!=1:raise ValueError('Unknown cleanup dispatcher interface')
        result=result.replace(old,'((void (*)(struct210 *))'+table+'[idx])(arg0);')
    return result


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero cleanup alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildCleanupOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('Cleanup image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('Cleanup predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('Cleanup old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,176)
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('Cleanup strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  recovered_caller(before.decode()).encode()if installed and name==CALLER_SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Cleanup current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if da or db:raise ValueError('Cleanup owner diagnostics: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=176 or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=(raw,bindings):
            raise ValueError('Cleanup direct C/original payload differs')
        linked,fs=link_owner(root,output,isolated,OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or sum(map(len,bindings.values()))!=5:
            raise ValueError('Cleanup linked words or five bindings differ')
        rows[name]=dict(words=44,frame=40,bindings=5,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('Cleanup predecessor extent changed')
        expected[name]['size']=176;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('Cleanup predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('Cleanup changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=42 or same_functions(old,obj,FUNCTIONS)!=42:raise ValueError('Cleanup neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('Cleanup owner pools changed')
    caller=recovered_caller(values[CALLER_SOURCE].decode())
    cb,d1=compile_owner(root,output,values[CALLER_SOURCE].decode(),'before-caller')
    ca,d2=compile_owner(root,output,caller,'after-caller')
    if diagnostics(d1)!=diagnostics(d2):raise ValueError('Cleanup caller diagnostics changed: '+d1+d2)
    count=same_functions(cb,ca,())
    if normalized_pools(cb)!=normalized_pools(ca):raise ValueError('Cleanup caller pools changed')
    data,fs=link_owner(root,output,ca,'game_169510')
    for t in TARGETS.values():
        name='func_%08X'%t['parent'];at=fs[name]['value'];rom=t['parent']-0x15000000+0x2D4B0
        if data[at:at+76]!=values['conker/conker.us.bin'][rom:rom+76]:
            raise ValueError('Cleanup actual C dispatcher differs from retail')
    (output/'proposed-owner.c').write_text(wanted);(output/'proposed-caller.c').write_text(caller)
    report=dict(functions=rows,total_words=88,new_guards=0,compiler_only=True,preserved_neighbors=42,
        caller_functions_preserved=count,compiler_diagnostics_empty=True,caller_diagnostics_unchanged=True,
        inherited_caller_warnings=d1.count('cfe: Warning'),all_owner_addresses_fixed=True,
        target_size_before=12,target_size_after=176)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';reports=[]
    for label,src,obj,proposal,raw,wanted in(
        ('target',SOURCE,OBJECT,'proposed-owner.c','after-owner.o',output/'qualified-padded.o'),
        ('caller',CALLER_SOURCE,CALLER_OBJECT,'proposed-caller.c','after-caller.o',root/CALLER_OBJECT)):
        shadow=output/('make-shadow-'+label);relative=obj.removeprefix('conker/build/')
        target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
            cwd=conker,capture_output=True,text=True,check=True)
        (output/('make-shadow-'+label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
                raise ValueError('Unexpected cleanup Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown cleanup redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/'before-caller-diagnostics.txt').read_text()if label=='caller'and args[0]=='../ido/ido5.3_recomp/cc'else''
            if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):
                raise ValueError(p.stdout+p.stderr)
            if redirect is not None:redirect.write_text(p.stdout)
            commands.append(args)
        actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        expected_commands=3 if label=='target'else 5
        processors=[a for a in commands if a[0]=='python3'and a[1]=='../tools/asm-processor/asm_processor.py']
        if(len(commands)!=expected_commands or len(compilers)!=1 or len(processors)!=(0 if label=='target'else 2)
                or not all(f in compilers[0]for f in('-O2','-g3'))):
            raise ValueError('Cleanup normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('Cleanup actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_11C2B0.c.o'
    if script.count(old)!=1:raise ValueError('Cleanup link owner changed')
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
    values=check_inputs(root,output,installed=True);expected=predicted_image(values['conker/build/conker.us.elf'],truths(values))
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():
        raise ValueError('Cleanup independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('Cleanup changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Cleanup protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-2,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
