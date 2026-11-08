"""View record list updater recovery and fail-closed, complete-owner/image gates."""
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
BUILD = 'conker/build/game-view-record-list-150A104C-match'
SOURCE = 'conker/src/game/generated_CDE80.c'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
OWNER, FUNCTION = 'generated_CDE80', 'func_150A104C'
ENTRY, ROM, WORDS, FRAME = 0x150A104C, 0xCE4FC, 94, 888
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = '3be4682d22779bf33a8fe268d5991efc97f06044f7f5fb69a915994ac2237ba2'
GUARD_SHA = '9a0c7123b46c9a22927ff17a9aa46b3eba0f53256d31f0c2a1b461b5dd05d3d0'
RAW_SHA = '51cbc833f40f00db183a7db6a9aa02dc3db4ce1ec15c13227dc3a4c3b649b709'
BINDINGS = {68: [('R_MIPS_HI16', 'D_8009F5AC')], 104: [('R_MIPS_LO16', 'D_8009F5AC')], 184: [('R_MIPS_26', 'func_150A1DA0')]}
STUB = 's32 func_150A104C() {\n    return 0;\n}'
DECLARATIONS = 'extern f32 D_8009F5AC;\ns32 func_150A1DA0(struct127 *, s32, s32);'
SELECTED = '/* Apply accepted class-1 records to the view flag and height. */\nvoid func_150A104C(struct108 *view, GeneratedCDE80Record **records, s32 count) {\n    struct127 query;\n    GeneratedCDE80Record *record;\n    query.x_position = view->unk2F8;\n    query.y_position = view->unk2FC;\n    query.z_position = view->unk300;\n    query.unk180 = query.y_position;\n    query.old_x_position = view->unk304;\n    query.old_y_position = view->unk308;\n    query.old_z_position = view->unk30C;\n    view->unk364 = D_8009F5AC;\n    view->unk84 &= ~0x40000;\n    for (; count != 0; count--, records++) {\n        record = *records;\n        if (record != 0) {\n            if (func_150A1DA0(&query, (s32)record, 0) == 0) {\n                record = *records;\n                if ((record->flags >> 2) == 1) {\n                    switch (record->field17) {\n                    case 2:\n                        view->unk364 = record->heightOffset + record->origin1;\n                        break;\n                    case 0:\n                        view->unk84 |= 0x40000;\n                        break;\n                    case 6:\n                        view->unk84 &= ~0x40000;\n                        break;\n                    }\n                }\n            }\n        }\n    }\n}'
sha = lambda b: hashlib.sha256(b).hexdigest()
OLD_RECORD_PAD = '    u8 pad6[0xF];'
NEW_RECORD_PAD = '    u8 pad6[2];\n    s16 heightOffset;\n    u8 padA[0xB];'


def source_states(live):
    anchor = 'extern f32 D_8009F5A4;'
    if live.count(STUB) == 1 and DECLARATIONS not in live:
        if live.count(OLD_RECORD_PAD) != 1: raise ValueError('Unknown record layout predecessor')
        return live, live.replace(STUB, SELECTED, 1).replace(anchor, anchor+'\n'+DECLARATIONS, 1).replace(OLD_RECORD_PAD, NEW_RECORD_PAD, 1), False
    if live.count(SELECTED) != 1 or live.count(anchor+'\n'+DECLARATIONS) != 1 or live.count(NEW_RECORD_PAD) != 1:
        raise ValueError('View-record-list source/declarations changed')
    return live.replace(SELECTED, STUB, 1).replace(anchor+'\n'+DECLARATIONS, anchor, 1).replace(NEW_RECORD_PAD, OLD_RECORD_PAD, 1), live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 376 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('View-record-list raw words or bindings changed')
    words = list(struct.unpack('>94I', raw))
    result = list(words)
    cycle = {19:20, 20:21, 21:22, 22:23, 23:30, 30:19}
    stores = (1, 11, 12, 13, 14, 15)
    for i, w in enumerate(words):
        if i in stores:
            reg = w >> 16 & 31
            if w >> 26 != 43 or w >> 21 & 31 != 29 or reg not in cycle:
                raise ValueError('View-record-list saved-register lifetime changed')
            new = cycle[reg]
            result[i] = (w & 0xFFE00000) | (new << 16) | (0x18+4*(8 if new == 30 else new-16))
            continue
        # These are body roles. The fixed callee-saved restore slots remain
        # untouched; the six stores above are one closed instruction permutation.
        op = w >> 26
        shifts = (21,16,11) if op == 0 else (21,16) if op in (9,13,20,21) else (16,) if op == 15 else ()
        for shift in shifts:
            reg = w >> shift & 31
            if reg in cycle: result[i] = (result[i] & ~(31 << shift)) | (cycle[reg] << shift)
    if sorted(words[i] for i in stores) != sorted(result[i] for i in stores) or sum(a!=b for a,b in zip(words,result)) != 20:
        raise ValueError('View-record-list role/store cycle is not closed')
    return struct.pack('>94I', *result), dict(refs)


def guard_rows(raw, refs):
    normal, rebound = normalize(raw, refs)
    rows = []
    for i, (a,b) in enumerate(zip(struct.unpack('>94I',raw),struct.unpack('>94I',normal))):
        if a == b: continue
        if i*4 in refs or i*4 in rebound: raise ValueError('Unexpected binding in allocation cycle')
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}','-','-',
            'Normalize closed view-record updater saved roles and save schedule','','','false'])
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA or not before.endswith(b'\n'):
        raise ValueError('View-record-list inherited guard history changed')
    stream = io.StringIO(newline='')
    csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs))
    return before+stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the view-record-list predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/CDE80.s', 'conker/symbol_addrs.us.txt',
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
            raise ValueError('View-record-list frozen input changed: '+name)
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
        raise ValueError('View-record-list linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 376:
        raise ValueError('View-record-list predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 376)
    wanted[at:at+376] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('View-record-list predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 376)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal view-record-list whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 376 if n == FUNCTION else f[2], *f[3:]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('View-record-list named definitions changed')
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
            raise ValueError('Unexpected view-record-list Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == SOURCE.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown view-record-list Make redirect')
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
        raise ValueError('View-record-list actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('View-record-list actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)


def prepare(root=ROOT):
    root = Path(root).resolve()
    out = root/BUILD
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(root, out)
    before, after, installed = source_states((root/SOURCE).read_text())
    if before != (out/'frozen'/SOURCE).read_text():
        raise ValueError('View-record-list predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('View-record-list owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    if alloc_pools(old) != alloc_pools(new):
        raise ValueError('View-record-list raw owner pools changed')
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+376]
    if struct.pack('>94I', *bound_blob(normal, normal_refs, {name: (0x10026800 if name == '__ull_rshift' else int(name.split('_')[1], 16)) for rows in normal_refs.values() for _, name in rows})) != truth:
        raise ValueError('View-record-list normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('View-record-list live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 28 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('View-record-list production/strict padded code or pools differ')
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    start, _, _, jump_labels = pad_generated_object.parse_retail_slice(root/'conker/asm/CDE80.s')
    labels = {name: (address-start, 0, 16, 0, 1) for address, names in jump_labels.items() for name in names}
    if set(generated_names)-set(strict_names) != set(labels) or generated_names != {**strict_names, **labels}:
        raise ValueError('View-record-list preserved case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('View-record-list padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('View-record-list live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('View-record-list live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('View-record-list linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('View-record-list protected data changed')
    report = dict(source_installed=installed, frozen_inputs=len(frozen), words=94, frame=888, guards=20, raw_metadata_unchanged=True, preserved_labels=len(labels),
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
