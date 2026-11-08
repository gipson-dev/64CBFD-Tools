"""Actor/list query semantic C, address rematerialization and full-owner/caller/image gates."""
import csv,hashlib,io,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_remaining_donor_candidates import compile_owner as base_compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-actor-list-query-150229E4-match'
SOURCE='conker/src/game/generated_49D30.c'
OBJECT='conker/build/src/game/generated_49D30.c.o'
CALLER_SOURCE='conker/src/game/generated_58F80.c'
CALLER_OBJECT='conker/build/src/game/generated_58F80.c.o'
OWNER,FUNCTION='generated_49D30','func_150229E4'
ENTRY,ROM,WORDS,FRAME=0x150229E4,0x4FE94,73,0
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='4f1c6cffa47cdb0b298956cc3a058e44cf0d61a6d2e0f01bd9e73ec269920a4f'
GUARD_SHA='5ec2bcc421e929efbf856ce3b03e3e8e30e06d56a3d8716492eafadb409bc166'
RAW_SHA='89aa4cb3ae59362a10d7cca9f45121729f33a1e380fb44c9d31ca51abf6ed045'
sha=lambda b:hashlib.sha256(b).hexdigest()
BINDINGS={20: [('R_MIPS_HI16', 'D_800C35C8')], 24: [('R_MIPS_LO16', 'D_800C35C8')], 76: [('R_MIPS_HI16', 'D_800CBFDF')], 152: [('R_MIPS_LO16', 'D_800CBFDF')], 48: [('R_MIPS_HI16', 'D_800C363A')], 160: [('R_MIPS_LO16', 'D_800C363A')], 176: [('R_MIPS_HI16', 'D_800C35F0')], 184: [('R_MIPS_LO16', 'D_800C35F0')]}
SELECTED='extern u8 D_800CBFDF[];\n/* Find an enabled type-two descriptor for the actor or its linked identity. */\ns32 func_150229E4(struct127 *actor) {\n    s32 group = 0;\n    s32 index;\n    s32 ownerSlot;\n    u8 identity;\n    u16 *enabled;\n    GroupActorRecord15022528 *record;\n\n    if (actor == NULL) return 0;\n    if (actor->interaction_state == 0) return 0;\n    if (D_800C35C8[0] == NULL) return 0;\n    if (actor->unk5 == 4) group = 1;\n    ownerSlot = actor->unk65;\n    if (ownerSlot != 0) identity = D_800CBFDF[ownerSlot * sizeof(struct127)];\n    else identity = actor->unique_id;\n    index = 0;\n    if (D_800C363A[group] > 0) {\n        enabled = D_800C35C8[group];\n        do {\n            if (*enabled != 0) {\n                record = (GroupActorRecord15022528 *)(D_800C35F0[group] + index * 8);\n                if (record->kind == 2 && record->actorId == identity) {\n                    if (ownerSlot == 0) return 1;\n                    return 2;\n                }\n            }\n            index++;\n            enabled++;\n        } while (index < D_800C363A[group]);\n    }\n    return 0;\n}'
STUB='s32 func_150229E4() {\n    return 0;\n}'


def compile_owner(root,out,source,name):
    run=subprocess.run;seen=[]
    def profiled(argv,**kwargs):
        if argv[0]==str(root/'ido/ido5.3_recomp/cc'):
            argv=list(argv);argv.insert(argv.index('-mips2'),'-Wo,-loopunroll,0');seen.append(argv)
        return run(argv,**kwargs)
    with patch.object(subprocess,'run',side_effect=profiled):result=base_compile_owner(root,out,source,name)
    if len(seen)!=1:raise ValueError('Expected one no-unroll compiler invocation')
    return result

def source_states(live):
    before_decl='s32 func_150229E4();';after_decl='s32 func_150229E4(struct127 *actor);'
    if live.count(STUB)==1 and live.count(before_decl)==1:
        return live,live.replace(STUB,SELECTED,1).replace(before_decl,after_decl,1),False
    if live.count(SELECTED)!=1 or live.count(after_decl)!=1:raise ValueError('Actor query source changed')
    return live.replace(SELECTED,STUB,1).replace(after_decl,before_decl,1),live,True

