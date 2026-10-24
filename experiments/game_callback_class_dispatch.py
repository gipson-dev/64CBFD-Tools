"""Direct-C actor class dispatch with complete caller and image qualification."""
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

OWNER='generated_1BFCB0'
SOURCE,ASM,OBJECT='conker/src/game/generated_1BFCB0.c','conker/asm/1BFCB0.s','conker/build/src/game/generated_1BFCB0.c.o'
BUILD='conker/build/game-callback-class-dispatch/qualified'
SNAPSHOT_SHA='9d4ee5d88bfcf486f98a14646f314e819a87774ccf406157a4e3e4cd298d5fb0'
BEFORE_OBJECT_SHA='9095f05f1e9f8925fbd5d869d168054144a2435a0adf8775bf2aeb9d0abcdb24'
BEFORE_ELF_SHA='5b0c22080c309f37cd7424673424d4f2c98923c73da2bb9f73b3ed2c7a5bb12e'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='''typedef void (*ClassCallback1BFCB0)(u8 *);
extern ClassCallback1BFCB0 *D_8008F860[];
extern s32 D_800BE9F0;
s32 func_151928B0(u8 *, s32 *);
s32 func_1510F8CC(s32);
'''
FUNCTION='func_15192800'
ENTRY,ROM,SIZE=0x15192800,0x1BFCB0,176
BODY=176
CALLER_SOURCE='conker/src/game_981E0.c'
CALLER_OBJECT='conker/build/src/game_981E0.c.o'
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='26aab509ba1d3ca63036f11094fa1f7d7e61d953c267eeea4c81294a76fb9a4b')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Dispatch the actor's class callback for its type and current world. */
void func_15192800(void *actor, s32 unused) {
    s32 row;
    s32 column;
    s32 kind;
    ClassCallback1BFCB0 callback;

    if (actor != NULL && func_151928B0(actor, &row)) {
        kind = func_1510F8CC(*(s32 *)((u8 *)actor + 0x184));
        switch (kind) {
            case 5:
                if (D_800BE9F0 == 0x14) {
                    column = 2;
                } else {
                    column = 1;
                }
                break;
            case 6:
                column = 3;
                break;
            default:
                column = 1;
                break;
        }
        callback = D_8008F860[row][column];
        if (callback != NULL) {
            callback(actor);
        }
    }
}'''}
BINDINGS={20:[('R_MIPS_26','func_151928B0')],36:[('R_MIPS_26','func_1510F8CC')],
    76:[('R_MIPS_HI16','D_800BE9F0')],80:[('R_MIPS_LO16','D_800BE9F0')],
    120:[('R_MIPS_HI16','D_8008F860')],128:[('R_MIPS_LO16','D_8008F860')]}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Class-dispatch manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Class-dispatch frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Class-dispatch old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Class-dispatch retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown class-dispatch placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    result=result.replace('Non-matching placeholders for the text-only asm slice','Actor-class dispatch and row selection for')
    at=result.index(SELECTED[FUNCTION])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def recovered_caller(before):
    anchor='#include "variables.h"\n'
    if before.count(anchor)!=1 or 'void func_15192800(' in before:raise ValueError('Class-dispatch caller declaration changed')
    return before.replace(anchor,anchor+'\nvoid func_15192800(void *, s32);\n',1)


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero class dispatch alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildClassDispatchOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('ClassDispatch image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('ClassDispatch predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('ClassDispatch old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('ClassDispatch strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  recovered_caller(before.decode()).encode()if installed and name==CALLER_SOURCE else before)
        if(root/name).read_bytes()!=expected:raise ValueError('ClassDispatch current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('ClassDispatch owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=BODY or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=(raw,bindings):
            raise ValueError('ClassDispatch direct C/original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=BINDINGS:
            raise ValueError('ClassDispatch linked words or six bindings differ')
        rows[name]=dict(words=44,frame=48,bindings=6,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER,
        rodata_symbol='jtbl_800A8160_game'))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('ClassDispatch predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('ClassDispatch predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('ClassDispatch changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('ClassDispatch neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('ClassDispatch owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    caller_wanted=recovered_caller(values[CALLER_SOURCE].decode())
    caller_before,caller_da=compile_owner(root,output,values[CALLER_SOURCE].decode(),'before-caller')
    caller_after,caller_db=compile_owner(root,output,caller_wanted,'after-caller')
    if diagnostics(caller_da)!=diagnostics(caller_db):raise ValueError('Class-dispatch caller diagnostics changed')
    caller_count=same_functions(caller_before,caller_after,())
    if normalized_pools(caller_before)!=normalized_pools(caller_after):raise ValueError('Class-dispatch caller pools changed')
    (output/'proposed-caller.c').write_text(caller_wanted)
    report=dict(functions=rows,total_words=44,slot_words=44,alignment_words=0,new_guards=0,compiler_only=True,preserved_neighbors=neighbors,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True,caller_functions_preserved=caller_count,caller_diagnostics_unchanged=True,target_size_before=12,target_size_after=BODY)
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
                raise ValueError('Unexpected class dispatch Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown class dispatch redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/('after-owner-diagnostics.txt'if label=='target'else'after-caller-diagnostics.txt')).read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
            if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):
                raise ValueError(p.stdout+p.stderr)
            if redirect is not None:redirect.write_text(p.stdout)
            commands.append(args)
        actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        expected_commands=3 if label=='target'else 5
        processors=[a for a in commands if a[0]=='python3'and a[1]=='../tools/asm-processor/asm_processor.py']
        if(len(commands)!=expected_commands or len(compilers)!=1 or len(processors)!=(0 if label=='target'else 2)
                or not all(f in compilers[0]for f in('-O2','-g3'))):
            raise ValueError('ClassDispatch normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('ClassDispatch actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_1BFCB0.c.o'
    if script.count(old)!=1:raise ValueError('ClassDispatch link owner changed')
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
        raise ValueError('ClassDispatch independent image or object differs')
    if(root/CALLER_OBJECT).read_bytes()!=values[CALLER_OBJECT]:raise ValueError('Class-dispatch caller object changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('ClassDispatch changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('ClassDispatch protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
