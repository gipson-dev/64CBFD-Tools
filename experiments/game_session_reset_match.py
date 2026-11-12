"""Private qualification of the session-reset C candidate against retail."""
from pathlib import Path
import csv
import inspect
import io
import json
import os
import struct
import subprocess
import sys

from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object', pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body, compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-session-reset-tests'
MANIFEST = json.loads(Path(__file__).with_name('game_session_reset_manifest.json').read_text())
NAME = MANIFEST['function']
OWNER = MANIFEST['owner']


def assemble(source, label):
    path = OUT / (label + '.s')
    path.write_text(source)
    obj = path.with_suffix('.o')
    result = subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
        '-mabi=32', '-I', 'include', '-o', str(obj), str(path)], cwd=ROOT/'conker',
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return obj


def payload(path):
    data, functions, relocations = parse_object(path)
    symbol = functions[NAME]
    start, size = symbol['value'], symbol['size']
    return data[start:start+size], {at-start: value for at,value in relocations.items()
                                    if start <= at < start+size}


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    header = (ROOT/'conker/include/variables.h').read_text()
    scalar = 'extern u8   D_800E0950;'
    array = 'extern u8   D_800E0950[20];'
    assert header.count(scalar)+header.count(array) == 1
    (OUT/'variables-array.h').write_text(header.replace(scalar,array))
    before = (ROOT/'conker/src/game_3BA70.c').read_text()
    source = before.replace('s32 func_1500E5C0();', 'void func_1500E5C0(void);')
    declarations = ('void func_15012470(void);', 'extern void *D_800D9894;',
                    'extern void *D_800D98D0[4];', 'extern u8 *D_80088870;')
    added = '\n'.join(line for line in declarations if line not in source)
    if added:
        marker = '#include "variables.h"'
        assert marker in source
        source = source.replace(marker, marker+'\n'+added, 1)
    source = source.replace(body(source, NAME), MANIFEST['body'], 1)
    source = source.replace('#include "variables.h"',
        '#include "build/game-session-reset-tests/variables-array.h"', 1)
    previous, _ = compile_owner(ROOT, OUT, before, 'previous')
    normal, diagnostics = compile_owner(ROOT, OUT, source, 'candidate-normal')
    assert not diagnostics
    assert same_functions(previous, normal, (NAME,)) == 5
    scope = dict(compile_owner.__globals__)
    modified = inspect.getsource(compile_owner).replace(
        '*flags,', '*[f for f in flags if not f.startswith("-Wo,")],', 1)
    exec(modified, scope)
    special, diagnostics = scope['compile_owner'](ROOT, OUT, source, 'candidate-special',
        ('-O2', '-g3', '-Wo,-loopunroll,0'))
    assert not diagnostics
    raw, refs = payload(special)
    assert len(raw) == MANIFEST['words']*4
    asm = (ROOT/'conker/asm/nonmatchings/game_3BA70/func_1500E5C0.s').read_text()
    retail_obj = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+
                          asm+'\n.size '+NAME+',.-'+NAME+'\n', 'retail')
    retail, retail_refs = payload(retail_obj)
    symbols = {v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
    lookup = {nm:(symbols[nm] if nm in symbols else int(nm[2:],16))
              for entries in retail_refs.values() for _,nm in entries}
    retail_words = bound_blob(retail, retail_refs, lookup)
    rom = (ROOT/'conker/conker.us.bin').read_bytes()
    start = MANIFEST['rom_offset']
    assert struct.pack('>83I', *retail_words) == rom[start:start+332]
    compiled_lookup = {nm:(symbols[nm] if nm in symbols else int(nm[2:],16))
                       for entries in refs.values() for _,nm in entries}
    compiled_words = bound_blob(raw, refs, compiled_lookup)
    fields = next(csv.reader(io.StringIO((ROOT/'conker/retail_word_patches.us.csv').read_text())))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    spec = lambda entries: ';'.join(a+':'+b for a,b in entries) if entries else '-'
    for row in MANIFEST['guard_rows']:
        writer.writerow(dict(filename=OWNER, function=NAME, offset=hex(row['offset']),
            expected='0x'+row['expected'], replacement='0x'+row['replacement'],
            expected_relocations=spec(row['expected_relocations']),
            replacement_relocations=spec(row['replacement_relocations']),
            note='Session reset schedule and relocation qualification',
            insert_after='', insert_after_relocations='', omit='false'))
    guard = OUT/'guards.csv'
    guard.write_text(output.getvalue())
    return dict(source=source, normal=normal, special=special, raw=raw, refs=refs,
        retail=retail, retail_refs=retail_refs, retail_words=retail_words,
        compiled_words=compiled_words, guards=guard, symbols=symbols)


def pad_both(state):
    layout = ROOT/'conker/retail_layout.us.txt'
    generic = pad_c_object.emit_padded_assembly(state['normal'], layout, OWNER,
        function_objects={NAME:state['special']}, word_patches_path=state['guards'])
    with layout.open(newline='') as stream:
        rows = sorted((row for row in csv.DictReader(stream) if row['filename']==OWNER),
                      key=lambda row:int(row['address'],16))
    synthetic = ''
    for row in rows:
        synthetic += 'glabel '+row['function']+'\n/* 000000 %08X 00000000 */ nop\n' % int(row['address'],16)
    synthetic += '/* 000000 %08X 00000000 */ nop\n' % (max(int(x['end'],16) for x in rows)-4)
    slice_path = OUT/'synthetic-layout.s'
    slice_path.write_text(synthetic)
    generated = pad_generated_object.emit_padded_assembly(state['normal'], slice_path,
        function_objects={NAME:state['special']}, word_patches_path=state['guards'], filename=OWNER)
    first, second = assemble(generic,'generic-pad'), assemble(generated,'generated-pad')
    assert same_functions(first,second) == 6
    assert payload(first) == (state['retail'],state['retail_refs'])
    return first, second
