"""Actor-attached emitter semantic C and closed scheduling/register qualification."""
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
PACKET = ROOT / 'conker/build/game-next-150bb760-private'
ADOPTION = PACKET
FROZEN = ADOPTION / 'baseline'
OUT = Path(os.environ.get('CBFD_ACTOR_ATTACHED_EMITTER_WORK', ADOPTION / 'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT / 'conker/build').resolve())
PIN = json.loads(Path(__file__).with_name('game_actor_attached_emitter_150bb760_manifest.json').read_text())
NAME = 'func_150BB760'
SOURCE = 'conker/src/game/generated_E8C10.c'
OWNER = 'game/generated_E8C10'
OBJECT = 'conker/build/src/game/generated_E8C10.c.o'
ENTRY, ROM, SIZE = 0x150BB760, 0xE8C10, 1020
STUB = 's32 func_150BB760() {\n    return 0;\n}\n'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def recover(text):
    assert text.count(STUB)==1
    return text.replace(STUB,PIN['declarations']+'\n\n'+PIN['body']).replace(
        '/* Non-matching placeholders for the text-only asm slice asm/E8C10.s. */',
        '/* Recovered C and remaining placeholders for asm/E8C10.s. */')


def installed():
    old = (FROZEN / SOURCE).read_text()
    live = (ROOT / SOURCE).read_text()
    assert live in (old, recover(old))
    return live != old


def check_inputs():
    assert sha(FROZEN/'fingerprints.json') == PIN['baseline_manifest_sha256']
    pins = json.loads((FROZEN / 'fingerprints.json').read_text())['inputs']
    assert len(pins) == PIN['frozen_inputs'] == 1849
    plan = json.loads((ADOPTION / 'adoption-plan.json').read_text()) if installed() else {}
    if plan: assert set(plan) == {SOURCE, OBJECT, 'conker/build/conker.us.elf','conker/retail_word_patches.us.csv'}
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
    assert len(raw) == 1016 and hashlib.sha256(raw).hexdigest() == PIN['raw_sha256']
    assert refs == expected


def qualify_source():
    check_inputs()
    OUT.mkdir(parents=True, exist_ok=False)
    before = (FROZEN / SOURCE).read_text()
    baseline, old_diagnostics = compile_owner(ROOT, OUT, before, 'baseline')
    obj, new_diagnostics = compile_owner(ROOT, OUT, recover(before), 'owner')
    assert not old_diagnostics and not new_diagnostics
    assert same_functions(baseline, obj, (NAME,)) == 8
    assert normalized_pools(baseline) == normalized_pools(obj)
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    assembly = (FROZEN / 'conker/asm/E8C10.s').read_text()
    fragment = 'glabel ' + NAME + '\n' + assembly.split('glabel ' + NAME + '\n')[1].split('endlabel ' + NAME)[0]
    fragment += '.size ' + NAME + ',.-' + NAME + '\n'
    original = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' + fragment, 'original')
    assert hashlib.sha256(payload(original, NAME)[0]).hexdigest() == PIN['retail_unbound_sha256']
    from tools.tests import game_actor_attached_emitter_150bb760_normalizer as normalizer
    normal,nrefs,relation=normalizer.derive(raw,refs,*payload(original,NAME))
    assert len(relation['guards'])==38 and relation['insertions']==1 and not relation['omissions']
    assert guard_rows(relation)==PIN['guard_rows']
    (OUT/'normalizer-proof.json').write_text(json.dumps(relation,indent=2)+'\n')
    lookup = {row[1]: row[2][1] for row in symbol_rows((FROZEN / 'conker/build/conker.us.elf').read_bytes())}
    source_words = bound_blob(normal, nrefs, lookup)
    bound = bound_blob(*payload(original, NAME), lookup)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + SIZE]
    assert struct.pack('>255I', *bound) == truth
    assert truth == raw_retail_slot()
    (OUT / 'candidate.body').write_text(PIN['body'])
    (OUT / 'proposed-owner.c').write_text(recover(before))
    (OUT / 'proposed-guards.csv').write_bytes(guard_bytes())
    (OUT / 'raw.bin').write_bytes(raw)
    (OUT / 'retail.bin').write_bytes(truth)
    report = dict(raw_words=254, retail_body_words=255, slot_words=255, alignment_words=0,
                  frame=248, raw_frame=248, guards=38, insertions=1, omissions=0, neighbors_unchanged=8,
                  pools_unchanged=True, source_installed=installed(), c_match_credit=0)
    (OUT / 'source-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def padders():
    obj = OUT / 'owner.o'
    raw, refs = payload(obj, NAME)
    verify(raw, refs)
    # Exercise the complete production owner in both real padders.
    generated = assemble(pg.emit_padded_assembly(obj, FROZEN / 'conker/asm/E8C10.s',
                         filename='generated_E8C10', word_patches_path=OUT / 'proposed-guards.csv'), 'padded-generated')
    generic = assemble(pc.emit_padded_assembly(obj, FROZEN / 'conker/retail_layout.us.txt',
                       'generated_E8C10', word_patches_path=OUT / 'proposed-guards.csv'), 'padded-generic')
    for padded in (generated, generic):
        assert payload(padded, NAME) == payload(OUT / 'original.o', NAME)
        text,functions,_=pg.parse_object(padded);at=functions[NAME]['value']
        assert text[at:at+SIZE]==payload(OUT/'original.o',NAME)[0]
        assert same_functions(FROZEN / OBJECT, padded, (NAME,)) == 8
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
    for i in range(254):
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
                  source_binding_corruptions_rejected=corruptions, guards=38)
    (OUT / 'object-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def strict_image(before, after, groups=None):
    code = inspect.getsource(image.strict_image)
    needle = "sizes={'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}"
    assert code.count(needle) == 1
    scope = dict(image.strict_image.__globals__)
    exec(code.replace(needle, "sizes={'func_150BB760':1020}"), scope)
    truth = (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM + 1020]
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
    assert same_functions(FROZEN / OBJECT, obj, (NAME,)) == 8
    assert same_functions(Path(str(obj) + '.compact'), OUT / 'owner.o') == 9
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
    plan = {SOURCE: sha(OUT / 'proposed-owner.c'), OBJECT: sha(obj), 'conker/build/conker.us.elf': sha(elf),'conker/retail_word_patches.us.csv':sha(OUT/'proposed-guards.csv')}
    (OUT / 'adoption-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    report = dict(actual_Make_commands=len(commands), image=audit, protected_data=protected,
                  neighbors_unchanged=8, all_other_6050_bodies_and_all_addresses_unchanged=True,
                  whole_image_controls_rejected=4, candidate_elf_sha256=sha(elf), c_match_credit=0)
    (OUT / 'image-report.json').write_text(json.dumps(report, indent=2) + '\n')
    check_inputs()
    return report


def guard_bytes():
    prefix=(FROZEN/'conker/retail_word_patches.us.csv').read_bytes()
    assert prefix.endswith(b'\n')
    fields=next(csv.reader(io.StringIO(prefix.decode())));stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(PIN['guard_rows'])
    return prefix+stream.getvalue().encode()


def guard_rows(proof):
    spec=lambda refs:';'.join(kind+':'+name for kind,name in refs)or'-'
    result=[]
    for item in proof['guards']:
        note='Preserve proved temporary register values and commutative floating add'
        if item['offset']in(0x20,0x28,0x34,0x40):note='Retarget forward branch across independent call-delay expansion'
        if item['offset']in(0x154,0x158):note='Restore independent descriptor byte store and empty call delay'
        result.append(dict(filename='generated_E8C10',function=NAME,offset=hex(item['offset']),expected='0x%08X'%item['expected'],replacement='0x%08X'%item['replacement'],expected_relocations=spec(item['expected_relocations']),replacement_relocations=spec(item['replacement_relocations']),note=note,insert_after=''if item['insert_after']is None else'0x%08X'%item['insert_after'],insert_after_relocations=''if item['insert_after']is None else'-',omit='false'))
    return result


def guard_controls():
    import copy
    from tools.tests import game_actor_attached_emitter_150bb760_normalizer as normalizer
    _,_,proof=normalizer.derive(*payload(OUT/'owner.o',NAME),*payload(OUT/'original.o',NAME))
    rows=guard_rows(proof);assert rows==PIN['guard_rows']and len(rows)==38
    prefix=(FROZEN/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(prefix.decode())))
    def write(changed,label):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(changed)
        path=OUT/(label+'.csv');path.write_bytes(prefix+stream.getvalue().encode());return path
    def emit(kind,path):
        if kind=='generated':return pg.emit_padded_assembly(OUT/'owner.o',FROZEN/'conker/asm/E8C10.s',filename='generated_E8C10',word_patches_path=path)
        return pc.emit_padded_assembly(OUT/'owner.o',FROZEN/'conker/retail_layout.us.txt','generated_E8C10',word_patches_path=path)
    rejected=0
    for i,row in enumerate(rows):
        bad=copy.deepcopy(rows);bad[i]['expected']='0x%08X'%(int(row['expected'],16)^1);path=write(bad,'bad-expected-%d'%i)
        for kind in('generated','generic'):
            try:emit(kind,path)
            except ValueError:rejected+=1
            else:raise AssertionError(('accepted wrong expected word',i,kind))
        if int(row['offset'],16)in(0x154,0x158):
            bad=copy.deepcopy(rows);bad[i]['expected_relocations']='R_MIPS_26:wrong_helper';path=write(bad,'bad-relocation-%d'%i)
            for kind in('generated','generic'):
                try:emit(kind,path)
                except ValueError:rejected+=1
                else:raise AssertionError(('accepted wrong expected relocation',i,kind))
    assert rejected==80
    index=next(i for i,v in enumerate(rows)if v['insert_after']);bad=copy.deepcopy(rows);bad[index]['insert_after']='0x00000001';path=write(bad,'bad-inserted-nop');controls=0
    for kind in('generated','generic'):
        obj=assemble(emit(kind,path),'bad-nop-'+kind);assert payload(obj,NAME)!=payload(OUT/'original.o',NAME);controls+=1
    row=dict(passes=True,derived_rows=38,expected_word_and_relocation_failures=rejected,effective_inserted_word_controls=controls,normalizer_table_is_independently_derived=True)
    (OUT/'guard-controls.json').write_text(json.dumps(row,indent=2)+'\n');return row

def pad_both(state):
    return OUT / 'padded-generated.o', OUT / 'padded-generic.o'


def prepare():
    qualify_source()
    padders()
    return state()



def raw_retail_slot():
    return (FROZEN / 'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]

def census():
    rom=(FROZEN/'conker/conker.us.bin').read_bytes();elf=(FROZEN/'conker/build/conker.us.elf').read_bytes()
    jal=struct.pack('>I',0x0c000000|(ENTRY>>2&0x3ffffff));pointer=struct.pack('>I',ENTRY)
    assert [i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]==[0x9c49c]
    assert not [i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer]
    at=elf_slot_offset(elf,0x1506efc8,60);assert elf[at:at+60]==rom[0x9c478:0x9c4b4]
    report=dict(passes=True,direct_jal_sites=['0x9c49c'],aligned_pointer_literals=[],caller='func_1506EFC8',caller_words=15,production_caller_literal=True,return_value_ignored=True)
    (OUT/'census.json').write_text(json.dumps(report,indent=2)+'\n');return report

def state():
    from tools.tests import game_actor_attached_emitter_150bb760_normalizer as normalizer
    lookup={row[1]:row[2][1]for row in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())}
    raw,refs=payload(OUT/'owner.o',NAME);truth,trefs=payload(OUT/'original.o',NAME);normal,nrefs,relation=normalizer.derive(raw,refs,truth,trefs)
    return dict(raw_words=bound_blob(raw,refs,lookup),normal_words=bound_blob(normal,nrefs,lookup),retail_words=bound_blob(truth,trefs,lookup),rom=(FROZEN/'conker/conker.us.bin').read_bytes())
