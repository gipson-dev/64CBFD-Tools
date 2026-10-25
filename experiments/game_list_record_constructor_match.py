"""Direct C recovery of the append-only 0x34-byte list record constructor."""
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

OWNER='generated_1AB530'
FUNCTION='func_1517E080'
SOURCE='conker/src/game/generated_1AB530.c'
ASM='conker/asm/1AB530.s'
OBJECT='conker/build/src/game/generated_1AB530.c.o'
CALLER='func_15009150'
CALLER_SOURCE='conker/src/game/done/game_36600.c'
CALLER_OBJECT='conker/build/src/game/done/game_36600.c.o'
BUILD='conker/build/game-list-record-constructor-match'
ENTRY,ROM,SIZE=0x1517E080,0x1AB530,180
PARENT,PARENT_ROM=0x15009150,0x36600
RAW_SHA='90cc02c9c9cd63748d3a100af9990078709120434db5a20be7070e08a0d169a4'
RETAIL_SHA='cae57ce334c0cf7d3d552d7fcbab08ff5e41d6b6c7bf2fc7db88a0bf1d7d82cc'
BEFORE_ELF_SHA='37453ffe5c12ed22d3ef731ac0f583111d3f792bffe94bc80dcb33238fb4e182'
SNAPSHOT_SHA='eeda7173e088d9fdde31ca9418f5e1ee05c7b62c7c34a78afa8e6a83eac47ad0'
BINDINGS={4:[('R_MIPS_HI16','D_800DDD64')],8:[('R_MIPS_LO16','D_800DDD64')],88:[('R_MIPS_26','allocate_memory')]}
PROTOTYPE='struct162 *func_1517E080(s32 first, s32 second);\n'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
DECLARATIONS='''/* Complete private view; the shared struct162 stops before byte 0x30. */
typedef struct ListRecord1AB530 {
    u8 opaque0[0xC];
    f32 valueC;
    f32 value10;
    u8 opaque14[0x10];
    struct ListRecord1AB530 *next;
    s16 state28;
    u8 opaque2A[4];
    u8 flags2E;
    u8 first2F;
    u8 second30;
    u8 opaque31[3];
} ListRecord1AB530;

extern ListRecord1AB530 *D_800DDD64;
s32 allocate_memory(s32, s32, s32, s32);
'''
SELECTED='''/* Append through the captured tail link and initialize only the owned fields. */
struct162 *func_1517E080(s32 first, s32 second) {
    ListRecord1AB530 *node;
    ListRecord1AB530 **link;

    node = D_800DDD64;
    if (node != NULL) {
        while (node->next != NULL) {
            node = node->next;
        }
        link = &node->next;
    } else {
        link = &D_800DDD64;
    }
    node = (ListRecord1AB530 *)allocate_memory(0x34, 1, 0, 1);
    if (node == NULL) {
        return NULL;
    }
    *link = node;
    node->next = NULL;
    node->state28 = 0;
    node->flags2E = 0;
    node->value10 = 0.0f;
    node->valueC = 0.0f;
    node->first2F = first;
    node->second30 = second;
    return (struct162 *)node;
}'''


def snapshot(output):
    if digest((output/'input-snapshot.json').read_bytes())!=SNAPSHOT_SHA:raise ValueError('List record manifest changed')
    values={}
    for name,wanted in json.loads((output/'input-snapshot.json').read_text())['INPUTS'].items():
        raw=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(raw)!=wanted:raise ValueError('List record frozen input changed: '+name)
        values[name]=raw
    if digest(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('List record predecessor changed')
    if digest(values['conker/conker.us.bin'][ROM:ROM+SIZE])!=RETAIL_SHA:raise ValueError('List record original changed')
    if values[OBJECT]!=(output/'before-padded.o').read_bytes():raise ValueError('List record old object changed')
    return values


def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517E080() {\n    return 0;\n}':raise ValueError('Unknown list record placeholder')
    if before.count('#include <ultra64.h>')!=1:raise ValueError('List record include changed')
    result=before[:lo]+DECLARATIONS+'\n'+SELECTED+before[hi:]
    result=result.replace('#include <ultra64.h>','#include <ultra64.h>\n#include "structs.h"',1)
    return result.replace('/* Non-matching placeholders for the text-only asm slice asm/1AB530.s. */',
        '/* C recoveries and remaining non-matching routines from asm/1AB530.s. */',1)


def typed_caller(before):
    marker='#include "variables.h"\n'
    if before.count(marker)!=1 or PROTOTYPE in before:raise ValueError('Unknown list record caller include')
    return before.replace(marker,marker+'\n'+PROTOTYPE,1)


def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('ListRecordOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def checked_payload(raw,bindings):
    if len(raw)!=SIZE or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('List record complete raw body or bindings changed')
    return raw,bindings


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('List record image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('List record old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('List record strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            typed_caller(before.decode()).encode()if installed and name==CALLER_SOURCE else
            (output/'qualified-padded.o').read_bytes()if installed and name==OBJECT else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else before)
        if(root/name).read_bytes()!=expected:raise ValueError('List record current input differs: '+name)
    return values


def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('List record owner diagnostics changed')
    selected,diag=compile_owner(root,output,HEADERS+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=checked_payload(*payload(selected,FUNCTION))
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=(raw,bindings):
        raise ValueError('List record isolated/owner/original payload differs')
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
    obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=SIZE
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('List record owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('List record linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('List record other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:raise ValueError('List record neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('List record pools changed')
    parent,diag=compile_owner(root,output,typed_caller(values[CALLER_SOURCE].decode()),'typed-caller')
    if diag:raise ValueError(diag)
    if same_functions(parent,output/('before-'+CALLER_OBJECT.replace('/','_')),())!=1:raise ValueError('List record typed caller changed')
    original_parent=values['conker/conker.us.bin'][PARENT_ROM:PARENT_ROM+128]
    if values['conker/build/conker.us.elf'][elf_slot_offset(values['conker/build/conker.us.elf'],PARENT,128):][:128]!=original_parent:
        raise ValueError('List record retained caller not exact')
    (output/'proposed-owner.c').write_text(wanted);(output/'proposed-caller.c').write_text(typed_caller(values[CALLER_SOURCE].decode()))
    report=dict(body_words=45,slot_words=45,alignment_words=0,frame=32,bindings=3,new_guards=0,direct_C=True,
        preserved_neighbors=neighbors,preserved_global_asm=values[SOURCE].count(b'#pragma GLOBAL_ASM('),owner_diagnostics_unchanged=True,
        pools_identical=True,canonical_ABI='struct162*(s32,s32)',typed_caller_words=32,typed_caller_body_unchanged=True,
        allocation_bytes=52,captured_tail_before_allocation=True,partial_initialization=True,allocation_failure_returns_NULL=True)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';shadow=output/'make-shadow-target';relative=OBJECT.removeprefix('conker/build/')
    target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown list record Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a==SOURCE.removeprefix('conker/')else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown list record redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    actual=conker/target;count=same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),())
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('List record actual Make padded object differs')
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=5 or len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('List record Make profile changed')
    if sum(a[0]=='python3'and a[1].endswith('/asm_processor.py')for a in commands)!=2:
        raise ValueError('List record original GLOBAL_ASM build route changed')
    report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,complete_padded_object_equal=True,inherited_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('List record link owner changed')
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
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('List record independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('List record other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('List record protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data,new_guards=0)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
