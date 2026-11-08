"""Record-dispatch callback direct C and complete owner/image qualification."""
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
BUILD='conker/build/game-record-dispatch-150A03B0-match'
SOURCE='conker/src/game/generated_CD860.c'
OBJECT='conker/build/src/game/generated_CD860.c.o'
OWNER,FUNCTION='generated_CD860','func_150A03B0'
ENTRY,ROM,WORDS,FRAME=0x150A03B0,0xCD860,74,40
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='6fdb290ac4d80a5872aeb222a1729b5f240a09adafdbabf16daaa403fd217509'
GUARD_SHA='944ed3d5d42a8d537e8730f76afa3da81d6806a5e8fd46391a3edd7cdb747f9b'
BINDINGS={36: [('R_MIPS_HI16', '.rodata')], 44: [('R_MIPS_LO16', '.rodata')], 60: [('R_MIPS_26', 'func_150A2864')], 80: [('R_MIPS_26', 'func_150A2864')], 104: [('R_MIPS_26', 'func_150A2940')], 132: [('R_MIPS_26', 'func_150A3444')], 176: [('R_MIPS_26', 'func_150A3398')], 248: [('R_MIPS_HI16', 'D_800D3098')], 252: [('R_MIPS_LO16', 'D_800D3098')], 264: [('R_MIPS_26', 'func_151C970C')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='s32 func_150A03B0() {\n    return 0;\n}'
SELECTED="typedef struct { u8 bytes[0x34]; } DispatchRecord150A03B0;\nextern DispatchRecord150A03B0 *D_800D3098;\nvoid func_150A2864(u32, s32);\nvoid func_150A2940(u32, s32, s32);\nvoid func_150A3444(s32, s16, s16, s16);\nvoid func_150A3398(s32, u16, s32, s32, s32, s32);\nvoid func_151C970C(s32, s32);\n/* Dispatch the record's command while preserving each command's field widths. */\ns32 func_150A03B0(u32 identity, u32 command, u32 *record) {\n    switch (command) {\n        case 0:\n            func_150A2864(identity, 0);\n            return 1;\n        case 1:\n            func_150A2864(identity, 1);\n            return 1;\n        case 2:\n            func_150A2940(identity, record[2], record[3]);\n            return 1;\n        case 3:\n            func_150A3444(identity, (s16)record[2], (s16)record[3], (s16)record[4]);\n            break;\n        case 4:\n            func_150A3398(identity, (u16)record[2], record[3], record[4], record[5], record[6]);\n            break;\n        case 5:\n            func_151C970C(record[2] == 999 ? 2 : (record[2] != 0 ? 0 : 1),\n                          (s32)&D_800D3098[identity]);\n            break;\n    }\n    return 0;\n}"
RAW_SHA='8f47f8c5bcb19ec50feadac837b441f77cf60fcca1634c36b6f503cfcbfa1727'
MAKE='conker/Makefile'
MAKE_ROW='$(BUILD_DIR)/$(SRC_DIR)/game/generated_CD860.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009F550\n'



def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Record dispatcher source changed')
    return live.replace(SELECTED,STUB,1),live,True

def make_states(live):
    if MAKE_ROW not in live:return live,live+MAKE_ROW,False
    if live.count(MAKE_ROW)!=1 or not live.endswith(MAKE_ROW):raise ValueError('Record dispatcher Make row changed')
    return live[:-len(MAKE_ROW)],live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def normalize(raw,refs):
    if len(raw)!=296 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Record-dispatch direct C words/bindings changed')
    return raw,{at:[(k,'jtbl_8009F550'if n=='.rodata'else n)for k,n in rows]for at,rows in refs.items()}

def guard_rows(raw,refs):
    normalize(raw,refs);return []

def guard_manifest(before,raw,refs):
    normalize(raw,refs)
    if sha(before)!=GUARD_SHA:raise ValueError('Inherited guard history changed')
    return before

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed record-dispatch predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/CD860.s','conker/asm/DAFA0.s','conker/asm/data/22BEF0.rodata.s','conker/asm/data/243F60.rodata.s','conker/src/game/generated_CDE80.c','conker/src/game/generated_1F4650.c',
          'conker/include/asm_processor_prelude.inc','conker/include/macro.inc',
          'conker/symbol_addrs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs.us.txt',
          'conker/undefined_syms_auto.txt','conker/undefined_funcs_auto.txt']
        names+=['conker/'+p for p in __import__('re').findall(r'#pragma GLOBAL_ASM\("([^\"]+)"\)',(root/SOURCE).read_text())]
        names += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in('cc','cfe','uopt','ugen')]
        for name in names:
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n:sha((folder/n).read_bytes())for n in names},indent=2)+'\n')
    hashes=json.loads(receipt.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,MAKE}
    for n,h in hashes.items():
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Record-dispatch input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=296:raise ValueError('Record-dispatch predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,296);wanted[at:at+296]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Record-dispatch predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,296)
    # The new early reference moves this pre-existing named-definition group.
    group=[r for r in symbol_rows(before)if 0x2B4964<=r[0]<0x2B4994]
    names=('jtbl_8009F550','func_15178750','func_15149838');order=(1,2,0)
    if tuple(r[1]for r in group)!=names:raise ValueError('Record dispatcher metadata group changed')
    start=group[0][3];name_index=group[0][2][0];strings=b''.join(n.encode()+b'\0'for n in names)
    if before[start:start+len(strings)]!=strings or any(r[2][0]!=name_index+14*i for i,r in enumerate(group)):raise ValueError('Record dispatcher name block changed')
    if [r[0]for r in symbol_rows(before)if name_index<=r[2][0]<name_index+42]!=[r[0]for r in group]:raise ValueError('Record dispatcher shared name reference changed')
    for slot,index in enumerate(order):
        row=group[index];struct.pack_into('>IIIBBH',wanted,group[slot][0],name_index+14*slot,*row[2][1:]);wanted[start+14*slot:start+14*(slot+1)]=row[1].encode()+b'\0'
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal record-dispatch entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    old,new=normalized_pools(a),normalized_pools(b)
    expected={'.rodata':(bytes(32),tuple((i*4,FUNCTION,v)for i,v in enumerate((56,76,96,120,148,192)))),'.data':None}
    if old!={'.rodata':None,'.data':None}or new!=expected:raise ValueError('Record dispatcher generated table changed')
    prior,actual,alone=(sections(p)['.reginfo']for p in(a,b,isolated))
    before,result,single=(struct.unpack('>6I',v[1])for v in(prior,actual,alone))
    if before!=(0x80000004,0,0,0,0,0x7FF0)or single!=(0xA303C1F6,0,0,0,0,0x7FF0)or result!=single or tuple(before[i]|single[i]if i<5 else before[i]for i in range(6))!=result:raise ValueError('Record dispatcher register union changed')
    return dict(generated_table_targets=[56,76,96,120,148,192],generated_table_bytes=32,isolated_register_union=True)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Record-dispatch predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Record-dispatch owner diagnostics changed')
    isolated,diag=compile_owner(root,out,'#include <ultra64.h>\n'+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Record dispatcher isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+296]
    if struct.pack('>74I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in nrefs.values()for _,name in rows}))!=truth:raise ValueError('Record-dispatch normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Record-dispatch live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=2 or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Record-dispatch strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Record-dispatch padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Record-dispatch live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);old_make,new_make,make_installed=make_states((root/MAKE).read_text())
    if old_make!=(out/'frozen'/MAKE).read_text()or make_installed!=installed:raise ValueError('Record dispatcher Make scope changed')
    proposed_make=out/'proposed-Makefile';proposed_make.write_text(new_make)
    make=make_shadow(root,out,proposal,guards,new_pad,new,proposed_make)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Record-dispatch live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record-dispatch linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record-dispatch protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/CD860.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Record-dispatch case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=74,raw_words=74,frame=40,guards=0,direct_C=True,metadata=metadata,
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
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards,rodata_symbol="jtbl_8009F550")
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/CD860.s', word_patches_path=guards, filename=OWNER,rodata_symbol="jtbl_8009F550")
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Record-dispatch linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination

def make_shadow(root, out, proposal, guards, wanted, compact,makefile):
    shadow = out/'make-shadow'
    source_path = SOURCE
    conker = root/'conker'
    target = shadow/'src/game/generated_CD860.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-f', str(makefile), '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected record-dispatch Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record-dispatch Make redirect')
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
    if len(commands) != 3 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Record-dispatch actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Record-dispatch actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
