"""Qualify the secondary registered-callback walker and its C interfaces."""
import csv
import hashlib
import io
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
from tools.pad_generated_object import parse_object
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-secondary-walker-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_secondary_walker_manifest.json').read_text())
NAME,OWNER=MANIFEST['function'],MANIFEST['owner']

def payload(path,name=NAME):
 data,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def assemble(text,tag):
 src=OUT/(tag+'.s');src.write_text(text);obj=src.with_suffix('.o');z=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True);assert z.returncode==0,z.stderr;return obj

def prepare():
 OUT.mkdir(parents=True,exist_ok=True);headers=OUT/'overlay';headers.mkdir(exist_ok=True)
 for name in ('functions.h','variables.h','structs.h'):shutil.copyfile(ROOT/'conker/include'/name,headers/name)
 h=headers/'structs.h';text=h.read_text();old='    u8 pad0[0x14];\n    void (*unk18)(struct102 *arg0);';new='    void (*unk4)(u8 *arg0);\n    u8 pad0[0x10];\n    void (*unk18)(struct102 *arg0);'
 assert text.count(old)+text.count(new)==1;h.write_text(text.replace(old,new))
 source=(ROOT/MANIFEST['source']).read_text()
 def overlay(s):
  for n in ('functions.h','variables.h'):
   old='#include "'+n+'"';new='#include "'+headers.relative_to(ROOT/'conker').as_posix()+'/'+n+'"';assert s.count(old)==1;s=s.replace(old,new)
  return s
 before=overlay(source);after=before.replace('s32 func_151671E8();','void func_151671E8(void);',1).replace(body(before,NAME),MANIFEST['body'],1)
 prior,prior_diag=compile_owner(ROOT,OUT,before,'prior');compiled,diagnostics=compile_owner(ROOT,OUT,after,'candidate')
 assert diagnostic_rows(prior_diag)==diagnostic_rows(diagnostics);assert same_functions(prior,compiled,(NAME,))==41
 raw,refs=payload(compiled);assert len(raw)==296
 asm=(ROOT/'conker/asm/nonmatchings/game_1944C0/func_151671E8.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;snippet=start+asm.split(start,1)[1].split(end,1)[0]+end+'\n';target=OUT/'target.s';target.write_text(snippet)
 retail_obj=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+snippet+'\n.size '+NAME+',.-'+NAME+'\n','retail');retail,retail_refs=payload(retail_obj)
 syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 def bind(blob,rr):return tuple(bound_blob(blob,rr,{nm:syms[nm] for es in rr.values()for _,nm in es}))
 retail_words,raw_words=bind(retail,retail_refs),bind(raw,refs);rom=(ROOT/'conker/conker.us.bin').read_bytes();at=MANIFEST['rom_offset'];assert struct.pack('>74I',*retail_words)==rom[at:at+296]
 fields=next(csv.reader(io.StringIO((ROOT/'conker/retail_word_patches.us.csv').read_text())));b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(MANIFEST['guard_rows']);guard=OUT/'guards.csv';guard.write_text(b.getvalue())
 text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  for typ,symbol in refs.get(i*4,[]):text+='.reloc ., '+typ+', '+symbol+'\n'
  text+='.word 0x%08X\n'%word
 raw_obj=assemble(text+'.size '+NAME+',.-'+NAME+'\n','raw-target');assert payload(raw_obj)==(raw,refs)
 lines=(ROOT/'conker/retail_layout.us.txt').read_text().splitlines();entry=[x for x in lines[1:]if x.split(',')[1:3]==[OWNER,NAME]];assert len(entry)==1;layout=OUT/'layout.csv';layout.write_text(lines[0]+'\n'+entry[0]+'\n')
 return dict(source=after,prior=prior,compiled=compiled,raw_obj=raw_obj,raw=raw,refs=refs,raw_words=raw_words,retail_obj=retail_obj,retail=retail,retail_refs=retail_refs,retail_words=retail_words,guard=guard,layout=layout,target=target,symbols=syms)

def pad_both(state):
 a=pad_c_object.emit_padded_assembly(state['raw_obj'],state['layout'],OWNER,word_patches_path=state['guard']);b=pad_generated_object.emit_padded_assembly(state['raw_obj'],state['target'],filename=OWNER,word_patches_path=state['guard']);first,second=assemble(a,'generic'),assemble(b,'generated');assert payload(first)==payload(second)==(state['retail'],state['retail_refs']);return first,second
