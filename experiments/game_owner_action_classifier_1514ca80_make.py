"""Replay the actual three-command owner recipe with immutable private source."""
from tools.experiments import game_owner_action_classifier_1514ca80_match as target_packet
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(target_packet.ROOT))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
r=target_packet.ROOT;o=target_packet.OUT;c=r/'conker'
def warning_signature(text):
 rows=diagnostic_rows(text);expected=diagnostic_rows((o/'before-owner-diagnostics.txt').read_text());assert rows==expected,(rows,expected);return []

def main():
 target_packet.prepare()
 shadow=o/'make-owner';source='src/game/generated_179F30.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 cmd=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(cmd,cwd=c,text=True,capture_output=True);assert q.returncode==0,q.stderr;(o/'actual-Make-plan.txt').write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as')
  args=[str(target_packet.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/'selected-owner.c').relative_to(c).as_posix()if a==source else a for a in args]
  if '>'in args:
   at=args.index('>');assert at==len(args)-2;q=subprocess.run(args[:at],cwd=c,text=True,capture_output=True);assert q.returncode==0,q.stderr;(c/args[-1]).write_text(q.stdout);diagnostics.append(q.stderr)
  else:
   q=subprocess.run(args,cwd=c,text=True,capture_output=True);assert q.returncode==0,(args,q.stdout,q.stderr);diagnostics.append(q.stderr);assert not q.stdout or args[1].endswith('check_bouncing_effect_150db114_pool.py')
  commands.append(args)
 assert len(commands)==3;assert warning_signature(''.join(diagnostics))==[];assert target.read_bytes()==(o/'qualified-owner/selected-generic.o').read_bytes();raw=Path(str(target)+'.compact');assert payload(raw,'func_1514CA80')==payload(o/'selected-owner.o','func_1514CA80')and normalized_pools(raw)==normalized_pools(o/'selected-owner.o')
 (o/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n');q=dict(commands=3,GLOBAL_ASM_processing=False,whole_padded_owner_equal=True,raw_body_bindings_pools_equal=True,profile_unchanged=True,diagnostics=4,new_diagnostics=0,unchanged_existing_diagnostics=True,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
