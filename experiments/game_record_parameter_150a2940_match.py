"""Record parameter updater recovery and fail-closed, complete-owner/image gates."""
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
BUILD = 'conker/build/game-record-parameter-150A2940-match'
SOURCE = 'conker/src/game/generated_CDE80.c'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
OWNER, FUNCTION = 'generated_CDE80', 'func_150A2940'
ENTRY, ROM, WORDS, FRAME = 0x150A2940, 0xCFDF0, 34, 0
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = '42e11f4c8d50d9f6bff2b207c2fb38f3eb9bb087e0763578efc840eb58de5c3e'
GUARD_SHA = 'e1220f138f75b7f07006759db2a57556f3d2a3e50806e199ce84e40e487a5e7a'
RAW_SHA = '823a558b4f10d9d5ecd9c2aa4a60f86717d73c2f2c0377d7cfd26167f0db9e7d'
BINDINGS = {0: [('R_MIPS_HI16', 'D_800D3094')], 4: [('R_MIPS_LO16', 'D_800D3094')], 36: [('R_MIPS_HI16', 'D_800D3098')], 48: [('R_MIPS_LO16', 'D_800D3098')], 84: [('R_MIPS_HI16', 'D_800D3098')], 92: [('R_MIPS_LO16', 'D_800D3098')]}
STUB = 's32 func_150A2940() {\n    return 0;\n}'
SELECTED = '/* Update optional word/byte parameters and clear field 0x1C. */\nvoid func_150A2940(u32 identity, s32 value, s32 kind) {\n    identity &= 0xFFF;\n    if (identity < (u32)D_800D3094) {\n        if (value != -1) D_800D3098[identity].field18 = value;\n        if (kind != -1) D_800D3098[identity].field17 = kind;\n        D_800D3098[identity].field1C = 0;\n    }\n}'
LAYOUT = 'conker/retail_layout.us.txt'
AUTO = 'conker/undefined_funcs_auto.txt'
SYMBOLS = 'conker/symbol_addrs.us.txt'
NEIGHBOR = 'func_150A29C8'


def recovered_metadata(out):
    before = (out/'frozen'/LAYOUT).read_text()
    old = 'game,generated_CDE80,func_150A2940,0x150A2940,0x150A2AEC'
    new = 'game,generated_CDE80,func_150A2940,0x150A2940,0x150A29C8\ngame,generated_CDE80,func_150A29C8,0x150A29C8,0x150A2AEC'
    if before.count(old) != 1 or NEIGHBOR in before:
        raise ValueError('Record-parameter predecessor layout changed')
    layout = before.replace(old, new)
    before = (out/'frozen'/AUTO).read_text()
    rule = 'func_150A29C8 = 0x150A29C8;\n'
    if before.count(rule) != 1:
        raise ValueError('Record-parameter predecessor absolute rule changed')
    auto = before.replace(rule, '')
    before = (out/'frozen'/SYMBOLS).read_text()
    if NEIGHBOR in before:
        raise ValueError('Record-parameter predecessor symbol declarations changed')
    declared = before+'func_150A29C8 = 0x150A29C8; // type:func defined:true\n'
    for name, text in (('qualified-symbol-addrs.us.txt', declared), ('qualified-layout.us.txt', layout), ('qualified-undefined-funcs.txt', auto)):
        (out/name).write_text(text)
    return {LAYOUT: layout, AUTO: auto, SYMBOLS: declared}


def metadata_state(root, out):
    changes = recovered_metadata(out)
    states = []
    for name, proposed in changes.items():
        live = (root/name).read_text()
        before = (out/'frozen'/name).read_text()
        if live not in (before, proposed):
            raise ValueError('Record-parameter metadata changed: '+name)
        states.append(live == proposed)
    if len(set(states)) != 1:
        raise ValueError('Partial record-parameter metadata installation')
    return states[0]


def progress_scope(before, after):
    old = list(csv.DictReader(io.StringIO(before)))
    new = list(csv.DictReader(io.StringIO(after)))
    indices = [i for i, row in enumerate(old) if row['function'] == FUNCTION]
    if len(indices) != 1 or any(row['function'] == NEIGHBOR for row in old):
        raise ValueError('Record-parameter predecessor progress changed')
    index = indices[0]
    wanted = [dict(row) for row in old]
    wanted[index]['length'] = '136'
    row = dict(wanted[index]);row.update(function=NEIGHBOR,offset=str(ENTRY+136),length='292')
    wanted.insert(index+1,row)
    if wanted != new:
        raise ValueError('Record-parameter progress changed outside recovered boundary')


sha = lambda b: hashlib.sha256(b).hexdigest()


def source_states(live):
    if live.count(STUB) == 1:
        return live, live.replace(STUB, SELECTED, 1), False
    if live.count(SELECTED) != 1:
        raise ValueError('Record-parameter source changed')
    return live.replace(SELECTED, STUB, 1), live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 136 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('Record-parameter raw words or bindings changed')
    # Exchange only an independent address addiu and register-only subu.
    # Both remain before the pointer load; preserve its memory/fault order.
    result = bytearray(raw)
    result[44:48], result[48:52] = raw[48:52], raw[44:48]
    bindings = dict(refs)
    bindings[44] = bindings.pop(48)
    return bytes(result), bindings


