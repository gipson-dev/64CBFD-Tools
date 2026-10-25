"""Direct C recovery of the linked-record RGBA16 image sampler."""
import json
from pathlib import Path
import shlex
import shutil
import struct
import subprocess

from tools.experiments import game_list_record_constructor_match as records
from tools.experiments.game_four_head_lookup_match import digest,diagnostics,payload
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='generated_1AB530'
FUNCTION='func_1517E1AC'
SOURCE='conker/src/game/generated_1AB530.c'
ASM='conker/asm/1AB530.s'
OBJECT='conker/build/src/game/generated_1AB530.c.o'
CALLER='func_1501878C'
CALLER_SOURCE='conker/src/game_45B80.c'
CALLER_OBJECT='conker/build/src/game_45B80.c.o'
CALLER_ASM='conker/asm/nonmatchings/game_45B80/func_1501878C.s'
BUILD='conker/build/game-list-record-sample-match'
ENTRY,ROM,SIZE=0x1517E1AC,0x1AB65C,224
PARENT,PARENT_ROM,PARENT_WORDS=0x1501878C,0x45C3C,412
RAW_SHA='418fb0289a421f4680957a0003d80c9e2dc29c746dbb6712b83e349dffd259c4'
RETAIL_SHA='e2ff360d01ee671976751fa8d514b1f0b033b1c0dd75fb7d64128a8c6a46a821'
BEFORE_ELF_SHA='d7f55e4df3b36403d433d98d12497133a35e74b135a9a944ddaef6247dd88f56'
SNAPSHOT_SHA='790b42a17519b9383a17eeba46d756ba4d3a89a0c255f363b70731b294857cef'
BINDINGS={0:[('R_MIPS_HI16','D_800DDD64')],4:[('R_MIPS_LO16','D_800DDD64')],
    8:[('R_MIPS_HI16','D_800BE9C4')],12:[('R_MIPS_LO16','D_800BE9C4')],
    20:[('R_MIPS_HI16','D_800BE624')],36:[('R_MIPS_LO16','D_800BE624')],
    24:[('R_MIPS_HI16','D_800BE620')],32:[('R_MIPS_LO16','D_800BE620')]}
PROTOTYPE='void func_1517E1AC(void);'
HEADERS=records.HEADERS
DECLARATIONS=records.DECLARATIONS.replace('    u8 opaque2A[4];',
    '    u16 sample2A;\n    u8 opaque2C[2];')+'''
extern s32 D_800BE620, D_800BE624;
extern s32 D_800BE9C4;
'''
SELECTED='''/* Sample the current RGBA16 image at each in-bounds record position. */
void func_1517E1AC(void) {
    ListRecord1AB530 *node = D_800DDD64;

    while (node != NULL) {
        if (node->valueC >= 0.0f && node->valueC < D_800BE620 &&
            node->value10 >= 0.0f && node->value10 < D_800BE624) {
            node->sample2A = ((u16 *)D_800BE9C4)[(s32)node->valueC + (s32)node->value10 * D_800BE620];
        }
        node = node->next;
    }
}'''


