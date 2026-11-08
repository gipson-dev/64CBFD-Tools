"""Class-6 actor scan recovery and fail-closed, complete-owner/image gates."""
import csv
import hashlib
import io
import json
import shlex
import struct
import subprocess
import sys
from collections import Counter
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools import pad_generated_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT = Path(__file__).resolve().parents[2]
BUILD = 'conker/build/game-class6-actor-scan-150A0D8C-match'
SOURCE = 'conker/src/game/generated_CDE80.c'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
OWNER, FUNCTION = 'generated_CDE80', 'func_150A0D8C'
ENTRY, ROM, WORDS, FRAME = 0x150A0D8C, 0xCE23C, 173, 128
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = 'af2715001558385cec85d33baac281f90e3a0a4f52397da02ce0afe141748bf4'
GUARD_SHA = '8d83b0e799e72ae61f2462c36f033d3d0757427d4839506e9d1bf59f1b319e69'
RAW_SHA = 'b98f5bb57bab00777996a0bacb3429473526f923ca4ef834516d965558a9aaeb'
BINDINGS = {64: [('R_MIPS_HI16', 'D_800D3094')], 68: [('R_MIPS_LO16', 'D_800D3094')], 84: [('R_MIPS_HI16', 'D_8009F5A8')], 88: [('R_MIPS_LO16', 'D_8009F5A8')], 112: [('R_MIPS_HI16', 'D_800D3098')], 124: [('R_MIPS_LO16', 'D_800D3098')], 164: [('R_MIPS_HI16', 'D_800CC2D0')], 168: [('R_MIPS_LO16', 'D_800CC2D0')], 228: [('R_MIPS_26', 'func_150A1DA0')], 380: [('R_MIPS_26', 'func_150AD9A0')], 528: [('R_MIPS_26', 'func_15035808')], 580: [('R_MIPS_26', 'func_15035808')], 600: [('R_MIPS_HI16', 'D_800D3094')], 604: [('R_MIPS_LO16', 'D_800D3094')]}
STUB = 's32 func_150A0D8C() {\n    return 0;\n}'
DECLARATIONS = 'extern f32 D_8009F5A8;\ns32 func_150AD9A0(s32, s32, s32);\ns32 func_15035808(s32, s32, f32, f32, f32, f32, f32, f32, f32, f32);'
SELECTED = '/* Submit effects for actors accepted by active class-6 records. */\nvoid func_150A0D8C(void) {\n    extern struct127 D_800CC2D0[26];\n    u32 index;\n    s32 offset;\n    struct127 *actor;\n    s32 actorIndex;\n    GeneratedCDE80Record *record;\n    s16 yDelta;\n    s32 distance;\n    f32 inner;\n    f32 scale;\n    index = 0;\n    offset = 0;\n    if (D_800D3094 != 0) {\n        scale = D_8009F5A8;\n        do {\n            record = (GeneratedCDE80Record *)(offset + (u32)D_800D3098);\n            if (record->disabled == 0 && (record->flags >> 2) == 6) {\n                for (actor = D_800CC2D0, actorIndex = 0; actorIndex != 25; actorIndex++, actor++) {\n                    if (actor->interaction_state != 0 && (actor->unk5 == 0 || actor->unk5 == 1)) {\n                        if (func_150A1DA0(actor, offset + (u32)D_800D3098, 1) == 0) {\n                            record = (GeneratedCDE80Record *)(offset + (u32)D_800D3098);\n                            yDelta = (s16)(actor->y_position - record->origin1);\n                            if (record->field17 == 0) {\n                                distance = func_150AD9A0((s16)(actor->x_position - record->origin0),\n                                    yDelta, (s16)(actor->z_position - record->origin2));\n                                record = (GeneratedCDE80Record *)(offset + (u32)D_800D3098);\n                                if (distance < record->radius) {\n                                    inner = (f32)record->radius * scale;\n                                    if (inner > 100.0f) inner = 100.0f;\n                                    func_15035808(2, actorIndex, record->origin0, record->origin1,\n                                        record->origin2, 0.0f, record->parameter10,\n                                        (f32)record->radius - inner, (f32)record->radius, 255.0f);\n                                }\n                            } else {\n                                func_15035808(1, actorIndex, actor->x_position, actor->unk180,\n                                    actor->z_position, 0.0f, 0.0f, 100.0f, 150.0f, 255.0f);\n                            }\n                        }\n                    }\n                }\n            }\n            index++;\n            offset += 0x34;\n        } while (index < (u32)D_800D3094);\n    }\n}'
sha = lambda b: hashlib.sha256(b).hexdigest()
OLD_RECORD_PAD = '    u8 pad6[2];\n    s16 heightOffset;\n    u8 padA[0xB];'
NEW_RECORD_PAD = '    s16 radius;\n    s16 heightOffset;\n    u8 padA[6];\n    f32 parameter10;\n    u8 disabled;'


