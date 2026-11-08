"""Packed-triangle facing recovery and fail-closed, complete-owner/image gates."""
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
BUILD = 'conker/build/game-triangle-facing-1510E670-match'
SOURCE = 'conker/src/game/generated_13BB20.c'
OBJECT = 'conker/build/src/game/generated_13BB20.c.o'
OWNER, FUNCTION = 'generated_13BB20', 'func_1510E670'
ENTRY, ROM, WORDS, FRAME = 0x1510E670, 0x13BB20, 77, 88
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = '85c87d6a7517a03de99e75e3ca4d66973af398e03c2ddc9947d4f69cc21a6402'
GUARD_SHA = 'aee1f39799c5248b3f94790093179df1c51f8232e5453ad36af313644000f152'
RAW_SHA = '2c666272900b9d24ade495e477190530d66ddd2fecc4931be539254671c08819'
BINDINGS = {8: [('R_MIPS_HI16', 'D_800D3300')], 12: [('R_MIPS_LO16', 'D_800D3300')],
            240: [('R_MIPS_26', 'func_150AD8B0')]}
STUB = 's32 func_1510E670() {\n    return 0;\n}'
SELECTED = '''/* Test the Y orientation of a triangle addressed by packed vertex offsets. */
s32 func_1510E670(s32 index) {
    extern s32 D_800D3300[];
    s16 *first, *second, *third;
    u32 *offsets;
    u8 *vertices;
    f32 edgeA[3], edgeB[3], normal[3];
    struct TriangleEntry1510E670 {
        s32 unused;
        u32 *offsets;
        u8 *vertices;
        s32 unusedC;
    };
    struct TriangleEntry1510E670 *entry = (struct TriangleEntry1510E670 *)&D_800D3300 + index;

    offsets = entry->offsets;
    vertices = entry->vertices;
    if (offsets != NULL) {
        first = (s16 *)(vertices + offsets[0]);
        second = (s16 *)(vertices + offsets[1]);
        third = (s16 *)(vertices + offsets[2]);
        edgeA[0] = second[0] - first[0];
        edgeA[1] = second[1] - first[1];
        edgeA[2] = second[2] - first[2];
        edgeB[0] = third[0] - first[0];
        edgeB[1] = third[1] - first[1];
        edgeB[2] = third[2] - first[2];
        func_150AD8B0(edgeA, edgeB, normal);
        if (normal[1] < 0.0f) {
            return 0;
        } else {
            return 1;
        }
    }
    return 0;
}'''
DECLARATION = 'void func_150AD8B0(f32 *, f32 *, f32 *);'
MARKER = 's32 func_1510E388(void *, void *, f32 *, f32 *);'
sha = lambda b: hashlib.sha256(b).hexdigest()


def source_states(live):
    declaration = MARKER + '\n' + DECLARATION
    if live.count(STUB) == 1 and DECLARATION not in live:
        if live.count('extern s32 D_800D3300;') != 1 or live.count('result = D_800D3300 *') != 1:
            raise ValueError('Triangle-facing shared scratch/table declaration changed')
        after = live.replace(STUB, SELECTED, 1).replace(MARKER, declaration, 1)
        after = after.replace('extern s32 D_800D3300;', 'extern s32 D_800D3300[];', 1).replace('result = D_800D3300 *', 'result = D_800D3300[0] *', 1)
        return live, after, False
    if live.count(SELECTED) != 1 or live.count(declaration) != 1:
        raise ValueError('Triangle-facing source changed')
    before = live.replace(SELECTED, STUB, 1).replace(declaration, MARKER, 1)
    if before.count('extern s32 D_800D3300[];') != 1 or before.count('result = D_800D3300[0] *') != 1:
        raise ValueError('Triangle-facing installed scratch/table declaration changed')
    before = before.replace('extern s32 D_800D3300[];', 'extern s32 D_800D3300;', 1).replace('result = D_800D3300[0] *', 'result = D_800D3300 *', 1)
    return before, live, True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw, refs):
    if len(raw) != 308 or sha(raw) != RAW_SHA or refs != BINDINGS:
        raise ValueError('Triangle-facing raw words or bindings changed')
    words = list(struct.unpack('>77I', raw))
    # A closed, dead-after-comparison F4/F6 -> F0/F4 role rename. The only
    # definitions are the normal-Y load and +zero; neither escapes the leaf.
    if [words[i] for i in (62, 63, 65)] != [0xC7A40024, 0x44803000, 0x4606203C]:
        raise ValueError('Triangle-facing FP roles changed')
    words[62] = (words[62] & ~(31 << 16)) | (0 << 16)
    words[63] = (words[63] & ~(31 << 11)) | (4 << 11)
    words[65] = (words[65] & ~((31 << 11) | (31 << 16))) | (0 << 11) | (4 << 16)
    return struct.pack('>77I', *words), dict(refs)


