"""Record occupancy query recovery and fail-closed, complete-owner/image gates."""
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
from unittest.mock import patch

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
BUILD = 'conker/build/game-record-occupancy-150A29C8-match'
SOURCE = 'conker/src/game/generated_CDE80.c'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
OWNER, FUNCTION = 'generated_CDE80', 'func_150A29C8'
ENTRY, ROM, WORDS, FRAME = 0x150A29C8, 0xCFE78, 73, 32
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = 'a493762c70c8084a6237b210df7caa8b9f5e0470dab737655bd4a08c31835d8d'
GUARD_SHA = '6792fe9767ba771d5a3c0a92abe798df38a6b4970cda689f4d93b84a7ad26b95'
RAW_SHA = '29c4ce4f891efd3b1fe016ddf35f85aeabf90bfd8b6c545a71e3b3feaded6e48'
METADATA_GROUPS = ((2993356, ('D_800DBE64', 'D_8009D2C0'), (1, 0)),)
BINDINGS = {20: [('R_MIPS_HI16', 'D_800D3094')], 24: [('R_MIPS_LO16', 'D_800D3094')], 64: [('R_MIPS_HI16', 'D_800D2340')], 72: [('R_MIPS_LO16', 'D_800D2340')], 116: [('R_MIPS_HI16', 'D_800D30F0')], 132: [('R_MIPS_LO16', 'D_800D30F0')], 120: [('R_MIPS_HI16', 'D_800D30F0')], 136: [('R_MIPS_LO16', 'D_800D30F0')], 144: [('R_MIPS_26', '__ull_rshift')], 236: [('R_MIPS_HI16', 'D_800CC2D0')], 248: [('R_MIPS_LO16', 'D_800CC2D0')], 224: [('R_MIPS_HI16', 'D_800D3098')], 228: [('R_MIPS_LO16', 'D_800D3098')], 264: [('R_MIPS_26', 'func_150A1DA0')]}
STUB = 's32 func_150A29C8() {\n    return 0;\n}'
SELECTED = '/* Query a record through the actor mask or collision provider. */\ns32 func_150A29C8(u32 actorIndex, u32 identity) {\n    extern u16 D_800D2340;\n    extern struct127 D_800CC2D0[];\n    identity &= 0xFFF;\n    if ((u32)D_800D3094 < identity) return 1;\n    if ((u32)actorIndex < 16 && (D_800D2340 & (1 << actorIndex))) {\n        if ((((u64 (*)[3])D_800D30F0)[actorIndex][identity >> 6] >>\n              (identity & 0x3F)) & 1) {\n            return 0;\n        } else {\n            return 1;\n        }\n    }\n    return func_150A1DA0(&D_800CC2D0[actorIndex],\n                          (s32)&D_800D3098[identity], 1);\n}'
HEADER = 'conker/include/functions.h'
CLEANUP = 'conker/src/game_16EE20.c'
OLD_DECLARATION = 's32  func_150A29C8(u8, u16);'
NEW_DECLARATION = 's32  func_150A29C8(u32, u32);'


def interface_states(root, out):
    before = (out/'frozen'/HEADER).read_text()
    if before.count(OLD_DECLARATION) != 1:
        raise ValueError('Record-occupancy predecessor declaration changed')
    proposed = before.replace(OLD_DECLARATION, NEW_DECLARATION)
    old_source = (out/'frozen'/CLEANUP).read_text()
    cleanup = old_source
    for part in ('/* The retail checker receives complete words, not the legacy narrow ABI. */\n#define func_150A29C8 func_150A29C8_legacy_narrow_signature\n', '#undef func_150A29C8\n', 's32 func_150A29C8(s32, s32);\n'):
        if cleanup.count(part) != 1:
            raise ValueError('Record-occupancy predecessor caller workaround changed')
        cleanup = cleanup.replace(part, '', 1)
    flags = []
    for name, old, new in ((HEADER, before, proposed), (CLEANUP, old_source, cleanup)):
        live = (root/name).read_text()
        if live not in (old, new):
            raise ValueError('Record-occupancy interface changed: '+name)
        flags.append(live == new)
    if len(set(flags)) != 1:
        raise ValueError('Record-occupancy partial interface installation')
    return flags[0], {HEADER: proposed, CLEANUP: cleanup}


def dependency_scope(root, out):
    receipt = json.loads((out/'header-audit.json').read_text())
    if receipt['pending'] or receipt['owners'] != len(receipt['records']):
        raise ValueError('Record-occupancy header dependency audit incomplete')
    installed, proposals = interface_states(root, out)
    for name, digest in receipt['input_sha256'].items():
        if name in (ELF, GUARDS):
            continue  # The complete before/after image gate below owns this input.
        actual = sha((root/name).read_bytes())
        if name in proposals and installed:
            if (root/name).read_text() != proposals[name]:
                raise ValueError('Record-occupancy adopted interface differs')
        elif actual != digest:
            raise ValueError('Record-occupancy dependency input changed: '+name)
    from tools.experiments.game_record_occupancy_150a29c8_dependencies import validate
    return validate(root, out)



