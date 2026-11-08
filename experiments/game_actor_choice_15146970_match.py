"""Actor effect choice recovery and fail-closed, complete-owner/image gates."""
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
BUILD = 'conker/build/game-actor-choice-15146970-match'
SOURCE = 'conker/src/game/generated_173D40.c'
OBJECT = 'conker/build/src/game/generated_173D40.c.o'
OWNER, FUNCTION = 'generated_173D40', 'func_15146970'
ENTRY, ROM, WORDS, FRAME = 0x15146970, 0x173E20, 74, 48
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = '2050d53ddcc1b2fa2d1cfba360db22a2abba2bb51a68e06c7d35482693d8efda'
GUARD_SHA = '12d95d0d56d691f1c6f2d855bf5d00b0935a8ec9dd09cb7cbf78d827c63421cf'
RAW_SHA = '33a60e3269401a1a71955da67358facfaa2a268a73ea6c22ed0a55ec7652b0bf'
METADATA_GROUPS = ((2740844, ('D_800A56D0', 'D_80096214'), (1, 0)),
                   (2816700, ('func_151A0F28', 'D_8009D7C0'), (1, 0)))
BINDINGS = {28: [('R_MIPS_HI16', '.rodata')], 36: [('R_MIPS_LO16', '.rodata')], 88: [('R_MIPS_HI16', 'D_800BE9F0')], 92: [('R_MIPS_LO16', 'D_800BE9F0')], 108: [('R_MIPS_26', 'func_151420F8')], 168: [('R_MIPS_HI16', '.data')], 172: [('R_MIPS_LO16', '.data')], 180: [('R_MIPS_HI16', 'D_800CC2D0')], 184: [('R_MIPS_LO16', 'D_800CC2D0')], 244: [('R_MIPS_26', 'func_150A2AEC')]}
STUB = 's32 func_15146970() {\n    return 0;\n}'
SELECTED = '''/* Select the actor effect, consulting state or the five-ID list when needed. */
s32 func_15146970(s32 kind, u8 *actor) {
    extern s32 D_800BE9F0;
    extern u8 D_800CC2D0[];
    extern s32 func_151420F8(u8 *);
    extern s32 func_150A2AEC(s32, s32, s32 *);
    switch (kind) {
        case 8: return 16;
        case 7: return 15;
        case 5: return 5;
        case 2: return 2;
        case 0: return 0;
        case 1:
            if (D_800BE9F0 == 4) {
                if (func_151420F8(actor)) {
                    return 6;
                } else {
                    return 3;
                }
            } else {
                return 1;
            }
        case 4: return 4;
        case 3: return 3;
        case 6: {
            s32 choices[5] = {0x401D, 0x401E, 0x401F, 0x4020, 0x4021};
            if (func_150A2AEC((s32)((u32)actor - (u32)D_800CC2D0) / 0x32C,
                              5, choices) == -1) {
                return -1;
            } else {
                return 6;
            }
        }
    }
    return -1;
}'''
sha = lambda b: hashlib.sha256(b).hexdigest()


def source_states(live):
    if live.count(STUB) == 1:
        return live, live.replace(STUB, SELECTED, 1), False
    if live.count(SELECTED) != 1:
        raise ValueError('Actor-choice source changed')
    return live.replace(SELECTED, STUB, 1), live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 296 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('Actor-choice raw words or bindings changed')
    # Instructions are already direct. Bind the recovered initializer pool
    # to its existing retail owner; the switch uses the normal rodata anchor.
    normalized = {p: [(kind, 'D_800A56D0' if name == '.data' else
                     'jtbl_800A56E4_game' if name == '.rodata' else name)
                     for kind, name in rows] for p, rows in refs.items()}
    return raw, normalized


def guard_rows(raw, refs):
    _, normal_refs = normalize(raw, refs)
    rows = []
    for offset in (168, 172):
        word = struct.unpack_from('>I', raw, offset)[0]
        old = ';'.join(kind+':'+name for kind, name in refs[offset])
        new = ';'.join(kind+':'+name for kind, name in normal_refs[offset])
        rows.append([OWNER, FUNCTION, '0x%03X' % offset, '0x%08X' % word,
                     '0x%08X' % word, old, new,
                     'Bind recovered five-ID initializer to preserved retail data', '', '', 'false'])
    return rows


MAKE = 'conker/Makefile'
RODATA = 'jtbl_800A56E4_game'
MAKE_ANCHOR = '$(BUILD_DIR)/$(SRC_DIR)/game/generated_133190.c.o: RETAIL_RODATA_SYMBOL := D_800A2420'
MAKE_BINDING = '$(BUILD_DIR)/$(SRC_DIR)/game/generated_173D40.c.o: RETAIL_RODATA_SYMBOL := jtbl_800A56E4_game'


def recovered_makefile(before):
    if before.count(MAKE_ANCHOR) != 1 or MAKE_BINDING in before:
        raise ValueError('Actor-choice Makefile predecessor changed')
    return before.replace(MAKE_ANCHOR, MAKE_ANCHOR+'\n# Actor-choice switch retains its original nine-entry pool.\n'+MAKE_BINDING)


