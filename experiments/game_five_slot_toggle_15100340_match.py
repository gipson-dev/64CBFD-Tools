"""Five-slot callback direct C and complete owner/image qualification."""
import csv,hashlib,io,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
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
BUILD='conker/build/game-five-slot-toggle-15100340-match'
SOURCE='conker/src/game/generated_12D7F0.c'
OBJECT='conker/build/src/game/generated_12D7F0.c.o'
OWNER,FUNCTION='generated_12D7F0','func_15100340'
ENTRY,ROM,WORDS,FRAME=0x15100340,0x12D7F0,73,80
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='cf8350b1a35a1cca76de197c1f9047b89b0cb0f67e0c13b63be328abfd51a479'
GUARD_SHA='931b6ca3673b8157c374871d9065dffbf39d419211960ab9383c6503808f7f25'
BINDINGS={28: [('R_MIPS_HI16', 'D_80088BC0')], 32: [('R_MIPS_LO16', 'D_80088BC0')], 44: [('R_MIPS_HI16', 'D_800DD405')], 56: [('R_MIPS_LO16', 'D_800DD405')], 72: [('R_MIPS_HI16', 'D_800BE500')], 76: [('R_MIPS_LO16', 'D_800BE500')], 124: [('R_MIPS_26', 'func_150ADA20')], 200: [('R_MIPS_26', 'func_151616D0')], 224: [('R_MIPS_26', 'func_151616D0')], 240: [('R_MIPS_26', 'func_151616D0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='s32 func_15100340() {\n    return 0;\n}'
SELECTED='extern u8 D_800BE500[5], D_800DD405;\ns32 func_150ADA20(void);\nvoid func_151616D0(u8, u8, s32);\ntypedef struct SlotIdentifiers15100340 { u8 ids[5]; } SlotIdentifiers15100340;\nextern SlotIdentifiers15100340 D_80088BC0;\n/* Advance the five registered slot states for the primary view. */\nvoid func_15100340(s32 view) {\n    u32 random;\n    SlotIdentifiers15100340 identifiers;\n    s32 index;\n    u32 chance;\n    u8 *states;\n    identifiers = D_80088BC0;\n\n    if (view == 0) {\n        D_800DD405++;\n        states = D_800BE500;\n        index = 0;\n        do {\n            chance = *states != 0 ? 70 : 35;\n            random = (u32)func_150ADA20();\n            if (random % 1000 < chance) {\n                *states ^= 1;\n                if (*states != 0) func_151616D0(identifiers.ids[index], 0x18, 0);\n                else {\n                    func_151616D0(identifiers.ids[index], 0x1C, 0);\n                    func_151616D0(identifiers.ids[index], 0x17, 0);\n                }\n            }\n            index++;\n            states++;\n        } while (index != 5);\n    }\n}'
RAW_SHA='cb59d7df9047afeefab3430ba3ec5f7b8bcea748e38c8da9194fd73788644c9d'


def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1).replace('/* Non-matching placeholders for the text-only asm slice asm/12D7F0.s. */','/* Recovered C for asm/12D7F0.s; the remaining routine retains assembly. */',1),False
    if live.count(SELECTED)!=1:raise ValueError('Five-slot source changed')
    return live.replace(SELECTED,STUB,1).replace('/* Recovered C for asm/12D7F0.s; the remaining routine retains assembly. */','/* Non-matching placeholders for the text-only asm slice asm/12D7F0.s. */',1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def normalize(raw,refs):
    if len(raw)!=292 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Five-slot direct C words/bindings changed')
    return raw,dict(refs)

def guard_rows(raw,refs):
    normalize(raw,refs);return []

def guard_manifest(before,raw,refs):
    normalize(raw,refs)
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard history changed')
    return before

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed five-slot predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/12D7F0.s','conker/asm/1A1E50.s',
          'conker/asm/data/231730.rodata.s','conker/asm/data/22D680.rodata.s',
          'conker/src/game/generated_1A1E50.c','conker/src/game_DAE50.c','conker/src/game_18D770.c',
          'conker/asm/nonmatchings/game_DAE50/func_150ADA20.s',
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
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Five-slot input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=292:raise ValueError('Five-slot predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,292);wanted[at:at+292]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Five-slot predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,292)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal five-slot entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Five-slot owner pools changed')
    if sections(a).get('.reginfo')!=sections(b).get('.reginfo'):raise ValueError('Five-slot owner register metadata changed')

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Five-slot predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Five-slot owner diagnostics changed')
    neighbors=same_functions(old,new,(FUNCTION,));owner_pools(old,new)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+292]
    if struct.pack('>73I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}))!=truth:raise ValueError('Five-slot normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Five-slot live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=2 or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Five-slot strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Five-slot padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Five-slot live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Five-slot live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Five-slot linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Five-slot protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/12D7F0.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Five-slot case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=73,raw_words=73,frame=80,guards=0,direct_C=True,
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
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/12D7F0.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Five-slot linker owner changed')
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
    target = shadow/'src/game/generated_12D7F0.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected five-slot Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown five-slot Make redirect')
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
        raise ValueError('Five-slot actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Five-slot actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
