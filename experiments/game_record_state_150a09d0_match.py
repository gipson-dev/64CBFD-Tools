"""Record state recovery and fail-closed, complete-owner/image gates."""
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
BUILD = 'conker/build/game-record-state-150A09D0-match'
SOURCE = 'conker/src/game/generated_CDE80.c'
CALLER_SOURCE = 'conker/src/game_45B80.c'
CALLER_OBJECT = 'conker/build/src/game_45B80.c.o'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
OWNER, FUNCTION = 'generated_CDE80', 'func_150A09D0'
ENTRY, ROM, WORDS, FRAME = 0x150A09D0, 0xCDE80, 209, 64
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = '68d7dd3659d2d20b824ca85fd7772d9445db5bdb3d3f6a1a7ab3fb11b26f3435'
GUARD_SHA = 'efa24cbf5b02ded109725d251bc83be27272659cf305dc84f8f2dfa710890f82'
RAW_SHA = 'f067b4a5d4110bbcdfc595661697af370bddd20ec7cf15dfc6d7d6d1b8ba71b8'
BINDINGS = {40: [('R_MIPS_HI16', 'D_800D3094')], 44: [('R_MIPS_LO16', 'D_800D3094')], 64: [('R_MIPS_HI16', 'D_800DBFF0')], 84: [('R_MIPS_LO16', 'D_800DBFF0')], 68: [('R_MIPS_HI16', 'D_80082FA0')], 80: [('R_MIPS_LO16', 'D_80082FA0')], 72: [('R_MIPS_HI16', 'D_800D3098')], 76: [('R_MIPS_LO16', 'D_800D3098')], 208: [('R_MIPS_26', 'func_1000FC18')], 228: [('R_MIPS_HI16', 'D_800C35EA')], 232: [('R_MIPS_LO16', 'D_800C35EA')], 240: [('R_MIPS_HI16', 'D_800CC2D0')], 248: [('R_MIPS_LO16', 'D_800CC2D0')], 260: [('R_MIPS_26', 'func_150A1DA0')], 280: [('R_MIPS_26', 'func_150A23E4')], 288: [('R_MIPS_HI16', 'D_800D3094')], 296: [('R_MIPS_LO16', 'D_800D3094')], 356: [('R_MIPS_26', 'func_1000E46C')], 392: [('R_MIPS_26', 'func_1000E46C')], 420: [('R_MIPS_HI16', 'D_800D3094')], 428: [('R_MIPS_LO16', 'D_800D3094')], 508: [('R_MIPS_HI16', 'D_800DDF5C')], 532: [('R_MIPS_LO16', 'D_800DDF5C')], 772: [('R_MIPS_HI16', 'D_800D3094')], 776: [('R_MIPS_LO16', 'D_800D3094')]}
STUB = 's32 func_150A09D0() {\n    return 0;\n}'
DECLARATIONS = 'extern s32 D_80082FA0;\nextern u8 D_800C35EA;\nextern u8 D_800DDF5C[];\nvoid func_1000FC18(u16, s16, s16, s16, u16);\ns32 func_1000E46C(s32, s32, s32, s32);\nvoid func_150A23E4(GeneratedCDE80Record *);\ntypedef struct {\n    u8 pad0[0x938];\n    f32 radius;\n    f32 x;\n    f32 y;\n    f32 z;\n    u8 enabled;\n    u8 parameter18;\n    u8 pad94A[0x56];\n} GeneratedCDE80ViewUpdate;'
SELECTED = '/* Advance record states and publish eligible viewer parameters. */\nvoid func_150A09D0(s32 unused) {\n    extern struct127 D_800CC2D0[26];\n    u32 index;\n    s32 offset;\n    GeneratedCDE80Record *record;\n    u32 state;\n    u32 low;\n    s32 parameter18;\n    s32 viewer;\n    s32 viewOffset;\n    GeneratedCDE80ViewUpdate *view;\n    for (index = 0, offset = 0; index < (u32)D_800D3094; index++, offset += 0x34) {\n        record = (GeneratedCDE80Record *)((u32)D_800D3098 + offset);\n        switch (record->flags >> 2) {\n        case 2:\n            state = record->field20;\n            if (state == 1) {\n                record->field20 = state ^ 3;\n            } else if (state == 2) {\n                func_1000FC18((u16)((u32)record->field1C >> 16),\n                    record->origin0, record->origin1, record->origin2,\n                    (u16)record->field18);\n                ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->field20 = 0;\n            }\n            if (D_800C35EA == 1 &&\n                func_150A1DA0(D_800CC2D0, offset + (u32)D_800D3098, 0) == 0) {\n                func_150A23E4((GeneratedCDE80Record *)(offset + (u32)D_800D3098));\n            }\n            break;\n        case 7:\n            if ((record->flags & 3) == 3) {\n                record->field20 = 0;\n            } else {\n                state = record->field20;\n                if (state == 1) {\n                    record->field20 = 2;\n                } else if (state == 2) {\n                    if (func_1000E46C(record->field17, 0, record->field18, 0) != 0) {\n                        record = (GeneratedCDE80Record *)((u32)D_800D3098 + offset);\n                        if (func_1000E46C(record->field17, 100, record->field1C, 0) != 0) {\n                            ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->field20 = 0;\n                        }\n                    }\n                }\n            }\n            break;\n        case 4:\n            if (record->field17 != 9) {\n                low = (u32)record->field1C & 255;\n                if (low != 0) {\n                    if (record->disabled == 0) { low--; }\n                    else { low = 0; }\n                    record->field1C = ((u32)record->field1C & ~255U) | low;\n                    if (low == 0) {\n                        record = (GeneratedCDE80Record *)((u32)D_800D3098 + offset);\n                        low = (u32)record->field1C;\n                        D_800DDF5C[(low >> 8) & 255] = 0;\n                        record->field1C &= 0xFFFF0000;\n                    }\n                }\n            }\n            record = (GeneratedCDE80Record *)((u32)D_800D3098 + offset);\n            /* fall through */\n        case 0:\n            if (record->field17 == 12 && record->disabled == 0) {\n                for (viewer = 0, viewOffset = 0; viewer <= D_80082FA0; viewer++, viewOffset += 0x9A0) {\n                    view = (GeneratedCDE80ViewUpdate *)((u32)D_800DBFF0 + viewOffset);\n                    view->x = ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->origin0;\n                    view->y = ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->origin1;\n                    view->z = ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->origin2;\n                    view->radius = ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->radius;\n                    parameter18 = ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->field18;\n                    view->enabled = 1;\n                    view->parameter18 = parameter18;\n                }\n            }\n            break;\n        }\n    }\n}'
sha = lambda b: hashlib.sha256(b).hexdigest()
def source_states(live):
    if live.count(STUB) == 1 and DECLARATIONS not in live:
        if live.count('    s32 field20;') != 1: raise ValueError('Unknown record state predecessor')
        return live, live.replace(STUB, DECLARATIONS+'\n\n'+SELECTED, 1).replace('    s32 field20;', '    u32 field20;', 1), False
    if live.count(SELECTED) != 1 or live.count(DECLARATIONS+'\n\n'+SELECTED) != 1 or live.count('    u32 field20;') != 1:
        raise ValueError('Record state source or declarations changed')
    return live.replace(DECLARATIONS+'\n\n'+SELECTED, STUB, 1).replace('    u32 field20;', '    s32 field20;', 1), live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 836 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('Record state raw words or bindings changed')
    words = list(struct.unpack('>209I', raw))
    normal = list(words)
    rebound = dict(refs)
    def registers(index, mapping):
        w = normal[index]; op = w >> 26
        shifts = (21,16,11) if op == 0 else (16,) if op == 15 or (op == 17 and w >> 21 & 31 in (0,4)) else (21,) if op in (49,53,57,61) else (21,16) if op in (1,4,5,9,12,13,20,21,32,33,35,36,37,40,41,43) else ()
        for shift in shifts:
            reg = w >> shift & 31
            if reg in mapping: normal[index] = (normal[index] & ~(31 << shift)) | (mapping[reg] << shift)
    # Complete S5/S6 value lifetimes, excluding their unchanged save/restore slots.
    for i in range(12,197): registers(i, {21:22,22:21})
    # Move the independent count-address LUI ahead of the viewer path, and
    # postpone the two register-only loop updates until after its six stores.
    order = list(range(142)) + [193] + list(range(142,154)) + [155,156,157] + list(range(159,190)) + [154,158,190,191,192] + list(range(194,209))
    if sorted(order) != list(range(209)): raise ValueError('Record state schedule is not a permutation')
    prior=list(normal); previous=dict(rebound)
    for dest, origin in enumerate(order):
        normal[dest]=prior[origin];rebound.pop(dest*4,None)
        if origin*4 in previous: rebound[dest*4]=previous[origin*4]
    # Closed viewer counter/offset lifetimes and the final byte-source temporary.
    for i in range(149,194): registers(i, {4:3,5:4})
    for i in (185,187): registers(i, {3:24})
    for i in (188,191): registers(i, {24:25})
    # Equality operands and the commutative view-pointer addition.
    for i in (39,43,81,85,157):
        w=normal[i]
        if not (w>>26==5 or (w>>26==0 and w&63==33)): raise ValueError('Record state commutative operation changed')
        normal[i]=(w & ~(0x3FF<<16)) | ((w>>21&31)<<16) | ((w>>16&31)<<21)
    return struct.pack('>209I', *normal), rebound


