"""Private complete impact-response C; source/neighbor/binding checks, no adoption."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-150b8f44-private';FROZEN=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_IMPACT_SCREEN_WORK',PACKET/'qualification/primary')).resolve()
assert OUT.is_relative_to(ROOT/'conker/build')
PIN=json.loads(Path(__file__).with_name('game_impact_terminal_150b8f44_manifest.json').read_text())
NAME='func_150B8F44';SOURCE='conker/src/game/generated_E5E90.c';ENTRY,ROM,SIZE=0x150B8F44,0xE63F4,1564
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def check_inputs():
 pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(pins)==PIN['frozen_inputs']
 for n,h in pins.items():assert sha(ROOT/n)==h and sha(FROZEN/n)==h,n
 return len(pins)

def recover(source):
 old=body(source,NAME);assert old=='s32 func_150B8F44() {\n    return 0;\n}'
 return source.replace(old,PIN['declarations']+'\n'+PIN['body'])

def symbols():return{v[1]:v[2][1]for v in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())}

def prepare():
 check_inputs();OUT.mkdir(parents=True,exist_ok=False);source=(FROZEN/SOURCE).read_text()
 before,bd=compile_owner(ROOT,OUT,source,'baseline');after,ad=compile_owner(ROOT,OUT,recover(source),'candidate');assert bd==ad==''
 assert same_functions(before,after,(NAME,))==7 and normalized_pools(before)==normalized_pools(after)
 raw,refs=payload(after,NAME);expected=lambda k:{int(at):[tuple(v)for v in rows]for at,rows in PIN[k].items()}
 assert len(raw)==1560 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']and refs==expected('refs')
 asm=(FROZEN/'conker/asm/E5E90.s').read_text();fragment='glabel '+NAME+'\n'+asm.split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0]+'.size '+NAME+',.-'+NAME+'\n'
 path=OUT/'original.s';obj=path.with_suffix('.o');path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr
 truth,trefs=payload(obj,NAME);assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']and trefs==expected('retail_refs')
 lookup=symbols();rw=bound_blob(raw,refs,lookup);tw=bound_blob(truth,trefs,lookup);rom=(FROZEN/'conker/conker.us.bin').read_bytes();assert struct.pack('>391I',*tw)==rom[ROM:ROM+SIZE]
 assert 65536-(rw[0]&65535)==65536-(tw[0]&65535)==416
 report=dict(passes=True,raw_words=390,raw_frame=416,retail_words=391,retail_frame=416,neighbors_unchanged=7,pools_unchanged=True,word_differences=sum(a!=b for a,b in zip(rw,tw))+1,frozen_inputs=check_inputs(),source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'proposed-owner.c').write_text(recover(source));print(json.dumps(report),flush=True)
 return dict(raw_words=rw,retail_words=tw,rom=rom)

def state():
 lookup=symbols();return dict(raw_words=bound_blob(*payload(OUT/'candidate.o',NAME),lookup),retail_words=bound_blob(*payload(OUT/'original.o',NAME),lookup),rom=(FROZEN/'conker/conker.us.bin').read_bytes())