def snapshot(output):
    if digest((output/'input-snapshot.json').read_bytes())!=SNAPSHOT_SHA:
        raise ValueError('List sample frozen manifest changed')
    values={}
    for name,wanted in json.loads((output/'input-snapshot.json').read_text())['INPUTS'].items():
        raw=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(raw)!=wanted:raise ValueError('List sample frozen input changed: '+name)
        values[name]=raw
    if digest(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:
        raise ValueError('List sample image predecessor changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE])!=RETAIL_SHA:
        raise ValueError('List sample original changed')
    if values[OBJECT]!=(output/'before-padded.o').read_bytes():
        raise ValueError('List sample predecessor object changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517E1AC() {\n    return 0;\n}':
        raise ValueError('Unknown list sample placeholder')
    if before.count(records.DECLARATIONS)!=1:
        raise ValueError('Qualified constructor private view changed')
    return (before[:lo]+SELECTED+before[hi:]).replace(records.DECLARATIONS,DECLARATIONS,1)


def typed_caller(before):
    old='s32 func_1517E1AC(void);'
    if before.count(old)!=1 or PROTOTYPE in before:
        raise ValueError('Unknown sample-query caller declaration')
    return before.replace(old,PROTOTYPE,1)


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ListSampleOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def checked_payload(raw,bindings):
    if len(raw)!=SIZE or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('List sample full raw body or bindings changed')
    return raw,bindings


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:
        raise ValueError('List sample strict image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)
        if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('List sample old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('List sample strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            typed_caller(before.decode()).encode()if installed and name==CALLER_SOURCE else
            (output/'qualified-padded.o').read_bytes()if installed and name==OBJECT else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])
            if installed and name=='conker/build/conker.us.elf'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('List sample current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('List sample owner diagnostics changed')
    selected,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=checked_payload(*payload(selected,FUNCTION))
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=(raw,bindings):
        raise ValueError('List sample isolated/owner/original payload differs')
    asm=output/'qualified-padded.s'
    asm.write_text(emit_padded_assembly(after,root/ASM,
        word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
    obj=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',
        str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=SIZE
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('List sample owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('List sample linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('List sample other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('List sample owner neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('List sample pools changed')
    prior,da=compile_owner(root,output,values[CALLER_SOURCE].decode(),'before-caller')
    parent,db=compile_owner(root,output,typed_caller(values[CALLER_SOURCE].decode()),'typed-caller')
    if diagnostics(da)!=diagnostics(db):raise ValueError('List sample caller diagnostics changed')
    caller_functions=same_functions(prior,parent,())
    if caller_functions!=len(parse_object(prior)[1])or normalized_pools(prior)!=normalized_pools(parent):
        raise ValueError('List sample typed caller functions/pools changed')
    original_parent=values['conker/conker.us.bin'][PARENT_ROM:PARENT_ROM+4*PARENT_WORDS]
    old_elf=values['conker/build/conker.us.elf'];at=elf_slot_offset(old_elf,PARENT,len(original_parent))
    if old_elf[at:at+len(original_parent)]!=original_parent:
        raise ValueError('List sample retained caller is not byte exact')
    (output/'proposed-owner.c').write_text(wanted)
    (output/'proposed-caller.c').write_text(typed_caller(values[CALLER_SOURCE].decode()))
    report=dict(body_words=56,slot_words=56,alignment_words=0,frame=0,bindings=8,new_guards=0,direct_C=True,
        preserved_neighbors=neighbors,preserved_global_asm=values[SOURCE].count(b'#pragma GLOBAL_ASM('),
        owner_diagnostics_unchanged=True,pools_identical=True,canonical_ABI='void(void)',
        canonical_buffer_global='s32',explicit_u16_pointer_cast=True,typed_caller_words=PARENT_WORDS,
        typed_caller_compact_functions_unchanged=caller_functions,caller_frame=104,
        original_constructor_unchanged=True,record_size=52,sample_offset=42)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def _make_target(root,output,source,object_path,proposal,folder,expected_compact):
    conker=root/'conker';shadow=output/folder;relative=object_path.removeprefix('conker/build/')
    target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (output/(folder+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unknown list sample Make command: '+repr(args))
        args=[proposal.relative_to(conker).as_posix()if a==source.removeprefix('conker/')else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown list sample redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/(expected_compact+'-diagnostics.txt')).read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):
            raise ValueError(p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):
        raise ValueError('List sample actual Make compiler profile changed')
    processors=[a for a in commands if a[0]=='python3'and a[1].endswith('/asm_processor.py')]
    padders=[a for a in commands if a[0]=='python3'and a[1].endswith(('/pad_c_object.py','/pad_generated_object.py'))]
    assemblers=[a for a in commands if a[0]=='mips-linux-gnu-as']
    if len(processors)not in(0,2)or len(padders)!=1 or len(assemblers)!=1 or len(commands)!=3+len(processors):
        raise ValueError('Unknown list sample actual Make route')
    actual=conker/target;count=same_functions(output/(expected_compact+'.o'),Path(str(actual)+'.compact'),())
    return actual,dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,
        asm_processor_commands=len(processors),inherited_warnings=plan.stderr)


def make_shadow(root,output):
    actual,child=_make_target(root,output,SOURCE,OBJECT,output/'proposed-owner.c','make-shadow-target','after-owner')
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():
        raise ValueError('List sample actual Make owner differs')
    caller,parent=_make_target(root,output,CALLER_SOURCE,CALLER_OBJECT,
        output/'proposed-caller.c','make-shadow-caller','typed-caller')
    if caller.read_bytes()!=(output/('before-'+CALLER_OBJECT.replace('/','_'))).read_bytes():
        raise ValueError('List sample actual Make typed caller object changed')
    shutil.copy2(caller,output/'qualified-caller.o')
    child['complete_padded_object_equal']=True;parent['complete_caller_object_unchanged']=True
    report=dict(target=child,caller=parent)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('List sample link owner changed')
    link=output/'first-link.ld'
    script=script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix())
    caller=CALLER_OBJECT.removeprefix('conker/')
    if script.count(caller)!=1:raise ValueError('List sample link caller changed')
    script=script.replace(caller,(output/'qualified-caller.o').relative_to(root/'conker').as_posix())
    link.write_text(script)
    elf=output/'first-linked.elf'
    result=subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt',
        '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
        '--no-check-sections','--no-warn-mismatch','-Map',elf.with_suffix('.map').relative_to(root/'conker').as_posix(),
        '-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,text=True)
    (output/'first-link-diagnostics.txt').write_text(result.stdout+result.stderr)
    if result.returncode:raise ValueError(result.stdout+result.stderr)
    actual=elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    check_image(values['conker/build/conker.us.elf'],actual,truth)
    before=values['conker/build/conker.us.elf'];changed=[i for i,(a,b)in enumerate(zip(before,actual))if a!=b]
    at=elf_slot_offset(before,ENTRY,SIZE)
    report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=len(changed),
        code_bytes=sum(at<=i<at+SIZE for i in changed),metadata_bytes=sum(not at<=i<at+SIZE for i in changed),
        exclusions=0,typed_caller_relinked=True)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root,output):
    values=check_inputs(root,output,installed=True)
    expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():
        raise ValueError('List sample independent image/object differs')
    if(root/CALLER_OBJECT).read_bytes()!=(output/'qualified-caller.o').read_bytes():
        raise ValueError('List sample installed caller object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:
        raise ValueError('List sample other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('List sample protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data,new_guards=0)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
