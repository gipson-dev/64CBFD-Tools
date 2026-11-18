"""Compile complete uninstalled parent recoveries; no byte-match adoption gate."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-150b7b40-private';ADOPTION=PACKET/'adoption';FROZEN=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_PARENT_SCREEN_WORK',ADOPTION/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_actor_bound_burst_150b7b40_manifest.json').read_text())
NAME='func_150B7B40';SOURCE='conker/src/game/generated_E4070.c';OBJECT='conker/build/src/game/generated_E4070.c.o'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check_inputs():
 pins=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(pins)==1696
 for name,h in pins.items():assert sha(ROOT/name)==sha(FROZEN/name)==h,name
 assert (ROOT/SOURCE).read_text().count('s32 func_150B7B40() {\n    return 0;\n}')==1
 return len(pins)
def source_for(label):
 text=(FROZEN/SOURCE).read_text();stub='s32 func_150B7B40() {\n    return 0;\n}';assert text.count(stub)==1
 return text.replace(stub,PIN['declarations']+'\n'+PIN['variants'][label]['body'])
def compile_variant(label,body=None):
 text=source_for(label)if body is None else source_for('captured-model').replace(PIN['variants']['captured-model']['body'],body)
 obj,d=compile_owner(ROOT,OUT,text,label);assert not d
 assert same_functions(OUT/'baseline.o',obj,(NAME,))==20 and normalized_pools(OUT/'baseline.o')==normalized_pools(obj)
 return obj
def qualify():
 check_inputs();OUT.mkdir(parents=True,exist_ok=False)
 base,d=compile_owner(ROOT,OUT,(FROZEN/SOURCE).read_text(),'baseline');assert not d
 assembly=(FROZEN/'conker/asm/E4070.s').read_text();fragment='glabel '+NAME+'\n'+assembly.split('glabel '+NAME+'\n')[1].split('endlabel '+NAME)[0]+'.size '+NAME+',.-'+NAME+'\n'
 asm=OUT/'original.s';original=asm.with_suffix('.o');asm.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(original),str(asm)],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,(q.stdout,q.stderr)
 symbols={v[1]:v[2][1]for v in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())}
 truth=(FROZEN/'conker/conker.us.bin').read_bytes()[0xE4FF0:0xE5780];assert len(truth)==1936
 assert struct.pack('>484I',*bound_blob(*payload(original,NAME),symbols))==truth
 (OUT/'retail.bin').write_bytes(truth);reports=[]
 for label,pin in PIN['variants'].items():
  obj=compile_variant(label);raw,refs=payload(obj,NAME);assert sha(OUT/(label+'.c'))==hashlib.sha256(source_for(label).encode()).hexdigest()
  assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256'] and refs=={int(k):[tuple(v)for v in rows]for k,rows in pin['refs'].items()}
  words=bound_blob(raw,refs,symbols);assert len(words)==pin['words'] and 65536-(words[0]&65535)==pin['frame']==600
  original_words=list(struct.unpack('>484I',truth));reports.append(dict(label=label,words=len(words),frame=600,retail_frame=616,differing_words=sum(x!=y for x,y in zip(words,original_words))+abs(len(words)-484),neighbors_unchanged=20,pools_unchanged=True,c_match_credit=0))
 report=dict(passes=True,variants=reports,original_assembly_and_ROM_verified=True,source_installed=False,padders_inductive_and_adoption_pending=True,native_and_caller_checks_separate=True,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
def controls():
 from tools.tests import game_actor_bound_burst_150b7b40_oracle as g
 programs=g.streams();truth=programs[0][1];cases=list(g.cases());expected={}
 for i,c in enumerate(cases):
  m=g.Oracle(truth,c).run();expected[i]=(m.calls,g.public(m.memory),m.r[2])
 body=PIN['variants']['captured-model']['body'];symbols={v[1]:v[2][1]for v in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())};reports=[]
 for label,old,new in(('heading','& 127;','& 63;'),('pitch','pitch = -32 -','pitch = -31 -'),('floor-depth','- 2000.0f','- 2048.0f'),('child-duration','child.field54 = 300;','child.field54 = 299;'),('spray-kind','0x220005;','0x220004;'),('spray-damping','spray.field18 = D_8009FD64;','spray.field18 = D_8009FD60;'),('clamp-upper','if (factorX > 1.0f) factorX = 1.0f;','if (factorX > 1.0f) factorX = 2.0f;'),('loop-count','while (index < 2);','while (index < 1);')):
  assert old in body,label;obj=compile_variant('negative-'+label,body.replace(old,new));words=bound_blob(*payload(obj,NAME),symbols);caught=None
  for i,c in enumerate(cases):
   m=g.Oracle(words,c,entry=0x15200000).run()
   if (m.calls,g.public(m.memory),m.r[2])!=expected[i]:caught=i;break
  assert caught is not None,('ineffective source negative',label)
  reports.append(dict(label=label,rejected_by_semantic_observation=True,first_case=caught))
 report=dict(passes=True,effective_source_negatives=reports,c_match_credit=0);(OUT/'controls-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
