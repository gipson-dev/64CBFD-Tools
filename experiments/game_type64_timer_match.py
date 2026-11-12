"""Compile and inspect the private type-0x64 timer callback candidate."""
import csv
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object', pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object
from tools.experiments.game_remaining_donor_candidates import body, compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT/'conker/build/game-type64-timer-tests'
MANIFEST = json.loads(Path(__file__).with_name('game_type64_timer_manifest.json').read_text())
NAME, OWNER = MANIFEST['function'], MANIFEST['owner']


def payload(path):
    data, functions, relocations = parse_object(path)
    start, size = functions[NAME]['value'], functions[NAME]['size']
    return data[start:start+size], {k-start:v for k,v in relocations.items() if start <= k < start+size}


def assemble(text, tag):
    source = OUT/(tag+'.s')
    source.write_text(text)
    obj = source.with_suffix('.o')
    proc = subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300',
        '-mabi=32','-I','include','-o',str(obj),str(source)],cwd=ROOT/'conker',capture_output=True,text=True)
    assert proc.returncode == 0, proc.stderr
    return obj


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    original = (ROOT/MANIFEST['source']).read_text()
    candidate = original
    header = MANIFEST['header']
    missing = [line for line in header.splitlines() if line and line not in candidate]
    if missing:
        candidate = candidate.replace('#include <ultra64.h>','#include <ultra64.h>\n'+'\n'.join(missing),1)
    candidate = candidate.replace(body(candidate,NAME),MANIFEST['body'],1)
    before, before_diag = compile_owner(ROOT,OUT,original,'before')
    compiled, diagnostics = compile_owner(ROOT,OUT,candidate,'candidate')
    assert not before_diag and not diagnostics, (before_diag,diagnostics)
    assert same_functions(before,compiled,(NAME,)) == 3
    raw, raw_refs = payload(compiled)
    assert len(raw) == MANIFEST['raw_words']*4
    asm = (ROOT/MANIFEST['retail_asm']).read_text()
    start, end = 'glabel '+NAME+'\n', 'endlabel '+NAME
    snippet = start+asm.split(start,1)[1].split(end,1)[0]+end+'\n'
    target = OUT/'target.s'; target.write_text(snippet)
    retail_obj = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+snippet+'\n.size '+NAME+',.-'+NAME+'\n','retail')
    retail, retail_refs = payload(retail_obj)
    assert len(retail) == MANIFEST['retail_words']*4
    symbols = {row[1]:row[2][1] for row in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
    def bind(blob, refs):
        return tuple(bound_blob(blob,refs,{nm:symbols[nm] for group in refs.values() for _,nm in group}))
    retail_words, raw_words = bind(retail,retail_refs), bind(raw,raw_refs)
    rom = (ROOT/'conker/conker.us.bin').read_bytes(); at=MANIFEST['rom_offset']
    assert struct.pack('>170I',*retail_words) == rom[at:at+680]
    fields = next(csv.reader(io.StringIO((ROOT/'conker/retail_word_patches.us.csv').read_text())))
    stream = io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(MANIFEST['guard_rows'])
    guard = OUT/'guards.csv';guard.write_text(stream.getvalue())
    src = '.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
    for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
        for typ,symbol in raw_refs.get(i*4,[]):src += '.reloc ., '+typ+', '+symbol+'\n'
        src += '.word 0x%08X\n'%word
    raw_obj = assemble(src+'.size '+NAME+',.-'+NAME+'\n','raw-target')
    assert payload(raw_obj) == (raw,raw_refs)
    layout = OUT/'layout.csv';lines=(ROOT/'conker/retail_layout.us.txt').read_text().splitlines()
    rows=[line for line in lines[1:] if line.split(',')[1:3]==[OWNER,NAME]]
    assert len(rows)==1;layout.write_text(lines[0]+'\n'+rows[0]+'\n')
    return dict(source=candidate,compiled=compiled,raw=raw,raw_refs=raw_refs,raw_words=raw_words,
        raw_obj=raw_obj,retail_obj=retail_obj,retail=retail,retail_refs=retail_refs,
        retail_words=retail_words,symbols=symbols,guard=guard,layout=layout,target=target)


def pad_both(state):
    generic = pad_c_object.emit_padded_assembly(state['raw_obj'],state['layout'],OWNER,word_patches_path=state['guard'])
    generated = pad_generated_object.emit_padded_assembly(state['raw_obj'],state['target'],filename=OWNER,word_patches_path=state['guard'])
    a,b = assemble(generic,'generic'),assemble(generated,'generated')
    assert payload(a)==payload(b)==(state['retail'],state['retail_refs'])
    return a,b
