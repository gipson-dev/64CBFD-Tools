"""Replay the actual three-command owner Make recipe using private inputs."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_timed_phase_update_15108658_match as p

def main():
 r=p.ROOT;o=p.OUT;c=r/'conker';shadow=o/'make-owner';source='src/game/generated_135780.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 cmd=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(cmd,cwd=c,text=True,capture_output=True);assert q.returncode==0,q.stderr;(o/'actual-Make-plan.txt').write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as')
  args=[str(p.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/'selected-owner.c').relative_to(c).as_posix()if a==source else a for a in args]
  result=subprocess.run(args,cwd=c,capture_output=True,text=True);assert result.returncode==0,(args,result.stdout,result.stderr);commands.append(args);diagnostics.append(result.stdout+result.stderr)
 assert len(commands)==3 and not ''.join(diagnostics);assert target.read_bytes()==(o/'qualified-owner/generic.o').read_bytes();raw=Path(str(target)+'.compact');assert payload(raw,'func_15108658')==payload(o/'selected-final/owner-candidate.o','func_15108658')and normalized_pools(raw)==normalized_pools(o/'selected-final/owner-candidate.o')
 (o/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n');q=dict(commands=3,GLOBAL_ASM_processing=False,whole_padded_owner_equal=True,raw_body_bindings_and_pools_equal=True,normal_IDO_O2_g3_profile=True,diagnostics=0,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_installed=p.installed(),matching_credit=0);(o/'actual-Make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=="__main__":main()
