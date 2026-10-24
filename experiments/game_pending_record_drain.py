"""Qualify the pending-record drain and its three independent setup guards."""
import csv
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments.game_four_head_lookup_match import digest,diagnostics,payload
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='generated_1A89B0'
FUNCTION='func_1517CFC4'
SOURCE='conker/src/game/generated_1A89B0.c'
ASM='conker/asm/1A89B0.s'
OBJECT='conker/build/src/game/generated_1A89B0.c.o'
CALLER='conker/src/game_45B80.c'
CALLER_OBJECT='conker/build/src/game_45B80.c.o'
BUILD='conker/build/game-pending-record-drain/qualified'
ENTRY,ROM,SIZE=0x1517CFC4,0x1AA474,176
SNAPSHOT_SHA='6dab0a00369d380c465cafd70b061628b4436f4c6abd88a0f90aa7ab04511603'
BEFORE_OBJECT_SHA='745ecc4f761e08777e33f52f3059acbf8a2bc2983f06e216b650383b5e2f83ef'
BEFORE_ELF_SHA='edba3f330f4c4e2cc2606b9152a3643dacce779ea73647c7c18de2a2c890a0e9'
GUARD_SHA='3549c907ae0c0fc23e481978b35699507c979357fecf496eef44b74064881404'
RAW_SHA='e0657ab8cf6943b229007db402d1aa9466befb962e77122b7f4bb4b74697566d'
RETAIL_SHA='34c6806c0435d8ee95970da3c6d50898842f67dc3743628b58a90dcba8063ac6'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='''/* Private view of the pending pointer in each 16-byte record. */
typedef struct {
    u8 reserved00[8];
    void *pending;
    u8 reserved0C[4];
} PendingRecord1A89B0;

extern s32 D_800DDA90;
extern s32 D_800DD478;
extern u32 D_8003809C;
s32 func_10006240(void *, void *, u32);
void func_10004074(void *);
'''
SELECTED='''/* Process present destinations, then consume each nonempty pending slot. */
void func_1517CFC4(void) {
    PendingRecord1A89B0 *record;
    s32 index;
    void *destination;

    record = (PendingRecord1A89B0 *)&D_800DDA90;
    for (index = 0; index != 15; index++) {
        if (record->pending != NULL) {
            destination = ((void **)&D_800DD478)[index * 26];
            if (destination != NULL) {
                func_10006240(record->pending, destination, D_8003809C);
                func_10004074(record->pending);
            }
            record->pending = NULL;
        }
        record++;
    }
}'''
BINDINGS={32:[('R_MIPS_HI16','D_800DDA90')],44:[('R_MIPS_LO16','D_800DDA90')],
 36:[('R_MIPS_HI16','D_8003809C')],52:[('R_MIPS_LO16','D_8003809C')],
 40:[('R_MIPS_HI16','D_800DD478')],48:[('R_MIPS_LO16','D_800DD478')],
 108:[('R_MIPS_26','func_10006240')],116:[('R_MIPS_26','func_10004074')]}


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Pending-drain manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Pending-drain frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Pending-drain old object changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE])!=RETAIL_SHA:raise ValueError('Pending-drain retail slot changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517CFC4() {\n    return 0;\n}':raise ValueError('Unknown pending-drain placeholder')
    return before[:lo]+DECLARATIONS+'\n'+SELECTED+before[hi:]


def recovered_caller(before):
    old='s32 func_1517CFC4(void);'
    if before.count(old)!=1:raise ValueError('Pending-drain caller prototype changed')
    return before.replace(old,'void func_1517CFC4(void);')


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('PendingDrainOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=SIZE or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Pending-drain complete raw body or bindings changed')
    words=list(struct.unpack('>44I',raw));result=list(words);moved=dict(bindings)
    # Cycle only the three independent low-address setups, with their bindings.
    for dst,src in ((11,12),(12,13),(13,11)):
        result[dst]=words[src];moved[dst*4]=bindings[src*4]
    return struct.pack('>44I',*result),moved


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Pending-drain guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    if fields!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Pending-drain guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Pending-drain guards already exist')
    fitted,moved=normalized(raw,bindings);before=struct.unpack('>44I',raw);after=struct.unpack('>44I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Pending-drain guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator=newline)
    encode=lambda rows:';'.join(kind+':'+name for kind,name in rows)or'-'
    for index in (11,12,13):
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(index*4),expected='0x%08X'%before[index],
            replacement='0x%08X'%after[index],expected_relocations=encode(bindings[index*4]),
            replacement_relocations=encode(moved[index*4]),omit='false',
            note='Cycle independent pending-drain destination, scratch and source address setup'))
    return old+stream.getvalue().encode()


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('Pending-drain image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('Pending-drain old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Pending-drain strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            recovered_caller(before.decode()).encode()if installed and name==CALLER else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else
            guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Pending-drain current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Pending-drain owner diagnostics changed')
    isolated,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=payload(isolated,FUNCTION);fitted=normalized(raw,bindings)
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=fitted:
        raise ValueError('Pending-drain isolated/owner/original payload differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=guards,filename=OWNER))
    obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=SIZE
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('Pending-drain owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('Pending-drain linked target/predecessor changed')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('Pending-drain other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('Pending-drain neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Pending-drain pools changed')
    caller_a,ca=compile_owner(root,output,values[CALLER].decode(),'before-caller')
    caller_b,cb=compile_owner(root,output,recovered_caller(values[CALLER].decode()),'after-caller')
    callers=same_functions(caller_a,caller_b,())
    if diagnostics(ca)!=diagnostics(cb)or normalized_pools(caller_a)!=normalized_pools(caller_b):raise ValueError('Pending-drain caller changed')
    if callers!=len(parse_object(caller_a)[1]):raise ValueError('Pending-drain caller function set changed')
    (output/'proposed-owner.c').write_text(wanted)
    (output/'proposed-caller.c').write_text(recovered_caller(values[CALLER].decode()))
    report=dict(words=44,frame=48,bindings=8,new_guards=3,compiler_only=False,preserved_neighbors=neighbors,
        caller_functions_identical=callers,owner_diagnostics_unchanged=True,caller_diagnostics_unchanged=True,pools_identical=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';reports=[]
    for label,src,obj,proposal,raw in (('target',SOURCE,OBJECT,'proposed-owner.c','after-owner.o'),
            ('caller',CALLER,CALLER_OBJECT,'proposed-caller.c','after-caller.o')):
        shadow=output/('make-shadow-'+label);relative=obj.removeprefix('conker/build/')
        target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
        (output/('make-'+label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown pending-drain Make command: '+repr(args))
            args=[(output/proposal).relative_to(conker).as_posix()if a==src.removeprefix('conker/')else
                (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
            redirect=None
            if '>'in args:
                if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown pending-drain redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            expected=(output/('after-owner-diagnostics.txt'if label=='target'else'after-caller-diagnostics.txt')).read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
            if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
            if redirect is not None:redirect.write_text(p.stdout)
            commands.append(args)
        actual=conker/target
        count=same_functions(output/raw,Path(str(actual)+'.compact'),())
        wanted=output/'qualified-padded.o'if label=='target'else root/CALLER_OBJECT
        if actual.read_bytes()!=wanted.read_bytes():raise ValueError('Pending-drain actual Make padded object differs: '+label)
        compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
        if len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('Pending-drain Make profile changed')
        reports.append(dict(copy=label,commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
            complete_padded_object_equal=True,cleanup_skipped=True,inherited_warnings=plan.stderr))
    (output/'make-shadow.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('Pending-drain link owner changed')
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
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Pending-drain independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Pending-drain other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Pending-drain protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
