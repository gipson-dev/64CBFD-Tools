"""Qualify two display-state functions and their corrected inventory boundary."""
import csv,hashlib,io,json,os,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-hud-state-15178eb0-qualified'
MANIFEST=json.loads(Path(__file__).with_name('game_hud_state_15178eb0_match_manifest.json').read_text())
NAMES=('func_15178EB0','func_15178EFC')
sha=lambda x:hashlib.sha256(x).hexdigest()
norm=lambda x:sha(x.replace(b'\r\n',b'\n'))
def assemble(text,label):
 src=OUT/(label+'.s');obj=OUT/(label+'.o');src.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);s=MANIFEST
 if sha((ROOT/'conker/conker.us.bin').read_bytes())!=s['rom_sha256']:raise ValueError('Retail input changed')
 live=(ROOT/s['source']).read_bytes()
 if live==s['old_source'].encode():installed=False
 elif live==s['selected_source'].encode():installed=True
 else:raise ValueError('Owner source changed')
 if sha(s['old_source'].encode())!=s['baseline_sha256']:raise ValueError('Baseline owner changed')
 files={'layout':'conker/retail_layout.us.txt','symbols':'conker/symbol_addrs.us.txt','auto':'conker/undefined_funcs_auto.txt','guards':'conker/retail_word_patches.us.csv'}
 for key,path in files.items():
  value=(ROOT/path).read_bytes()
  if norm(value)!=s[key+('_after' if installed else '_before')]:raise ValueError('Inventory input changed '+key)
 if installed:
  for key,path in files.items():(OUT/('private-'+key+'.txt')).write_bytes((ROOT/path).read_bytes())
 else:
  old=b'game,generated_1A6360,func_15178EB0,0x15178EB0,0x15179008'
  new=b'game,generated_1A6360,func_15178EB0,0x15178EB0,0x15178EFC\ngame,generated_1A6360,func_15178EFC,0x15178EFC,0x15179008'
  data=(ROOT/files['layout']).read_bytes();assert data.count(old)==1;(OUT/'private-layout.txt').write_bytes(data.replace(old,new))
  data=(ROOT/files['symbols']).read_bytes();assert b'func_15178EFC' not in data;(OUT/'private-symbols.txt').write_bytes(data+b'func_15178EFC = 0x15178EFC; // type:func defined:true\n')
  data=(ROOT/files['auto']).read_bytes();line=b'func_15178EFC = 0x15178EFC;';assert data.count(line)==1
  ending=b'\r\n' if line+b'\r\n' in data else b'\n';(OUT/'private-auto.txt').write_bytes(data.replace(line+ending,b'',1))
  data=(ROOT/files['guards']).read_bytes();fields=next(csv.reader(io.StringIO(data.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(s['guard_rows']);(OUT/'private-guards.txt').write_bytes(data+stream.getvalue().encode())
 for key in files:
  if norm((OUT/('private-'+key+'.txt')).read_bytes())!=s[key+'_after']:raise ValueError('Proposed inventory input changed '+key)
 before,bd=compile_owner(ROOT,OUT,s['old_source'],'before');after,ad=compile_owner(ROOT,OUT,s['selected_source'],'after')
 if same_functions(before,after,NAMES)!=7 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Owner neighbors or pools changed')
 if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Diagnostics changed')
 truth={}
 assembly=(ROOT/s['assembly']).read_text()
 for i,name in enumerate(NAMES):
  raw,refs=payload(after,name)
  if sha(raw)!=s['raw_sha256'][i]:raise ValueError('Candidate words changed '+name)
  fragment='glabel '+name+'\n'+assembly.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]+'endlabel '+name
  obj=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+name+',.-'+name+'\n','retail-'+name)
  data,r=payload(obj,name);truth[name]=(data,r)
  if sha(data)!=s['retail_sha256'][i] or refs!=r:raise ValueError('Retail words or bindings changed '+name)
  if i==0 and (raw,refs)!=(data,r):raise ValueError('Initializer is not direct')
 for kind,text in [('generated',pg.emit_padded_assembly(after,ROOT/s['assembly'],filename=s['owner'],word_patches_path=OUT/'private-guards.txt')),('generic',pc.emit_padded_assembly(after,OUT/'private-layout.txt',s['owner'],word_patches_path=OUT/'private-guards.txt'))]:
  obj=assemble(text,kind)
  for name in NAMES:
   if payload(obj,name)!=truth[name]:raise ValueError('Padded output differs: '+kind+' '+name)
 return dict(before=before,after=after,installed=installed)
