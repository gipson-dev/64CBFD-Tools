"""Uninstalled complete C recovery, immutable input checks and owner qualification."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-150b89e0-private';FROZEN=PACKET/'baseline';QUALIFICATION=PACKET/'qualification'
OUT=Path(os.environ.get('CBFD_TERMINAL_SCREEN_WORK',QUALIFICATION/'primary')).resolve();assert OUT.is_relative_to(ROOT/'conker/build')
PIN=json.loads(Path(__file__).with_name('game_amplitude_terminal_150b89e0_manifest.json').read_text())
NAME='func_150B89E0';SOURCE='conker/src/game/generated_E5E90.c';ENTRY,ROM,SIZE=0x150B89E0,0xE5E90,1380
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def check_inputs():
 pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(pins)==PIN['frozen_inputs']
 for n,h in pins.items():assert sha(ROOT/n)==h,n
 return len(pins)

def recover(source):
 old=body(source,NAME);assert old=='s32 func_150B89E0() {\n    return 0;\n}'
 return source.replace(old,PIN['declarations']+'\n'+PIN['body'])

def symbols():return{v[1]:v[2][1]for v in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())}

def prepare():
 check_inputs();OUT.mkdir(exist_ok=False);source=(FROZEN/SOURCE).read_text();before,bd=compile_owner(ROOT,OUT,source,'baseline');after,ad=compile_owner(ROOT,OUT,recover(source),'candidate');assert bd==ad==''
 assert same_functions(before,after,(NAME,))==7 and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,NAME)
 assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']and refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 asm=(FROZEN/'conker/asm/E5E90.s').read_text();fragment='glabel '+NAME+'\n'+asm.split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0]+'.size '+NAME+',.-'+NAME+'\n'
 path=OUT/'original.s';obj=path.with_suffix('.o');path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 run=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True);assert run.returncode==0 and not run.stderr
 truth,trefs=payload(obj,NAME);assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']and trefs=={int(k):[tuple(v)for v in values]for k,values in PIN['retail_refs'].items()}
 lookup=symbols();source_words=bound_blob(raw,refs,lookup);retail_words=bound_blob(truth,trefs,lookup);rom=(FROZEN/'conker/conker.us.bin').read_bytes();assert struct.pack('>345I',*retail_words)==rom[ROM:ROM+SIZE]
 report=dict(passes=True,raw_words=345,raw_frame=408,retail_words=345,retail_frame=400,neighbors_unchanged=7,pools_unchanged=True,word_differences=sum(a!=b for a,b in zip(source_words,retail_words)),frozen_inputs=check_inputs(),source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'candidate.body').write_text(PIN['body']);(OUT/'proposed-owner.c').write_text(recover(source));print(json.dumps(report),flush=True)
 return dict(raw_words=source_words,retail_words=retail_words,rom=rom)

def state():
 lookup=symbols();return dict(raw_words=bound_blob(*payload(OUT/'candidate.o',NAME),lookup),retail_words=bound_blob(*payload(OUT/'original.o',NAME),lookup),rom=(FROZEN/'conker/conker.us.bin').read_bytes())

def frame_diagnostic(state):
 """Project measured stack homes only; this is not an installation normalizer."""
 result=[]
 for w in state['raw_words']:
  op,rs,rt=w>>26,w>>21&31,w>>16&31;off=w&65535
  if op==9 and rs==rt==29:
   assert off in(0xfe68,408);w+=8 if off==0xfe68 else-8
  elif rs==29 and op in(9,32,33,35,36,37,40,41,43,49,53,57,61)and off>=96:w=(w&0xffff0000)|(off-(16 if off==108 else 8))
  result.append(w)
 indices=[i for i,(a,b)in enumerate(zip(result,state['retail_words']))if a!=b]
 report=dict(raw_frame=408,retail_frame=400,private_frame_relation_not_proved=True,remaining_differences=len(indices),indices=indices,guard_rows_generated=0,source_installed=False,c_match_credit=0)
 (OUT/'frame-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n');return report
