"""Inline owner identity events: identical retail body, ordinary-owner qualification."""
import csv
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess

from tools.experiments.game_four_head_lookup_match import digest,diagnostics,payload,fields
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.pad_generated_object import parse_object
emit_padded_assembly=pad_c_object.emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='game_DBA60'
FUNCTION='func_150AEDF8'
SOURCE='conker/src/game_DBA60.c'
ASM='conker/asm/nonmatchings/game_DBA60/func_150AEDF8.s'
OBJECT='conker/build/src/game_DBA60.c.o'
CALLER_SOURCE='conker/src/game/done/game_1765E0.c'
CALLER_OBJECT='conker/build/src/game/done/game_1765E0.c.o'
BUILD='conker/build/game-inline-owner-identity-match'
ENTRY,ROM,SIZE,BODY=0x150AEDF8,0xDC2A8,184,172
PARENT,TABLE,TABLE_ROM=0x15149434,0x8008A8D8,0x22F398
SNAPSHOT_SHA='fce174db569f175e697adf176778a301be702ba968859345f20725d3592e3514'
BEFORE_OBJECT_SHA='b7b35c59d755b5e630347c645d1d91c44a8c1d3caa1d1081980ef7b571407b97'
BEFORE_ELF_SHA='08f3110edeb2864ff15ffb896bbfb76573dcd62bcfcb31bf569af0e3511a5820'
GUARD_SHA='3e824bc7b855f611e262a233050f0caad0e21af1386deca9965a740258e1b588'
RAW_SHA='c85a7adaeb83153172857e9ba8072d604a6cc280a4d393976cdd93d92eef2f35'
RETAIL_SHA='771fdfa585ef5a9b1c3e2387f8ac51688536ef743da67d414d1fe9a5259abc71'
CALLER_SHA='dcc2285633c2d0497b6bc24d71aaa3c884d25925d0282ce530e29b6d30b34b4a'
TABLE_SHA='2e141cceb4d96cca9cedaf57161088aa51ab333ff81d4c46bca9aea7f40a4de8'
HEADERS='#include <ultra64.h>\n#include "structs.h"\n'
RELEASE_DECLARATION='void func_1516972C(struct102 *);\n'
DECLARATIONS='''/* Only the inline link's identity word and saved key are exposed. */
typedef struct {
    s32 value;
    u8 key;
} InlineOwnerIdentityDBA60;
'''
SELECTED='''/* Retarget the inline owner link, or release the owner for a matching event. */
void func_150AEDF8(struct260 *record, s32 eventAddress, u8 command) {
    u8 *owner = (u8 *)record;
    InlineOwnerIdentityDBA60 *state = (InlineOwnerIdentityDBA60 *)(owner + 0x28);
    u8 *event = (u8 *)eventAddress;
    s32 code = command;

    if (command == 0x2D) {
        s32 current = state->value;
        s32 first = *(s32 *)event;
        if (first == current) {
            state->value = *(s32 *)(event + 4);
            state->key = event[9];
        } else if (*(s32 *)(event + 4) == current) {
            state->value = first;
            state->key = event[8];
        }
    } else if (code == 0) {
        if (*(s32 *)event == state->value || state->key == event[4]) {
            func_1516972C((struct102 *)owner);
        }
    }
}'''
BINDINGS={148:[('R_MIPS_26','func_1516972C')]}
GUARD_WORDS=(10,11,12,20,22,29,30,31,33,34,35)


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Inline-identity manifest changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Inline-identity frozen input changed: '+name)
        values[name]=data
    if digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Inline-identity old object changed')
    rom=values['conker/conker.us.bin']
    if digest(rom[ROM:ROM+SIZE])!=RETAIL_SHA or digest(rom[0x1768E4:0x176940])!=CALLER_SHA:
        raise ValueError('Inline-identity original target/caller changed')
    if digest(rom[TABLE_ROM:TABLE_ROM+296])!=TABLE_SHA:raise ValueError('Inline-identity registry changed')
    return values


def recovered_owner(before):
    marker='/* Non-matching C placeholders for asm/nonmatchings/game_DBA60/func_150AEDF8.s. */'
    old='s32 func_150AEDF8() {\n    return 0;\n}'
    prototype='s32 func_150AEDF8();\n'
    if before.count(marker)!=1 or before.count(old)!=1 or before.count(prototype)!=1:
        raise ValueError('Inline identity predecessor anchors changed')
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!=old:raise ValueError('Inline identity placeholder changed')
    tail=before[hi:]
    if not tail.startswith('\n// void func_150AEDF8(')or any(line and not line.startswith('//')for line in tail.strip().splitlines()):
        raise ValueError('Inline identity historical comment boundary changed')
    prefix=before[:before.index(marker)].replace(prototype,'')
    return prefix+DECLARATIONS+'\n'+SELECTED+'\n'



