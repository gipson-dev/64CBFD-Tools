"""Curve progress semantic C, closed scheduling permutation and full-owner/image gates."""
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
BUILD='conker/build/game-curve-progress-151AE2BC-match'
SOURCE='conker/src/game/generated_1D92F0.c'
OBJECT='conker/build/src/game/generated_1D92F0.c.o'
OWNER,FUNCTION='generated_1D92F0','func_151AE2BC'
ENTRY,ROM,WORDS,FRAME=0x151AE2BC,0x1DB76C,59,0
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='dcb555ac9ca55bad1eb96fa40b6aef6b6b8fd58b693a452a86050b0f56fcad28'
GUARD_SHA='06cc6c67e6b7af7ab0e60ecad7733faef8aefdc26aee4eb326c1a391b5d386c3'
BINDINGS={}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='s32 func_151AE2BC() {\n    return 0;\n}'
SELECTED='typedef struct {\n    u8 reserved00[4];\n    f32 value;\n    u8 reserved08[0x10];\n} CurveKnot1D92F0;\ntypedef struct {\n    u8 reserved00[0x38];\n    CurveKnot1D92F0 *knots;\n    u8 reserved3C[6];\n    u8 count;\n} CurveProgress1D92F0;\n\n/* Locate the height segment and publish its normalized curve progress. */\nvoid func_151AE2BC(f32 *output, CurveProgress1D92F0 *curve,\n                  f32 x, f32 height, f32 z) {\n    s32 count = curve->count;\n    s32 index = 0;\n    CurveKnot1D92F0 *knot;\n    f32 fraction;\n\n    if ((count - 1) > 0) {\n        knot = curve->knots;\n        do {\n            if (height <= knot->value) break;\n            index++;\n            knot++;\n        } while (index < (count - 1));\n    }\n    if (index >= count - 2) {\n        *output = 1.0f;\n        return;\n    }\n    if (index == 0) {\n        *output = 0.0f;\n        return;\n    }\n    knot = &curve->knots[index];\n    fraction = knot->value - knot[-1].value;\n    if (fraction != 0.0f) fraction = (height - knot[-1].value) / fraction;\n    else fraction = 0.0f;\n    *output = (f32)(index - 1) / (f32)(count - 3) + fraction / (f32)(count - 1);\n}'
RAW_SHA='330fd2dfd39cea3a99cd893965421887d0f72b23a97335ccd90997b7cafe4c83'


def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Curve progress source changed')
    return live.replace(SELECTED,STUB,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def normalize(raw,refs):
    if len(raw)!=236 or sha(raw)!=RAW_SHA or refs:raise ValueError('Curve C words/bindings changed')
    words=list(struct.unpack('>59I',raw))
    # Closed permutation of compiler-emitted instructions. It moves the common
    # zero and independent index/count conversions into retail's live ranges,
    # and delays the independent index ratio until after the fraction branch.
    # No new operation, register role, literal, memory access or binding is added.
    order=list(range(29))+[40,35,29,30,31,32,33,34,36,38,37,39,41,43,52,45,46,47,48,49,50,51,42,53,44,54,55,56,57,58]
    if sorted(order)!=list(range(59)):raise ValueError('Curve schedule is not a closed permutation')
    inverse={old:new for new,old in enumerate(order)};result=[]
    for j,i in enumerate(order):
        w=words[i];op=w>>26
        if op in(1,4,5,6,7,20,21,22,23)or op==17 and(w>>21&31)==8:
            target=i+1+((w&65535)^32768)-32768
            if target not in inverse:raise ValueError('Curve branch left the function')
            # The interior block now begins with the moved zero/index setup,
            # two words before its old table load. Preserve the block edge.
            destination=29 if target==29 else inverse[target]
            w=(w&0xFFFF0000)|((destination-j-1)&65535)
        result.append(w)
    normal=struct.pack('>59I',*result)
    if sha(normal)!='92605b2d63cb44c6ebeb2b311cf4b4f48c2d6aff3e69e3a6d6620b88bdd36ec3':raise ValueError('Curve closed schedule differs')
    return normal,{}

def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);a=struct.unpack('>59I',raw);b=struct.unpack('>59I',normal)
    rows=[[OWNER,FUNCTION,hex(i*4),f'0x{x:08X}',f'0x{y:08X}','-','-',
           'Normalize closed curve scalar live ranges and independent interpolation scheduling','','','false']for i,(x,y)in enumerate(zip(a,b))if x!=y]
    if len(rows)!=23 or nrefs!=refs:raise ValueError('Curve progress guard derivation changed')
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited guard history changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs))
    return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed curve predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
               'conker/conker.us.bin','conker/progress.csv','conker/asm/1D92F0.s','conker/symbol_addrs.us.txt','conker/undefined_syms.us.txt',
               'conker/undefined_funcs.us.txt','conker/undefined_syms_auto.txt','conker/undefined_funcs_auto.txt']
        names += ['conker/'+p for p in __import__('re').findall(r'#pragma GLOBAL_ASM\("([^"]+)"\)',(root/SOURCE).read_text())]
        names += ['conker/include/asm_processor_prelude.inc','conker/include/macro.inc']
        names = list(dict.fromkeys(names))
        names += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in('cc','cfe','uopt','ugen')]
        for name in names:
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n:sha((folder/n).read_bytes())for n in names},indent=2)+'\n')
    hashes=json.loads(receipt.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS}
    for n,h in hashes.items():
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Curve progress input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=236:raise ValueError('Curve predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,236);wanted[at:at+236]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Curve predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,236)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal curve entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Curve owner pools changed')
    old,new,single=(sections(p).get('.reginfo')for p in(a,b,isolated))
    if any(v is None or len(v[1])!=24 for v in(old,new,single))or old[0]!=new[0]or old[0]!=single[0]:raise ValueError('Curve register metadata shape changed')
    before,actual,alone=(struct.unpack('>6I',v[1])for v in(old,new,single))
    if before!=(0xA31FFFFE,0,0x3F5D77,0,0,0x7FF0)or alone!=(0xA300C1FE,0,0xF5FF7,0,0,0x7FF0):raise ValueError('Curve predecessor/isolated register declaration changed')
    expected=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6))
    if actual!=expected:raise ValueError('Curve register metadata exceeds the exact isolated-body union')
    return dict(CPR1_added_bits='0x00000280',isolated_target_words_equal=True,exact_register_mask_union=True)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Curve predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Curve owner diagnostics changed')
    isolated,isolated_diag=compile_owner(root,out,'#include <ultra64.h>\n'+SELECTED,'qualified-isolated')
    if isolated_diag or function_blob(isolated)!=function_blob(new):raise ValueError('Curve isolated compiler body differs')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+236]
    if struct.pack('>59I',*bound_blob(normal,nrefs,{}))!=truth:raise ValueError('Curve normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Curve live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=len(parse_object(new)[1]) or normalized_pools(new_pad)!=normalized_pools(strict)or sections(new_pad).get('.reginfo')!=sections(strict).get('.reginfo'):raise ValueError('Curve strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Curve padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Curve live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Curve live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Curve linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Curve protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/1D92F0.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Curve case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=59,raw_words=59,frame=0,guards=23,
      preserved_labels=len(labels),raw_neighbors=neighbors,padded_neighbors=padded_neighbors,diagnostics=0,register_metadata=metadata,
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
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/1D92F0.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Curve-progress linker owner changed')
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
    target = shadow/'src/game/generated_1D92F0.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected record-state Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record-state Make redirect')
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
        raise ValueError('Curve-progress actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Curve-progress actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
