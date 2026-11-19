"""SDK32 finite source qualification with full event words and typed actor backing."""
from pathlib import Path
import hashlib,itertools,json,struct,subprocess
from tools.tests import game_actor_burst_150bbb5c_oracle as g
from tools.experiments import game_actor_burst_150bbb5c_recovery as s
from tools.tests.test_game_projected_packet_draw import native_command

def run(attempt="native"):
 r=s.ROOT;o=s.OUT/attempt;s.check_inputs();o.mkdir(parents=True,exist_ok=False)
 W=lambda n:struct.pack('<I',n&0xFFFFFFFF)
 rows=[g.Case(seed,pattern,mutation,0,gate) for seed,pattern,mutation,gate in itertools.product(range(16),range(4),(0,1),range(3))]
 blob=bytearray(W(len(rows)));tags={'sprite':1,'descriptor':2,'position':3,'velocity':4}
 for c in rows:
  initial=g.fixture(c);final,calls,observations=g.reference(initial,c);observations=iter(observations)
  for value in (c.seed,c.pattern,c.gate,c.mutation,*(g.read(initial,address)for address in g.GLOBALS)):blob+=W(value)
  for i in range(512):blob+=W(initial[c.actor+i])
  blob+=W(len(calls))
  for target,args in calls:
   data=[]
   if target in (g.COLOR,g.FACTORY,g.TRAIL):
    observed=next(observations);assert observed[0]==target
    data=list(observed[1])+list(observed[2])if target==g.TRAIL else list(observed[1])
   blob+=W(target)+W(len(args))+b''.join(W(tags[value]if isinstance(value,str)else value)for value in args)
   blob+=W(len(data))+b''.join(W(value)for value in data)
  assert next(observations,None)is None
  for address in g.GLOBALS:blob+=W(g.read(final,address))
  for i in range(512):blob+=W(final[c.actor+i])
 binary=o/'fixture.bin';binary.write_bytes(blob);assembly=o/'fixture.s';obj=assembly.with_suffix('.o')
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_actor_burst_150bbb5c_native.c.in').read_text()
 baseline=(s.FROZEN/s.SOURCE).read_text()
 declarations=baseline.split('/* Emit an attached particle',1)[0].replace('#include <ultra64.h>','')+s.PIN['declarations']
 variants=[('recovered-O'+str(opt),opt,s.PIN['body'],True)for opt in (0,2,3)]
 for label,old,new in s.PIN['negative_controls']:
  assert old in s.PIN['body'],label
  body=s.PIN['body'].replace(old,new)
  if label=='late-size-base-reload':
   body=body.replace('    f32 sizeBase;\n','').replace('            sizeBase = D_8009FEAC;\n','')
  variants.append(('negative-'+label,2,body,False))
 reports=[]
 for label,opt,body,positive in variants:
  source=o/(label+'.c');exe=source.with_suffix('')
  source.write_text(template.replace('@DECLARATIONS@',declarations).replace('@BODY@',body))
  q=subprocess.run(native_command('-O'+str(opt))+['-Wno-return-type','-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(source),str(obj),'-o',str(exe)],capture_output=True,text=True,cwd=r)
  (o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
  (o/(label+'-run.txt')).write_text(q.stdout+q.stderr)
  row=dict(label=label,positive=positive,exit=q.returncode,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest());reports.append(row)
  print(json.dumps(row),flush=True)
  assert q.returncode==(0 if positive else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(rows),positive_runs=3,effective_negatives=len(s.PIN['negative_controls']),
  UBSan=True,strict_aliasing=True,typed_actor_bytes=512,non_null_actor_domain=True,
  descriptor_defined_bytes=112,descriptor_reserved_bytes_excluded=12,sprite_header_bytes=25,
  all18_trail_words_checked=True,all10_sound_words_checked=True,return_unused=True,
  fixture_sha256=hashlib.sha256(blob).hexdigest(),fixture_bytes=len(blob),runs=reports,
  source_installed=False,c_match_credit=0)
 (o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({key:value for key,value in report.items()if key!='runs'}),flush=True)
 s.check_inputs()
 return report

if __name__=='__main__':run()