def guard_rows(raw, refs):
    normal, rebound = normalize(raw, refs)
    spec = lambda rows: ';'.join(kind+':'+name for kind,name in rows) or '-'
    rows = []
    for i,(a,b) in enumerate(zip(struct.unpack('>209I',raw),struct.unpack('>209I',normal))):
        before,after = refs.get(i*4,[]),rebound.get(i*4,[])
        if a==b and before==after: continue
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(before),spec(after),
            'Normalize closed record-state roles and independent register schedule','','','false'])
    if len(rows)!=60: raise ValueError('Record state guard scope changed')
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA or not before.endswith(b'\n'):
        raise ValueError('Record-state inherited guard history changed')
    stream = io.StringIO(newline='')
    csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs))
    return before+stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the record-state predecessor before installation')
        names = [SOURCE, OBJECT, CALLER_SOURCE, CALLER_OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/CDE80.s', 'conker/asm/156160.s', 'conker/src/game/generated_156160.c', 'conker/asm/nonmatchings/init_EB00/func_1000FC18.s', 'conker/src/init_EB00.c', 'conker/src/init_B1B0.c', 'conker/symbol_addrs.us.txt',
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
    allowed = {SOURCE, OBJECT, CALLER_SOURCE, CALLER_OBJECT, ELF, GUARDS}
    for name, digest in hashes.items():
        if sha((folder/name).read_bytes()) != digest or (name not in allowed and sha((root/name).read_bytes()) != digest):
            raise ValueError('Record-state frozen input changed: '+name)
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
        raise ValueError('Record-state linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 836:
        raise ValueError('Record-state predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 836)
    wanted[at:at+836] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('Record-state predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 836)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal record-state whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 836 if n == FUNCTION else f[2], *f[3:]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Record-state named definitions changed')
    return sum(a != b for a, b in zip(before, actual))


def make_shadow(root, out, proposal, guards, wanted, compact, caller=False):
    shadow = out/('caller-make-shadow' if caller else 'make-shadow')
    source_path = CALLER_SOURCE if caller else SOURCE
    conker = root/'conker'
    target = shadow/('src/game_45B80.c.o' if caller else 'src/game/generated_CDE80.c.o')
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/('caller-Make-plan.txt' if caller else 'actual-Make-plan.txt')).write_text(plan.stdout+plan.stderr)
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
        allowed_diagnostics = diagnostic_rows((out/'qualified-caller-diagnostics.txt').read_text()) if caller and args[0] == '../ido/ido5.3_recomp/cc' else Counter()
        if result.returncode or diagnostic_rows(result.stderr) != allowed_diagnostics or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != (3 if caller else 5) or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Record-state actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Record-state actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/('caller-Make-commands.json' if caller else 'actual-Make-commands.json')).write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)


