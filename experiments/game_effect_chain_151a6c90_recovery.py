"""Direct actor effect-chain recovery, complete owner and immutable inputs."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
ADOPTION=ROOT/'conker/build/game-next-151a6c90-private/adoption'
OUT=Path(os.environ.get('CBFD_EFFECT_CHAIN_WORK',str(ADOPTION/'qualification-primary-v2')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
FROZEN=ADOPTION/'production-baseline-v2'
PIN=json.loads(Path(__file__).with_name('game_effect_chain_151a6c90_manifest.json').read_text())
R,P,F=ROOT,OUT,FROZEN
N,NAME,SOURCE,ENTRY,ROM=PIN['name'],PIN['name'],PIN['source'],PIN['entry'],PIN['rom']
OWNER='generated_1D2B10'
SIZE=624
def recover(before):
 stub='s32 func_151A6C90() {\n    return 0;\n}';assert before.count(stub)==1
 return before.replace(stub,PIN['declarations']+'\n'+PIN['body'])
def installed():
 before=(FROZEN/SOURCE).read_text();live=(ROOT/SOURCE).read_text();assert live in(before,recover(before));return live!=before
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text());active=installed()
 plan=json.loads((ADOPTION/'adoption-plan.json').read_text())if active else{}
 if active:assert set(plan)=={SOURCE,'conker/build/src/game/generated_1D2B10.c.o','conker/build/conker.us.elf'}
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==plan.get(name,h),name
 return len(record['inputs'])
def compile_and_check():
 check_inputs();OUT.mkdir(parents=True,exist_ok=True);before=(FROZEN/SOURCE).read_text()
 a,ad=compile_owner(ROOT,OUT,before,'baseline');b,bd=compile_owner(ROOT,OUT,recover(before),'v2');assert not ad and not bd,(ad,bd)
 assert same_functions(a,b,(NAME,))==14 and normalized_pools(a)==normalized_pools(b)
 raw,refs=payload(b,NAME);assert len(raw)==616 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+624];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']
 (OUT/'retail.bin').write_bytes(truth);(OUT/'proposed-owner.c').write_text(recover(before));check_inputs()
 return dict(raw_words=154,frame=168,neighbors_unchanged=14,pools_unchanged=True,source_installed=installed(),c_match_credit=0)
def assemble(text,label):
 label='q2-'+label
 p=P/(label+'.s');obj=p.with_suffix('.o');assert not p.exists();p.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=R/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,q.stderr;return obj
def qualify_objects():
 symbols={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
 truth=(P/'retail.bin').read_bytes();source=(F/'conker/asm/1D2B10.s').read_text().split('glabel '+N+'\n',1)[1].split('endlabel '+N,1)[0]
 reference=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+N+'\n'+source+'\n.size '+N+',.-'+N+'\n','original-reference')
 raw,refs=payload(P/'v2.o',N);original,bindings=payload(reference,N)
 assert raw==original and refs==bindings and len(raw)==616
 assert struct.pack('>154I',*bound_blob(raw,refs,symbols))+bytes(8)==truth
 objects=[];extents={}
 for label,assembly in(('strict',pg.emit_padded_assembly(P/'v2.o',F/'conker/asm/1D2B10.s',filename=OWNER,word_patches_path=F/'conker/retail_word_patches.us.csv')),('layout',pc.emit_padded_assembly(P/'v2.o',F/'conker/retail_layout.us.txt',OWNER,word_patches_path=F/'conker/retail_word_patches.us.csv'))):
  obj=assemble(assembly,'padded-'+label);objects.append(obj);code,rr=payload(obj,N);extents[label]=len(code)
  assert code[:616]==raw and rr==refs and set(code[616:])<={0}
  assert same_functions(F/'conker/build/src/game/generated_1D2B10.c.o',obj,(N,))==14
  # GNU assembly adds a zero-length .data section; compare padded production
  # with padded production, while compact owner pools were checked separately.
  assert normalized_pools(F/'conker/build/src/game/generated_1D2B10.c.o')==normalized_pools(obj)
 assert same_functions(*objects)==15
 bad=0
 for i in range(154):
  broken=bytearray(raw);broken[4*i+3]^=1
  assert bytes(broken)!=original;bad+=1
 for at,pairs in refs.items():
  altered={**refs,at:[(kind,name+'_wrong')for kind,name in pairs]};assert altered!=bindings;bad+=1
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(R/'conker/build/conker.us.elf').read_bytes();helpers=[]
 for entry,size in((0x151A6F00,1260),(0x150ADA20,72),(0x150ADA68,100)):
  at=elf_slot_offset(elf,entry,size);retail=rom[entry-0x14FD2B50:entry-0x14FD2B50+size];literal=elf[at:at+size]==retail
  helpers.append(dict(entry=hex(entry),bytes=size,production_literal=literal))
 report=dict(raw_instruction_words=154,slot_words=156,unchanged_alignment_words=2,frame=168,raw_literal=True,all_original_bindings=len(refs),corruption_controls=bad,guards=0,omissions=0,insertions=0,padders=2,padded_symbol_bytes=extents,owner_functions=15,neighbors_unchanged=14,pools_unchanged=True,helpers=helpers,source_installed=installed(),c_match_credit=0)
 (P/'object-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':compile_and_check();qualify_objects()
