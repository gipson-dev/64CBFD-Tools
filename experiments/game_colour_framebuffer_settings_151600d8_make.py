"""Replay the actual three-command owner recipe with immutable private source."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_colour_framebuffer_settings_151600d8_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;c=r/'conker'
def main():
 target_packet.prepare()
 shadow=o/'make-owner';source='src/game/generated_18D250.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
 cmd=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(cmd,cwd=c,text=True,capture_output=True);assert q.returncode==0,q.stderr;(o/'actual-Make-plan.txt').write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as')
  args=[str(target_packet.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/'selected-owner.c').relative_to(c).as_posix()if a==source else a for a in args]
  if '>'in args:
   at=args.index('>');assert at==len(args)-2;q=subprocess.run(args[:at],cwd=c,text=True,capture_output=True);assert q.returncode==0,q.stderr;(c/args[-1]).write_text(q.stdout);diagnostics.append(q.stderr)
  else:
   q=subprocess.run(args,cwd=c,text=True,capture_output=True);assert q.returncode==0,(args,q.stdout,q.stderr);diagnostics.append(q.stdout+q.stderr)
  commands.append(args)
 assert len(commands)==3 and not ''.join(diagnostics);assert target.read_bytes()==(o/'qualified-owner/generic.o').read_bytes();raw=Path(str(target)+'.compact');assert payload(raw,'func_151600D8')==payload(o/'selected-owner.o','func_151600D8')and normalized_pools(raw)==normalized_pools(o/'selected-owner.o')
 (o/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n');q=dict(commands=3,GLOBAL_ASM_processing=False,whole_padded_owner_equal=True,raw_body_bindings_pools_equal=True,profile_unchanged=True,diagnostics=0,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
