"""Dual-point motion callback with checked address and return scheduling."""
import csv
import io
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

OWNER='generated_1BA1D0'
SOURCE,ASM,OBJECT='conker/src/game/generated_1BA1D0.c','conker/asm/1BA1D0.s','conker/build/src/game/generated_1BA1D0.c.o'
BUILD='conker/build/game-dual-point-motion/qualified'
SNAPSHOT_SHA='6d743ad282f935077946744627cd1d22c1f4392627ebaeffcb3e78bac0f509c0'
BEFORE_OBJECT_SHA='44a8ce6dfca8a07609c957ba325708cc9fe9b024e2551a209e570ad7ce006e93'
BEFORE_ELF_SHA='cf1d1caf927af6465ce45f5e95b09fa292b5ddcd454b37207736f309d2011fa7'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='''typedef struct {
    u8 reserved[0x34];
    f32 position[3];
    f32 endPoint[3];
    u8 reserved4C[0xF4];
    f32 velocity[3];
    f32 verticalAcceleration;
    f32 damping;
} DualPointMotion1BA1D0;
extern f32 D_800BE9A4;
'''
FUNCTION='func_1518F058'
ENTRY,ROM,SIZE=0x1518F058,0x1BC508,176
BODY=176
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='b5dcf3352427638d5d24889006cc09eae5888dc51ead8fa0bdfa4bbce391db6c')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Damp planar velocity and advance both points by the same displacement. */
s32 func_1518F058(DualPointMotion1BA1D0 *motion) {
    f32 damping = motion->damping;
    f32 step;
    f32 dx, dy, dz;

    motion->velocity[0] *= damping;
    motion->velocity[1] += motion->verticalAcceleration * D_800BE9A4;
    motion->velocity[2] *= damping;
    step = D_800BE9A4;
    dx = motion->velocity[0] * step;
    dy = motion->velocity[1] * step;
    dz = motion->velocity[2] * step;
    motion->position[0] += dx;
    motion->position[1] += dy;
    motion->position[2] += dz;
    motion->endPoint[0] += dx;
    motion->endPoint[1] += dy;
    motion->endPoint[2] += dz;
    return 1;
}'''}
BINDINGS={0:[('R_MIPS_HI16','D_800BE9A4')],4:[('R_MIPS_LO16','D_800BE9A4')]}
GUARD_SHA='c29ddb1088d2b844a43b92bae7199d7045f19bab36c29b25798c9b44d4bcc6a5'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Dual-point motion manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Dual-point motion frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Dual-point motion old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Dual-point motion retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown character dual-point motion placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS.replace('extern f32 D_800BE9A4;\n','')+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero dual-point motion alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildDualPointMotionOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def normalized(raw,bindings):
    if digest(raw)!='5b0da6fb4d23890270aaf0d3bffeb52077855823711a217722bd216b67eaa1e4' or bindings!=BINDINGS:
        raise ValueError('Dual-point raw body or symbolic binding changed')
    words=list(struct.unpack('>44I',raw));before=list(words)
    # Free V0 for the independent return value; V1 carries only the step address.
    for index,shift in ((0,16),(1,21),(1,16),(8,21),(17,21)):
        if words[index]>>shift&31!=2:raise ValueError('Dual-point address role changed')
        words[index]=(words[index]&~(31<<shift))|(3<<shift)
    if words[22]!=0x24020001 or words.count(0x24020001)!=1:
        raise ValueError('Dual-point return initializer changed')
    words.insert(5,words.pop(22))
    if sum(a!=b for a,b in zip(before,words))!=20:
        raise ValueError('Dual-point schedule normalization extent changed')
    return struct.pack('>44I',*words),dict(bindings)


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Dual-point guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()))
    fields=['filename','function','offset','expected','replacement','expected_relocations',
        'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if reader.fieldnames!=fields or any(row['function']==FUNCTION for row in reader):
        raise ValueError('Dual-point guard schema or prior function changed')
    fitted,after_bindings=normalized(raw,bindings)
    newline='\r\n' if old.endswith(b'\r\n') else '\n'
    if not old.endswith(newline.encode()):raise ValueError('Dual-point guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=newline)
    for at in range(0,len(raw),4):
        a,b=struct.unpack_from('>I',raw,at)[0],struct.unpack_from('>I',fitted,at)[0]
        if a==b:continue
        spec=lambda rs:';'.join(kind+':'+symbol for kind,symbol in rs.get(at,[]))or'-'
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
            expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=spec(bindings),
            replacement_relocations=spec(after_bindings),
            note='Normalize checked timestep address role and independent return initialization',omit='false'))
    return old+stream.getvalue().encode()


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('DualPointMotion image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('DualPointMotion predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('DualPointMotion old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('DualPointMotion strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('DualPointMotion current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('DualPointMotion owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=BODY or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=normalized(raw,bindings):
            raise ValueError('DualPointMotion direct C/original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=BINDINGS:
            raise ValueError('DualPointMotion linked words or two bindings differ')
        rows[name]=dict(words=44,frame=0,bindings=2,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],*payload(after,FUNCTION)))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('DualPointMotion predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('DualPointMotion predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('DualPointMotion changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('DualPointMotion neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('DualPointMotion owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=44,slot_words=44,alignment_words=0,new_guards=20,compiler_only=False,preserved_neighbors=neighbors,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True,target_size_before=12,target_size_after=BODY)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';reports=[]
    for label,src,obj,proposal,raw,wanted in(
        ('target',SOURCE,OBJECT,'proposed-owner.c','after-owner.o',output/'qualified-padded.o'),):
        shadow=output/('make-shadow-'+label);relative=obj.removeprefix('conker/build/')
        target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
            cwd=conker,capture_output=True,text=True,check=True)
        (output/('make-shadow-'+label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
                raise ValueError('Unexpected dual-point motion Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown dual-point motion redirect')
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
            raise ValueError('DualPointMotion normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('DualPointMotion actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_1BA1D0.c.o'
    if script.count(old)!=1:raise ValueError('DualPointMotion link owner changed')
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
        raise ValueError('DualPointMotion independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('DualPointMotion changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('DualPointMotion protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
