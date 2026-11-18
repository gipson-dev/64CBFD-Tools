"""Direct C recovery, owner qualification, padders and strict linked-image audit."""
from pathlib import Path
import hashlib
import csv
import io
import inspect
import json
import os
import shutil
import struct
import subprocess
import sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows, elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_sequence_direction_1501fe68_match as image
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
PACKET = ROOT / 'conker/build/game-next-151afc88-private'
ADOPTION = PACKET / 'adoption'
FROZEN = PACKET / 'baseline'
OUT = Path(os.environ.get('CBFD_RADIAL_DAMPING_WORK', ADOPTION / 'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT / 'conker/build').resolve())
PIN = json.loads(Path(__file__).with_name('game_radial_damping_151afc88_manifest.json').read_text())
NAME = 'func_151AFC88'
SOURCE = 'conker/src/game/generated_1DCA70.c'
OWNER = 'game/generated_1DCA70'
OBJECT = 'conker/build/src/game/generated_1DCA70.c.o'
ENTRY, ROM, SIZE = 0x151AFC88, 0x1DD138, 540
STUB = 's32 func_151AFC88() {\n    return 0;\n}'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def recover(text):
    assert text.count(STUB) == 1
    return text.replace(STUB, PIN['declarations'] + '\n' + PIN['body'])


def installed():
    old = (FROZEN / SOURCE).read_text()
    live = (ROOT / SOURCE).read_text()
    assert live in (old, recover(old))
    return live != old


def check_inputs():
    pins = json.loads((FROZEN / 'fingerprints.json').read_text())['inputs']
    assert len(pins) == PIN['frozen_inputs']
    plan = json.loads((ADOPTION / 'adoption-plan.json').read_text()) if installed() else {}
    if plan:
        assert set(plan) == {SOURCE, OBJECT, 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'}
    for name, value in pins.items():
        assert sha(ROOT / name) == plan.get(name, value), name
    extra = json.loads((ADOPTION / 'dependency-baseline/fingerprints.json').read_text())
    for name, value in extra.items():
        assert sha(ROOT / name) == value and sha(ADOPTION / 'dependency-baseline' / name) == value, name
    return len(pins) + len(extra)


def assemble(text, label):
    source = OUT / (label + '.s')
    obj = source.with_suffix('.o')
    source.write_text(text)
    run = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
                          '-mabi=32', '-I', 'include', '-o', str(obj), str(source)],
                         cwd=ROOT / 'conker', capture_output=True, text=True)
    assert run.returncode == 0 and not run.stderr, (run.stdout, run.stderr)
    return obj


def verify(raw, refs):
    expected = {int(k): [tuple(v) for v in values] for k, values in PIN['refs'].items()}
    assert len(raw) == SIZE and hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert refs == expected


def qualify_source():
    check_inputs()
    OUT.mkdir(parents=True, exist_ok=False)
    before = (FROZEN / SOURCE).read_text()
    baseline, old_diagnostics = compile_owner(ROOT, OUT, before, 'baseline')
    obj, new_diagnostics = compile_owner(ROOT, OUT, recover(before), 'owner')
    assert not old_diagnostics and not new_diagnostics
    assert same_functions(baseline, obj, (NAME,)) == 6
    assert normalized_pools(baseline) == normalized_pools(obj)
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    assembly = (FROZEN / 'conker/asm/1DCA70.s').read_text()
    fragment = 'glabel ' + NAME + '\n' + assembly.split('glabel ' + NAME + '\n')[1].split('endlabel ' + NAME)[0]
    fragment += '.size ' + NAME + ',.-' + NAME + '\n'
    original = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' + fragment, 'original')
    assert payload(original, NAME)[1] == refs
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    source_words = bound_blob(raw, refs, lookup)
    bound = bound_blob(*payload(original, NAME), lookup)
    from tools.tests import game_radial_damping_151afc88_proof as proof
    assert proof.derive(source_words) == bound
    proof.main(source_words, bound)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + SIZE]
    assert struct.pack('>135I', *bound) == truth
    assert hashlib.sha256(truth).hexdigest() == PIN['retail_sha256']
    (OUT / 'proposed-owner.c').write_text(recover(before))
    (OUT / 'proposed-guards.csv').write_bytes(guard_bytes())
    (OUT / 'raw.bin').write_bytes(raw)
    (OUT / 'retail.bin').write_bytes(truth)
    report = dict(raw_words=135, retail_body_words=135, slot_words=135, alignment_words=0,
                  frame=168, guards=10, insertions=0, omissions=0, neighbors_unchanged=6,
                  pools_unchanged=True, source_installed=installed(), c_match_credit=0)
    (OUT / 'source-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def padders():
    obj = OUT / 'owner.o'
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    # Exercise the complete production owner in both real padders.
    generated = assemble(pg.emit_padded_assembly(obj, FROZEN / 'conker/asm/1DCA70.s',
                         filename='generated_1DCA70', word_patches_path=OUT / 'proposed-guards.csv'), 'padded-generated')
    generic = assemble(pc.emit_padded_assembly(obj, FROZEN / 'conker/retail_layout.us.txt',
                       'generated_1DCA70', word_patches_path=OUT / 'proposed-guards.csv'), 'padded-generic')
    for padded in (generated, generic):
        assert payload(padded, NAME) == payload(OUT / 'original.o', NAME)
        assert same_functions(FROZEN / OBJECT, padded, (NAME,)) == 6
    links = 0
    for label, target in (('original', OUT / 'original.o'), ('generated', generated), ('generic', generic)):
        data, bindings = payload(target, NAME)
        for low in (0, 0x7FFC, 0x8000, 0xFFFC):
            symbols = {name: (0x80010000 + i*0x10000 + low if name.startswith('D_') else 0x15100000 + i*0x10000 + low) for i,name in enumerate(sorted({name for rows in bindings.values() for _,name in rows}))}
            expected = bound_blob(data, bindings, symbols)
            script = OUT / ('rebase-' + label + '-%04x.ld' % low)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
            # Full owners start earlier; use the actual object symbol's relative location.
            from tools.pad_generated_object import parse_object
            _, functions, _ = parse_object(target)
            origin = ENTRY - functions[NAME]['value']
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % origin)
            elf = script.with_suffix('.elf')
            names = {symbol for rows in parse_object(target)[2].values() for _, symbol in rows}
            lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
            lookup.update(symbols)
            argv = ['mips-linux-gnu-ld', '-T', str(script), '-e', NAME]
            argv += ['--defsym=%s=0x%X' % (name, lookup[name]) for name in names]
            run = subprocess.run([*argv, '-o', str(elf), str(target)], capture_output=True, text=True)
            assert run.returncode == 0, run.stderr
            assert list(struct.unpack_from('>135I', elf.read_bytes(), elf_slot_offset(elf.read_bytes(), ENTRY, SIZE))) == expected
            links += 1
    corruptions = 0
    for i in range(135):
        bad = bytearray(raw)
        bad[4 * i] ^= 1
        try:
            verify(bytes(bad), refs)
        except AssertionError:
            corruptions += 1
        else:
            raise AssertionError(('accepted source corruption', i))
    for at in refs:
        bad = {k: list(v) for k, v in refs.items()}
        kind, name = bad[at][0]
        bad[at][0] = (kind, name + '_wrong')
        try:
            verify(raw, bad)
        except AssertionError:
            corruptions += 1
        else:
            raise AssertionError(('accepted binding corruption', at))
    report = dict(full_owner_dual_padder_matches=True, gnu_links=links,
                  source_binding_corruptions_rejected=corruptions, guards=10)
    (OUT / 'object-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def strict_image(before, after, groups=None):
    code = inspect.getsource(image.strict_image)
    needle = "sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}"
    assert code.count(needle) == 1
    scope = dict(image.strict_image.__globals__)
    exec(code.replace(needle, "sizes={'func_151AFC88':540}"), scope)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + SIZE]
    return scope['strict_image'](before, after, {NAME: truth}, groups=groups)


