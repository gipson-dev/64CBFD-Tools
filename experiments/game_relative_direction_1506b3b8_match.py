"""Relative-heading semantic C and complete owner/image qualification."""
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
BUILD='conker/build/game-relative-direction-1506B3B8-match/resume-2189'
SOURCE='conker/src/game_981E0.c'
OBJECT='conker/build/src/game_981E0.c.o'
OWNER,FUNCTION='game_981E0','func_1506B3B8'
ENTRY,ROM,WORDS,FRAME=0x1506B3B8,0x98868,77,32
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='5bef769822f533a2b3abd6aff915b80ae0f134078f3414d6035a1c0edb24a0f4'
GUARD_SHA='7b76c76b62b7c36f9a538ce31c3f5d48712e111f2c9f2367e70d8548166168d4'
BINDINGS={4: [('R_MIPS_HI16', 'D_800CC2D0')], 16: [('R_MIPS_LO16', 'D_800CC2D0')], 8: [('R_MIPS_HI16', 'D_800D154C')], 12: [('R_MIPS_LO16', 'D_800D154C')], 56: [('R_MIPS_26', 'func_1505A630')], 64: [('R_MIPS_HI16', 'D_800D154C')], 68: [('R_MIPS_LO16', 'D_800D154C')], 140: [('R_MIPS_HI16', 'D_80099A3C')], 144: [('R_MIPS_LO16', 'D_80099A3C')], 156: [('R_MIPS_HI16', 'D_80099A43')], 180: [('R_MIPS_LO16', 'D_80099A43')], 184: [('R_MIPS_HI16', 'D_80099A3E')], 208: [('R_MIPS_LO16', 'D_80099A3E')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='/* Non-matching C placeholders for asm/nonmatchings/game_981E0/func_1506B3B8.s. */\ns32 func_1506B3B8() {\n    return 0;\n}\n// NON-MATCHING: 5% there...\n// void func_1506B3B8(void) {\n//     u8 sp19;\n//     s16 temp_t0;\n//     s32 temp_a3;\n//     s32 temp_v0;\n//     s32 temp_v1;\n//     struct127 *temp_a1;\n//     struct127 *temp_a1_2;\n//     s32 phi_a2;\n//     s32 phi_a0;\n//     u8 phi_a0_2;\n//\n//     temp_a1 = D_800D154C;\n//     sp19 = 0;\n//     temp_a1_2 = D_800D154C;\n//     temp_t0 = (temp_a1_2->unk7A + (temp_a1_2->unk1FD << 8)) - func_1505A630(D_800CC2D0[0].x_position - temp_a1->x_position, temp_a1->z_position - D_800CC2D0[0].z_position, temp_a1, 0);\n//     temp_v1 = (s32) temp_t0 >> 8;\n//     temp_a3 = temp_v1 & 0xFF;\n//     phi_a2 = temp_v1 & 0xFF;\n//     if ((temp_a3 & 0x80) != 0) {\n//         phi_a2 = -temp_a3 & 0xFF;\n//     }\n//     temp_v0 = phi_a2;\n//     if (phi_a2 < (s32) D_80099A3C) {\n//         phi_a0 = 1;\n//     } else {\n//         if ((s32) D_80099A43 < temp_v0) {\n//             phi_a0_2 = (u8)5U;\n//         } else {\n//             phi_a0_2 = sp19;\n//             if ((s32) D_80099A3E < temp_v0) {\n//                 phi_a0_2 = (u8)2U;\n//             }\n//         }\n//         if ((s32) temp_t0 < 0) {\n//             phi_a0 = (phi_a0_2 + 4) & 0xFF;\n//         } else {\n//             phi_a0 = (phi_a0_2 + 3) & 0xFF;\n//         }\n//     }\n//     temp_a1_2->unk138 = (u8)0;\n//     D_800D154C->unk244 = (s16) D_80099A3C[phi_a0]; // + 0x800A0000)->unk-65C4;\n//     D_800D154C->unk21C = (u16)0x4E20;\n// }'
SELECTED='/* Select a relative-facing table entry, restart it, and set the actor timeout. */\nvoid func_1506B3B8(void) {\n    s16 difference;\n    u8 magnitude;\n    u16 angle;\n    u8 choice = 0;\n    s32 signedHigh;\n    s32 highByte;\n    struct127 *actor;\n\n    angle = func_1505A630(D_800CC2D0[0].x_position - D_800D154C->x_position,\n                         D_800D154C->z_position - D_800CC2D0[0].z_position, 0);\n    actor = D_800D154C;\n    difference = actor->unk7A + (actor->unk1FD << 8) - angle;\n    signedHigh = difference >> 8;\n    highByte = signedHigh & 0xFF;\n    magnitude = signedHigh;\n    if ((highByte & 0x80) != 0) {\n        magnitude = (u8)-highByte;\n    }\n    if (magnitude < ((u8 *)D_80099A3C)[0]) {\n        choice = 1;\n    } else {\n        if (D_80099A43 < magnitude) {\n            choice = 5;\n        } else if (((u8 *)&D_80099A3E)[0] < magnitude) {\n            choice = 2;\n        }\n        if (difference < 0) {\n            choice += 4;\n        } else {\n            choice += 3;\n        }\n    }\n    actor->unk138 = 0;\n    D_800D154C->unk244 = ((u8 *)D_80099A3C)[choice];\n    D_800D154C->unk21C = 20000;\n}'
RAW_SHA='1db2220b4471fe4d980cc6783866d3abda9a2371b1c09123f6f7d270e16acee2'
BODY=SLOT=308


def source_states(live):
    old='s32 func_1506B3B8();';new='void func_1506B3B8(void);'
    if live.count(STUB)==1 and live.count(old)==1:return live,live.replace(STUB,SELECTED,1).replace(old,new,1),False
    if live.count(SELECTED)!=1 or live.count(new)!=1:raise ValueError('Relative heading source/declaration changed')
    return live.replace(SELECTED,STUB,1).replace(new,old,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

# Split the complete table base into an early HI16 and two signed LO16
# byte accesses, preserving modular address arithmetic and instruction count.
OMIT=set()
def normalize(raw,refs):
    if len(raw)!=308 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Relative heading compiler words/bindings changed')
    w=list(struct.unpack('>77I',raw));order=list(range(20))+[35]+list(range(20,35))+list(range(36,77));z=[];nr={}
    for j,i in enumerate(order):
     x=w[i];op=x>>26;mp={}
     if i in(1,4,7,8):mp={3:2}
     if i in(6,9,10):mp={2:5}
     if i in(18,20,21,66):mp={7:5}
     if i in(28,29,32):mp={5:7}
     if i==35:mp={3:11}
     if i==67:mp={3:11}
     if i==68:mp={12:11}
     if i in(69,71):mp={13:12,12:11}
     if i in(70,73):mp={15:13,14:15}
     if i==72:mp={14:15}
     fields=(21,16,11)if op==0 else()if op in(2,3,17)else(21,)if op in(49,57)else(16,)if op==15 else(21,16)
     for b in fields:x=(x&~(31<<b))|(mp.get(w[i]>>b&31,w[i]>>b&31)<<b)
     rr=refs.get(4*i,[])
     if i==36:
      assert x>>26==9 and rr==[('R_MIPS_LO16','D_80099A3C')];x=(15<<26)|(15<<16)|(x&65535);rr=[('R_MIPS_HI16','D_80099A3C')]
     if i==37:
      assert x>>26==36 and x&65535==0;x=(x&~(31<<21))|(15<<21);rr=[('R_MIPS_LO16','D_80099A3C')]
     if i==68:rr=[('R_MIPS_LO16','D_80099A3C')]
     z.append(x)
     if rr:nr[4*j]=rr
    return struct.pack('>77I',*z),nr

def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);values=struct.unpack('>77I',normal);spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-';rows=[]
    for i,(a,)in enumerate(struct.iter_unpack('>I',raw)):
        omit=i in OMIT;at=i-sum(k<i for k in OMIT);b=a if omit else values[at];rr=refs.get(i*4,[]);nr=[]if omit else nrefs.get(at*4,[])
        if not omit and a==b and rr==nr:continue
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(rr),spec(nr),
          'Omit unused argument copy/home artifact'if omit else'Normalize equivalent table HI/LO factorization and closed GPR lifetimes','','','true'if omit else'false'])
    if len(rows)!=34:raise ValueError('Relative heading guard derivation changed')
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited relative heading guards changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs));return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed relative heading predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/asm/nonmatchings/game_981E0/func_1506B3B8.s',
          'conker/asm/nonmatchings/game_83300/func_1505E0C4.s','conker/src/game_83300.c','conker/src/game/generated_A9260.c',
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
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Relative heading input changed: '+n)
    return hashes