def owner_pools(before, after):
    if alloc_pools(before) != alloc_pools(after):
        raise ValueError('Record state owner pools or register metadata changed')
    return '0x00000000'


def qualify_caller(root, out, installed):
    from tools import pad_c_object
    before = (out/'frozen'/CALLER_SOURCE).read_text()
    anchor = '/* Frame-coordinator interfaces recovered from their integer call sites. */'
    after = before.replace(anchor, anchor+'\nvoid func_150A09D0(s32);', 1)
    if before == after or (root/CALLER_SOURCE).read_text() != (after if installed else before):
        raise ValueError('Record-state caller declaration changed')
    old, od = compile_owner(root, out, before, 'before-caller')
    new, nd = compile_owner(root, out, after, 'qualified-caller')
    functions = same_functions(old, new)
    if alloc_pools(old) != alloc_pools(new) or diagnostic_rows(od) != diagnostic_rows(nd) or sum(diagnostic_rows(nd).values()) != 3:
        raise ValueError('Record-state caller code, pools or inherited diagnostics changed')
    objects=[]
    for label, obj in (('before-caller',old),('qualified-caller',new)):
        assembly=pad_c_object.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt','game_45B80',word_patches_path=out/'predecessor-guards.csv')
        p=out/(label+'-padded.s');p.write_text(assembly);dest=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(dest),str(p)],cwd=root/'conker',check=True,capture_output=True)
        objects.append(dest)
    if not(objects[0].read_bytes()==objects[1].read_bytes()==(out/'frozen'/CALLER_OBJECT).read_bytes()==(root/CALLER_OBJECT).read_bytes()):
        raise ValueError('Record-state complete padded caller object changed')
    proposal=out/'proposed-caller.c';proposal.write_text(after)
    make=make_shadow(root,out,proposal,out/'predecessor-guards.csv',objects[1],new,caller=True)
    return dict(functions=functions,raw_code_and_pools_fixed=True,padded_whole_object_fixed=True,inherited_diagnostics=3,new_diagnostics=0,actual_Make=make)