def qualify_image():
    check_inputs()
    image.root = image.p.root = ROOT
    image.out = image.p.out = OUT
    for name in ('conker.ld', 'conker.us.elf'):
        target = OUT / 'frozen/conker/build' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / 'conker/build' / name, target)
    targets, commands = image.actual_make({OWNER: OUT / 'proposed-owner.c'})
    obj = targets[OWNER]
    assert same_functions(FROZEN / OBJECT, obj, (NAME,)) == 6
    assert same_functions(Path(str(obj) + '.compact'), OUT / 'owner.o') == 7
    assert payload(obj, NAME) == payload(OUT / 'original.o', NAME)
    elf = image.link(targets)
    before = (FROZEN / 'conker/build/conker.us.elf').read_bytes()
    after = elf.read_bytes()
    audit = strict_image(before, after)
    old, _, old_addresses = load_elf_functions(str(FROZEN / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    new, _, new_addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
    assert len(old) == len(new) == 6051 and old_addresses == new_addresses
    assert {name for name in old if old[name] != new[name]} == {NAME}
    protected = audit_layout(elf, ROOT / 'conker')
    assert protected['exact'] and protected['bytes'] == 189088 and protected['different_bytes'] == 0
    row = next(row for row in symbol_rows(after) if row[1] == 'D_800BE9F0')
    sites = (row[0] + 4, row[3] + len(row[1]) - 1,
             elf_slot_offset(after, 0x80082B20, 1), elf_slot_offset(after, ENTRY + 16, 4))
    for site in sites:
        bad = bytearray(after)
        bad[site] ^= 1
        try:
            strict_image(before, bytes(bad), groups=audit['metadata_groups'])
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError(('accepted full-image corruption', site))
    plan = {SOURCE: sha(OUT / 'proposed-owner.c'), OBJECT: sha(obj), 'conker/build/conker.us.elf': sha(elf), 'conker/retail_word_patches.us.csv': sha(OUT / 'proposed-guards.csv')}
    (OUT / 'adoption-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    report = dict(actual_Make_commands=len(commands), image=audit, protected_data=protected,
                  neighbors_unchanged=6, all_other_6050_bodies_and_all_addresses_unchanged=True,
                  whole_image_controls_rejected=4, candidate_elf_sha256=sha(elf), c_match_credit=0)
    (OUT / 'image-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def guard_bytes():
    old = (FROZEN / 'conker/retail_word_patches.us.csv').read_bytes()
    fields = next(csv.reader(io.StringIO(old.decode())))
    assert old.endswith(b'\n')
    assert not any(row['function'] == NAME for row in csv.DictReader(io.StringIO(old.decode())))
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=fields, lineterminator='\n').writerows(PIN['guard_rows'])
    return old + stream.getvalue().encode()


def pad_both(state):
    return OUT / 'padded-generated.o', OUT / 'padded-generic.o'


def prepare():
    qualify_source()
    padders()
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    source_words = bound_blob(*payload(OUT / 'owner.o', NAME), lookup)
    retail_words = bound_blob(*payload(OUT / 'original.o', NAME), lookup)
    return dict(raw_words=source_words, retail_words=retail_words, rom=(FROZEN / 'conker/conker.us.bin').read_bytes(), guards=OUT / 'proposed-guards.csv', after=OUT / 'owner.o')


def guard_controls():
    before = (FROZEN / 'conker/retail_word_patches.us.csv').read_bytes()
    fields = next(csv.reader(io.StringIO(before.decode())))
    count = 0
    for i in range(10):
        for variant in ('expected', 'replacement', 'omitted'):
            rows = [dict(row) for row in PIN['guard_rows']]
            if variant == 'omitted': rows.pop(i)
            else: rows[i][variant] = '0x%08X' % (int(rows[i][variant],0) ^ 1)
            stream = io.StringIO(newline='')
            csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writerows(rows)
            path = OUT / 'invalid-guards.csv'; path.write_bytes(before+stream.getvalue().encode())
            for module, layout in ((pg,FROZEN/'conker/asm/1DCA70.s'),(pc,FROZEN/'conker/retail_layout.us.txt')):
                try:
                    fixed = module.emit_padded_assembly(OUT/'owner.o',layout,filename='generated_1DCA70',word_patches_path=path)
                    wrong = assemble(fixed,'bad-guard')
                    assert payload(wrong,NAME)==payload(OUT/'original.o',NAME)
                except (AssertionError,ValueError): count+=1
                else: raise AssertionError(('ineffective guard corruption',i,variant))
    assert count==60
    return count
