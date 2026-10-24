"""Guarded owner payload with explicit returns and preserved unspecified storage."""
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

OWNER='generated_FB600'
SOURCE,ASM,OBJECT='conker/src/game/generated_FB600.c','conker/asm/FB600.s','conker/build/src/game/generated_FB600.c.o'
BUILD='conker/build/game-large-owner-payload/qualified'
SNAPSHOT_SHA='d4f57ea369f93945127a24a47e52cc6ded0a3a0266cdc27d0478c7af0fbe4baf'
BEFORE_OBJECT_SHA='c55cc38790f75ea10afa3fecf5db7e2d79d9e798ebfea3450ed6d4c0b1ac60f8'
BEFORE_ELF_SHA='f5f5c17a2ccd35e3c59fe76fe161bfc6241e271c49ed9744e38c7facceff6710'
HEADERS='#include <ultra64.h>\n#include <string.h>\n'
DECLARATIONS='''typedef struct {
    u8 active, callback, flags, reserved3;
    s16 duration;
    u8 category, reserved7;
} OwnerPayloadHeaderFB600;

typedef struct {
    u8 *owner;
    u8 identity, reserved5[3];
    f32 first, second;
    s32 limit;
    u8 enabled, reserved15[0x8DB];
} LargeOwnerPayloadFB600;

extern f32 D_800A07FC;
void *func_1515FF74(void *, s32, u8, s32);
'''
FUNCTION='func_150CE150'
ENTRY,ROM,SIZE=0x150CE150,0xFB600,176
BODY=176
TARGETS={FUNCTION:dict(entry=ENTRY,rom=ROM,retail_SHA256='6b1e98bf88d1d86811408d002e0323a5ac86ab6427da77651dbb84dd380bce9a')}
FUNCTIONS=tuple(TARGETS)
SELECTED={FUNCTION:'''/* Allocate an owner-linked record and copy its partially initialized payload. */
void *func_150CE150(u8 *owner, s16 duration, u8 selector, s32 category) {
    OwnerPayloadHeaderFB600 header;
    LargeOwnerPayloadFB600 payload;
    void *record;

    if (owner == NULL) {
        return NULL;
    }
    header.active = 1;
    header.callback = 1;
    header.flags = 0;
    header.duration = duration;
    header.category = 2;
    payload.first = D_800A07FC;
    payload.second = D_800A07FC;
    payload.limit = 10000;
    payload.enabled = 0;
    payload.owner = owner;
    payload.identity = owner[0x3B];
    record = func_1515FF74(&header, sizeof(payload), selector, category);
    if (record != NULL) {
        record = memcpy((u8 *)record + 0x18, &payload, sizeof(payload));
    }
    return record;
}'''}
RAW_BINDINGS={56:[('R_MIPS_HI16','D_800A07FC')],60:[('R_MIPS_LO16','D_800A07FC')],
    128:[('R_MIPS_26','func_1515FF74')],152:[('R_MIPS_26','memcpy')]}
BINDINGS={32:[('R_MIPS_HI16','D_800A07FC')],56:[('R_MIPS_LO16','D_800A07FC')],
    128:[('R_MIPS_26','func_1515FF74')],152:[('R_MIPS_26','memcpy')]}
RAW_SHA='09ad51fae08e63f2c78a773194062540f1b5250c5dba8bacc8897ae0a6d6034c'
GUARD_SHA='37202e65d9b3ba00aa994bc102fef71630337a9f6ea736a05d492e7d0a2e5c07'



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
    result=before.replace('#include <ultra64.h>',HEADERS.rstrip())
    for name in FUNCTIONS:
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 %s() {\n    return 0;\n}'%name:raise ValueError('Unknown character large-owner payload placeholder')
        result=result[:lo]+SELECTED[name]+result[hi:]
    at=result.index(SELECTED[FUNCTIONS[0]])
    return result[:at]+DECLARATIONS+'\n'+result[at:]


def payload(obj,name):
    data,functions,bindings=parse_object(obj);info=functions[name]
    raw=data[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero large-owner payload alignment tail')
    return raw[:end*4],{at-info['value']:rows for at,rows in bindings.items()if info['value']<=at<info['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ChildLargeOwnerPayloadOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def schedule(raw,bindings):
    if len(raw)!=184 or digest(raw)!=RAW_SHA or bindings!=RAW_BINDINGS:
        raise ValueError('Large-owner complete C payload or bindings changed')
    words=list(struct.unpack('>46I',raw))
    # Move independent setup lifetimes; memory accesses retain their original relative order.
    order=[*range(8),14,8,10,9,12,13,15,16,17,11,*range(18,46)]
    if sorted(order)!=list(range(46)):raise ValueError('Invalid owner-payload permutation')
    after=[words[i] for i in order]
    rel={i*4:bindings[p*4]for i,p in enumerate(order)if p*4 in bindings}
    omitted={40,41}
    if words[40:42]!=[0x00401825,0x00601025]:
        raise ValueError('Owner-payload redundant result copies changed')
    kept=[i for i in range(46)if i not in omitted];positions={p:i for i,p in enumerate(kept)}
    # Both return edges skip the redundant phi copies to the same live-V0 epilogue.
    for branch,target in ((12,42),(34,42)):
        previous=branch+1+((after[branch]&65535)^0x8000)-0x8000
        if previous!=(42 if branch==12 else 41):raise ValueError('Owner-payload return edge changed')
        displacement=positions[target]-positions[branch]-1
        after[branch]=(after[branch]&0xFFFF0000)|(displacement&65535)
    # The delay-slot copy established V1=V0 before the conditional payload address.
    if after[35]!=0x00401825 or after[36]!=0x24440018:raise ValueError('Owner-payload result lifetime changed')
    after[36]=(after[36]&~(31<<21))|(3<<21)
    return after,rel,omitted


def normalized(raw,bindings):
    words,rs,omitted=schedule(raw,bindings)
    kept=[i for i in range(46)if i not in omitted]
    return struct.pack('>44I',*(words[i]for i in kept)),{
        n*4:rs[i*4]for n,i in enumerate(kept)if i*4 in rs}


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Large-owner guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()))
    fields=['filename','function','offset','expected','replacement','expected_relocations',
        'replacement_relocations','note','insert_after','insert_after_relocations','omit']
    if reader.fieldnames!=fields or any(row['function']==FUNCTION for row in reader):
        raise ValueError('Large-owner guard schema or prior target changed')
    words,rs,omitted=schedule(raw,bindings)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Large-owner guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=newline)
    count=0
    for i,b in enumerate(words):
        at=i*4;a=struct.unpack_from('>I',raw,at)[0]
        if a==b and bindings.get(at,[])==rs.get(at,[])and i not in omitted:continue
        spec=lambda rows:';'.join(k+':'+s for k,s in rows.get(at,[]))or'-'
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
            expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=spec(bindings),
            replacement_relocations=spec(rs),
            note='Normalize checked owner-payload setup and redundant result copies',
            omit='true'if i in omitted else'false'))
        count+=1
    if count!=12:raise ValueError('Large-owner guard extent changed')
    return old+stream.getvalue().encode()