def guard_rows(raw, refs):
    normal, _ = normalize(raw, refs)
    rows = []
    for i, ((old,), (new,)) in enumerate(zip(struct.iter_unpack('>I', raw), struct.iter_unpack('>I', normal))):
        if old != new:
            rows.append([OWNER, FUNCTION, '0x%03X' % (i*4), '0x%08X' % old, '0x%08X' % new,
                         '-', '-', 'Normalize closed final normal-Y floating register roles', '', '', 'false'])
    if len(rows) != 3:
        raise ValueError('Triangle-facing guard scope changed')
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA:
        raise ValueError('Triangle-facing inherited guard prefix changed')
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerows(guard_rows(raw, refs))
    return before + stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the triangle-facing predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/13BB20.s', 'conker/asm/nonmatchings/generated_13BB20/func_1510E950.s',
                 'conker/asm/DAFA0.s', 'conker/symbol_addrs.us.txt',
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
            raise ValueError('Triangle-facing frozen input changed: '+name)
    return hashes


def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/13BB20.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination


def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Triangle-facing linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before) != BEFORE_SHA or len(truth) != 308:
        raise ValueError('Triangle-facing predecessor image/slot changed')
    wanted = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 308)
    wanted[at:at+308] = truth
    rows = [(p, f) for p, n, f, _ in symbol_rows(before) if n == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 12):
        raise ValueError('Triangle-facing predecessor symbol changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, 308)
    if actual != wanted:
        differences = [i for i, (a, b) in enumerate(zip(wanted, actual)) if a != b]
        raise ValueError('Literal triangle-facing whole image differs: '+repr((len(wanted), len(actual), len(differences), differences[:32])))
    expected = Counter((n, f[1], 308 if n == FUNCTION else f[2], *f[3:]) for _, n, f, _ in symbol_rows(before))
    if expected != Counter((n, *f[1:]) for _, n, f, _ in symbol_rows(actual)):
        raise ValueError('Triangle-facing named definitions changed')
    return sum(a != b for a, b in zip(before, actual))


def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    conker = root/'conker'
    target = shadow/'src/game/generated_13BB20.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected triangle-facing Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == SOURCE.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown triangle-facing Make redirect')
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
        raise ValueError('Triangle-facing actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Triangle-facing actual Make padded owner differs')
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
        raise ValueError('Triangle-facing predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Triangle-facing owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    if alloc_pools(old) != alloc_pools(new):
        raise ValueError('Triangle-facing raw owner pools changed')
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+308]
    if struct.pack('>77I', *bound_blob(normal, normal_refs, dict(D_800D3300=0x800D3300, func_150AD8B0=0x150AD8B0))) != truth:
        raise ValueError('Triangle-facing normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('Triangle-facing live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if strict.read_bytes() != new_padded.read_bytes():
        raise ValueError('Triangle-facing production/strict padders disagree')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Triangle-facing padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('Triangle-facing live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('Triangle-facing live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Triangle-facing linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Triangle-facing protected data changed')
    report = dict(source_installed=installed, frozen_inputs=len(frozen), words=77, frame=88, guards=3,
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
