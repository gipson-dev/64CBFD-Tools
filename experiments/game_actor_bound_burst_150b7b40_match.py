"""Owner record recovery, owner qualification, padders and strict linked-image audit."""
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
from tools.experiments.game_active_record_lookup_match import compile_owner
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
PACKET = ROOT / 'conker/build/game-next-150b7b40-private'
ADOPTION = PACKET / 'adoption-match'
FROZEN = PACKET / 'baseline'
OUT = Path(os.environ.get('CBFD_ACTOR_BOUND_MATCH_WORK', ADOPTION / 'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT / 'conker/build').resolve())
PIN = json.loads(Path(__file__).with_name('game_actor_bound_burst_150b7b40_match_manifest.json').read_text())
NAME = 'func_150B7B40'
SOURCE = 'conker/src/game/generated_E4070.c'
OWNER = 'game/generated_E4070'
OBJECT = 'conker/build/src/game/generated_E4070.c.o'
ENTRY, ROM, SIZE = 0x150B7B40, 0xE4FF0, 1936
STUB = 's32 func_150B7B40() {\n    return 0;\n}'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
from tools.tests import game_actor_bound_burst_150b7b40_match_normalizer as normalizer


def recover(text):
    assert text.count(STUB) == 1
    return text.replace(STUB, PIN['declarations'] + '\n\n' + PIN['body'])


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
    assert len(raw) == PIN['raw_words'] * 4 and hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert refs == expected


def qualify_source():
    check_inputs()
    OUT.mkdir(parents=True, exist_ok=False)
    before = (FROZEN / SOURCE).read_text()
    baseline, old_diagnostics = compile_owner(ROOT, OUT, before, 'baseline')
    obj, new_diagnostics = compile_owner(ROOT, OUT, recover(before), 'owner')
    assert not old_diagnostics and not new_diagnostics
    assert same_functions(baseline, obj, (NAME,)) == 20
    assert normalized_pools(baseline) == normalized_pools(obj)
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    assembly = (FROZEN / 'conker/asm/E4070.s').read_text()
    fragment = 'glabel ' + NAME + '\n' + assembly.split('glabel ' + NAME + '\n')[1].split('endlabel ' + NAME)[0]
    fragment += '.size ' + NAME + ',.-' + NAME + '\n'
    original = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' + fragment, 'original')
    normal, normal_refs = normalizer.derive(raw, refs)
    assert (normal, normal_refs) == payload(original, NAME)
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    bound = bound_blob(normal, normal_refs, lookup)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + SIZE]
    assert struct.pack('>484I', *bound) == truth
    assert hashlib.sha256(truth).hexdigest() == PIN['retail_sha256']
    (OUT / 'candidate.body').write_text(PIN['body'])
    (OUT / 'proposed-owner.c').write_text(recover(before))
    (OUT / 'proposed-guards.csv').write_bytes(guard_bytes())
    (OUT / 'raw.bin').write_bytes(raw)
    (OUT / 'retail.bin').write_bytes(truth)
    report = dict(raw_words=483, retail_body_words=484, slot_words=484, alignment_words=0,
                  frame=616, guards=len(PIN['guard_rows']), insertions=1, omissions=0, neighbors_unchanged=20,
                  retained_source_operations=480, redundant_source_operations=3, generated_setup_operations=4,
                  pools_unchanged=True, source_installed=installed(), c_match_credit=0)
    (OUT / 'source-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def padders():
    obj = OUT / 'owner.o'
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    # Exercise the complete production owner in both real padders.
    generated = assemble(pg.emit_padded_assembly(obj, FROZEN / 'conker/asm/E4070.s',
                         filename='generated_E4070', word_patches_path=OUT / 'proposed-guards.csv', rodata_symbol='jtbl_8009FD00_game'), 'padded-generated')
    generic = assemble(pc.emit_padded_assembly(obj, FROZEN / 'conker/retail_layout.us.txt',
                       'generated_E4070', word_patches_path=OUT / 'proposed-guards.csv', rodata_symbol='jtbl_8009FD00_game'), 'padded-generic')
    for padded in (generated, generic):
        assert payload(padded, NAME) == payload(OUT / 'original.o', NAME)
        assert same_functions(FROZEN / OBJECT, padded, (NAME,)) == 20
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
            assert list(struct.unpack_from('>484I', elf.read_bytes(), elf_slot_offset(elf.read_bytes(), ENTRY, SIZE))) == expected
            links += 1
    corruptions = 0
    for i in range(len(raw) // 4):
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
                  source_binding_corruptions_rejected=corruptions, guards=len(PIN['guard_rows']))
    (OUT / 'object-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def strict_image(before, after, groups=None):
    code = inspect.getsource(image.strict_image)
    needle = "sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}"
    assert code.count(needle) == 1
    scope = dict(image.strict_image.__globals__)
    exec(code.replace(needle, "sizes={'func_150B7B40':1936}"), scope)
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
    assert same_functions(FROZEN / OBJECT, obj, (NAME,)) == 20
    assert same_functions(Path(str(obj) + '.compact'), OUT / 'owner.o') == 21
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
                  neighbors_unchanged=20, all_other_6050_bodies_and_all_addresses_unchanged=True,
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


def programs():
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    raw, refs = payload(OUT / 'owner.o', NAME)
    verify(raw, refs)
    normalized, bindings = normalizer.derive(raw, refs)
    return [('retail', list(struct.unpack('>484I', (OUT / 'retail.bin').read_bytes()))),
            ('raw', bound_blob(raw, refs, lookup)), ('normalized', bound_blob(normalized, bindings, lookup))]


def guard_controls():
    from tools.tests.game_actor_bound_burst_150b7b40_match_padders import controls
    return controls()
