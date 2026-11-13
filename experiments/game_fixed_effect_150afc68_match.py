"""Qualify the direct fixed-effect packet wrapper against retail."""
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
OUT=ROOT/'conker/build/game-fixed-effect-150afc68-qualified'
MANIFEST=json.loads(Path(__file__).with_name('game_fixed_effect_150afc68_match_manifest.json').read_text())
sha=lambda x:hashlib.sha256(x).hexdigest()
norm=lambda x:x.replace(b'\r\n',b'\n')
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
 guards=ROOT/'conker/retail_word_patches.us.csv';guardbytes=guards.read_bytes()
 if sha(norm(guardbytes))!=spec['guard_sha256_normalized']:raise ValueError('Guard baseline changed')
 if any(r['function']==name for r in csv.DictReader(io.StringIO(guardbytes.decode()))):raise ValueError('Unexpected target guards')
 source=norm((ROOT/spec['source']).read_bytes());old=spec['old_source'].encode();selected=spec['selected_source'].encode()
 if source not in (old,selected) or sha(old)!=spec['baseline_sha256']:raise ValueError('Owner source changed')
 helper=(ROOT/'conker/src/game/generated_19A8B0.c').read_text();proto='void func_1516D99C('+helper.split('void func_1516D99C(',1)[1].split(') {',1)[0]+');'
 if proto!=spec['helper_prototype']:raise ValueError('Factory helper ABI changed')
 before,bd=compile_owner(ROOT,OUT,spec['old_source'],'before');after,ad=compile_owner(ROOT,OUT,spec['selected_source'],'after')
 if same_functions(before,after,(name,))!=17 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Neighbor or pool changed')
 if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Compiler diagnostics changed')
 raw,rawrefs=payload(after,name)
 if len(raw)!=328 or sha(raw)!=spec['raw_sha256']:raise ValueError('Candidate words changed')
 assembly=(ROOT/spec['assembly']).read_text();fragment='glabel '+name+'\n'+assembly.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]+'endlabel '+name
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+name+',.-'+name+'\n','retail');truth,refs=payload(retail,name)
 if (raw,rawrefs)!=(truth,refs):raise ValueError('Direct C differs from retail')
 for kind,text in [('generated',pg.emit_padded_assembly(after,ROOT/spec['assembly'],filename=spec['owner'],word_patches_path=guards)),('generic',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',spec['owner'],word_patches_path=guards))]:
  obj=assemble(text,kind)
  if payload(obj,name)!=(truth,refs):raise ValueError('Padded output differs: '+kind)
 return dict(before=before,after=after,retail=retail,generated=OUT/'generated.o',generic=OUT/'generic.o',installed=source==selected)