def original(root,output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('InlineOwnerIdentityOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+FUNCTION,(root/ASM).read_text(),FUNCTION)


def normalized(raw,bindings):
    if len(raw)!=BODY or digest(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Inline-identity complete raw body or bindings changed')
    words=list(struct.unpack('>43I',raw));out=list(words)
    def roles(word,mapping,rs=False,rt=False):
        a,b=word>>21&31,word>>16&31
        return fields(word,rs=mapping.get(a,a)if rs else None,rt=mapping.get(b,b)if rt else None)
    def commute(word):
        if word>>26 not in(4,21):raise ValueError('Inline-identity comparison shape changed')
        return fields(word,rs=word>>16&31,rt=word>>21&31)
    # The retarget path exchanges its saved-current and first-event-word roles.
    identity={3:4,4:3}
    for at in(10,11):
        if words[at]>>26!=35:raise ValueError('Inline-identity identity load changed')
        out[at]=roles(words[at],identity,rt=True)
    for at in(12,20):
        if words[at]>>26!=21:raise ValueError('Inline-identity identity comparison changed')
        out[at]=roles(words[at],identity,rs=True,rt=True)
    out[20]=commute(out[20])
    if words[22]>>26!=43:raise ValueError('Inline-identity identity store changed')
    out[22]=roles(words[22],identity,rt=True)
    # Restore event-before-state reads and the following non-overlapping roles.
    release={10:3,11:10,12:11}
    if(words[29]>>26,words[30]>>26,words[29]>>21&31,words[30]>>21&31)!=(35,35,2,5):
        raise ValueError('Inline-identity release read pair changed')
    out[29]=roles(words[30],release,rt=True);out[30]=words[29]
    if words[31]>>26!=4:raise ValueError('Inline-identity release comparison changed')
    out[31]=commute(roles(words[31],release,rs=True,rt=True))
    for at in(33,34):
        if words[at]>>26!=36:raise ValueError('Inline-identity key load changed')
        out[at]=roles(words[at],release,rt=True)
    if words[35]>>26!=21:raise ValueError('Inline-identity key comparison changed')
    out[35]=roles(words[35],release,rs=True,rt=True)
    if tuple(i for i,(a,b)in enumerate(zip(words,out))if a!=b)!=GUARD_WORDS:
        raise ValueError('Inline-identity derived guard closure changed')
    return struct.pack('>43I',*out),dict(bindings)


def guard_bytes(old,raw,bindings):
    if digest(old)!=GUARD_SHA:raise ValueError('Inline-identity guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:
        raise ValueError('Inline-identity guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Inline-identity guards already exist')
    fitted,_=normalized(raw,bindings);before=struct.unpack('>43I',raw);after=struct.unpack('>43I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Inline-identity guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for i in GUARD_WORDS:
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],
            expected_relocations='-',replacement_relocations='-',omit='false',
            note='Derive inline identity roles, independent read order and commutative comparisons'))
    return old+stream.getvalue().encode()


def predicted_image(before,truth):
    if digest(before)!=BEFORE_ELF_SHA or digest(truth)!=RETAIL_SHA:raise ValueError('Inline-identity image predecessor/body changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[off for off,name,f,_ in symbol_rows(before)if name==FUNCTION and f[1:3]==(ENTRY,12)and f[3]&15==2]
    if len(rows)!=1:raise ValueError('Inline-identity old symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Inline-identity strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output)
    for name,before in values.items():
        expected=(recovered_owner(before.decode()).encode()if installed and name==SOURCE else
            predicted_image(before,values['conker/conker.us.bin'][ROM:ROM+SIZE])if installed and name=='conker/build/conker.us.elf'else
            guard_bytes(before,*payload(output/'after-owner.o',FUNCTION))if installed and name=='conker/retail_word_patches.us.csv'else
            (output/'qualified-padded.o').read_bytes()if installed and name==OBJECT else before)
        if(root/name).read_bytes()!=expected:raise ValueError('Inline identity current input differs: '+name)
    return values



def qualify(root,output):
    values=check_inputs(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    if diagnostics(da)!=diagnostics(db):raise ValueError('Inline-identity owner diagnostics changed')
    isolated,diag=compile_owner(root,output,HEADERS+RELEASE_DECLARATION+DECLARATIONS+SELECTED,'selected')
    if diag:raise ValueError(diag)
    raw,bindings=payload(isolated,FUNCTION);fitted=normalized(raw,bindings)
    if payload(after,FUNCTION)!=(raw,bindings)or payload(original(root,output),FUNCTION)!=fitted:
        raise ValueError('Inline-identity isolated/owner/original payload differs')
    guards=output/'qualified-guards.csv';guards.write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],raw,bindings))
    asm=output/'qualified-padded.s';asm.write_text(emit_padded_assembly(after,root/"conker/retail_layout.us.txt",word_patches_path=guards,filename=OWNER))
    obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(i)for n,i in fa.items()};expected[FUNCTION]['size']=BODY
    if fa[FUNCTION]['size']!=12 or expected!=fb:raise ValueError('Inline-identity owner extents changed')
    at=fb[FUNCTION]['value'];truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]or b[at:at+SIZE]!=truth:
        raise ValueError('Inline-identity linked target/predecessor differs')
    if a[:at]+a[at+SIZE:]!=b[:at]+b[at+SIZE:]:raise ValueError('Inline-identity other owner bytes changed')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=len(parse_object(before)[1])-1 or same_functions(old,obj,(FUNCTION,))!=neighbors:
        raise ValueError('Inline-identity neighbors changed')
    if normalized_pools(before)!=normalized_pools(after)or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Inline-identity pools changed')
    before_image=values['conker/build/conker.us.elf'];rom=values['conker/conker.us.bin']
    if before_image[elf_slot_offset(before_image,PARENT,92):][:92]!=rom[0x1768E4:0x176940]:raise ValueError('Inline-identity retained caller changed')
    if before_image[elf_slot_offset(before_image,TABLE,296):][:296]!=rom[TABLE_ROM:TABLE_ROM+296]:raise ValueError('Inline-identity live registry changed')
    if(root/CALLER_OBJECT).read_bytes()!=values[CALLER_OBJECT]:raise ValueError('Inline-identity caller owner changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(body_words=43,slot_words=46,alignment_words=3,frame=24,bindings=1,new_guards=11,compiler_only=False,
        preserved_neighbors=neighbors,preserved_global_asm=values[SOURCE].count(b'#pragma GLOBAL_ASM('),
        owner_diagnostics_unchanged=True,pools_identical=True,dead_duplicate_load_word=19,
        canonical_ABI='void(struct260*,s32,u8)',existing_typed_release_interface_preserved=True,
        caller_words=23,caller_preexisting_exact=True,caller_owner_object_unchanged=True,registry_entries=74,registry_index=39)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    conker=root/'conker';shadow=output/'make-shadow-target';relative=OBJECT.removeprefix('conker/build/')
    target=(shadow/relative).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown record-event Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a==SOURCE.removeprefix('conker/')else
            (output/'qualified-guards.csv').relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown record-event redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr)!=diagnostics(expected)or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    actual=conker/target;count=same_functions(output/'after-owner.o',Path(str(actual)+'.compact'),())
    if actual.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Inline-identity actual Make padded object differs')
    compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=3 or len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3')):raise ValueError('Inline-identity Make profile changed')
    report=dict(commands=len(commands),normal_O2_g3=True,compact_functions_equal=count,complete_padded_object_equal=True,
        cleanup_skipped=True,inherited_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predict(root,output):
    values=snapshot(output);script=(root/'conker/build/conker.ld').read_text();old=OBJECT.removeprefix('conker/')
    if script.count(old)!=1:raise ValueError('Inline-identity link owner changed')
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
    if(output/'first-linked.elf').read_bytes()!=expected or(root/OBJECT).read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Inline-identity independent image/object differs')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Inline-identity other linked function/address changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Inline-identity protected Game data changed')
    report=dict(other_bodies_fixed=len(b)-1,all_addresses_fixed=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report


ARTIFACTS=('before-owner.o','after-owner.o','selected.o','qualified-padded.o',
           'qualified-guards.csv','proposed-owner.c','first-linked.elf')


def verify_prepared(output):
    frozen=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(frozen)!=set(ARTIFACTS):raise ValueError('Inline identity artifact set changed')
    for name,wanted in frozen.items():
        if digest((output/name).read_bytes())!=wanted:
            raise ValueError('Inline identity prepared artifact changed: '+name)
    return frozen


def prepare(root,output):
    if(output/'artifact-fingerprint.json').exists():
        raise ValueError('Inspect previous preparation instead of recompiling frozen objects')
    result=dict(owner=qualify(root,output),Make=make_shadow(root,output),image=predict(root,output))
    frozen={name:digest((output/name).read_bytes())for name in ARTIFACTS}
    (output/'artifact-fingerprint.json').write_text(json.dumps(frozen,indent=2)+'\n')
    verify_prepared(output)
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];output=root/BUILD
    print(json.dumps(prepare(root,output)if args.prepare else audit(root,output)),flush=True)
