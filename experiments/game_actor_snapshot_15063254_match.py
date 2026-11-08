"""Actor snapshot callback direct C and complete owner/image qualification."""
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
BUILD='conker/build/game-actor-snapshot-15063254-match'
SOURCE='conker/src/game_83300.c'
OBJECT='conker/build/src/game_83300.c.o'
OWNER,FUNCTION='game_83300','func_15063254'
ENTRY,ROM,WORDS,FRAME=0x15063254,0x90704,76,88
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='0e30fac10f61f81713ed1ad9574f79aafdad34d6b66a37dfc7a651ec69c35579'
GUARD_SHA='ab4a2eb5c63a044bbb705009b55df2cf31a32791f1b99391efa32ab30544426c'
BINDINGS={132: [('R_MIPS_26', 'func_15060F28')], 140: [('R_MIPS_HI16', 'D_800CC2D0')], 144: [('R_MIPS_LO16', 'D_800CC2D0')], 184: [('R_MIPS_26', 'func_15082A44')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_15063254.s. */\ns32 func_15063254() {\n    return 0;\n}'
SELECTED='s32 func_15082A44(u8 *, s32, s32, s32, s32);\n/* Refresh the actor resource while preserving its placement and motion snapshots. */\nvoid func_15063254(struct127 *actor, u32 field4, u32 field3, f32 value) {\n    u32 identifier;\n    struct129 *auxiliary;\n    struct108 *camera;\n    f32 x;\n    f32 y;\n    f32 z;\n    f32 fieldB8;\n    f32 field40;\n    f32 fieldC4;\n    u32 facing;\n\n    identifier = actor->unk13F;\n    auxiliary = actor->unk144;\n    auxiliary->unk4 = field4;\n    auxiliary->unk3 = field3;\n    auxiliary->unk20 = value;\n    auxiliary->unk24 = value;\n    auxiliary->unk2 = 0;\n    camera = actor->camera;\n    x = actor->x_position;\n    y = actor->y_position;\n    z = actor->z_position;\n    fieldB8 = actor->unkB8;\n    field40 = actor->unk40;\n    fieldC4 = actor->unkC4;\n    facing = actor->unk76;\n    func_15060F28(actor, 0);\n    func_15082A44((u8 *)auxiliary, identifier, 0, 0,\n                  (s32)((u32)actor - (u32)D_800CC2D0) / (s32)sizeof(struct127) + 1);\n    actor->x_position = x;\n    actor->y_position = y;\n    actor->camera = camera;\n    actor->z_position = z;\n    actor->unkB8 = fieldB8;\n    actor->unk40 = field40;\n    actor->unk76 = facing;\n    actor->unk7A = facing;\n    actor->old_x_position = x;\n    actor->old_y_position = y;\n    actor->unk1CC = actor->y_position;\n    actor->old_z_position = actor->z_position;\n    actor->unkC4 = fieldC4;\n    camera->unk3D4 = (struct127 *)actor->unk31C;\n}'
RAW_SHA='684c24f425122236c83397bd2837649560b9d648423a7ffe01cc5e26d5042ce1'
BODY,SLOT=304,316


def source_states(live):
    old='s32 func_15063254();';new='void func_15063254(struct127 *, u32, u32, f32);'
    if live.count(STUB)==1 and live.count(old)==1:return live,live.replace(STUB,SELECTED,1).replace(old,new,1),False
    if live.count(SELECTED)!=1 or live.count(new)!=1:raise ValueError('Actor snapshot source/declaration changed')
    return live.replace(SELECTED,STUB,1).replace(new,old,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

# Remove only a redundant argument copy and unused compiler home spill. Every
# semantic field access survives. The checked permutation derives the retail
# FP/GPR lifetimes, private cell offsets and 0x58-byte frame.
OMIT={3,7}
def normalize(raw,refs):
    if len(raw)!=312 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Actor snapshot compiler words/bindings changed')
    w=list(struct.unpack('>78I',raw))
    ORDER=[0,1,2,4,5,6,8,9,11,12,13,14,15,16,17,18,10,19,24,20,22,25,26,27,28,29,30,31,32,21,23,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,49,50,51,48,53,54,52,55,56,57,58,59,60,61,62,69,70,63,64,65,66,67,68,71,72,73,74,75,76,77]
    assert sorted(ORDER)==[i for i in range(78)if i not in(3,7)]
    gpr={13:{7:5},32:{24:2},34:{24:2},35:{25:24},36:{25:24},37:{25:24,8:25},39:{8:25},40:{9:8},41:{9:8,10:9},42:{10:9},48:{2:10},49:{3:2},52:{2:10},63:{3:2},64:{3:2},72:{2:10}}
    fp={20:0,21:0,22:2,23:2,24:4,25:4,26:6,27:6,28:8,29:8,30:10,31:10,55:16,58:16,59:18,61:18,60:8,68:8,62:4,69:4,70:6,71:6}
    z=[];nr={}
    for j,i in enumerate(ORDER):
     x=w[i];op=x>>26;fields=(21,16,11)if op==0 else()if op in(2,3,17)else(21,)if op in(49,57)else(16,)if op==15 else(21,16)
     for b in fields:x=(x&~(31<<b))|(gpr.get(i,{}).get(w[i]>>b&31,w[i]>>b&31)<<b)
     if i in fp:assert op in(49,57);x=(x&~(31<<16))|(fp[i]<<16)
     if op in(35,43,49,57)and w[i]>>21&31==29 and w[i]&65535>=40:x=(x&0xFFFF0000)|((w[i]&65535)+4)
     if i in(0,77):x=(x&0xFFFF0000)|((-88 if i==0 else 88)&65535)
     z.append(x)
     if 4*i in refs:nr[4*j]=refs[4*i]
    return struct.pack('>76I',*z),nr

def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);values=struct.unpack('>76I',normal);spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-';rows=[]
    for i,(a,)in enumerate(struct.iter_unpack('>I',raw)):
        omit=i in OMIT;at=i-sum(k<i for k in OMIT);b=a if omit else values[at];rr=refs.get(i*4,[]);nr=[]if omit else nrefs.get(at*4,[])
        if not omit and a==b and rr==nr:continue
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(rr),spec(nr),
          'Omit unused argument copy/home artifact'if omit else'Normalize closed actor snapshot FP/GPR cells, frame and memory schedule','','','true'if omit else'false'])
    if len(rows)!=59:raise ValueError('Actor snapshot guard derivation changed')
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited actor snapshot guards changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs));return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed actor snapshot predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/nonmatchings/game_83300/func_15063254.s','conker/asm/C4DC0.s','conker/asm/AEB40.s','conker/src/game/generated_C4DC0.c','conker/src/game/generated_AEB40.c',
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
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Actor snapshot input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=SLOT or truth[BODY:]!=bytes(12):raise ValueError('Actor snapshot predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT);wanted[at:at+SLOT]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Actor snapshot predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,BODY)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b];raise ValueError('Actor snapshot literal ELF differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Actor snapshot owner pools changed')
    values=[sections(p)['.reginfo']for p in(a,b,isolated)];before,actual,alone=[struct.unpack('>6I',v[1])for v in values]
    if (before,alone)!=REGISTER_INPUTS or actual!=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6)):raise ValueError('Actor snapshot register union changed')
    return dict(before=list(before),isolated=list(alone),exact_register_union=True)
