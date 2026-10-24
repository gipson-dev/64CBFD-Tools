"""Direct-C character-effect pairs with strict owner, ABI and whole-image gates."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows,SYMBOL
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='generated_179F30'
SOURCE,ASM,OBJECT='conker/src/game/generated_179F30.c','conker/asm/179F30.s','conker/build/src/game/generated_179F30.c.o'
BUILD='conker/build/game-character-effect-pair/qualified'
SNAPSHOT_SHA='073b5ad6f76cfb1261138858c595cf286f52a49881a5371145eee733d5150db3'
BEFORE_OBJECT_SHA='380203df6b429aeb3bf92095973af7a1b5dee48cf55f63242c59ec84590dabb9'
BEFORE_ELF_SHA='af5894403d84c78df0b9c28198bdc75a51a02adf229f3c711a83bb82edeee4e8'
HEADERS='#include <ultra64.h>\ns32 func_1514EC1C(s32, s32, s32);\n'
DECLARATIONS=''.join('extern u8 D_%08X[];\n'%a for a in(0x800A58D0,0x800A58E4,0x800A58F8,0x800A590C))+'''s32 func_1518D1C0(void *, s32, s32, s32, u8, u8, void *);
s32 func_1515D5F8(s32, s32, s32, s32, u8, u8, u8, u8, s32, s32);
'''
TARGETS={
 'func_1514E508':dict(entry=0x1514E508,rom=0x17B9B8,descriptor=0x800A58D0,key=13,index=6,
  retail_SHA256='18609e6fe21c043e9c4fce197d8a30b993127897dbe7bab4ddb05798b727b00f'),
 'func_1514E5B8':dict(entry=0x1514E5B8,rom=0x17BA68,descriptor=0x800A58E4,key=13,index=4,
  retail_SHA256='9bd171db829ab8065034cffb80a4e157fc9bc483c3e55ab86a28f4db9ce8335b'),
 'func_1514E668':dict(entry=0x1514E668,rom=0x17BB18,descriptor=0x800A58F8,key=13,index=5,
  retail_SHA256='966f98d0a6b5f8542344fb4c6f0c2ace18d8cb448cc2daa6f182d09b5a7649b5'),
 'func_1514E718':dict(entry=0x1514E718,rom=0x17BBC8,descriptor=0x800A590C,key=14,index=7,
  retail_SHA256='b61b6ba2fe0dbe0dc52571cebf6915db7cd6fe5467da834665ed84bc98ac1c49')}
FUNCTIONS=tuple(TARGETS)
SELECTED={}
for name,t in TARGETS.items():
 SELECTED[name]='''/* Create the character effect and attach its owner-address companion. */
void NAME(u8 *owner) {
    s32 result;
    s32 address;

    result = func_1518D1C0(owner, 5, 0, 1, 0xFF, 1, DESCRIPTOR);
    func_1514EC1C(result, (s32)owner, KEY);
    address = (s32)(owner + 0x14);
    result = func_1515D5F8(-0x8000, address >> 16, address & 0xFFFF,
                          5, 0xFF, 0xFF, 0xFF, 0xFF, 0, 0);
    func_1514EC1C(result, (s32)owner, 0x18);
}'''.replace('NAME',name).replace('DESCRIPTOR','D_%08X'%t['descriptor']).replace('KEY','0x%X'%t['key'])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Character effects manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Character effects frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Character effects old object changed')
    for name,t in TARGETS.items():
        if digest(values['conker/conker.us.bin'][t['rom']:t['rom']+176])!=t['retail_SHA256']:
            raise ValueError('Character effects retail slot changed: '+name)
    return values


def recovered_owner(before):
    result=before
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown character effects placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    for mode in(7,5):
        old='func_1518D1C0(arg0, %d, 0, 1, 0xFF, 1,'%mode
        if result.count(old)!=1:raise ValueError('Unknown legacy constructor call')
        result=result.replace(old,'func_1518D1C0((void *)arg0, %d, 0, 1, 0xFF, 1,'%mode)
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero effects alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildCharacterEffectsOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('CharacterEffects image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('CharacterEffects predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('CharacterEffects old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,176)
    return reorder_metadata(bytes(result))


def reorder_metadata(image):
    groups=(('D_800A58E4','D_80097BB4'),
            ('D_800A58F8','func_1507B8F4','D_80097BC8'),
            ('D_800A590C','D_800A1B5C','D_800A5E5C'))
    result=bytearray(image)
    entries={name:(at,fields,string)for at,name,fields,string in symbol_rows(image)}
    for names in groups:
        rows=[entries[name]for name in names];start,string_at=rows[0][0],rows[0][2]
        strings_base=string_at-rows[0][1][0]
        if any(row[0]!=start+i*SYMBOL.size or row[2]-row[1][0]!=strings_base for i,row in enumerate(rows)):
            raise ValueError('Character-effects bounded symbol order changed')
        old=b''.join(name.encode()+b'\0'for name in names)
        if image[string_at:string_at+len(old)]!=old:raise ValueError('Character-effects bounded strings changed')
        for i,name in enumerate(names[1:]+names[:1]):
            fields=list(entries[name][1]);fields[0]=string_at-strings_base
            SYMBOL.pack_into(result,start+i*SYMBOL.size,*fields)
            literal=name.encode()+b'\0';result[string_at:string_at+len(literal)]=literal;string_at+=len(literal)
    canonical=lambda data:sorted((name,fields[1:])for _,name,fields,_ in symbol_rows(data))
    if canonical(result)!=canonical(image):raise ValueError('Character-effects named symbol definition changed')
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('CharacterEffects strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('CharacterEffects current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('CharacterEffects owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=176 or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=(raw,bindings):
            raise ValueError('CharacterEffects direct C/original payload differs')
        linked,fs=link_owner(root,output,isolated,OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or sum(map(len,bindings.values()))!=6:
            raise ValueError('CharacterEffects linked words or six bindings differ')
        rows[name]=dict(words=44,frame=48,bindings=6,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('CharacterEffects predecessor extent changed')
        expected[name]['size']=176;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('CharacterEffects predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('CharacterEffects changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-4 or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('CharacterEffects neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('CharacterEffects owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=176,new_guards=0,compiler_only=True,preserved_neighbors=neighbors,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,
        all_owner_addresses_fixed=True,target_size_before=12,target_size_after=176)
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
                raise ValueError('Unexpected effects Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown effects redirect')
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
            raise ValueError('CharacterEffects normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('CharacterEffects actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_179F30.c.o'
    if script.count(old)!=1:raise ValueError('CharacterEffects link owner changed')
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
        raise ValueError('CharacterEffects independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('CharacterEffects changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('CharacterEffects protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-4,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
