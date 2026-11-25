"""Replay the exact private Make route, including actual GLOBAL_ASM processing."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_height_interpolation_151155c0_match as p
def main():
 r,o=p.ROOT,p.OUT;c=r/'conker';shadow=o/'make-owner';source='src/game/generated_142560.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 cmd=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(cmd,cwd=c,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;(o/'actual-Make-plan.txt').write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[str(p.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else (o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/'selected-owner.c').relative_to(c).as_posix()if a==source else a for a in args];output=None
  if '>'in args:
   at=args.index('>');assert at==len(args)-2;output=c/args[-1];args=args[:at];assert output.resolve().is_relative_to(shadow.resolve());output.parent.mkdir(parents=True,exist_ok=True)
  result=subprocess.run(args,cwd=c,capture_output=True,text=True);assert result.returncode==0,(args,result.stdout,result.stderr)
  if output:output.write_text(result.stdout)
  diagnostics.append(result.stderr if output else result.stdout+result.stderr);commands.append(dict(argv=args,redirect=output.relative_to(c).as_posix()if output else None))
 assert len(commands)==5 and not ''.join(diagnostics);assert target.read_bytes()==(o/'qualified-owner/generic.o').read_bytes();raw=Path(str(target)+'.compact');assert payload(raw,p.FUNCTION)==payload(o/'selected-final/owner-candidate.o',p.FUNCTION)and normalized_pools(raw)==normalized_pools(o/'selected-final/owner-candidate.o')
 (o/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n');q=dict(commands=5,actual_GLOBAL_ASM_pre_and_post_processing=True,whole_padded_owner_equal=True,raw_body_and_pools_equal=True,diagnostics=0,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_installed=p.installed(),matching_credit=0);(o/'actual-Make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
