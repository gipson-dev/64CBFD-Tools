"""Build and qualify a private proposal for the registered resource callback."""
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body, compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-resource-callback-151572d0-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_resource_callback_151572d0_manifest.json').read_text())
NAME, OWNER = MANIFEST['function'], MANIFEST['owner']
COMMENT='/* Update resource lifetime and callbacks; release expired records. */'


def proposal(source):
    current=body(source,NAME)
    if current == MANIFEST['body']:
        if MANIFEST['declarations'] not in source or COMMENT not in source:
            raise ValueError('installed body has no matching declarations or comment')
        return source
    if current != 's32 func_151572D0() {\n    return 0;\n}':
        raise ValueError('unknown target source; refusing to replace it')
    marker='/* Non-matching placeholders'
    if source.count(marker)!=1 or MANIFEST['declarations'] in source:
        raise ValueError('unexpected owner declarations')
    source=source.replace(current,COMMENT+'\n'+MANIFEST['body'],1)
    return source.replace(marker,'\n'+MANIFEST['declarations']+'\n\n'+marker,1)


def payload(path):
    data,funcs,refs=parse_object(path)
    a,n=funcs[NAME]['value'],funcs[NAME]['size']
    return data[a:a+n],{i-a:v for i,v in refs.items() if a<=i<a+n}


def assemble(text,tag):
    src=OUT/(tag+'.s');src.write_text(text);obj=src.with_suffix('.o')
    result=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300',
                           '-mabi=32','-I','include','-o',str(obj),str(src)],
                          cwd=ROOT/'conker',capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stderr)
    return obj


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    original=(ROOT/MANIFEST['source']).read_text()
    before,old_diag=compile_owner(ROOT,OUT,original,'baseline')
    proposed=proposal(original)
    after,new_diag=compile_owner(ROOT,OUT,proposed,'candidate')
    if same_functions(before,after,(NAME,)) != 25:raise ValueError('owner neighbors changed')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag):raise ValueError('owner diagnostics changed')
    asm=(ROOT/MANIFEST['assembly']).read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME
    snippet=start+asm.split(start,1)[1].split(end,1)[0]+end
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+
                    snippet+'\n.size '+NAME+',.-'+NAME+'\n','retail')
    if payload(after)!=payload(retail):raise ValueError('compiled body or relocations differ from retail')
    raw,refs=payload(after)
    elf=(ROOT/'conker/build/conker.us.elf').read_bytes()
    symbols={v[1]:v[2][1] for v in symbol_rows(elf)}
    words=tuple(bound_blob(raw,refs,{nm:symbols[nm] for es in refs.values() for _,nm in es}))
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    truth=struct.unpack_from('>84I',rom,MANIFEST['rom_offset'])
    if words!=truth:raise ValueError('bound body differs from retail image')
    return dict(source=proposed,before=before,after=after,retail=retail,words=words,
                symbols=symbols,rom=rom,installed=body(original,NAME)==MANIFEST['body'])


def pad_both(state):
    patches=ROOT/'conker/retail_word_patches.us.csv'
    generated=pad_generated_object.emit_padded_assembly(state['after'],ROOT/MANIFEST['assembly'],
                                                         filename=OWNER,word_patches_path=patches)
    generic=pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',
                                               OWNER,word_patches_path=patches)
    a,b=assemble(generated,'generated'),assemble(generic,'generic')
    if payload(a)!=payload(b) or payload(a)!=payload(state['retail']):raise ValueError('padded target differs')
    if same_functions(a,b)!=26:raise ValueError('padders disagree')
    return a,b
