"""Reproduce the shared-header consumer; audit every debugger object section."""
from pathlib import Path
import hashlib,json,re,shlex,subprocess
from tools.experiments import game_actor_preset_constructor_15196438_match as p
from tools.experiments.game_channel_command_poller_header_audit import audit_owner
from tools.experiments.game_actor_classifier_candidates import sections
NAME='conker/build/src/debugger_258ED0.c.o'
EXPECTED='e7ee62423430a1ec75906e1a853b0b51d0249003f0db4747a63a650e0f44eac5'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def metadata(before,after):
 pattern=rb'(</4Debug/>\0[^\0]+\0)([0-9]{10})(\0)([0-9]+)(\0)';a=list(re.finditer(pattern,before));b=list(re.finditer(pattern,after));assert len(a)==len(b)==43
 oldtime={m[2]for m in a};newtime={m[2]for m in b};assert len(oldtime)==len(newtime)==1;oldtime=oldtime.pop();newtime=newtime.pop();headers=0
 oldsize=len((p.OUT/'baseline/conker/include/functions.h').read_bytes());newsize=len(p.MANIFEST['selected_sources']['conker/include/functions.h'].encode())
 def replace(m):
  nonlocal headers
  size=m[4]
  if m[1].endswith(b'/functions.h\0'):
   assert size==str(oldsize).encode();size=str(newsize).encode();headers+=1
  return m[1]+newtime+m[3]+size+m[5]
 expected=re.sub(pattern,replace,before);assert headers==1 and expected==after,'Unexpected debugger metadata byte'
 return dict(file_records=43,uniform_compiler_timestamp_substitution=True,functions_header_bytes_before=oldsize,functions_header_bytes_after=newsize,every_metadata_byte_reconstructed=True)
def audit():
 old=p.OUT/'baseline'/NAME;new=p.ROOT/NAME;assert sha(old)==p.MANIFEST['inputs'][NAME]and sha(new)==EXPECTED
 q=audit_owner(old,new);assert q['functions_fixed']==1 and {x['section']for x in q['changed_sections']}=={'.mdebug'}and not any(q['symbol_changes'].values())
 proof=metadata(sections(old)['.mdebug'][1],sections(new)['.mdebug'][1]);return dict(object=NAME,before_sha256=sha(old),after_sha256=sha(new),metadata=proof,**q)
def main():
 r,o=p.ROOT,p.OUT;c=r/'conker';root=o/'debugger-recipe-audit';root.mkdir(exist_ok=True);rows=[]
 for phase,header in(('before',(o/'baseline/conker/include/functions.h').read_text()),('after',p.MANIFEST['selected_sources']['conker/include/functions.h'])):
  w=root/'controlled';overlay=w/'headers';overlay.mkdir(parents=True,exist_ok=True);(overlay/'functions.h').write_text(header);target=w/'src/debugger_258ED0.c.o';target.parent.mkdir(exist_ok=True);q=subprocess.run(['make','-n','-B','-o','Makefile','BUILD_DIR='+w.relative_to(c).as_posix(),target.relative_to(c).as_posix()],cwd=c,capture_output=True,text=True,check=True);(root/(phase+'-Make-plan.txt')).write_text(q.stdout+q.stderr);commands=[]
  for line in q.stdout.replace('\\\n','').splitlines():
   args=shlex.split(line)
   if not args or args[0]=='rm':continue
   assert args[0]in('python3','../ido/ido5.3_recomp/cc','mips-linux-gnu-as')
   args=[str(p.TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else a for a in args]
   if args[0]=='../ido/ido5.3_recomp/cc':args[1:1]=['-I',overlay.relative_to(c).as_posix()]
   dest=None
   if '>'in args:assert args[-2]=='>'and args.count('>')==1;dest=c/args[-1];args=args[:-2]
   q=subprocess.run(args,cwd=c,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
   if dest:dest.write_text(q.stdout)
   commands.append(args)
  expected=o/'baseline'/NAME if phase=='before'else r/NAME
  saved=root/(phase+'.o');saved.write_bytes(target.read_bytes());comparison=audit_owner(expected,saved);assert {x['section']for x in comparison['changed_sections']}<={'.mdebug'}and not any(comparison['symbol_changes'].values())
  rows.append(dict(phase=phase,commands=len(commands),all_non_debug_sections_and_symbols_reproduced=True,sha256=sha(target)))
 before,after=[sections(root/(n+'.o'))['.mdebug'][1]for n in('before','after')];old,new=[sections(f)['.mdebug'][1]for f in(o/'baseline'/NAME,r/NAME)];assert len(before)==len(after)and len(old)==len(new)
 controlled=metadata(before,after);bad=bytearray(new);bad[0]^=1
 try:metadata(old,bad)
 except AssertionError:pass
 else:raise AssertionError('Metadata comparator accepted unrelated mutation')
 tooling={f.relative_to(p.TOOLROOT).as_posix():sha(f)for f in(p.TOOLROOT/'asm-processor').rglob('*.py')};assert 'asm-processor/asm_processor.py'in tooling
 (o/'debugger-recipe-log.json').write_text(json.dumps(rows,indent=2)+'\n');report=dict(actual_Make_commands=sum(x['commands']for x in rows),recipe_tooling=tooling,controlled_header_pair=controlled,production=audit(),all_other_object_bytes_and_symbols_fixed=True,effective_unrelated_metadata_rejection=True,exclusions=0,source_installed=p.installed(),matching_credit=0);(o/'debugger-header-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