def predicted_image(before,truths):
    if digest(before)!=BEFORE_ELF_SHA or set(truths)!=set(FUNCTIONS):raise ValueError('LargeOwnerPayload image predecessor changed')
    result=bytearray(before)
    for name,t in TARGETS.items():
        truth=truths[name]
        if digest(truth)!=t['retail_SHA256']:raise ValueError('LargeOwnerPayload predicted body changed')
        at=elf_slot_offset(before,t['entry'],176);result[at:at+176]=truth
        rows=[offset for offset,n,fields,_ in symbol_rows(before)
              if n==name and fields[1:3]==(t['entry'],12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('LargeOwnerPayload old symbol extent changed')
        struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def truths(values):
    rom=values['conker/conker.us.bin']
    return {name:rom[t['rom']:t['rom']+176]for name,t in TARGETS.items()}


def check_image(before,actual,bodies):
    if actual!=predicted_image(before,bodies):raise ValueError('LargeOwnerPayload strict image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
                  predicted_image(before,truths(values))if installed and name=='conker/build/conker.us.elf'else
                  guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('LargeOwnerPayload current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('LargeOwnerPayload owner diagnostics changed: '+da+db)
    bodies=truths(values);rows={}
    for name,t in TARGETS.items():
        isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED[name],'selected-'+name)
        if diag:raise ValueError(diag)
        raw,bindings=payload(isolated,name)
        if len(raw)!=184 or payload(after,name)!=(raw,bindings)or payload(original(root,output,name),name)!=normalized(raw,bindings):
            raise ValueError('LargeOwnerPayload direct C/original payload differs')
        linked,fs=link_owner(root,output,original(root,output,name),OWNER);at=fs[name]['value']
        if linked[at:at+176]!=bodies[name]or bindings!=RAW_BINDINGS:
            raise ValueError('LargeOwnerPayload linked words or three bindings differ')
        rows[name]=dict(words=44,raw_words=46,frame=2328,bindings=4,raw_SHA256=digest(raw),retail_SHA256=digest(bodies[name]))
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],*payload(after,FUNCTION)))
    padded=output/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=padded.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(obj),str(padded)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};masked_a=bytearray(a);masked_b=bytearray(b)
    for name,t in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('LargeOwnerPayload predecessor extent changed')
        expected[name]['size']=BODY;at=fb[name]['value']
        slot=elf_slot_offset(values['conker/build/conker.us.elf'],t['entry'],176)
        if a[at:at+176]!=values['conker/build/conker.us.elf'][slot:slot+176]or b[at:at+176]!=bodies[name]:
            raise ValueError('LargeOwnerPayload predecessor or linked target differs')
        masked_a[at:at+176]=bytes(176);masked_b[at:at+176]=bytes(176)
    if expected!=fb or masked_a!=masked_b:raise ValueError('LargeOwnerPayload changed another owner extent/body')
    neighbors=same_functions(before,after,FUNCTIONS)
    if neighbors!=len(parse_object(before)[1])-len(FUNCTIONS) or same_functions(old,obj,FUNCTIONS)!=neighbors:raise ValueError('LargeOwnerPayload neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('LargeOwnerPayload owner pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=rows,total_words=44,slot_words=44,alignment_words=0,new_guards=12,omitted_redundant_words=2,compiler_only=False,preserved_neighbors=neighbors,
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
                raise ValueError('Unexpected large-owner payload Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown large-owner payload redirect')
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
            raise ValueError('LargeOwnerPayload normal Make profile changed')
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('LargeOwnerPayload actual Make padded object differs: '+label)
        reports.append(dict(copy=label,actual_Make_commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_FB600.c.o'
    if script.count(old)!=1:raise ValueError('LargeOwnerPayload link owner changed')
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
        raise ValueError('LargeOwnerPayload independent image or object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!=set(FUNCTIONS):
        raise ValueError('LargeOwnerPayload changed other function/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('LargeOwnerPayload protected Game data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-len(FUNCTIONS),all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
