"""Replay the proposed/live three-command Make route with scheduling guards."""
from pathlib import Path
import json,shlex,subprocess
from tools.experiments import game_angular_extended_150b2eb4_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
r,o=p.ROOT,p.OUT
def main():
 c=r/'conker';shadow=o/'make-owner';source='src/game/generated_DFBF0.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True);command=['make','-f',(o/'selected-Makefile').relative_to(c).as_posix(),'-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(command,cwd=c,capture_output=True,text=True,check=True);(o/'actual-Make-owner-plan.txt').write_bytes((q.stdout+q.stderr).encode());commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/'selected-final/selected-owner.c').relative_to(c).as_posix()if a==source else str(p.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else a for a in args]
  result=subprocess.run(args,cwd=c,capture_output=True,text=True);assert result.returncode==0,(args,result.stdout,result.stderr);commands.append(args);diagnostics.append(result.stdout+result.stderr)
 assert len(commands)==3;assert target.read_bytes()==(o/'qualified-owner/generic.o').read_bytes();assert payload(Path(str(target)+'.compact'),p.FUNCTION)==payload(o/'selected-final/owner-candidate.o',p.FUNCTION);assert normalized_pools(Path(str(target)+'.compact'))==normalized_pools(o/'selected-final/owner-candidate.o')
 (o/'actual-Make-owner-commands.json').write_bytes((json.dumps(commands,indent=2)+'\n').encode());(o/'actual-Make-owner-diagnostics.txt').write_bytes(''.join(diagnostics).encode());q=dict(commands=len(commands),selected_guard_manifest_replayed=True,pool_checker_replayed=False,owner_has_no_literal_or_data_pools=True,whole_padded_owner_equal=True,proposed_Makefile_sha256=p.sha(o/'selected-Makefile'),Makefile_is_live_proposal=p.installed(),padded_sha256=p.sha(target),source_installed=p.installed(),matching_credit=0);(o/'actual-Make.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
