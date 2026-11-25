"""Replay the actual Make commands for both changed source owners privately."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_sibling_preset_150b5c38_match as p
def main():
 r,o=p.ROOT,p.OUT;c=r/'conker';shadow=o/'make-owner'
 rows=[('target','src/game/generated_E2DA0.c','selected-owner.c','qualified-owner/generic.o','matched-sibling-order.o','func_150B5C38'),('producer','src/game_981E0.c','best-producer.c','qualified-owner/producer-after.o','caller-position-first.o','func_15071690')]
 reports={}
 for label,source,selected,qualified,raw,fn in rows:
  target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True)
  cmd=['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()]
  q=subprocess.run(cmd,cwd=c,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;(o/('actual-Make-'+label+'-plan.txt')).write_text(q.stdout+q.stderr)
  commands=[];diagnostics=[]
  for line in q.stdout.replace('\\\n','').splitlines():
   args=shlex.split(line)
   if not args or args[0]=='rm':continue
   assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
   args=[(o/'selected-guards.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else(o/selected).relative_to(c).as_posix()if a==source else str(p.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else a for a in args]
   output=None
   if '>'in args:
    at=args.index('>');assert at==len(args)-2;output=c/args[-1];args=args[:at];assert output.resolve().is_relative_to(shadow.resolve());output.parent.mkdir(parents=True,exist_ok=True)
   result=subprocess.run(args,cwd=c,capture_output=True,text=True);assert result.returncode==0,(args,result.stdout,result.stderr)
   if output is not None:output.write_text(result.stdout)
   commands.append(dict(argv=args,redirect=str(output.relative_to(c))if output else None));diagnostics.append(result.stderr if output else result.stdout+result.stderr)
  assert len(commands)==(3 if label=='target'else 5),commands
  assert target.read_bytes()==(o/qualified).read_bytes()
  compact=Path(str(target)+'.compact');assert payload(compact,fn)==payload(o/raw,fn);assert normalized_pools(compact)==normalized_pools(o/raw)
  if label=='target':assert not ''.join(diagnostics)
  else:
   prior=(o/'producer-before.diagnostics.txt')
   assert sum(diagnostic_rows(''.join(diagnostics)).values())==36
  (o/('actual-Make-'+label+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n');(o/('actual-Make-'+label+'-diagnostics.txt')).write_text(''.join(diagnostics))
  reports[label]=dict(commands=len(commands),raw_function_and_pools_equal=True,whole_padded_object_equal=True,padded_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),diagnostic_count=sum(diagnostic_rows(''.join(diagnostics)).values()))
 reports.update(both_changed_owners_replayed=True,producer_whole_object_identical_to_frozen_baseline=True,source_installed=p.installed(),matching_credit=0)
 (o/'actual-Make.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
 return reports
if __name__=='__main__':main()