def strict_image(before,actual,truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=SLOT:raise ValueError('Relative heading predecessor/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT);wanted[at:at+SLOT]=truth
    rows=[r for r in symbol_rows(before)if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Relative heading predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,BODY)
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b];raise ValueError('Relative heading literal ELF differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    return sum(a!=b for a,b in zip(before,actual))

def owner_pools(a,b,isolated):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Relative heading owner pools changed')
    values=[sections(p)['.reginfo']for p in(a,b,isolated)];before,actual,alone=[struct.unpack('>6I',v[1])for v in values]
    if (before,alone)!=REGISTER_INPUTS or actual!=tuple(before[i]|alone[i]if i<5 else before[i]for i in range(6)):raise ValueError('Relative heading register union changed')
    return dict(before=list(before),isolated=list(alone),exact_register_union=True)
REGISTER_INPUTS=((2736783358, 0, 4194303, 0, 0, 32752), (2734751742, 0, 390400, 0, 0, 32752))
OWNER_FUNCTIONS=328
INHERITED_WARNINGS=36

def inherited_diagnostics(a,b):
    old,new=diagnostic_rows(a),diagnostic_rows(b)
    if old!=new or sum(old.values())!=INHERITED_WARNINGS:raise ValueError('Relative heading inherited diagnostics changed')
    return dict(inherited_warnings=INHERITED_WARNINGS,new_warnings=0)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Relative heading predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    diagnostics=inherited_diagnostics(old_diag,new_diag)
    isolated,diag=compile_owner(root,out,'#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\nextern struct127 *D_800D154C;\nextern s16 D_80099A3C[],D_80099A3E;\nextern u8 D_80099A43;\nu16 func_1505A630(f32,f32,s32);\n'+SELECTED,'qualified-isolated')
    if diag or function_blob(isolated)!=function_blob(new):raise ValueError('Relative heading isolated body changed')
    neighbors=same_functions(old,new,(FUNCTION,));metadata=owner_pools(old,new,isolated)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SLOT]
    if struct.pack('>77I',*bound_blob(normal,nrefs,{name:int(name.split('_')[1],16)for rows in refs.values()for _,name in rows}))!=truth[:BODY]:raise ValueError('Relative heading normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Relative heading live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=new_pad
    if len(parse_object(new_pad)[1])!=OWNER_FUNCTIONS:raise ValueError('Relative heading complete owner inventory changed')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Relative heading padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Relative heading live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Relative heading live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Relative heading linked body/address census changed')
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Relative heading protected data changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=77,raw_words=77,raw_frame=32,frame=32,slot_words=77,trailing_padding_words=0,guards=34,direct_C=False,omissions=0,
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
    # GNU ld supplies an STT_FILE name for this owner's local symbols. Keep
    # the actual Make basename so a scratch path cannot change ELF metadata.
    staged=out/(label+'-objects')/Path(OBJECT).name
    staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(owner.read_bytes());owner=staged
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Relative heading linker owner changed')
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
    target = shadow/'src/game_981E0.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected relative heading Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown relative heading Make redirect')
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
        raise ValueError('Relative heading actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Relative heading actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
