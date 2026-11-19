"""Direct extended emitter C with complete owner and linked-image qualification."""
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
PACKET = ROOT / 'conker/build/game-next-150bb498-private'
ADOPTION = PACKET
FROZEN = ADOPTION / 'baseline'
OUT = Path(os.environ.get('CBFD_EXTENDED_EMITTER_WORK', ADOPTION / 'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT / 'conker/build').resolve())
PIN = json.loads(Path(__file__).with_name('game_extended_emitter_150bb498_manifest.json').read_text())
NAME = 'func_150BB498'
SOURCE = 'conker/src/game/generated_E8090.c'
OWNER = 'game/generated_E8090'
OBJECT = 'conker/build/src/game/generated_E8090.c.o'
ENTRY, ROM, SIZE = 0x150BB498, 0xE8948, 616
STUB = 's32 func_150BB498() {\n    return 0;\n}\n'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def recover(text):
    assert text.count(STUB)==1
    return text.replace(STUB,PIN['declarations']+'\n\n'+PIN['body'])


def installed():
    old = (FROZEN / SOURCE).read_text()
    live = (ROOT / SOURCE).read_text()
    assert live in (old, recover(old))
    return live != old


def check_inputs():
    pins = json.loads((FROZEN / 'fingerprints.json').read_text())['inputs']
    assert len(pins) == PIN['frozen_inputs'] == 1841
    plan = json.loads((ADOPTION / 'adoption-plan.json').read_text()) if installed() else {}
    if plan: assert set(plan) == {SOURCE, OBJECT, 'conker/build/conker.us.elf'}
    for name, value in pins.items(): assert sha(ROOT / name) == plan.get(name, value), name
    return len(pins)


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
    assert len(raw) == 604 and hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert refs == expected


def qualify_source():
    check_inputs()
    OUT.mkdir(parents=True, exist_ok=False)
    before = (FROZEN / SOURCE).read_text()
    baseline, old_diagnostics = compile_owner(ROOT, OUT, before, 'baseline')
    obj, new_diagnostics = compile_owner(ROOT, OUT, recover(before), 'owner')
    assert not old_diagnostics and not new_diagnostics
    assert same_functions(baseline, obj, (NAME,)) == 5
    assert normalized_pools(baseline) == normalized_pools(obj)
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    assembly = (FROZEN / 'conker/asm/E8090.s').read_text()
    fragment = 'glabel ' + NAME + '\n' + assembly.split('glabel ' + NAME + '\n')[1].split('endlabel ' + NAME)[0]
    fragment += '.size ' + NAME + ',.-' + NAME + '\n.space 12\n'
    original = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' + fragment, 'original')
    assert hashlib.sha256(payload(original, NAME)[0]).hexdigest() == PIN['raw_sha256']
    assert (raw, refs) == payload(original, NAME)
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    source_words = bound_blob(raw, refs, lookup)
    bound = bound_blob(*payload(original, NAME), lookup)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + 604]
    assert struct.pack('>151I', *bound) == truth
    assert truth + b'\0'*12 == raw_retail_slot()
    (OUT / 'candidate.body').write_text(PIN['body'])
    (OUT / 'proposed-owner.c').write_text(recover(before))
    (OUT / 'proposed-guards.csv').write_bytes(guard_bytes())
    (OUT / 'raw.bin').write_bytes(raw)
    (OUT / 'retail.bin').write_bytes(truth)
    report = dict(raw_words=151, retail_body_words=151, slot_words=154, alignment_words=3,
                  frame=192, raw_frame=192, guards=0, insertions=0, omissions=0, neighbors_unchanged=5,
                  pools_unchanged=True, source_installed=installed(), c_match_credit=0)
    (OUT / 'source-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def padders():
    obj = OUT / 'owner.o'
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    # Exercise the complete production owner in both real padders.
    generated = assemble(pg.emit_padded_assembly(obj, FROZEN / 'conker/asm/E8090.s',
                         filename='generated_E8090', word_patches_path=OUT / 'proposed-guards.csv'), 'padded-generated')
    generic = assemble(pc.emit_padded_assembly(obj, FROZEN / 'conker/retail_layout.us.txt',
                       'generated_E8090', word_patches_path=OUT / 'proposed-guards.csv'), 'padded-generic')
    for padded in (generated, generic):
        assert payload(padded, NAME) == payload(OUT / 'original.o', NAME)
        text,functions,_=pg.parse_object(padded);at=functions[NAME]['value']
        assert text[at:at+SIZE]==payload(OUT/'original.o',NAME)[0]+b'\0'*12
        assert same_functions(FROZEN / OBJECT, padded, (NAME,)) == 5
    links = 0
    for label, target in (('original', OUT / 'original.o'), ('generated', generated), ('generic', generic)):
        data, bindings = payload(target, NAME)
        text,functions,_=pg.parse_object(target);at=functions[NAME]['value'];data=text[at:at+SIZE];assert len(data)==SIZE
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
            assert list(struct.unpack_from('>%dI' % (len(data)//4), elf.read_bytes(), elf_slot_offset(elf.read_bytes(), ENTRY, len(data)))) == expected
            links += 1
    corruptions = 0
    for i in range(151):
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
                  source_binding_corruptions_rejected=corruptions, guards=0)
    (OUT / 'object-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def strict_image(before, after, groups=None):
    code = inspect.getsource(image.strict_image)
    needle = "sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}"
    assert code.count(needle) == 1
    scope = dict(image.strict_image.__globals__)
    exec(code.replace(needle, "sizes={'func_150BB498':604}"), scope)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + 604]
    for blob in (before, after):
        at=elf_slot_offset(blob,ENTRY+604,12);assert blob[at:at+12]==b'\0'*12
    if groups is not None: assert groups == PIN['metadata_groups']
    return scope['strict_image'](before, after, {NAME: truth}, groups=PIN['metadata_groups'])


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
    assert same_functions(FROZEN / OBJECT, obj, (NAME,)) == 5
    assert same_functions(Path(str(obj) + '.compact'), OUT / 'owner.o') == 6
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
    plan = {SOURCE: sha(OUT / 'proposed-owner.c'), OBJECT: sha(obj), 'conker/build/conker.us.elf': sha(elf)}
    (OUT / 'adoption-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    report = dict(actual_Make_commands=len(commands), image=audit, protected_data=protected,
                  neighbors_unchanged=5, all_other_6050_bodies_and_all_addresses_unchanged=True,
                  whole_image_controls_rejected=4, candidate_elf_sha256=sha(elf), c_match_credit=0)
    (OUT / 'image-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def guard_bytes():
    return (FROZEN / 'conker/retail_word_patches.us.csv').read_bytes()


def pad_both(state):
    return OUT / 'padded-generated.o', OUT / 'padded-generic.o'


def prepare():
    qualify_source()
    padders()
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    source_words = bound_blob(*payload(OUT / 'owner.o', NAME), lookup)
    retail_words = bound_blob(*payload(OUT / 'original.o', NAME), lookup)
    return dict(raw_words=source_words, retail_words=retail_words, rom=(FROZEN / 'conker/conker.us.bin').read_bytes(), guards=OUT / 'proposed-guards.csv', after=OUT / 'owner.o')



def raw_retail_slot():
    return (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]

def census():
    rom=(FROZEN/'conker/conker.us.bin').read_bytes();elf=(FROZEN/'conker/build/conker.us.elf').read_bytes()
    jal=struct.pack('>I',0x0c000000|(ENTRY>>2&0x3ffffff));pointer=struct.pack('>I',ENTRY)
    assert not [i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]
    assert [i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer]==[0x22f4d8]
    registry=(FROZEN/'conker/asm/data/22EF80.rodata.s').read_text()
    block=registry.split('dlabel D_8008AA00\n',1)[1].split('enddlabel D_8008AA00',1)[0]
    entries=[v.split('.word',1)[1].strip()for v in block.splitlines()if'.word'in v]
    assert len(entries)==28 and entries[6]==NAME and block.count(NAME)==1
    at=elf_slot_offset(elf,0x8008aa18,4);assert elf[at:at+4]==pointer
    at=elf_slot_offset(elf,0x1514c3c4,64);assert elf[at:at+64]==rom[0x179874:0x1798b4]
    report=dict(passes=True,direct_jal_sites=[],aligned_pointer_literals=['0x22f4d8'],registry='D_8008AA00[6]',callback_words=15,coordinates=[2,3,4],heading_word=8,context_byte=14,return_controls_loop=True,caller_window_production_literal=True,complete_parent_qualified=False)
    (OUT/'census.json').write_text(json.dumps(report,indent=2)+'\n');return report

def state():
    lookup={row[1]:row[2][1] for row in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())}
    return dict(raw_words=bound_blob(*payload(OUT/'owner.o',NAME),lookup),retail_words=bound_blob(*payload(OUT/'original.o',NAME),lookup),rom=(FROZEN/'conker/conker.us.bin').read_bytes())
