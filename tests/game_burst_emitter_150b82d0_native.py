"""Native32 execution of the explicitly sequenced complete burst source."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.tests import game_burst_emitter_150b82d0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def main():
 p=g.p;W=lambda n:struct.pack('<I',n&0xffffffff);windows=[(g.INPUT,0x120),(g.OUTPUT,32),(g.MARK,4)]
 def native_bytes(m,a,n):
  raw=g.data(m,a,n);return b''.join(raw[i:i+4][::-1]for i in range(0,n,4))
 def trace(calls):
  h=2166136261
  def word(v):
   nonlocal h
   h=((h^v)*16777619)&0xffffffff
  for t,args,observed in calls:
   word(t);word(len(args))
   for arg in args:word(0xffffff00+arg[1]if isinstance(arg,tuple)else arg)
   word(len(observed))
   for b in observed:word(b)
  return h
 cases=list(g.cases());out=bytearray(W(len(cases))+W(3))
 for c in cases:
  initial=g.fixture(c);expected,s,trips=g.reference(initial,c)
  for n in(c.seed,c.initial,c.mutation,c.success,*g.args(c),trace(s.calls),trips):out+=W(n)
  for a,n in windows:out+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(expected,a,n)
 fixture=p/'native-fixture.bin';fixture.write_bytes(out);assembly=p/'native-fixture.s';obj=p/'native-fixture.o'
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 body=(p/'candidate.body').read_text();template=Path(__file__).with_name('game_burst_emitter_150b82d0_native.c.in').read_text();variants=[('O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in(('count','% 26U + 35','% 25U + 35'),('pitch','% 61U - 63','% 60U - 63'),('heading','& 255;','& 127;'),('ratio','position.y *= *ratio;','position.y += *ratio;'),('rotation','* 360.0f;','* 359.0f;'),('acceleration','+ -1570.0f','+ -1569.0f'),('sample-order','firstSample = func_150ADA68();\n            secondSample = func_150ADA68();','secondSample = func_150ADA68();\n            firstSample = func_150ADA68();'),('duration','% 51U + 75','% 51U + 74')):
  assert old in body,label;variants.append((label,2,body.replace(old,new),False))
 reports=[]
 for label,opt,code,good in variants:
  source=p/('native-'+label+'.c');binary=source.with_suffix('');source.write_text(template.replace('@BODY@',code))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-ffp-contract=off','-fno-builtin',str(source),str(obj),'-o',str(binary)],capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
  q=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(p/('native-'+label+'.txt')).write_text(log)
  assert q.returncode==(0 if good else 3),(label,q.returncode,log)
  row=dict(label=label,positive=good,exit_code=q.returncode,log=log.strip(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,cases_per_positive_run=len(cases),submissions_per_positive_run=sum(c.initial%26+35 for c in cases),positive_runs=3,effective_negatives=8,strict_aliasing=True,UBSan=True,explicit_provider_order=True,runs=reports,fixture_sha256=hashlib.sha256(out).hexdigest(),c_match_credit=0)
 (p/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