def guard_rows(raw, refs):
    normal, bindings = normalize(raw, refs)
    rows = []
    for offset in (44, 48):
        old = ';'.join(kind+':'+name for kind, name in refs.get(offset, []))
        new = ';'.join(kind+':'+name for kind, name in bindings.get(offset, []))
        rows.append([OWNER, FUNCTION, '0x%03X' % offset,
                     '0x%08X' % struct.unpack_from('>I', raw, offset)[0],
                     '0x%08X' % struct.unpack_from('>I', normal, offset)[0], old or '-', new or '-',
                     'Normalize independent record address setup schedule', '', '', 'false'])
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA:
        raise ValueError('Record-parameter inherited guard prefix changed')
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerows(guard_rows(raw, refs))
    return before + stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the record-parameter predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/CDE80.s', 'conker/asm/CD860.s', 'conker/src/game/generated_CD860.c', 'conker/symbol_addrs.us.txt',
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
    allowed = {SOURCE, OBJECT, ELF, GUARDS, LAYOUT, AUTO, SYMBOLS, 'conker/progress.csv'}
    for name, digest in hashes.items():
        if sha((folder/name).read_bytes()) != digest or (name not in allowed and sha((root/name).read_bytes()) != digest):
            raise ValueError('Record-parameter frozen input changed: '+name)
    return hashes


def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, out/'qualified-layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/CDE80.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination


def link(root, out, owner, label, recovered=False):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Record-parameter linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', str((out/'qualified-undefined-funcs.txt' if recovered else out/'frozen'/AUTO).relative_to(root/'conker')) if n == 'undefined_funcs_auto.txt' else n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 136:
        raise ValueError('Record-parameter predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 136)
    wanted[at:at+136] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('Record-parameter predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 136)
    neighbor = [(p, f) for p, n, f, _ in symbol_rows(before) if n == NEIGHBOR]
    if len(neighbor) != 1 or neighbor[0][1][1:] != (ENTRY+136, 12, 18, 0, 65521):
        raise ValueError('Record-parameter predecessor absolute neighbor changed')
    struct.pack_into('>H', wanted, neighbor[0][0]+14, 5)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal record-parameter whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 136 if n == FUNCTION else f[2], f[3], f[4], 5 if n == NEIGHBOR else f[5]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Record-parameter named definitions changed')
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
            raise ValueError('Unexpected record-parameter Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == SOURCE.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record-parameter Make redirect')
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
        raise ValueError('Record-parameter actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Record-parameter actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)


def prepare(root=ROOT):
    root = Path(root).resolve()
    out = root/BUILD
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(root, out)
    metadata_installed = metadata_state(root, out)
    before, after, source_installed = source_states((root/SOURCE).read_text())
    installed = source_installed and metadata_installed
    if metadata_installed and not source_installed:
        raise ValueError('Record-parameter metadata installed without source')
    if before != (out/'frozen'/SOURCE).read_text():
        raise ValueError('Record-parameter predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Record-parameter owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    if alloc_pools(old) != alloc_pools(new):
        raise ValueError('Record-parameter raw owner pools changed')
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+136]
    if struct.pack('>34I', *bound_blob(normal, normal_refs, {name: int(name.split('_')[1], 16) for rows in normal_refs.values() for _, name in rows})) != truth:
        raise ValueError('Record-parameter normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if source_installed else old_guards).read_bytes():
        raise ValueError('Record-parameter live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 28 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('Record-parameter production/strict padded code or pools differ')
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    start, _, _, jump_labels = pad_generated_object.parse_retail_slice(root/'conker/asm/CDE80.s')
    labels = {name: (address-start, 0, 16, 0, 1) for address, names in jump_labels.items() for name in names}
    if set(generated_names)-set(strict_names) != set(labels) or generated_names != {**strict_names, **labels}:
        raise ValueError('Record-parameter preserved case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Record-parameter padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if source_installed else old_padded).read_bytes():
        raise ValueError('Record-parameter live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image', recovered=True)
    intermediate = link(root, out, new_padded, 'pre-census-image') if source_installed and not metadata_installed else None
    current = new_image if installed else intermediate if source_installed else old_image
    if (root/ELF).read_bytes() != current.read_bytes():
        raise ValueError('Record-parameter live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if (set(b)-set(a) != {NEIGHBOR} or set(a)-set(b) or
        {n:v for n,v in bb.items() if n != NEIGHBOR} != aa or
        [n for n in a if a[n] != b[n]] != [FUNCTION] or
        b[NEIGHBOR] != a[FUNCTION][34:]):
        raise ValueError('Record-parameter linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Record-parameter protected data changed')
    if metadata_installed:
        progress_scope((out/'frozen/conker/progress.csv').read_text(), (root/'conker/progress.csv').read_text())
    elif (root/'conker/progress.csv').read_bytes() != (out/'frozen/conker/progress.csv').read_bytes():
        raise ValueError('Record-parameter pre-census progress changed')
    report = dict(source_installed=installed, metadata_installed=metadata_installed, frozen_inputs=len(frozen), words=34, frame=0, guards=2, raw_metadata_unchanged=True, preserved_labels=len(labels),
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(b), recovered_function_boundary=NEIGHBOR,
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
