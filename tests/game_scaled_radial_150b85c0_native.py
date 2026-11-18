"""Native32 strict-alias/UBSan qualification from independent Python fixtures."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.tests import game_scaled_radial_150b85c0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def main():
 p=g.p;W=lambda n:struct.pack('<I',n&0xffffffff);windows=[(g.INPUT,0x120),(g.OUTPUT,32),(g.MARK,4),(g.K,4)]
 def native_bytes(m,a,n):
  raw=g.data(m,a,n);return b''.join(raw[i:i+4][::-1]for i in range(0,n,4))
 def trace(calls):
  h=2166136261
  def word(v):
   nonlocal h
   h=((h^v)*16777619)&0xffffffff
  for t,args,observed in calls:
   word(t);word(len(args))
   for arg in args:word(0xFFFFFF01 if arg=='packet'else arg)
   selected=bytes(observed[i]for i in g.DEFINED)if observed else b'';word(len(selected))
   for b in selected:word(b)
  return h
 cases=list(g.cases());out=bytearray(W(len(cases))+W(4))
 for c in cases:
  initial=g.fixture(c);expected,s,result=g.reference(initial,c)
  for n in(c.seed,c.success,c.mutation,c.profile,*g.args(c),trace(s.calls),result):out+=W(n)
  for a,n in windows:out+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(expected,a,n)
 fixture=p/'native-fixture.bin';fixture.write_bytes(out);assembly=p/'native-fixture.s';obj=p/'native-fixture.o'
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 compiled=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert compiled.returncode==0 and not compiled.stderr,compiled.stderr
 kind=g.source.PIN['declarations'].split('extern f32')[0]
 template=Path(__file__).with_name('game_scaled_radial_150b85c0_native.c.in').read_text().replace('@TYPE@',kind).replace('@FIELDS@',','.join('{%d,%d}'%row for row in g.fields())).replace('@DEFINED@',','.join(map(str,g.DEFINED)))
 body=(p/'candidate.body').read_text();variants=[('O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in(
  ('kind','packet.field1D = 41;','packet.field1D = 40;'),('duration','% 11U + 35','% 10U + 35'),('color','% 51U + 100','% 50U + 100'),
  ('radius','packet.field28 = *radius * 20.0f;','packet.field28 = *height * 20.0f;'),('coordinate','packet.position = *position;','packet.position = *position; packet.position.x = position->z;'),
  ('flag','? 0x40 : 0','? 0x20 : 0'),('context','&packet, 1, 0, slot, context','&packet, 1, 0, slot, context + 1'),
  ('return','return func_15130374(&packet, 1, 0, slot, context);','func_15130374(&packet, 1, 0, slot, context); return NULL;')):
  assert body.count(old)==1,label;variants.append((label,2,body.replace(old,new),False))
 reports=[]
 for label,opt,code,good in variants:
  path=p/('native-'+label+'.c');binary=path.with_suffix('');path.write_text(template.replace('@BODY@',code))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(path),str(obj),'-o',str(binary)],capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
  q=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(p/('native-'+label+'.txt')).write_text(log)
  assert q.returncode==(0 if good else 3),(label,q.returncode,log)
  row=dict(label=label,positive=good,exit_code=q.returncode,log=log.strip(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=3,effective_negatives=8,defined_descriptor_bytes=98,unwritten_bytes_uncredited=14,strict_aliasing=True,UBSan=True,runs=reports,fixture_sha256=hashlib.sha256(out).hexdigest(),c_match_credit=0)
 (p/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