def check_pools(old, new, root, out):
    a, b = alloc_pools(old), alloc_pools(new)
    if set(b) != set(a) | {'.rodata', '.data'} or any(a[n] != b[n] for n in a):
        raise ValueError('Actor-choice neighboring allocatable pools changed')
    data, table = b['.data'], b['.rodata']
    if data[4] != struct.pack('>5i', 0x401D, 0x401E, 0x401F, 0x4020, 0x4021)+bytes(12) or data[5]:
        raise ValueError('Actor-choice initializer pool changed')
    offsets = (80,88,72,156,148,64,164,56,48)
    if table[4] != bytes(48) or table[5] != tuple((i*4,2,('text',FUNCTION,v)) for i,v in enumerate(offsets)):
        raise ValueError('Actor-choice nine-entry switch pool changed')
    before = (out/'frozen'/ELF).read_bytes()
    at = elf_slot_offset(before, 0x800A56D0, 20)
    if before[at:at+20] != data[4][:20]:
        raise ValueError('Actor-choice preserved initializer differs')
    at = elf_slot_offset(before, 0x800A56E4, 36)
    if before[at:at+36] != struct.pack('>9I', *[ENTRY+x for x in offsets]):
        raise ValueError('Actor-choice preserved switch pool differs')
    return dict(initializer_words=5, switch_words=9, alignment_bytes_per_pool=12, neighboring_pools_fixed=True)


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA:
        raise ValueError('Actor-choice inherited guard prefix changed')
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerows(guard_rows(raw, refs))
    return before + stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the actor-choice predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/173D40.s', 'conker/asm/nonmatchings/game_16EE20/func_15141A7C.s',
                 'conker/asm/CDE80.s', 'conker/src/game_16EE20.c', 'conker/symbol_addrs.us.txt',
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
    allowed = {SOURCE, OBJECT, ELF, GUARDS, MAKE}
    for name, digest in hashes.items():
        if sha((folder/name).read_bytes()) != digest or (name not in allowed and sha((root/name).read_bytes()) != digest):
            raise ValueError('Actor-choice frozen input changed: '+name)
    return hashes


def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards, rodata_symbol=RODATA)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/173D40.s', word_patches_path=guards, filename=OWNER, rodata_symbol=RODATA)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination


def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Actor-choice linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 296:
        raise ValueError('Actor-choice predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 296)
    wanted[at:at+296] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('Actor-choice predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 296)
    from tools.experiments import game_actor_height_effect_match as metadata
    with patch.object(metadata, 'METADATA_GROUPS', METADATA_GROUPS):
        metadata.reorder_metadata(before, wanted)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal actor-choice whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 296 if n == FUNCTION else f[2], *f[3:]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Actor-choice named definitions changed')
    return sum(a != b for a, b in zip(before, actual))


def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    conker = root/'conker'
    target = shadow/'src/game/generated_173D40.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-f', (out/'proposed-Makefile').relative_to(conker).as_posix(), '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor-choice Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == SOURCE.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor-choice Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        if result.returncode or result.stderr or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 3 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Actor-choice actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Actor-choice actual Make padded owner differs')
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
        raise ValueError('Actor-choice predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Actor-choice owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    pools = check_pools(old, new, root, out)
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+296]
    if struct.pack('>74I', *bound_blob(normal, normal_refs, dict(jtbl_800A56E4_game=0x800A56E4, D_800BE9F0=0x800BE9F0, func_151420F8=0x151420F8, D_800A56D0=0x800A56D0, D_800CC2D0=0x800CC2D0, func_150A2AEC=0x150A2AEC))) != truth:
        raise ValueError('Actor-choice normalized body differs')
    before_make = (out/'frozen'/MAKE).read_text()
    after_make = recovered_makefile(before_make)
    if (root/MAKE).read_text() != (after_make if installed else before_make):
        raise ValueError('Actor-choice live Makefile changed')
    (out/'proposed-Makefile').write_text(after_make)
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('Actor-choice live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 13 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('Actor-choice production/strict padded code or pools differ')
    # The assembly-slice padder retains nine original global case labels.
    # The strict layout padder has no such labels; account for each definition
    # explicitly instead of comparing serialized symbol indices as bindings.
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    offsets = (80, 88, 72, 156, 148, 64, 164, 56, 48)
    labels = {'.L%08X_game_data' % (ENTRY+x): (ENTRY+x-0x15146890, 0, 16, 0, 1) for x in offsets}
    if generated_names != {**strict_names, **labels}:
        raise ValueError('Actor-choice original case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Actor-choice padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('Actor-choice live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('Actor-choice live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Actor-choice linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Actor-choice protected data changed')
    report = dict(source_installed=installed, frozen_inputs=len(frozen), words=74, frame=48, guards=2, pools=pools,
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
