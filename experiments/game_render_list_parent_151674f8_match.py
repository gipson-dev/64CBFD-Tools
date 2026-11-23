"""Complete render-list parent: SDK32, callers, closed GPR roles and strict ELF."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_render_list_parent_151674f8_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():
 live=sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
 assert(sha(ROOT/MANIFEST['caller_source'])==MANIFEST['selected_caller_sha256'])==live
 return live
def prepare():
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['caller_source']:MANIFEST['selected_caller_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256']}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 assert sha(TOOLROOT/'experiments/game_render_list_parent_151674f8_role_plan.json')==MANIFEST['role_plan_sha256']
 return live
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments import game_render_list_parent_151674f8_normalize as norm
 where=OUT/'selected'
 for old,new,label,exclude,neighbors in((MANIFEST['old_source'],MANIFEST['selected_source'],'candidate',(FUNCTION,),41),(MANIFEST['old_caller'],MANIFEST['selected_caller'],'caller',(),16)):
  before,bd=compile_owner(ROOT,where,old,'before-'+label,('-O2','-g3'));after,ad=compile_owner(ROOT,where,new,label,('-O2','-g3'))
  assert same_functions(before,after,exclude)==neighbors and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
  if label=='caller':assert payload(after,'func_15018E88')==payload(OUT/'caller-screen/candidate.o','func_15018E88')
 for name,key in(('selected-owner.c','selected_source'),('selected-caller-owner.c','selected_caller'),('body.c','body'),('declarations.c','declarations')):(where/name).write_text(MANIFEST[key])
 text='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(OUT/'baseline/conker/asm/nonmatchings/game_1944C0/func_151674F8.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n'
 norm.assemble(text,OUT/'original-target.o');q=norm.main()
 assert q['guards']==91 and q['neighbors']==41 and sha(OUT/'private-word-patches.csv')==MANIFEST['guards_sha256']and sha(OUT/'qualified-owner/game_1944C0.c.o')==MANIFEST['padded_sha256']
 return q
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_render_list_parent_151674f8_make as make
 from tools.experiments import game_render_list_parent_151674f8_image as image
 make.main();q=image.main();assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
