"""Parameter-defaults direct C and complete owner/image qualification."""
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
BUILD='conker/build/game-parameter-defaults-151872B0-match'
SOURCE='conker/src/game/generated_1B1600.c'
OBJECT='conker/build/src/game/generated_1B1600.c.o'
OWNER,FUNCTION='generated_1B1600','func_151872B0'
ENTRY,ROM,WORDS,FRAME=0x151872B0,0x1B4760,77,0
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='ad4ca11544662ecbafe0e09850fdfab2fc3f46d0a116d1d3eaa856695c328963'
GUARD_SHA='f67f8d18908dc6db9ba58dfa2db4b4204a7202104e67173c35213711333f4dd9'
BINDINGS={0: [('R_MIPS_HI16', 'D_800DE01C')], 60: [('R_MIPS_LO16', 'D_800DE01C')], 4: [('R_MIPS_HI16', 'D_800DE020')], 56: [('R_MIPS_LO16', 'D_800DE020')], 8: [('R_MIPS_HI16', 'D_800DE024')], 52: [('R_MIPS_LO16', 'D_800DE024')], 12: [('R_MIPS_HI16', 'D_800DE038')], 48: [('R_MIPS_LO16', 'D_800DE038')], 16: [('R_MIPS_HI16', 'D_800DE040')], 44: [('R_MIPS_LO16', 'D_800DE040')], 20: [('R_MIPS_HI16', 'D_800DE030')], 40: [('R_MIPS_LO16', 'D_800DE030')], 24: [('R_MIPS_HI16', 'D_800DE034')], 36: [('R_MIPS_LO16', 'D_800DE034')], 28: [('R_MIPS_HI16', 'D_800DE041')], 32: [('R_MIPS_LO16', 'D_800DE041')], 120: [('R_MIPS_HI16', 'D_800DE03C')], 124: [('R_MIPS_LO16', 'D_800DE03C')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='s32 func_151872B0() {\n    return 0;\n}'
SELECTED="extern s32 D_800DE01C,D_800DE020,D_800DE024,D_800DE030,D_800DE034,D_800DE038;\nextern f32 D_800DE03C;\nextern u8 D_800DE040,D_800DE041;\n/* Set parameter defaults before applying the selected variant's overrides. */\nvoid func_151872B0(s32 variant) {\n    D_800DE01C = 600;\n    D_800DE020 = 180;\n    D_800DE024 = 90;\n    D_800DE030 = 1016;\n    D_800DE034 = 0;\n    D_800DE038 = 1;\n    D_800DE03C = 1.0f;\n    D_800DE040 = 1;\n    D_800DE041 = 1;\n    switch (variant) {\n        case 0x21:\n            D_800DE01C = 4800;\n            D_800DE020 = D_800DE01C - 1;\n            D_800DE024 = D_800DE01C - 2;\n            D_800DE030 = 1010;\n            D_800DE034 = 1;\n            D_800DE038 = 4;\n            D_800DE040 = 0;\n            break;\n        case 0x22:\n            D_800DE01C = 2400;\n            D_800DE020 = D_800DE01C - 1;\n            D_800DE024 = D_800DE01C - 2;\n            D_800DE038 = 4;\n            D_800DE040 = 0;\n            break;\n        case 0x14:\n            D_800DE041 = 0;\n            break;\n        case 0x29:\n            D_800DE01C = 1200;\n            D_800DE020 = 600;\n            D_800DE024 = 300;\n            break;\n    }\n}"
RAW_SHA='e0f4d4acd39253d1b990ef962522984888889bc2e5835d628919cfc186be5300'


def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Parameter defaults source changed')
    return live.replace(SELECTED,STUB,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def normalize(raw,refs):
    if len(raw)!=308 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Parameter-defaults direct C words/bindings changed')
    return raw,refs

def guard_rows(raw,refs):
    normalize(raw,refs);return []

def guard_manifest(before,raw,refs):
    normalize(raw,refs)
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited parameter-defaults guard history changed')
    return before

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed parameter-defaults predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/1B1600.s',
          'conker/asm/nonmatchings/game_3B920/func_1500E470.s','conker/src/game_3B920.c',
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
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Parameter-defaults input changed: '+n)
    return hashes

METADATA_GROUPS=((('D_800DE01C','D_800C3674'),(1,0)),
    (('D_800DE030','func_15095A90'),(1,0)),
    (('D_800DE034','D_80089570','D_80089120'),(1,2,0)),
    (('D_800DE03C','D_8008A284'),(1,0)))

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=308:raise ValueError('Parameter-defaults predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,308);wanted[at:at+308]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Parameter-defaults predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,308)
    # New external references change four GNU ld hash-bucket orders. Derive
    # exactly these nine unchanged named definitions and their contiguous
    # string blocks from the frozen predecessor; no metadata is excluded.
    all_rows=symbol_rows(before)
    for names,order in METADATA_GROUPS:
        group=sorted((r for r in all_rows if r[1]in names),key=lambda r:r[0])
        if tuple(r[1]for r in group)!=names or any(r[0]!=group[0][0]+16*i for i,r in enumerate(group)):
            raise ValueError('Parameter-defaults metadata group changed')
        start=group[0][3];base=group[0][2][0];strings=b''.join(n.encode()+b'\0'for n in names);delta=0
        if before[start:start+len(strings)]!=strings:raise ValueError('Parameter-defaults metadata strings changed')
        for row,name in zip(group,names):
            if row[2][0]!=base+delta or row[3]!=start+delta:raise ValueError('Parameter-defaults metadata offsets changed')
            delta+=len(name)+1
        if {r[0]for r in all_rows if base<=r[2][0]<base+len(strings)}!={r[0]for r in group}:
            raise ValueError('Parameter-defaults shared metadata reference changed')
        delta=0
        for slot,index in enumerate(order):
            row=group[index];name=row[1].encode()+b'\0';struct.pack_into('>IIIBBH',wanted,group[slot][0],base+delta,*row[2][1:]);wanted[start+delta:start+delta+len(name)]=name;delta+=len(name)
        if delta!=len(strings):raise ValueError('Parameter-defaults metadata byte accounting changed')
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal parameter-defaults entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Parameter defaults owner pools changed')
    old,new,single=(sections(p)['.reginfo']for p in(a,b,isolated))
    before,result,alone=(struct.unpack('>6I',v[1])for v in(old,new,single))
    if (before,alone)!=REGISTER_INPUTS or result!=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6)):raise ValueError('Parameter defaults register union changed')
    return dict(before=list(before),isolated=list(alone),exact_register_union=True)
REGISTER_INPUTS=((2743074814, 0, 1040375, 0, 0, 32752), (2197880830, 0, 16, 0, 0, 32752))
OWNER_FUNCTIONS=32

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Parameter-defaults predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Parameter-defaults owner diagnostics changed')
    isolated,diag=compile_owner(root,out,'#include <ultra64.h>\n'+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Parameter defaults isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+308]
    if struct.pack('>77I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}))!=truth:raise ValueError('Parameter-defaults normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Parameter-defaults live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=OWNER_FUNCTIONS or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Parameter-defaults strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Parameter-defaults padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Parameter-defaults live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Parameter-defaults live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Parameter-defaults linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Parameter-defaults protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/1B1600.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Parameter-defaults case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=77,raw_words=77,frame=0,guards=0,direct_C=True,register_metadata=metadata,
      preserved_labels=len(labels),raw_neighbors=neighbors,padded_neighbors=padded_neighbors,diagnostics=0,
      named_metadata_groups=len(METADATA_GROUPS),named_metadata_rows=sum(len(names)for names,_ in METADATA_GROUPS),
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
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/1B1600.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    staged=out/(label+'-objects')/Path(OBJECT).name
    staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(owner.read_bytes());owner=staged
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Parameter-defaults linker owner changed')
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
    target = shadow/'src/game/generated_1B1600.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected parameter-defaults Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown parameter-defaults Make redirect')
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
        raise ValueError('Parameter-defaults actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Parameter-defaults actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
