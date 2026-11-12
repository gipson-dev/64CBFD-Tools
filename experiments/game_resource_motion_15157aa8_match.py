"""Qualify guarded C for the resource motion callback in an isolated build."""
import csv
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-resource-motion-15157aa8-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_resource_motion_15157aa8_manifest.json').read_text())
NAME,OWNER=MANIFEST['function'],MANIFEST['owner']
COMMENT='/* Integrate resource motion, damping, and angular velocity. */'

def proposal(source):
 current=body(source,NAME)
 if current==MANIFEST['body']:
  if MANIFEST['declarations'] not in source or COMMENT not in source:raise ValueError('installed declarations or comment differ')
  return source
 if current!='s32 func_15157AA8() {\n    return 0;\n}':raise ValueError('unknown target source')
 marker='/* Non-matching placeholders'
 if source.count(marker)!=1 or MANIFEST['declarations'] in source:raise ValueError('unexpected owner declarations')
 return source.replace(current,COMMENT+'\n'+MANIFEST['body'],1).replace(marker,'\n'+MANIFEST['declarations']+'\n\n'+marker,1)

def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size']
 return data[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def assemble(text,tag):
 path=OUT/(tag+'.s');path.write_text(text);out=path.with_suffix('.o')
 z=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out),str(path)],cwd=ROOT/'conker',capture_output=True,text=True)
 if z.returncode:raise ValueError(z.stderr)
 return out

def guards():
 base=(ROOT/'conker/retail_word_patches.us.csv').read_bytes()
 reader=csv.DictReader(io.StringIO(base.decode()));fields=reader.fieldnames;existing=[r for r in reader if r['function']==NAME]
 rows=MANIFEST['guard_rows']
 if existing and existing!=rows:raise ValueError('existing target guards differ')
 if not existing:
  out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in base else '\n');writer.writerows(rows);base+=out.getvalue().encode()
 path=OUT/'proposed-guards.csv';path.write_bytes(base);return path

def prepare():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/MANIFEST['source']).read_text()
 before,bd=compile_owner(ROOT,OUT,original,'baseline');source=proposal(original)
 after,ad=compile_owner(ROOT,OUT,source,'candidate')
 if same_functions(before,after,(NAME,))!=25:raise ValueError('owner neighbors changed')
 if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('owner diagnostics changed')
 text=(ROOT/MANIFEST['assembly']).read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME
 snippet=start+text.split(start,1)[1].split(end,1)[0]+end
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+snippet+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after);truth,trefs=payload(retail)
 if len(raw)!=736 or refs!=trefs:raise ValueError('raw size or bindings differ')
 actual=list(struct.unpack('>184I',raw));expected=list(struct.unpack('>184I',truth));rows=MANIFEST['guard_rows']
 changes=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
 if len(rows)!=16 or changes!=[int(r['offset'],0)//4 for r in rows]:raise ValueError('guard positions differ')
 for row in rows:
  i=int(row['offset'],0)//4
  if refs.get(i*4) or actual[i]!=int(row['expected'],0) or expected[i]!=int(row['replacement'],0):raise ValueError('guard word changed')
 syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 resolve={nm:syms[nm] for es in refs.values() for _,nm in es}
 raw_words=tuple(bound_blob(raw,refs,resolve));retail_words=tuple(bound_blob(truth,trefs,resolve))
 rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if retail_words!=struct.unpack_from('>184I',rom,MANIFEST['rom_offset']):raise ValueError('retail body mismatch')
 return dict(source=source,before=before,after=after,retail=retail,raw_words=raw_words,
             retail_words=retail_words,symbols=syms,rom=rom,guards=guards(),installed=body(original,NAME)==MANIFEST['body'])

def pad_both(state,path=None):
 patches=state['guards'] if path is None else path
 a=pad_generated_object.emit_padded_assembly(state['after'],ROOT/MANIFEST['assembly'],filename=OWNER,word_patches_path=patches)
 b=pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=patches)
 one,two=assemble(a,'generated'),assemble(b,'generic')
 if payload(one)!=payload(two) or payload(one)!=payload(state['retail']) or same_functions(one,two)!=26:raise ValueError('padders disagree')
 return one,two
