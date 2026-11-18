"""Cached steering-factor recovery and full relation; no normalization or adoption."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments import game_target_terminal_150b963c_screen as semantic
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT,PACKET,FROZEN,NAME,SOURCE,ENTRY,ROM,SIZE=(getattr(semantic,n)for n in('ROOT','PACKET','FROZEN','NAME','SOURCE','ENTRY','ROM','SIZE'))
STAGE=PACKET/'adoption-relation';OUT=Path(os.environ.get('CBFD_TARGET_FIT_WORK',STAGE/'preview')).resolve();assert OUT.is_relative_to(ROOT/'conker/build')
PIN=json.loads(Path(__file__).with_name('game_target_terminal_150b963c_fitting_manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
symbols=semantic.symbols

def check_inputs():
 count=semantic.check_inputs();extra=json.loads((STAGE/'dependency-baseline/fingerprints.json').read_text());assert len(extra)==7
 for name,h in extra.items():assert sha(ROOT/name)==h and sha(STAGE/'dependency-baseline'/name)==h,name
 return count+len(extra)

def recover(text):
 old=body(text,NAME);assert old=='s32 func_150B963C() {\n    return 0;\n}'
 return text.replace(old,PIN['declarations']+'\n'+PIN['body'])

def prepare():
 check_inputs();OUT.mkdir(parents=True,exist_ok=False);semantic.OUT=OUT;text=(FROZEN/SOURCE).read_text()
 before,bd=compile_owner(ROOT,OUT,text,'baseline');after,ad=compile_owner(ROOT,OUT,recover(text),'candidate');assert bd==ad==''
 assert same_functions(before,after,(NAME,))==7 and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,NAME);expected=lambda k:{int(at):[tuple(v)for v in rows]for at,rows in PIN[k].items()}
 assert len(raw)==1736 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']and refs==expected('refs')
 asm=(FROZEN/'conker/asm/E5E90.s').read_text();fragment='glabel '+NAME+'\n'+asm.split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0]+'.size '+NAME+',.-'+NAME+'\n';path=OUT/'original.s';obj=path.with_suffix('.o');path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr
 truth,trefs=payload(obj,NAME);assert len(truth)==1752 and hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']and trefs==expected('retail_refs')
 lookup=symbols();rw=bound_blob(raw,refs,lookup);tw=bound_blob(truth,trefs,lookup);rom=(FROZEN/'conker/conker.us.bin').read_bytes();assert struct.pack('>438I',*tw)==rom[ROM:ROM+SIZE]
 assert 65536-(rw[0]&65535)==392 and 65536-(tw[0]&65535)==384
 report=dict(passes=True,raw_words=434,raw_frame=392,retail_words=438,retail_frame=384,neighbors_unchanged=7,pools_unchanged=True,bindings=sum(map(len,refs.values())),frozen_inputs=check_inputs(),source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'proposed-owner.c').write_text(recover(text));print(json.dumps(report),flush=True)
 return dict(raw_words=rw,retail_words=tw,rom=rom)

def state():
 semantic.OUT=OUT;lookup=symbols();return dict(raw_words=bound_blob(*payload(OUT/'candidate.o',NAME),lookup),retail_words=bound_blob(*payload(OUT/'original.o',NAME),lookup),rom=(FROZEN/'conker/conker.us.bin').read_bytes())
