"""Replay both real Make recipes in private output directories."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
from tools.experiments import game_ground_burst_callback_150df334_match as packet
r,o=packet.ROOT,packet.OUT
c=r/'conker'
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def build(source,selected,label,expected,compact,function,neighbors):
 shadow=o/('make-'+label);target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 q=subprocess.run(['make','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()],cwd=c,capture_output=True,text=True,check=True)
 (o/('actual-Make-'+label+'-plan.txt')).write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[selected.relative_to(c).as_posix()if a==source else(o/'private-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  args=[str(packet.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else a for a in args]
  redirect=None
  if'>'in args:
   assert args[-2]=='>'and args.count('>')==1;redirect=(c/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  p=subprocess.run(args,cwd=c,capture_output=True,text=True);assert p.returncode==0,(args,p.stdout,p.stderr)
  if redirect:redirect.write_text(p.stdout)
  else:diagnostics.append(p.stdout+p.stderr)
  commands.append(args)
 (o/('actual-Make-'+label+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n');(o/('actual-Make-'+label+'-diagnostics.txt')).write_text(''.join(diagnostics))
 assert target.read_bytes()==expected.read_bytes(),('Whole padded owner changed',label,sha(target),sha(expected))
 assert payload(Path(str(target)+'.compact'),function)==payload(compact,function)
 if label=='caller':assert same_functions(Path(str(target)+'.compact'),compact,())==16
 baseline=o/'baseline/conker/build'/Path(source+'.o')
 if not baseline.is_file():baseline=o/'additional-baseline/conker/build'/Path(source+'.o')
 assert same_functions(baseline,target,(function,))==neighbors
 assert normalized_pools(target)==normalized_pools(baseline)
 return dict(commands=len(commands),complete_padded_owner_equal=True,all_neighbors_and_pools_fixed=neighbors,sha256=sha(target),object=str(target.relative_to(o)))
def main():
 report=build('src/game/generated_10C170.c',o/'selected-final/selected-owner.c','owner',o/'qualified-owner/generated_10C170.c.o',o/'selected-final/candidate.o','func_150DF334',2)
 report.update(source_installed=packet.installed(),matching_credit=0)
 (o/'actual-Make-owner.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