def source_states(live):
    anchor = 'extern f32 D_8009F5A4;'
    if live.count(STUB) == 1 and DECLARATIONS not in live:
        if live.count(OLD_RECORD_PAD) != 1: raise ValueError('Unknown record layout predecessor')
        return live, live.replace(STUB, SELECTED, 1).replace(anchor, anchor+'\n'+DECLARATIONS, 1).replace(OLD_RECORD_PAD, NEW_RECORD_PAD, 1), False
    if live.count(SELECTED) != 1 or live.count(anchor+'\n'+DECLARATIONS) != 1 or live.count(NEW_RECORD_PAD) != 1:
        raise ValueError('Class-6-actor-scan source/declarations changed')
    return live.replace(SELECTED, STUB, 1).replace(anchor+'\n'+DECLARATIONS, anchor, 1).replace(NEW_RECORD_PAD, OLD_RECORD_PAD, 1), live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 692 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('Class-6 actor scan raw words or bindings changed')
    words=list(struct.unpack('>173I',raw));normal=list(words);rebound=dict(refs);cycle={19:20,20:19,21:22,22:21}
    for i in range(16,156):
     w=words[i];op=w>>26
     shifts=(21,16,11)if op==0 else(16,)if op==15 or(op==17 and w>>21&31 in(0,4))else(21,)if op in(49,53,57,61)else(21,16)if op in(4,5,9,12,13,20,21,32,33,35,36,37,40,41,43)else()
     for shift in shifts:
      reg=w>>shift&31
      if reg in cycle:normal[i]=(normal[i]&~(31<<shift))|(cycle[reg]<<shift)
    permutations=[((21,22,23,24),(23,24,21,22)),((33,34),(34,33)),(tuple(range(137,145)),(144,137,138,143,142,141,140,139))]
    for dest,origin in permutations:
     prior=list(normal);prior_refs=dict(rebound)
     for d,s in zip(dest,origin):
      normal[d]=prior[s];rebound.pop(d*4,None)
      if s*4 in prior_refs:rebound[d*4]=prior_refs[s*4]
    for i in(36,64,98):
     w=normal[i];assert w>>26==0 and w&63==33 and w>>21&31==20
     normal[i]=(w&~(0x3FF<<16))|((w>>21&31)<<16)|((w>>16&31)<<21)
    if sha(struct.pack('>173I', *normal)) != '0fbf52d819a85fd142a9a9e88ee05464a72b9980051e5b45ae1511b18c02056d':
        raise ValueError('Class-6 actor allocation/schedule derivation changed')
    return struct.pack('>173I', *normal), rebound


def guard_rows(raw, refs):
    normal, rebound = normalize(raw, refs)
    spec = lambda rows: ';'.join(kind+':'+name for kind,name in rows) or '-'
    rows = []
    for i,(a,b) in enumerate(zip(struct.unpack('>173I',raw),struct.unpack('>173I',normal))):
        before,after = refs.get(i*4,[]),rebound.get(i*4,[])
        if a==b and before==after: continue
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(before),spec(after),
            'Normalize closed actor scan roles and independent address or argument schedule','','','false'])
    if len(rows)!=31: raise ValueError('Class-6 actor scan guard scope changed')
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA or not before.endswith(b'\n'):
        raise ValueError('Class-6-actor-scan inherited guard history changed')
    stream = io.StringIO(newline='')
    csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs))
    return before+stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the class6-actor-scan predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/CDE80.s', 'conker/asm/nonmatchings/game_45B80/func_15019130.s', 'conker/src/game_45B80.c', 'conker/asm/nonmatchings/game_DAE50/func_150AD9A0.s', 'conker/src/game_DAE50.c', 'conker/asm/61D10.s', 'conker/src/game/generated_61D10.c', 'conker/symbol_addrs.us.txt',
                 'conker/undefined_syms.us.txt', 'conker/undefined_funcs.us.txt',
                 'conker/undefined_syms_auto.txt', 'conker/undefined_funcs_auto.txt']
        names += [p.relative_to(root).as_posix() for p in (root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in ('cc', 'cfe', 'uopt', 'ugen')]
        for name in names:
            p = folder/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n: sha((folder/n).read_bytes()) for n in names}, indent=2)+'\n')
    hashes = json.loads(receipt.read_text())
    allowed = {SOURCE, OBJECT, ELF, GUARDS}
    for name, digest in hashes.items():
        if sha((folder/name).read_bytes()) != digest or (name not in allowed and sha((root/name).read_bytes()) != digest):
            raise ValueError('Class-6-actor-scan frozen input changed: '+name)
    return hashes


