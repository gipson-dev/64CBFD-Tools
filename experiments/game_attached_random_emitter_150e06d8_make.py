"""Replay the unchanged mixed owner recipe and prove baseline reconstruction."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
from tools.experiments import game_attached_random_emitter_150e06d8_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;b=o/'baseline';c=r/'conker';shadow=o/'selected-actual-Make';src='src/game/generated_10CD70.c';target=shadow/(src+'.o');target.parent.mkdir(parents=True,exist_ok=True)
def main():
 target_packet.prepare()
 command=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(command,cwd=c,capture_output=True,text=True);assert q.returncode==0,q.stderr;(o/'selected-actual-Make-plan.txt').write_text(q.stdout+q.stderr);executed=[];removals=[]
 for line in q.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args:continue
  if args[0]=='rm':removals.append(args);continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[str(target_packet.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else(o/'selected-owner.c').relative_to(c).as_posix()if a==src else(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(b/'conker/asm/10CD70.s').relative_to(c).as_posix()if a=='asm/10CD70.s'else a for a in args];result=subprocess.run(args,cwd=c,capture_output=True,text=True);(shadow/('command-'+str(len(executed))+'.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,(args,result.stdout,result.stderr);assert not result.stderr,(args,result.stderr);executed.append(args)
 assert len(executed)==4 and len(removals)==1;assert '-DRETAIL_FUNC_150DFCA8'in executed[1];assert '--function-object'in executed[2]and'--rodata-symbol'in executed[2]and'D_800A0FD0'in executed[2];assert target.read_bytes()==(o/'qualified-owner/selected-generic.o').read_bytes()
 q=dict(planned_commands=5,executed_commands=4,cleanup_commands_deferred_to_retain_evidence=1,base_and_motion_owner_compiles=True,existing_clamp_function_object_selected=True,existing_rodata_anchor_retained='D_800A0FD0',whole_padded_owner_equal=True,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q

if __name__=="__main__":main()
