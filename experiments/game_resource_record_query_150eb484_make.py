"""Replay both actual production owner recipes with private source and guards."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_resource_record_query_150eb484_match as packet

def main():
 packet.prepare()
 r=packet.ROOT;o=packet.OUT;c=r/'conker';shadow=o/'make-owner';reports=[]
 for owner,selected,names in [('1188E0','selected-owner.c',('func_150EB430','func_150EB484','func_150EB614','func_150EB8C4','func_150EBC80')),('CDE80','selected-gate-owner.c',('func_150A34B0','func_150A3504'))]:
  source='src/game/generated_'+owner+'.c';target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
  cmd=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()];q=subprocess.run(cmd,cwd=c,text=True,capture_output=True);assert q.returncode==0,q.stderr;(o/('actual-Make-'+owner+'-plan.txt')).write_text(q.stdout+q.stderr);commands=[];diagnostics=[]
  for line in q.stdout.replace('\\\n','').splitlines():
   args=shlex.split(line)
   if not args or args[0]=='rm':continue
   assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as')
   args=[str(packet.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/selected).relative_to(c).as_posix()if a==source else a for a in args]
   if '>'in args:
    at=args.index('>');assert at==len(args)-2;redirect=c/args[-1];result=subprocess.run(args[:at],cwd=c,capture_output=True,text=True);assert result.returncode==0,(args,result.stdout,result.stderr);redirect.write_text(result.stdout);diagnostics.append(result.stderr)
   else:
    result=subprocess.run(args,cwd=c,capture_output=True,text=True);assert result.returncode==0,(args,result.stdout,result.stderr);diagnostics.append(result.stdout+result.stderr)
   commands.append(args)
  assert len(commands)==(3 if owner=='1188E0'else 5)and not ''.join(diagnostics)
  assert target.read_bytes()==(o/('qualified-owner/'+owner+'-generic.o')).read_bytes()
  raw=Path(str(target)+'.compact');expected=o/('selected-'+owner+'.o')
  assert all(payload(raw,n)==payload(expected,n)for n in names)and normalized_pools(raw)==normalized_pools(expected)
  (o/('actual-Make-'+owner+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n');reports.append(dict(owner=owner,commands=len(commands),GLOBAL_ASM=(owner=='CDE80'),whole_padded_owner_equal=True,raw_bodies_bindings_pools_equal=True,normal_IDO_O2_g3_mips2_o32_profile=True,diagnostics=0,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
 q=dict(owners=reports,source_installed=packet.installed(),matching_credit=0);(o/'make.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=="__main__":main()