def prepare(root=ROOT):
    root = Path(root).resolve()
    out = root/BUILD
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(root, out)
    before, after, installed = source_states((root/SOURCE).read_text())
    if before != (out/'frozen'/SOURCE).read_text():
        raise ValueError('Record-state predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Record-state owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    owner_pools(old,new)
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+836]
    if struct.pack('>209I', *bound_blob(normal, normal_refs, {name: (0x10026800 if name == '__ull_rshift' else int(name.split('_')[1], 16)) for rows in normal_refs.values() for _, name in rows})) != truth:
        raise ValueError('Record-state normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    caller=qualify_caller(root,out,installed)
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('Record-state live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 28 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('Record-state production/strict padded code or pools differ')
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    start, _, _, jump_labels = pad_generated_object.parse_retail_slice(root/'conker/asm/CDE80.s')
    labels = {name: (address-start, 0, 16, 0, 1) for address, names in jump_labels.items() for name in names}
    if set(generated_names)-set(strict_names) != set(labels) or generated_names != {**strict_names, **labels}:
        raise ValueError('Record-state preserved case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Record-state padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('Record-state live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('Record-state live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Record-state linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Record-state protected data changed')
    report = dict(source_installed=installed, frozen_inputs=len(frozen), words=209, frame=64, guards=60, raw_CPR1_added_bits="0x00000000", preserved_labels=len(labels),
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, caller=caller, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
