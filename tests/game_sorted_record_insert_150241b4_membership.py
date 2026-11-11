import json,subprocess
from pathlib import Path
from tools.experiments import game_sorted_record_insert_150241b4_match as p
out=p.out;root=p.root;conker=root/'conker';names=('MIXED_PROFILE_GENERATED_SLICE_O_FILES','STANDARD_GENERATED_SLICE_O_FILES','GLOBAL_ASM_GENERATED_SLICE_O_FILES','UNPADDED_GLOBAL_ASM_O_FILES','RETAIL_PAD_O_FILES','O_FILES')
def main():
 results={};target='build/game-next-15015FBC-private/plan-150241B4/src/game/generated_50D80.c.o'
 for label,src in (('baseline',out/'frozen/conker/Makefile'),('proposed',out/'proposed.Makefile')):
  text=src.read_text();text+='\n'+''.join('$(info AUDIT_'+n+'=$('+n+'))\n'for n in names);p=out/('membership_150241B4_'+label+'.mk');p.write_text(text)
  args=['make','-n','-f',p.relative_to(conker).as_posix(),'-o','Makefile','-o','retail_word_patches.us.csv','BUILD_DIR=build/game-next-15015FBC-private/plan-150241B4',target];r=subprocess.run(args,cwd=conker,capture_output=True,text=True);assert r.returncode==0,r.stderr;lines={line.split('=',1)[0][6:]:line.split('=',1)[1].split()for line in r.stdout.splitlines()if line.startswith('AUDIT_')};assert set(lines)==set(names);results[label]=lines
 for name in names:
  a,b=results['baseline'][name],results['proposed'][name]
  if name=='MIXED_PROFILE_GENERATED_SLICE_O_FILES':assert set(b)-set(a)=={target}and not(set(a)-set(b))
  elif name=='STANDARD_GENERATED_SLICE_O_FILES':assert set(a)-set(b)=={target}and not(set(b)-set(a))
  else:assert a==b,name
 report=dict(target=target,moved_from_standard_to_mixed=True,other_object_lists_identical=True,source_installed=False,makefile_installed=False);(out/'membership_150241B4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