def caller_states(live):
    old='s32 func_150229E4(u8 *);';new='struct struct127;\ns32 func_150229E4(struct struct127 *);'
    call='func_150229E4((u8 *)D_800CC2D0 + (u32)slot * 0x32C)'
    typed='func_150229E4((struct struct127 *)((u8 *)D_800CC2D0 + (u32)slot * 0x32C))'
    if live.count(old)==1 and live.count(call)==1:return live,live.replace(old,new,1).replace(call,typed,1),False
    if live.count(new)!=1 or live.count(typed)!=1:raise ValueError('Actor query C caller changed')
    return live.replace(new,old,1).replace(typed,call,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);a=struct.unpack('>73I',raw);b=struct.unpack('>73I',normal)
    spec=lambda rows:';'.join(k+':'+n for k,n in rows)or'-'
    rows=[[OWNER,FUNCTION,hex(i*4),f'0x{x:08X}',f'0x{y:08X}',spec(refs.get(i*4,[])),spec(nrefs.get(i*4,[])),
           'Normalize query address rematerialization and closed register lifetimes','','','false']for i,(x,y)in enumerate(zip(a,b))if x!=y or refs.get(i*4)!=nrefs.get(i*4)]
    if len(rows)!=55:raise ValueError('Actor query guard derivation changed')
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited guard history changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs))
    return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze committed query predecessor first')
        names=[SOURCE,OBJECT,CALLER_SOURCE,CALLER_OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld',
          'conker/retail_layout.us.txt','conker/conker.us.bin','conker/progress.csv','conker/asm/49D30.s','conker/asm/58F80.s',
          'conker/src/game/generated_A9260.c','conker/src/game_77AD0.c','conker/src/game_83300.c',
          'conker/symbol_addrs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs.us.txt','conker/undefined_syms_auto.txt','conker/undefined_funcs_auto.txt']
        for source in(SOURCE,CALLER_SOURCE):names+=['conker/'+p for p in __import__('re').findall(r'#pragma GLOBAL_ASM\("([^"]+)"\)',(root/source).read_text())]
        names+=['conker/include/asm_processor_prelude.inc','conker/include/macro.inc']
        names+=[p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        names+=['ido/ido5.3_recomp/'+n for n in('cc','cfe','uopt','ugen')];names=list(dict.fromkeys(names))
        for n in names:
            p=folder/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        receipt.write_text(json.dumps({n:sha((folder/n).read_bytes())for n in names},indent=2)+'\n')
    hashes=json.loads(receipt.read_text());allowed={SOURCE,OBJECT,CALLER_SOURCE,CALLER_OBJECT,ELF,GUARDS}
    for n,h in hashes.items():
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Query input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=292:raise ValueError('Query predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,292);wanted[at:at+292]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Query predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,292)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal query entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Query owner pools changed')
    if sections(a).get('.reginfo')!=sections(b).get('.reginfo'):raise ValueError('Query owner register metadata changed')

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text());cb,ca,ci=caller_states((root/CALLER_SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text()or cb!=(out/'frozen'/CALLER_SOURCE).read_text()or ci!=installed:raise ValueError('Query predecessor sources changed')
    old,od=compile_owner(root,out,before,'predecessor-owner');new,nd=compile_owner(root,out,after,'qualified-owner')
    cold,cd=base_compile_owner(root,out,cb,'predecessor-caller');cnew,cnd=base_compile_owner(root,out,ca,'qualified-caller')
    if diagnostic_rows(od)!=diagnostic_rows(nd)or nd or diagnostic_rows(cd)!=diagnostic_rows(cnd):raise ValueError('Query owner/caller diagnostics changed')
    neighbors=same_functions(old,new,(FUNCTION,));caller_functions=same_functions(cold,cnew);owner_pools(old,new);owner_pools(cold,cnew)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+292]
    syms={n:int(n.split('_')[1],16)for rows in nrefs.values()for _,n in rows}
    if struct.pack('>73I',*bound_blob(normal,nrefs,syms))!=truth:raise ValueError('Query normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes());guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Query live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=len(parse_object(new)[1])or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Query strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Query padded body/pools changed')
    caller_pad=caller_padded(root,out,cnew,old_guards,'qualified-caller-padded');old_caller_pad=caller_padded(root,out,cold,old_guards,'predecessor-caller-padded')
    if caller_pad.read_bytes()!=old_caller_pad.read_bytes():raise ValueError('Query caller padded object changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes()or(root/CALLER_OBJECT).read_bytes()!=caller_pad.read_bytes():raise ValueError('Query live owners differ')
    proposal=out/'proposed-owner.c';proposal.write_text(after);cp=out/'proposed-caller.c';cp.write_text(ca)
    make=make_shadow(root,out,proposal,guards,new_pad,new);cmake=make_caller_shadow(root,out,cp,old_guards,caller_pad,cnew)
    old_image,new_image=link(root,out,old_pad,'predecessor-image',caller_pad),link(root,out,new_pad,'qualified-image',caller_pad)
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Query live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Query linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Query protected data changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=73,raw_words=73,frame=0,guards=55,raw_neighbors=neighbors,padded_neighbors=padded_neighbors,
      caller_functions=caller_functions,caller_object_fixed=True,diagnostics=0,caller_diagnostics=sum(diagnostic_rows(cnd).values()),actual_Make=make,caller_actual_Make=cmake,
      strict_changed_bytes=changed,exclusions=0,functions=len(a),all_addresses_fixed=True,changed_bodies=[FUNCTION],protected_data=data,
      owner_sha256=sha(new_pad.read_bytes()),caller_sha256=sha(caller_pad.read_bytes()),ELF_sha256=sha(new_image.read_bytes()),guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,normal=normal,normal_refs=nrefs,predecessor_elf=old_image,qualified_elf=new_image,qualified_object=new_pad)

def normalize(raw,refs):
    if len(raw)!=292 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Unknown query C words')
    w=list(struct.unpack('>73I',raw))
    order=list(range(5))+[5,7,11,9,10,8,12,13,14,15,16,17,18,19,20,6,22]+list(range(23,41))+[42,41,43,44,45,46,21]+list(range(47,73))
    assert sorted(order)==list(range(73));inverse={v:i for i,v in enumerate(order)}
    mapping={3:5,5:6,6:7,7:8,8:3,9:10,10:9}
    tail={**mapping,12:11,13:12,14:13,15:14,24:15,25:24}
    def rename(x,mp):
        op=x>>26;shifts=(21,16,11)if op==0 else(16,)if op==15 else(21,16)
        result=x
        for bit in shifts:result=(result&~(31<<bit))|(mp.get((x>>bit)&31,(x>>bit)&31)<<bit)
        return result
    result=[];relocs={}
    for j,i in enumerate(order):
        x=w[i];r=refs.get(i*4,[])
        if i==5:x=rename(x,{9:15})
        elif i==6:x=rename(w[5],{9:8});r=[('R_MIPS_HI16','D_800C35C8')]
        elif i==7:x=(x&0x03FFFFFF)|(5<<26)
        elif i==8:x=rename(x,{9:15});r=[('R_MIPS_LO16','D_800C35C8')]
        elif i==11:x=0;r=[]
        elif i>=12:
            mp=tail if i>=47 else {**mapping,9:8,11:8}if i in(41,45)else mapping
            x=rename(x,mp)
            if i==45:r=[('R_MIPS_LO16','D_800C35C8')]
        op=x>>26
        if op in(1,4,5,6,7,20,21,22,23):
            target=i+1+((w[i]&65535)^32768)-32768
            dest=10 if i==7 else inverse[target]
            x=(x&0xFFFF0000)|((dest-j-1)&65535)
        result.append(x)
        if r:relocs[j*4]=r
    return struct.pack('>73I',*result),relocs

def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/49D30.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def caller_padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', 'generated_58F80', word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/58F80.s', word_patches_path=guards, filename='generated_58F80', rodata_symbol='jtbl_80096DF8_game')
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    source_path = SOURCE
    conker = root/'conker'
    target = shadow/'src/game/generated_49D30.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor-query Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor-query Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        allowed_diagnostics = Counter()
        if result.returncode or diagnostic_rows(result.stderr) != allowed_diagnostics or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 3 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a and '-Wo,-loopunroll,0' in a]) != 1:
        raise ValueError('Query actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Actor-query actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

def make_caller_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'caller-make-shadow'
    source_path = CALLER_SOURCE
    conker = root/'conker'
    target = shadow/'src/game/generated_58F80.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'caller-actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor-query Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor-query Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        allowed_diagnostics = Counter()
        if result.returncode or diagnostic_rows(result.stderr) != allowed_diagnostics or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 5 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Actor-query actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Actor-query actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'caller-actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

def link(root, out, owner, label, caller):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Actor-query linker owner changed')
    p = out/(label+'.ld')
    caller_name=CALLER_OBJECT.removeprefix('conker/')
    if script.count(caller_name)!=1:raise ValueError('Query caller link owner changed')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()).replace(caller_name,caller.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