REGISTER_INPUTS=((3825205246, 0, 4294967295, 0, 0, 32752), (2734936062, 0, 333141, 0, 0, 32752))

def inherited_diagnostics(a,b):
    old,new=diagnostic_rows(a),diagnostic_rows(b)
    if old!=new or sum(old.values())!=8:raise ValueError('Actor snapshot inherited diagnostics changed')
    return dict(inherited_warnings=8,new_warnings=0)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Actor snapshot predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    diagnostics=inherited_diagnostics(old_diag,new_diag)
    isolated,diag=compile_owner(root,out,'#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\nvoid func_15060F28(struct127 *,s32);\n'+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Actor snapshot isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SLOT]
    if struct.pack('>76I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}))!=truth[:BODY]:raise ValueError('Actor snapshot normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Actor snapshot live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=new_pad
    if len(parse_object(new_pad)[1])!=89:raise ValueError('Actor snapshot complete owner inventory changed')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Actor snapshot padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Actor snapshot live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Actor snapshot live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Actor snapshot linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor snapshot protected data changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=76,raw_words=78,raw_frame=80,frame=88,slot_words=79,trailing_padding_words=3,guards=59,direct_C=False,omissions=2,
      raw_neighbors=neighbors,padded_neighbors=padded_neighbors,diagnostics=diagnostics,register_metadata=metadata,
      actual_Make=make,strict_changed_bytes=changed,exclusions=0,functions=len(a),all_addresses_fixed=True,
      changed_bodies=[FUNCTION],protected_data=data,owner_sha256=sha(new_pad.read_bytes()),ELF_sha256=sha(new_image.read_bytes()),guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,normal=normal,normal_refs=nrefs,predecessor_elf=old_image,qualified_elf=new_image,qualified_object=new_pad)

def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    from tools import pad_c_object
    assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Actor snapshot linker owner changed')
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
    target = shadow/'src/game_83300.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor snapshot Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor snapshot Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        allowed_diagnostics = diagnostic_rows((out/'qualified-owner-diagnostics.txt').read_text()) if args[0]=='../ido/ido5.3_recomp/cc'else Counter()
        if result.returncode or diagnostic_rows(result.stderr) != allowed_diagnostics or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 5 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Actor snapshot actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Actor snapshot actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
