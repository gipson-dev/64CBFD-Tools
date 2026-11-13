"""Qualify the camera direction update against retail instructions."""
import csv,hashlib,io,json,os,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-camera-direction-15122980-qualified'
MANIFEST=json.loads(Path(__file__).with_name('game_camera_direction_15122980_match_manifest.json').read_text())
sha=lambda x:hashlib.sha256(x).hexdigest()
def payload(path,name):
 t,fs,refs=parse_object(path);f=fs[name];a=f['value'];return t[a:a+f['size']],{i-a:v for i,v in refs.items() if a<=i<a+f['size']}
def assemble(text,label):
 src=OUT/(label+'.s');obj=OUT/(label+'.o');src.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);spec=MANIFEST;name=spec['name']
 if sha((ROOT/'conker/conker.us.bin').read_bytes())!=spec['rom_sha256']:raise ValueError('Retail input changed')
 live=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();assert live.endswith(b'\n')
 existing=list(csv.DictReader(io.StringIO(live.decode())));fields=next(csv.reader(io.StringIO(live.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(spec['guard_rows']);suffix=stream.getvalue().encode()
 actual=[r for r in existing if r['function']==name];installed=actual==spec['guard_rows']
 if actual and not installed:raise ValueError('Unexpected target guards')
 if installed and not live.endswith(suffix):raise ValueError('Installed guards not at expected suffix')
 source=(ROOT/spec['source']).read_bytes();expected=spec['selected_source'].encode() if installed else spec['old_source'].encode()
 if source!=expected or sha(spec['old_source'].encode())!=spec['baseline_sha256']:raise ValueError('Owner source changed')
 guards=OUT/'private-guards.csv';guards.write_bytes(live if installed else live+suffix)
 before,bd=compile_owner(ROOT,OUT,spec['old_source'],'before');after,ad=compile_owner(ROOT,OUT,spec['selected_source'],'after')
 if same_functions(before,after,(name,))!=1 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Neighbor or pool changed')
 if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Compiler diagnostics changed')
 raw,_=payload(after,name)
 if len(raw)!=348 or sha(raw)!=spec['raw_sha256']:raise ValueError('Candidate words changed')
 assembly=(ROOT/spec['assembly']).read_text(); fragment='glabel '+name+'\n'+assembly.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]+'endlabel '+name;retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+name+',.-'+name+'\n','retail');truth,refs=payload(retail,name)
 if len(truth)!=348 or sha(truth)!=spec['retail_sha256']:raise ValueError('Retail words changed')
 single=OUT/'single-guards.csv';only=io.StringIO(newline='');w=csv.DictWriter(only,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(spec['guard_rows']);single.write_text(only.getvalue())
 parts=['.section .text, "ax"','.set noat','.set noreorder','.set gp=64','.globl '+name,'.type '+name+',@function',name+':']
 import struct
 raw,rawrefs=payload(after,name)
 for offset in range(0,len(raw),4):
  for kind,symbol in rawrefs.get(offset,[]):parts.append('.reloc ., '+kind+', '+symbol)
  parts.append('.word 0x%08X'%struct.unpack_from('>I',raw,offset)[0])
 parts.append('.size '+name+',.-'+name);singleobj=assemble('\n'.join(parts)+'\n','single')
 if payload(singleobj,name)!=(raw,rawrefs):raise ValueError('Single-function extraction changed')
 for kind,text in [('generated',pg.emit_padded_assembly(after,ROOT/spec['assembly'],filename=spec['owner'],word_patches_path=guards)),('generic',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',spec['owner'],word_patches_path=guards))]:
  obj=assemble(text,kind)
  if payload(obj,name)!=(truth,refs):raise ValueError('Padded output differs: '+kind)
 return dict(before=before,after=after,retail=retail,generated=OUT/'generated.o',generic=OUT/'generic.o',installed=installed)
