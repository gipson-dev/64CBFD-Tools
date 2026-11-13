"""Qualify paired randomized constructors with retail frame and checked scheduling."""
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
OUT=ROOT/'conker/build/game-random-paired-constructor-qualified'
MANIFEST=json.loads(Path(__file__).with_name('game_random_paired_constructor_match_manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
def payload(path,name):
 t,fs,refs=parse_object(path);f=fs[name];a=f['value'];return t[a:a+f['size']],{i-a:v for i,v in refs.items()if a<=i<a+f['size']}
def assemble(text,label):
 src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
 r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
 if r.returncode:raise ValueError(r.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 if sha((ROOT/'conker/conker.us.bin').read_bytes())!=MANIFEST['rom_sha256']:raise ValueError('Retail image changed')
 if sha((ROOT/'conker/src/game/generated_15D730.c').read_bytes())!=MANIFEST['helper_source_sha256']:raise ValueError('Factory wrapper changed')
 live=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();assert live.endswith(b'\n')
 existing=list(csv.DictReader(io.StringIO(live.decode())));fields=next(csv.reader(io.StringIO(live.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
 for spec in MANIFEST['targets']:writer.writerows(spec['guard_rows'])
 suffix=stream.getvalue().encode();actual=[r for r in existing if r['function'] in {x['name'] for x in MANIFEST['targets']}];wanted=[r for spec in MANIFEST['targets'] for r in spec['guard_rows']]
 installed=actual==wanted
 if actual and not installed:raise ValueError('Unexpected target guards')
 if installed and not live.endswith(suffix):raise ValueError('Installed target guards not at expected suffix')
 guards=OUT/'private-guards.csv';guards.write_bytes(live if installed else live+suffix);result={}
 for spec in MANIFEST['targets']:
  name=spec['name'];source=(ROOT/spec['source']).read_bytes();expected=spec['selected_source'].encode() if installed else spec['old_source'].encode()
  if source!=expected or sha(spec['old_source'].encode())!=spec['baseline_sha256']:raise ValueError('Owner source changed: '+name)
  before,bd=compile_owner(ROOT,OUT,spec['old_source'],name+'-before');after,ad=compile_owner(ROOT,OUT,spec['selected_source'],name+'-after')
  if same_functions(before,after,(name,))!=9 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Neighbor or pool changed: '+name)
  if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Compiler diagnostics changed: '+name)
  raw,_=payload(after,name)
  if len(raw)!=788 or sha(raw)!=spec['raw_sha256'] or raw[:4]!=bytes.fromhex('27bdff48'):raise ValueError('Candidate changed: '+name)
  assembly=(ROOT/spec['assembly']).read_text();marker='glabel '+name+'\n';end='endlabel '+name;fragment=marker+assembly.split(marker,1)[1].split(end,1)[0]+end
  retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+name+',.-'+name+'\n',name+'-retail');truth,refs=payload(retail,name)
  if len(truth)!=788 or sha(truth)!=spec['retail_sha256']:raise ValueError('Retail changed: '+name)
  generated=assemble(pg.emit_padded_assembly(after,ROOT/spec['assembly'],filename=spec['owner'],word_patches_path=guards),name+'-generated')
  generic=assemble(pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',spec['owner'],word_patches_path=guards),name+'-generic')
  if payload(generated,name)!=(truth,refs) or payload(generic,name)!=(truth,refs):raise ValueError('Padded output differs: '+name)
  result[name]=dict(before=before,after=after,retail=retail,generated=generated,generic=generic,installed=installed)
 return result
