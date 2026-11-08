"""Record-relocation semantic C and complete owner/image qualification."""
import csv,hashlib,io,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments.game_actor_list_query_150229e4_match import compile_owner
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
BUILD='conker/build/game-record-relocation-1509CF28-match'
SOURCE='conker/src/game/generated_C9EC0.c'
OBJECT='conker/build/src/game/generated_C9EC0.c.o'
OWNER,FUNCTION='generated_C9EC0','func_1509CF28'
ENTRY,ROM,WORDS,FRAME=0x1509CF28,0xCA3D8,75,80
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='893d4b26ca5699639ac50e69c09aa49fc5e7b3e9893a09cffcc658a750593cfc'
GUARD_SHA='944ed3d5d42a8d537e8730f76afa3da81d6806a5e8fd46391a3edd7cdb747f9b'
BINDINGS={52: [('R_MIPS_26', 'func_1502B6BC')], 60: [('R_MIPS_HI16', 'D_800D2FB0')], 64: [('R_MIPS_LO16', 'D_800D2FB0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='s32 func_1509CF28() {\n    return 0;\n}'
SELECTED='void *func_1502B6BC(s32 *, s32, s32 *, s32, ...);\n/* Relocate every list, including its final flagged pair, and publish the last index.\n * Inner bases remain live through the global; the outer cursor keeps the load result. */\ns32 func_1509CF28(s32 resource, u32 *lastIndex) {\n    u32 index;\n    u32 offset;\n    u8 *cursor;\n    u32 count;\n    u8 *loaded;\n    u32 *pair;\n    u32 *record;\n    s32 finished;\n\n    count = 0;\n    D_800D2FB0 = func_1502B6BC(NULL, 0, (s32 *)&count, 3, 8, 0, resource);\n    loaded = D_800D2FB0;\n    if (loaded == NULL) {\n        *lastIndex = 0;\n        return 0;\n    }\n    *(u32 *)(loaded + 4) = count - 1;\n    *lastIndex = count - 1;\n    cursor = loaded;\n    index = 1;\n    offset = 8;\n    if (count >= 2) {\n        do {\n            finished = 0;\n            pair = (u32 *)*(u32 *)(D_800D2FB0 + offset);\n            do {\n                pair[0] += *(u32 *)(D_800D2FB0 + offset);\n                if (pair[1] & 0x80000000U) finished = 1;\n                pair[1] &= 0x0FFFFFFF;\n                pair += 2;\n            } while (finished == 0);\n            record = (u32 *)*(u32 *)(cursor + 8);\n            record[3] = (record[3] & 0x0FFFFFFF) >> 1;\n            cursor += 8;\n            offset += 8;\n            index++;\n        } while (index < count);\n    }\n    return 1;\n}'
RAW_SHA='1e78fe7e7ee0d6f90b1b735a5d435aa359322affe3d69487749b522d403eb335'


def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Record relocation source changed')
    return live.replace(SELECTED,STUB,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def normalize(raw,refs):
    if len(raw)!=300 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Record relocation compiler words/bindings changed')
    w=list(struct.unpack('>75I',raw));order=list(range(75));order[26],order[35]=35,26;order[60],order[62]=62,60
    mapping={8:6,5:7,10:9,7:5,6:8,9:10};result=[]
    # All mapped temporaries start after the sole helper call. Swap only an
    # independent ORI/cursor move and the two independent cursor increments.
    for i in order:
        x=w[i];op=x>>26;fields=(21,16,11)if op==0 else()if op in(2,3)else(16,)if op==15 else(21,16)
        if i>=15:
            for bit in fields:x=(x&~(31<<bit))|(mapping.get(w[i]>>bit&31,w[i]>>bit&31)<<bit)
        result.append(x)
    return struct.pack('>75I',*result),dict(refs)

def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
    rows=[[OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(refs.get(i*4,[])),spec(nrefs.get(i*4,[])),
      'Normalize closed relocation-loop register lifetimes and independent setup/cursor scheduling','','','false']for i,(a,b)in enumerate(zip(struct.unpack('>75I',raw),struct.unpack('>75I',normal)))if a!=b or refs.get(i*4)!=nrefs.get(i*4)]
    if len(rows)!=22:raise ValueError('Record relocation guard derivation changed')
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited relocation guards changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs));return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed record-relocation predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/C9EC0.s','conker/asm/20AE20.s','conker/src/game_57FA0.c','conker/src/game/generated_20AE20.c','conker/asm/nonmatchings/game_57FA0/func_1502B6BC.s',
          'conker/include/asm_processor_prelude.inc','conker/include/macro.inc',
          'conker/symbol_addrs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs.us.txt',
          'conker/undefined_syms_auto.txt','conker/undefined_funcs_auto.txt']
        names+=['conker/'+p for p in __import__('re').findall(r'#pragma GLOBAL_ASM\("([^\"]+)"\)',(root/SOURCE).read_text())]
        names += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in('cc','cfe','uopt','ugen')]
        for name in names:
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n:sha((folder/n).read_bytes())for n in names},indent=2)+'\n')
    hashes=json.loads(receipt.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS}
    for n,h in hashes.items():
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Record-relocation input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=300:raise ValueError('Record-relocation predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,300);wanted[at:at+300]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record-relocation predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,300)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal record-relocation entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Record relocation owner pools changed')
    old,new,single=(sections(p)['.reginfo']for p in(a,b,isolated))
    before,result,alone=(struct.unpack('>6I',v[1])for v in(old,new,single))
    if (before,alone)!=REGISTER_INPUTS or result!=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6)):raise ValueError('Record relocation register union changed')
    return dict(before=list(before),isolated=list(alone),exact_register_union=True)
REGISTER_INPUTS=((2743074814, 0, 0, 0, 0, 32752), (2734751742, 0, 0, 0, 0, 32752))

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Record-relocation predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Record-relocation owner diagnostics changed')
    isolated,diag=compile_owner(root,out,'#include <ultra64.h>\nextern u8 *D_800D2FB0;\n'+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Record relocation isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+300]
    if struct.pack('>75I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}))!=truth:raise ValueError('Record-relocation normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Record-relocation live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=19 or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Record-relocation strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Record-relocation padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Record-relocation live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Record-relocation live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record-relocation linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record-relocation protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/C9EC0.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Record-relocation case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=75,raw_words=75,frame=80,guards=22,direct_C=False,register_metadata=metadata,
      preserved_labels=len(labels),raw_neighbors=neighbors,padded_neighbors=padded_neighbors,diagnostics=0,
      actual_Make=make,strict_changed_bytes=changed,exclusions=0,functions=len(a),all_addresses_fixed=True,
      changed_bodies=[FUNCTION],protected_data=data,owner_sha256=sha(new_pad.read_bytes()),ELF_sha256=sha(new_image.read_bytes()),guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,normal=normal,normal_refs=nrefs,predecessor_elf=old_image,qualified_elf=new_image,qualified_object=new_pad)

def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/C9EC0.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Record-relocation linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination

def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    source_path = SOURCE
    conker = root/'conker'
    target = shadow/'src/game/generated_C9EC0.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected record-relocation Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record-relocation Make redirect')
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
    if len(commands) != 3 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a and a.count('-Wo,-loopunroll,0')==1]) != 1:
        raise ValueError('Record-relocation actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Record-relocation actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
