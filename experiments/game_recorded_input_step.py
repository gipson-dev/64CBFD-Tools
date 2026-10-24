"""Guarded recorded-input playback with explicit integer wrapping and ordering."""
import csv
import io
import hashlib
from collections import Counter
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

OWNER='generated_20A990'
SOURCE,ASM,OBJECT='conker/src/game/generated_20A990.c','conker/asm/20A990.s','conker/build/src/game/generated_20A990.c.o'
BUILD='conker/build/game-recorded-input-step/qualified'
SNAPSHOT_SHA='812d7e2e31743da724e1afc7719f8e6729ff452d0b6f81166b5c79fdba92424b'
BEFORE_OBJECT_SHA='30afeb237cc17362474c58611dcc54a6883818f3110aa903f63b7678e572bd78'
BEFORE_ELF_SHA='693badff1224f03e5d012f81d6701439265561c94a0e98a76b56470d277ef9ae'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='''typedef struct {
    s8 x, y;
    u16 ticks;
    u16 buttons;
} RecordedInput20A990;
extern RecordedInput20A990 *D_800E0A70;
extern s32 D_800E0A74, D_800BE9E4;
extern u8 D_800E0BD2;
extern OSContPad D_800BE748;
'''
FUNCTION='func_151DD8C0'
ENTRY,ROM,SIZE=0x151DD8C0,0x20AD70,176
BODY=172
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='ef52073270f9e8922b45411803ec5ba3ff84ab79bafbd65bedab516f2d881f2e')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Apply a recorded sample, preserve Start, and cap the playback cursor. */
void func_151DD8C0(void) {
    s32 index;
    RecordedInput20A990 *record;
    u16 held;
    u16 buttons;

    index = D_800E0A74;
    record = &D_800E0A70[index];
    held = D_800BE748.button;
    D_800BE748.stick_x = record->x;
    D_800BE748.stick_y = record->y;
    buttons = record->buttons;
    D_800E0BD2 = 0;
    D_800BE748.button = buttons | (held & 0x1000);
    if (index < 499) {
        s32 next = record[1].ticks;
        s32 previous = D_800BE9E4;
        if (previous < next) {
            D_800E0BD2 = (u8)((u32)next - (u32)previous);
        }
    }
    D_800BE9E4 = record->ticks;
    D_800E0A74 = (s32)((u32)index + 1U);
    if (D_800E0A74 >= 499) {
        D_800E0A74 = 499;
    }
}'''}
BINDINGS={0:[('R_MIPS_HI16','D_800E0A74')],20:[('R_MIPS_LO16','D_800E0A74')],
    4:[('R_MIPS_HI16','D_800BE748')],16:[('R_MIPS_LO16','D_800BE748')],
    8:[('R_MIPS_HI16','D_800E0BD2')],12:[('R_MIPS_LO16','D_800E0BD2')],
    28:[('R_MIPS_HI16','D_800E0A70')],32:[('R_MIPS_LO16','D_800E0A70')],
    104:[('R_MIPS_HI16','D_800BE9E4')],112:[('R_MIPS_LO16','D_800BE9E4')],
    136:[('R_MIPS_HI16','D_800BE9E4')],144:[('R_MIPS_LO16','D_800BE9E4')]}
GUARD_SHA='0699ca82d26f56db1928f885e454fb639c2675cb957c1a8f7861cb9cf573e671'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Recorded-input manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Recorded-input frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Recorded-input old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Recorded-input retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown character recorded input placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero recorded input alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildRecordedInputOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def normalized(raw,bindings):
    if digest(raw)!='d8dcafa10c22e6b8d883039a1fa199ac38ac56a5d63f40c2d445379253114072' or bindings!=BINDINGS:
        raise ValueError('Recorded-input raw body or symbolic bindings changed')
    before=list(struct.unpack('>43I',raw));words=list(before)
    for i,w in enumerate(before):
        # Renaming is simultaneous, with disjoint early-button/late-clock roles.
        roles={2:3,3:4,4:2,5:10 if i<26 else 5,6:6,7:5,8:7,9:15,10:11,11:12,
            12:2,13:13,14:25,15:24 if i<19 else 15,24:8,25:9}
        op=w>>26
        shifts=(21,16,11)if op==0 and w&63 in(0,0x21,0x23,0x25,0x2A)else (21,16)if op in(9,10,12,15,32,35,36,37,40,41,43)else ()
        if op==15:shifts=(16,)
        if not shifts and w not in(0x10200008,0x10200002,0x14200002,0x03E00008):
            raise ValueError('Recorded-input instruction class changed')
        for shift in shifts:
            old=w>>shift&31;words[i]=(words[i]&~(31<<shift))|(roles.get(old,old)<<shift)
    w=words[12]
    if w&63!=0x21:raise ValueError('Recorded-input unsigned address addition changed')
    words[12]=(w&~((31<<21)|(31<<16)))|((w>>16&31)<<21)|((w>>21&31)<<16)
    order=list(range(43))
    order[0],order[1]=order[1],order[0];order[4],order[5]=order[5],order[4]
    if before[19]!=0x240F01F3:raise ValueError('Recorded-input clamp constant changed')
    order.insert(39,order.pop(19));after=[words[i]for i in order]
    branch,target=order.index(38),order.index(41)
    if after[branch]!=0x14200002:raise ValueError('Recorded-input clamp branch changed')
    after[branch]=(after[branch]&0xFFFF0000)|(target-branch-1)
    moved={4*n:bindings[4*i]for n,i in enumerate(order)if 4*i in bindings}
    if sum(a!=b or bindings.get(i*4,[])!=moved.get(i*4,[])for i,(a,b)in enumerate(zip(before,after)))!=40:
        raise ValueError('Recorded-input normalization extent changed')
    return struct.pack('>43I',*after),moved


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
        if a==b and bindings.get(at,[])==after_bindings.get(at,[]):continue
        spec=lambda rs:';'.join(kind+':'+symbol for kind,symbol in rs.get(at,[]))or'-'
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
            expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=spec(bindings),
            replacement_relocations=spec(after_bindings),
            note='Normalize checked playback register lifetimes, address setup and clamp scheduling',omit='false'))
    return old+stream.getvalue().encode()


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('RecordedInput image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('RecordedInput predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('RecordedInput old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)
    rows={name:(offset,fields,location)for offset,name,fields,location in symbol_rows(before)}
    for names in (
            ('D_800E0A70','D_8009A0A8','D_80099260','D_800A3560','D_800A3108'),
            ('D_800E0A74','D_800E0A31','D_80099264','D_800A3564')):
        slots=[rows[name]for name in names]
        for i,(name,(offset,fields,location))in enumerate(zip(names,slots)):
            if (offset-slots[0][0],location-slots[0][2],fields[1:])!=(16*i,11*i,(int(name[2:],16),0,16,0,65521)):
                raise ValueError('Recorded-input closed symbol cycle changed')
            if before[location:location+11]!=name.encode()+b'\0':raise ValueError('Recorded-input symbol string changed')
            other,_,_=slots[(i+1)%len(slots)]
            result[offset+4:offset+16]=before[other+4:other+16]
            result[location:location+11]=names[(i+1)%len(names)].encode()+b'\0'
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('RecordedInput strict image differs')
    expected=Counter((name,fields[1],BODY if name==FUNCTION else fields[2],*fields[3:])
        for _,name,fields,_ in symbol_rows(before))
    observed=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Recorded-input named definition changed beyond target size')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('RecordedInput current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('RecordedInput owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=BODY or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=normalized(raw,bindings):
            raise ValueError('RecordedInput direct C/original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=BINDINGS:
            raise ValueError('RecordedInput linked words or twelve bindings differ')
        rows[name]=dict(words=43,frame=0,bindings=12,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],*payload(after,FUNCTION)))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('RecordedInput predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('RecordedInput predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('RecordedInput changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('RecordedInput neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('RecordedInput owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=43,slot_words=44,alignment_words=1,new_guards=40,compiler_only=False,preserved_neighbors=neighbors,
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
                raise ValueError('Unexpected recorded input Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown recorded input redirect')
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
            raise ValueError('RecordedInput normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('RecordedInput actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_20A990.c.o'
    if script.count(old)!=1:raise ValueError('RecordedInput link owner changed')
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
        raise ValueError('RecordedInput independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('RecordedInput changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('RecordedInput protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
