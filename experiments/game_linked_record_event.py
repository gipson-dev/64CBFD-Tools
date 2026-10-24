"""Canonical linked-record callback with derived setup and return-path guards."""
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

OWNER='generated_124920'
SOURCE,ASM,OBJECT='conker/src/game/generated_124920.c','conker/asm/124920.s','conker/build/src/game/generated_124920.c.o'
BUILD='conker/build/game-linked-record-event/qualified'
SNAPSHOT_SHA='a8184b84756b5b6d335a1e6b239c41f4b765207a41f4c6fc06982e140faa46ca'
BEFORE_OBJECT_SHA='cbaa6267b3ad4ef351a6301e5e64fe4b3b8988a831efe2618ccfc55f3b642016'
BEFORE_ELF_SHA='e828f0d65cc68d8ead6eea5c36cd2dfa2f4427ad8401bf5284b26998b93ee9b3'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='''typedef struct {
    s32 reference;
    u8 tag, reserved05[3];
    u8 selected, reserved09[3];
    u8 *records[8];
} LinkedRecordGroup124920;

s32 func_150F892C();
'''
FUNCTION='func_150F887C'
ENTRY,ROM,SIZE=0x150F887C,0x125D2C,176
BODY=176
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='ca33fd71aa84e7b731007d6f840322324a96fefa1e137fe6e91d57e99b5c98d9')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Select the final linked record or forward a matching reference event. */
void func_150F887C(struct260 *owner, s32 packetAddress, u8 command) {
    LinkedRecordGroup124920 *group;
    u8 i;

    if (command == 0x42) {
        group = (LinkedRecordGroup124920 *)((u8 *)owner + 0x28);
        if (((u8 *)packetAddress)[4] == group->tag) {
            for (i = 0; i < 7; i++) {
                group->records[i][0x6E] = 1;
            }
            group->records[7][0x6E] = 0;
            group->selected = 7;
        }
    } else if (command == 0x3F) {
        if (*(s32 *)packetAddress == *(s32 *)((u8 *)owner + 0x28)) {
            func_150F892C(owner);
        }
    }
}'''}
BINDINGS={144:[('R_MIPS_26','func_150F892C')]}
GUARD_SHA='33c920d93cb96bd2061b122f95620df6e15632fdc959baf491f1c2eba27ddf7e'
RAW_SHA='f2b02e8534548f0f7d738710ad067ccfbf75ea7f85aa8d8410d589a259588da3'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Random-vector payload manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Random-vector payload frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Random-vector payload old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Random-vector payload retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown character linked-record event placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero linked-record event alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildLinkedRecordEventOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def checked_parts(raw,bindings):
    if len(raw)!=168 or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Linked-record complete raw body or binding changed')
    w=list(struct.unpack('>42I',raw))
    if (w[0],w[4],w[38],w[39],w[40],w[41])!=(0x27BDFFE8,0xAFBF0014,0x8FBF0014,0x27BD0018,0x03E00008,0):
        raise ValueError('Linked-record frame or retained return changed')
    order=list(range(42));order[9:15]=[12,9,10,11,14,13];order[27:29]=[28,27]
    insertions={14:w[38],28:w[38]}
    locations={source:index+sum(at<index for at in insertions)for index,source in enumerate(order)}
    replacements=[]
    for index,source in enumerate(order):
        word=w[source]
        if source==9:
            # Fold the existing owner offset through the derived group-address value.
            word=(word&0xFC000000)|((w[12]>>16&31)<<21)|((w[10]>>16&31)<<16)|((word&65535)-(w[12]&65535))
        elif source==10:word=(word&~(31<<16))|(w[9]>>16&31)<<16
        if source in(7,13,22,27,30,34):
            old=w[source]&65535;old-=65536 if old&0x8000 else 0
            target=source+1+old
            if source in(13,27):
                if target!=38:raise ValueError('Linked-record return edge changed')
                target=39
            if source==13:word=((word>>26|16)<<26)|(word&0x03FFFFFF)
            distance=locations[target]-locations[source]-1
            word=(word&0xFFFF0000)|(distance&65535)
        replacements.append(word)
    moved={locations[at//4]*4:rs for at,rs in bindings.items()}
    return w,replacements,insertions,moved


def normalized(raw,bindings):
    _,replacements,insertions,moved=checked_parts(raw,bindings);out=[]
    for index,word in enumerate(replacements):
        out.append(word)
        if index in insertions:out.append(insertions[index])
    if len(out)!=44:raise ValueError('Linked-record fitted extent changed')
    return struct.pack('>44I',*out),moved


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Linked-record guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    if fields!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Linked-record guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Linked-record rows already exist')
    w,replacements,insertions,_=checked_parts(raw,bindings)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Linked-record guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=newline);count=0
    for index,(before,after)in enumerate(zip(w,replacements)):
        if before==after and index not in insertions:continue
        if index*4 in bindings:raise ValueError('Unexpected binding inside linked-record setup/return guards')
        row=dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(index*4),expected='0x%08X'%before,replacement='0x%08X'%after,
            expected_relocations='-',replacement_relocations='-',omit='false',
            note='Derive linked-record setup lifetime and split shared return restoration')
        if index in insertions:row.update(insert_after='0x%08X'%insertions[index],insert_after_relocations='-')
        writer.writerow(row);count+=1
    if count!=9:raise ValueError('Linked-record derived guard count changed')
    return old+stream.getvalue().encode()


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('LinkedRecordEvent image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('LinkedRecordEvent predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('LinkedRecordEvent old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('LinkedRecordEvent strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('LinkedRecordEvent current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('LinkedRecordEvent owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=168 or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=normalized(raw,bindings):
            raise ValueError('LinkedRecordEvent semantic C/normalized original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=BINDINGS:
            raise ValueError('LinkedRecordEvent linked words or binding differ')
        rows[name]=dict(words=44,raw_words=42,frame=24,bindings=1,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],*payload(after,FUNCTION)))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('LinkedRecordEvent predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('LinkedRecordEvent predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('LinkedRecordEvent changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('LinkedRecordEvent neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('LinkedRecordEvent owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=44,slot_words=44,alignment_words=0,new_guards=9,inserted_return_loads=2,compiler_only=False,preserved_neighbors=neighbors,
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
                raise ValueError('Unexpected linked-record event Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown linked-record event redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
            if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):
                raise ValueError(p.stdout+p.stderr)
            if redirect is not None:redirect.write_text(p.stdout)
            commands.append(args)
        actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        expected_commands=5
        processors=[a for a in commands if a[0]=='python3'and a[1]=='../tools/asm-processor/asm_processor.py']
        if(len(commands)!=expected_commands or len(compilers)!=1 or len(processors)!=2
                or not all(f in compilers[0]for f in('-O2','-g3'))):
            raise ValueError('LinkedRecordEvent normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('LinkedRecordEvent actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_124920.c.o'
    if script.count(old)!=1:raise ValueError('LinkedRecordEvent link owner changed')
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
        raise ValueError('LinkedRecordEvent independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('LinkedRecordEvent changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('LinkedRecordEvent protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