def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/CDE80.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination


def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Class-6-actor-scan linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 692:
        raise ValueError('Class-6-actor-scan predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 692)
    wanted[at:at+692] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('Class-6-actor-scan predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 692)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal class6-actor-scan whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 692 if n == FUNCTION else f[2], *f[3:]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Class-6-actor-scan named definitions changed')
    return sum(a != b for a, b in zip(before, actual))


def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    conker = root/'conker'
    target = shadow/'src/game/generated_CDE80.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected class6-actor-scan Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == SOURCE.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown class6-actor-scan Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        if result.returncode or result.stderr or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 5 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Class-6-actor-scan actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Class-6-actor-scan actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)


def owner_pools(before, after):
    a,b=alloc_pools(before),alloc_pools(after)
    if a.keys()!=b.keys() or any(a[n]!=b[n] for n in a if n!='.reginfo'):
        raise ValueError('Class-6 actor scan non-register pools changed')
    old,new=a['.reginfo'],b['.reginfo']
    if old[:4]!=new[:4] or old[5:]!=new[5:] or len(old[4])!=24 or len(new[4])!=24:
        raise ValueError('Class-6 actor scan register metadata geometry changed')
    x,y=list(struct.unpack('>6I',old[4])),list(struct.unpack('>6I',new[4]))
    if x[2]!=0x003FFDFF: raise ValueError('Class-6 actor scan inherited floating mask changed')
    # The restored scan reserves the F8/F9 arithmetic pair and saved F22..F29
    # pairs. Existing owners already reserve F8 and F20/F21. Other fields stay fixed.
    x[2]|=0x3FC00200
    if x!=y: raise ValueError('Class-6 actor scan register mask delta changed')
    return '0x3FC00200'


def prepare(root=ROOT):
    root = Path(root).resolve()
    out = root/BUILD
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(root, out)
    before, after, installed = source_states((root/SOURCE).read_text())
    if before != (out/'frozen'/SOURCE).read_text():
        raise ValueError('Class-6-actor-scan predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Class-6-actor-scan owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    owner_pools(old,new)
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+692]
    if struct.pack('>173I', *bound_blob(normal, normal_refs, {name: (0x10026800 if name == '__ull_rshift' else int(name.split('_')[1], 16)) for rows in normal_refs.values() for _, name in rows})) != truth:
        raise ValueError('Class-6-actor-scan normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('Class-6-actor-scan live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 28 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('Class-6-actor-scan production/strict padded code or pools differ')
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    start, _, _, jump_labels = pad_generated_object.parse_retail_slice(root/'conker/asm/CDE80.s')
    labels = {name: (address-start, 0, 16, 0, 1) for address, names in jump_labels.items() for name in names}
    if set(generated_names)-set(strict_names) != set(labels) or generated_names != {**strict_names, **labels}:
        raise ValueError('Class-6-actor-scan preserved case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Class-6-actor-scan padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('Class-6-actor-scan live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('Class-6-actor-scan live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Class-6-actor-scan linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Class-6-actor-scan protected data changed')
    report = dict(source_installed=installed, frozen_inputs=len(frozen), words=173, frame=128, guards=31, raw_CPR1_added_bits="0x3FC00200", preserved_labels=len(labels),
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
