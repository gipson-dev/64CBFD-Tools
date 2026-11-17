"""Private ground-link fitting gates; no installation or matching credit."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
ADOPTION=ROOT/'conker/build/game-next-151aadf8-private'
OUT=Path(os.environ.get('CBFD_GROUND_LINK_PRIVATE_WORK',ADOPTION/'qualification-primary'))
PIN=json.loads(Path(__file__).with_name('game_ground_link_151aadf8_private_manifest.json').read_text())
ENTRY=PIN['entry']
def installed():return False
def check_inputs():
 for name,h in PIN['baseline']['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert (ROOT/PIN['source']).read_text()==PIN['baseline_source']
def assemble(text,label):
 src=OUT/(label+'.s');obj=src.with_suffix('.o');assert not src.exists();src.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 return obj
def prepare():
 check_inputs();OUT.mkdir(exist_ok=False);before=PIN['baseline_source'];base,diag=compile_owner(ROOT,OUT,before,'baseline');assert not diag,diag
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[PIN['rom']:PIN['rom']+PIN['retail_bytes']];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256'];(OUT/'retail.bin').write_bytes(truth)
 rows=[]
 for label,v in PIN['variants'].items():
  source=before.replace('s32 func_151AADF8() {\n    return 0;\n}',v['declarations']+'\n'+v['body']);assert source!=before
  obj,diag=compile_owner(ROOT,OUT,source,label);assert not diag,diag;raw,refs=payload(obj,PIN['name']);assert hashlib.sha256(raw).hexdigest()==v['report']['raw_sha256']
  assert len(raw)==v['report']['words']*4 and same_functions(base,obj,(PIN['name'],))==40 and normalized_pools(base)==normalized_pools(obj)
  (OUT/('body-'+label+'.txt')).write_text(v['body']);(OUT/('declarations-'+label+'.txt')).write_text(v['declarations'])
  for kind,text in(('strict',pg.emit_padded_assembly(obj,ROOT/'conker/asm/1D6E80.s',filename=PIN['owner'],word_patches_path=ROOT/'conker/retail_word_patches.us.csv')),('layout',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',PIN['owner'],word_patches_path=ROOT/'conker/retail_word_patches.us.csv'))):
   padded=assemble(text,label+'-'+kind);b,r=payload(padded,PIN['name']);assert b==raw and r==refs
   text_bytes,functions,_=pg.parse_object(padded);start=functions[PIN['name']]['value']
   assert text_bytes[start:start+PIN['retail_bytes']]==raw+bytes(PIN['retail_bytes']-len(raw))
   production=pg.parse_object(ROOT/'conker/build/src/game/generated_1D6E80.c.o')[1]
   assert all(f['value']==production[n]['value']for n,f in functions.items())
   assert same_functions(ROOT/'conker/build/src/game/generated_1D6E80.c.o',padded,(PIN['name'],))==40
   assert normalized_pools(ROOT/'conker/build/src/game/generated_1D6E80.c.o')==normalized_pools(padded)
  rows.append(dict(label=label,words=len(raw)//4,frame=v['report']['frame'],neighbors_preserved=40,padders=2,raw_sha256=v['report']['raw_sha256']))
 check_inputs();report=dict(variants=rows,immutable_inputs=len(PIN['baseline']['inputs']),new_guards=0,source_installed=False,c_match_credit=0)
 (OUT/'object-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
