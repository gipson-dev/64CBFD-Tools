"""Native32 positive source runs and effective semantic negative controls."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.tests import game_motion_impact_151b118c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
 p=g.p;W=lambda n:struct.pack('<I',n&0xffffffff)
 windows=[(g.A,512),(g.MARK,4),(g.TIME,4),(g.COEF,12)]
 fields=[(off,4)for off in(0x30,0x34,0x38,0x3C,0x40,0x44,0x48,0x78,0x110,0x114,0x118,0x11C,0x124,0x128,0x12C,0x130)]
 fields += [(0x7C+2*i,2)for i in range(10)]+[(0x90,4),(0x96,2),(0x98,4)]
 assert all(a+n<=b or b+m<=a for i,(a,n)in enumerate(fields)for b,m in fields[i+1:])
 def native_bytes(m,a,n):
  out=bytearray(g.data(m,a,n))
  if a==g.A:
   for off,width in fields:out[off:off+width]=out[off:off+width][::-1]
  else:
   for off in range(0,n,4):out[off:off+4]=out[off:off+4][::-1]
  return out
 def trace(calls):
  value=2166136261
  def word(n):
   nonlocal value
   value=((value^n)*16777619)&0xffffffff
  for target,args,observed in calls:
   word(target);word(len(args))
   for arg in args:word({'probe':0xFFFFFF01,'impact':0xFFFFFF02}[arg]if isinstance(arg,str)else arg)
   word(len(observed))
   for b in observed:word(b)
  return value
 cases=list(g.cases());out=bytearray(W(len(cases))+W(len(windows)))
 for c in cases:
  initial=g.fixture(c);expected,s,answer=g.reference(initial,c)
  out+=W(c.seed)+W(c.hit)+W(c.parity)+W(c.mutation)+W(trace(s.calls))+W(answer)
  for a,n in windows:out+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(expected,a,n)
 fixture=p/'native-fixture.bin';fixture.write_bytes(out)
 assembly=p/'native-fixture.s';obj=p/'native-fixture.o'
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 result=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert result.returncode==0 and not result.stderr,result.stderr
 template=Path(__file__).with_name('game_motion_impact_151b118c_native.c.in').read_text().replace('@FIELDS@',','.join('{%d,%d}'%v for v in fields))
 decl='\n'.join(line for line in(p/'phase-s8.decl').read_text().splitlines()if not line.startswith('extern '))
 template=template.replace('@DECLARATIONS@',decl)
 variants=[]
 for label in('phase-s8','blend-oldX-ordered'):
  body=(p/(label+'.body')).read_text()
  for opt in(0,2,3):variants.append((label+'-O'+str(opt),opt,body,True))
 body=(p/'blend-oldX-ordered.body').read_text()
 for label,old,new in(
  ('damping','0.25f * D_800BE9A4','0.5f * D_800BE9A4'),
  ('disable-probe','parameters[0x24] != 0','parameters[0x24] == 0'),
  ('surface-width','(HeightResult71820 *)(effect + 0x78)','(HeightResult71820 *)(effect + 0x7C)'),
  ('wrong-hit','0x78) + 5.0f','0x78) + 6.0f'),
  ('wrong-rng-bit','func_150ADA20() & 1','func_150ADA20() & 2'),
  ('wrong-context','effect[0xC], effect[1]','effect[1], effect[0xC]'),
  ('capture-after-rng','if ((u32)func_150ADA20() & 1) {','if ((u32)func_150ADA20() & 1) {\n                impact.x = probe.x;'),
  ('wrong-result','active = 0;','active = 1;'),
 ):
  assert old in body,label;variants.append((label,2,body.replace(old,new),False))
 reports=[]
 for label,opt,body,good in variants:
  source=p/('native-'+label+'.c');binary=source.with_suffix('');source.write_text(template.replace('@BODY@',body))
  command=native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(source),str(obj),'-o',str(binary)]
  compiled=subprocess.run(command,capture_output=True,text=True);assert compiled.returncode==0,(label,compiled.stderr)
  run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);log=run.stdout+run.stderr
  (p/('native-'+label+'.txt')).write_text(log);assert run.returncode==(0 if good else 3),(label,run.returncode,log)
  row=dict(label=label,optimization=opt,positive=good,exit_code=run.returncode,log=log.strip(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=6,effective_negatives=8,strict_aliasing=True,UBSan=True,fixture_sha256=hashlib.sha256(out).hexdigest(),runs=reports,all_public_bytes=True,private_unexposed_bytes_uncredited=True,c_match_credit=0)
 (p/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
