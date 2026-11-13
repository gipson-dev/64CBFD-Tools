"""Reproduce an uncredited effect-descriptor candidate and its alias gap."""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-effect-descriptor-150b9d8c-match'
MANIFEST=json.loads(Path(__file__).with_name('game_effect_descriptor_150b9d8c_manifest.json').read_text())
NAME=MANIFEST['name']
sha=lambda b:hashlib.sha256(b).hexdigest()


def payload(path):
    text,funcs,refs=parse_object(path);f=funcs[NAME];a=f['value'];n=f['size']
    return text[a:a+n],{i-a:rows for i,rows in refs.items()if a<=i<a+n}


def assemble(text,label):
    src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
    result=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
                           '-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stderr)
    return obj


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    source=(ROOT/MANIFEST['source']).read_bytes().replace(b'\r\n',b'\n')
    if sha(source)!=MANIFEST['source_sha256']:
        from tools.experiments import game_effect_descriptor_150b9d8c_direct as direct
        if source!=direct.MANIFEST['selected_source'].encode():raise ValueError('Owner baseline changed')
        source=direct.MANIFEST['old_source'].encode()
        if sha(source)!=MANIFEST['source_sha256']:raise ValueError('Archived owner baseline changed')
    before,diagnostics=compile_owner(ROOT,OUT,source.decode(),'baseline');objects={}
    for label,spec in MANIFEST['candidates'].items():
        obj,current=compile_owner(ROOT,OUT,spec['source'],label)
        raw,_=payload(obj)
        if sha(raw)!=spec['raw_sha256']:raise ValueError('Candidate fingerprint changed: '+label)
        if same_functions(before,obj,(NAME,))!=7 or normalized_pools(before)!=normalized_pools(obj):
            raise ValueError('Neighbor or data-pool change: '+label)
        if diagnostic_rows(current)!=diagnostic_rows(diagnostics):raise ValueError('Compiler diagnostics changed: '+label)
        objects[label]=obj
    assembly=(ROOT/MANIFEST['assembly']).read_text();marker='glabel '+NAME+'\n';end='endlabel '+NAME
    fragment=marker+assembly.split(marker,1)[1].split(end,1)[0]+end
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n','retail')
    truth,bindings=payload(retail)
    if len(truth)!=312 or sha(truth)!=MANIFEST['retail_sha256']:raise ValueError('Retail body changed')
    for label,expected in (('four',4),('two',2),('frame',19)):
        raw,refs=payload(objects[label]);diffs=sum(raw[i:i+4]!=truth[i:i+4]for i in range(0,len(truth),4))
        if len(raw)!=len(truth) or diffs!=expected or refs!=bindings:raise ValueError('Screen shape changed: '+label)
    live=(ROOT/'conker/retail_word_patches.us.csv').read_bytes()
    if any(r['function']==NAME for r in csv.DictReader(io.StringIO(live.decode()))):raise ValueError('Unexpected target guards')
    fields=next(csv.reader(io.StringIO(live.decode())));stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(MANIFEST['guard_rows'])
    if not live.endswith(b'\n'):raise ValueError('Guard file lacks terminal newline')
    guards=OUT/'private-guards.csv';guards.write_bytes(live+stream.getvalue().encode())
    generated=assemble(pad_generated_object.emit_padded_assembly(objects['four'],ROOT/MANIFEST['assembly'],
                       filename=MANIFEST['owner'],word_patches_path=guards),'generated')
    generic=assemble(pad_c_object.emit_padded_assembly(objects['four'],ROOT/'conker/retail_layout.us.txt',
                     MANIFEST['owner'],word_patches_path=guards),'generic')
    if payload(generated)!=(truth,bindings) or payload(generic)!=(truth,bindings):raise ValueError('Padded outputs differ from retail')
    return {'before':before,'retail':retail,'generated':generated,'generic':generic,**objects}
