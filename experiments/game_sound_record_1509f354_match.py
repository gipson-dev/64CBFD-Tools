"""Sound-mask callback direct C and complete owner/image qualification."""
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
BUILD='conker/build/game-sound-record-1509F354-match'
SOURCE='conker/src/game/generated_CBDB0.c'
OBJECT='conker/build/src/game/generated_CBDB0.c.o'
OWNER,FUNCTION='generated_CBDB0','func_1509F354'
ENTRY,ROM,WORDS,FRAME=0x1509F354,0xCC804,74,48
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='c750ef3ced2079ca65c441ef9078decdb8ed3fc74678cf658e25ba75b45ee19f'
GUARD_SHA='8afb07a0bd5847fd90c6786e7f9e6d074d0f93a794f8bed58d61e702a12489cd'
BINDINGS={32:[('R_MIPS_26','func_1505EEF4')],84:[('R_MIPS_26','func_10010894')],156:[('R_MIPS_26','func_150ADA20')],252:[('R_MIPS_26','func_10010344')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='s32 func_1509F354() {\n    return 0;\n}'
SELECTED='struct struct127;\nstruct struct127 *func_1505EEF4(s32);\ns32 func_10010894(struct struct127 *);\ns32 func_150ADA20(void);\ns32 func_10010344(u16, void *, s32, s16, u16);\n/* Choose an enabled sound and consume its mask bit only if playback succeeds.\n * Sound offsets wrap to u16; shift indices follow the N64 modulo-32 rule.\n * A zero byte span retains the original divide trap; an unreachable mask retries.\n * Distance words remain live until the successful selection is submitted. */\nu32 func_1509F354(u32 first, u32 last, u32 mask, u32 volume,\n                  s32 actorKey, s16 distance, u32 farDistance) {\n    struct struct127 *actor;\n    u8 span;\n    u8 selected;\n\n    actor = func_1505EEF4(actorKey);\n    if (volume >= 0x8000U) volume = 0x7FFF;\n    if (actor == NULL) return mask;\n    if (func_10010894(actor) == 0) {\n        if (mask == 0) {\n            mask = 0xFFFFFFFFU >> ((0U - (u8)(last - first + 1)) & 31);\n        }\n        span = last - first + 1;\n        do {\n            selected = (u32)func_150ADA20() % span;\n        } while ((mask & (1U << (selected & 31))) == 0);\n        if (func_10010344((u16)(first + selected), actor, volume, distance, farDistance) != 0) {\n            mask ^= 1U << (selected & 31);\n        }\n    }\n    return mask;\n}'
RAW_SHA='c902b4fb2cf8800249e94104e259f675a472cbd3eb1a98625c262bcb50e7b4af'


def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Sound-mask source changed')
    return live.replace(SELECTED,STUB,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

# Reorder only independent home loads, the modulo-32 default-mask operations,
# and the final constant into the branch delay slot. Explicit safe C shift masks
# are hardware-redundant at the two SLLV consumers. Every other operation survives.
OMIT={44,66}
ORDER=list(range(26))+[34,26,27,28,29,30,32,31,33]+list(range(35,44))+list(range(45,66))+list(range(67,76))
RENAMES={24:{15:14},34:{24:15},28:{14:13},30:{11:10},32:{12:10,13:11},33:{13:12,14:13},
 35:{15:14,24:15},37:{25:24},38:{25:24},43:{9:25},45:{11:9},46:{10:25,11:9,12:10},47:{12:10,14:11},
 52:{14:11},55:{24:14},58:{15:12},59:{15:12},64:{24:14},67:{9:15},68:{25:16,9:15,11:24},69:{11:24}}
def normalize(raw,refs):
    if len(raw)!=304 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Sound-mask compiler words/bindings changed')
    w=list(struct.unpack('>76I',raw));assert sorted(ORDER)==[i for i in range(76)if i not in OMIT]
    assert w[44]==0x312A001F and w[66]==0x3219001F
    inverse={v:i for i,v in enumerate(ORDER)};result=[];relocs={}
    for j,i in enumerate(ORDER):
        x=w[i];op=x>>26;mapping=RENAMES.get(i,{})
        shifts=(21,16,11)if op==0 else()if op in(2,3)else(16,)if op==15 else(21,16)
        for bit in shifts:x=(x&~(31<<bit))|(mapping.get(w[i]>>bit&31,w[i]>>bit&31)<<bit)
        if i==32:x=(x&0xFFFF0000)|255
        if op in(4,5):
            dest=i+1+((w[i]&65535)^32768)-32768
            if i==25:dest=35 # first home read moved into the branch delay slot
            x=(x&0xFFFF0000)|((inverse[dest]-j-1)&65535)
        result.append(x)
        if i*4 in refs:relocs[j*4]=refs[i*4]
    return struct.pack('>74I',*result),relocs

def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);values=struct.unpack('>74I',normal);spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-';rows=[]
    for i,(a,)in enumerate(struct.iter_unpack('>I',raw)):
        omit=i in OMIT;at=i-sum(k<i for k in OMIT);b=a if omit else values[at]
        rr=refs.get(i*4,[]);nr=[]if omit else nrefs.get(at*4,[])
        if not omit and a==b and rr==nr:continue
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(rr),spec(nr),
          'Omit modulo-32 mask consumed by hardware SLLV'if omit else'Normalize closed sound-mask register allocation and independent scheduling','','','true'if omit else'false'])
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited sound-mask guards changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs));return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed sound-mask predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/CBDB0.s','conker/src/game_83300.c','conker/src/init_EB00.c','conker/asm/nonmatchings/game_DAE50/func_150ADA20.s',
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
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Sound-mask input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=296:raise ValueError('Sound-mask predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,296);wanted[at:at+296]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Sound-mask predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,296)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal sound-mask entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Sound-mask owner pools changed')
    old,new,single=(sections(p).get('.reginfo')for p in(a,b,isolated))
    if any(v is None or len(v[1])!=24 for v in(old,new,single))or old[0]!=new[0]or old[0]!=single[0]:raise ValueError('Sound-mask register metadata shape changed')
    before,actual,alone=(struct.unpack('>6I',v[1])for v in(old,new,single))
    if before!=(2734817278,0,855504,0,0,32752)or alone!=(2734948350,0,0,0,0,32752):raise ValueError('Sound-mask predecessor/isolated register declaration changed')
    expected=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6))
    if actual!=expected:raise ValueError('Sound-mask register metadata exceeds isolated-body union')
    return dict(GPR_added_bits='0x00020000',isolated_target_words_equal=True,exact_register_mask_union=True)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Sound-mask predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Sound-mask owner diagnostics changed')
    isolated,diag=compile_owner(root,out,'#include <ultra64.h>\n'+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Sound-mask isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+296]
    if struct.pack('>74I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}))!=truth:raise ValueError('Sound-mask normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Sound-mask live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=padded(root,out,new,guards,'strict-qualified-padded',True)
    if same_functions(new_pad,strict)!=17 or normalized_pools(new_pad)!=normalized_pools(strict):raise ValueError('Sound-mask strict padder differs')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Sound-mask padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Sound-mask live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Sound-mask live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Sound-mask linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sound-mask protected data changed')
    generated={n:tuple(f[1:])for _,n,f,_ in symbol_rows(new_pad.read_bytes())};strict_names={n:tuple(f[1:])for _,n,f,_ in symbol_rows(strict.read_bytes())}
    start,_,_,jumps=pad_generated_object.parse_retail_slice(root/'conker/asm/CBDB0.s');labels={n:(a-start,0,16,0,1)for a,ns in jumps.items()for n in ns}
    if set(generated)-set(strict_names)!=set(labels)or generated!={**strict_names,**labels}:raise ValueError('Sound-mask case labels changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=74,raw_words=76,frame=48,guards=len(guard_rows(raw,refs)),direct_C=False,omissions=2,
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
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/CBDB0.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Sound-mask linker owner changed')
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
    target = shadow/'src/game/generated_CBDB0.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected sound-mask Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown sound-mask Make redirect')
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
        raise ValueError('Sound-mask actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Sound-mask actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
