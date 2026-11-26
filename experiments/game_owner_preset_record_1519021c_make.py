"""Replay the actual three-command owner recipe with immutable private source."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_owner_preset_record_1519021c_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;c=r/'conker'
def warning_signature(text):
 import re
 lines=[line.strip()for line in text.splitlines()if line.strip()];assert len(lines)==12,text;calls=[]
 for i in range(0,len(lines),3):
  assert re.fullmatch(r'cfe: Warning 712: .+, line [0-9]+: illegal combination of pointer and integer',lines[i]),lines[i]
  assert re.fullmatch(r'[- ]+\^',lines[i+2]),lines[i+2];calls.append(lines[i+1])
 assert calls==['func_1518E4A0(arg0);']*2+['func_15190454(arg0);']*2,calls;return calls

def main():
 target_packet.prepare()
 shadow=o/'make-owner';source='src/game/generated_1BA1D0.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
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
 assert len(commands)==3;assert len(warning_signature(''.join(diagnostics)))==4;assert target.read_bytes()==(o/'qualified-owner/generic.o').read_bytes();raw=Path(str(target)+'.compact');assert payload(raw,'func_1519021C')==payload(o/'selected-owner.o','func_1519021C')and normalized_pools(raw)==normalized_pools(o/'selected-owner.o')
 (o/'actual-Make-commands.json').write_text(json.dumps(commands,indent=2)+'\n');q=dict(commands=3,GLOBAL_ASM_processing=False,whole_padded_owner_equal=True,raw_body_bindings_pools_equal=True,profile_unchanged=True,diagnostics=4,new_diagnostics=0,unchanged_existing_warning712=True,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