sha = lambda b: hashlib.sha256(b).hexdigest()


def source_states(live):
    if live.count(STUB) == 1:
        return live, live.replace(STUB, SELECTED, 1), False
    if live.count(SELECTED) != 1:
        raise ValueError('Record-occupancy source changed')
    return live.replace(SELECTED, STUB, 1), live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 292 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('Record-occupancy raw words or bindings changed')
    # Preserve the low-word alias as its own HI/LO pair. A shared-symbol
    # padded pair otherwise loses the carry when base+4 crosses signed LO16.
    result = bytearray(raw)
    struct.pack_into('>I', result, 136, struct.unpack_from('>I', raw, 136)[0] & 0xFFFF0000)
    bindings = dict(refs)
    bindings[120] = [('R_MIPS_HI16', 'D_800D30F4')]
    bindings[136] = [('R_MIPS_LO16', 'D_800D30F4')]
    return bytes(result), bindings


def guard_rows(raw, refs):
    normal, bindings = normalize(raw, refs)
    rows = []
    for offset in (120, 136):
        old = ';'.join(kind+':'+name for kind, name in refs[offset])
        new = ';'.join(kind+':'+name for kind, name in bindings[offset])
        rows.append([OWNER, FUNCTION, '0x%03X' % offset,
                     '0x%08X' % struct.unpack_from('>I', raw, offset)[0],
                     '0x%08X' % struct.unpack_from('>I', normal, offset)[0], old, new,
                     'Bind original low mask word alias with independent signed LO16 carry', '', '', 'false'])
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA:
        raise ValueError('Record-occupancy inherited guard history changed')
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerows(guard_rows(raw, refs))
    return before + stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the record-occupancy predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/CDE80.s', 'conker/asm/CD860.s', 'conker/src/game/generated_CD860.c', 'conker/symbol_addrs.us.txt',
                 'conker/undefined_syms.us.txt', 'conker/undefined_funcs.us.txt',
                 'conker/undefined_syms_auto.txt', 'conker/undefined_funcs_auto.txt']
        names += list(json.loads((out/'header-audit.json').read_text())['input_sha256'])
        names = list(dict.fromkeys(names))
        names += [p.relative_to(root).as_posix() for p in (root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in ('cc', 'cfe', 'uopt', 'ugen')]
        for name in names:
            p = folder/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n: sha((folder/n).read_bytes()) for n in names}, indent=2)+'\n')
    hashes = json.loads(receipt.read_text())
    allowed = {SOURCE, OBJECT, ELF, GUARDS, HEADER, CLEANUP}
    for name, digest in hashes.items():
        if sha((folder/name).read_bytes()) != digest or (name not in allowed and sha((root/name).read_bytes()) != digest):
            raise ValueError('Record-occupancy frozen input changed: '+name)
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
        raise ValueError('Record-occupancy linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 292:
        raise ValueError('Record-occupancy predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 292)
    wanted[at:at+292] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('Record-occupancy predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 292)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata, 'METADATA_GROUPS', METADATA_GROUPS):
        metadata.reorder_metadata(before, wanted)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal record-occupancy whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 292 if n == FUNCTION else f[2], *f[3:]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Record-occupancy named definitions changed')
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
            raise ValueError('Unexpected record-occupancy Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == SOURCE.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record-occupancy Make redirect')
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
        raise ValueError('Record-occupancy actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Record-occupancy actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)


def prepare(root=ROOT):
    root = Path(root).resolve()
    out = root/BUILD
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(root, out)
    header_installed, _ = interface_states(root, out)
    dependencies = dependency_scope(root, out)
    before, after, installed = source_states((root/SOURCE).read_text())
    if installed != header_installed:
        raise ValueError('Record-occupancy source/interface installation disagrees')
    if before != (out/'frozen'/SOURCE).read_text():
        raise ValueError('Record-occupancy predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Record-occupancy owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    if alloc_pools(old) != alloc_pools(new):
        raise ValueError('Record-occupancy raw pools changed')
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+292]
    if struct.pack('>73I', *bound_blob(normal, normal_refs, {name: (0x10026800 if name == '__ull_rshift' else int(name.split('_')[1], 16)) for rows in normal_refs.values() for _, name in rows})) != truth:
        raise ValueError('Record-occupancy normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('Record-occupancy live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 28 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('Record-occupancy production/strict padded code or pools differ')
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    start, _, _, jump_labels = pad_generated_object.parse_retail_slice(root/'conker/asm/CDE80.s')
    labels = {name: (address-start, 0, 16, 0, 1) for address, names in jump_labels.items() for name in names}
    if set(generated_names)-set(strict_names) != set(labels) or generated_names != {**strict_names, **labels}:
        raise ValueError('Record-occupancy preserved case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Record-occupancy padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('Record-occupancy live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('Record-occupancy live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Record-occupancy linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Record-occupancy protected data changed')
    report = dict(source_installed=installed, header_dependencies=dependencies, frozen_inputs=len(frozen), words=73, frame=32, guards=2, raw_metadata_unchanged=True, preserved_labels=len(labels),
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
