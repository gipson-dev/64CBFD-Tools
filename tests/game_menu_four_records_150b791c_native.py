"""Native source/ABI and effective mutation-sensitive negative controls."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.tests import game_menu_four_records_150b791c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def main():
 p=g.p;W=lambda n:struct.pack('<I',n&0xffffffff)
 fields=[(off,n)for off,v,n in g.fields()];windows=[(g.BASE-16,80),(g.MARK,4)]
 def native_bytes(m,a,n):
  out=bytearray(g.data(m,a,n));locations=[(g.BASE+off,4)for off in(8,20,24,28,36)]if a==g.BASE-16 else[(g.MARK,4)]
  for at,width in locations:off=at-a;out[off:off+width]=out[off:off+width][::-1]
  return out
 def trace(calls):
  value=2166136261
  def word(n):
   nonlocal value
   value=((value^n)*16777619)&0xffffffff
  for target,arg,observed in calls:
   observed=bytes(observed[i]for i in g.DEFINED)if observed else b''
   word(target);word(1);word(0xFFFFFF01 if arg=='descriptor'else arg);word(len(observed))
   for b in observed:word(b)
  return value
 cases=list(g.cases());out=bytearray(W(len(cases))+W(2))
 for c in cases:
  initial=g.fixture(c);expected,s=g.reference(initial,c);out+=W(c.seed)+W(c.failure)+W(c.mutation)+W(trace(s.calls))
  for a,n in windows:out+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(expected,a,n)
 fixture=p/'native-fixture.bin';fixture.write_bytes(out);assembly=p/'native-fixture.s';obj=p/'native-fixture.o'
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 result=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert result.returncode==0 and not result.stderr,result.stderr
 owner=(p/'proposed-owner.c').read_text();end=owner.index('} MenuRecordDescriptorE4070;')+len('} MenuRecordDescriptorE4070;');start=owner.rfind('typedef struct {',0,end);kind=owner[start:end]
 template=Path(__file__).with_name('game_menu_four_records_150b791c_native.c.in').read_text().replace('@FIELDS@',','.join('{%d,%d}'%v for v in fields)).replace('@DEFINED@',','.join(map(str,g.DEFINED))).replace('@TYPE@',kind)
 body=(p/'candidate.body').read_text();variants=[('O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in(
  ('clear-wrong-slot','((void **)D_800D9898)[2] = NULL;','((void **)D_800D9898)[1] = NULL;'),
  ('wrong-release6','if (((void **)D_800D9898)[6] != NULL) func_1516972C(((void **)D_800D9898)[5]);','if (((void **)D_800D9898)[6] != NULL) func_1516972C(((void **)D_800D9898)[6]);'),
  ('wrong-release7','func_1516972C(((void **)D_800D9898)[5]);\n    }','func_1516972C(((void **)D_800D9898)[7]);\n    }'),
  ('wrong-coordinate','descriptor.field20 = 170.0f;\n    descriptor.field0C = (s32)descriptor.field20;','descriptor.field20 = 170.0f;'),
  ('wrong-asset','descriptor.asset = D_8009190C;','descriptor.asset = D_800918E8;'),
  ('wrong-alpha','descriptor.field35 = 128;','descriptor.field35 = 255;'),
  ('lost-final-inheritance','descriptor.field30 = 0;','descriptor.field30 = 0;\n    descriptor.field08 = 0;'),
  ('wrong-state','D_800D9890 = 3;','D_800D9890 = 4;'),
 ):
  assert old in body,label;variants.append((label,2,body.replace(old,new),False))
 reports=[]
 for label,opt,code,good in variants:
  source=p/('native-'+label+'.c');binary=source.with_suffix('');source.write_text(template.replace('@BODY@',code))
  command=native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(source),str(obj),'-o',str(binary)]
  compiled=subprocess.run(command,capture_output=True,text=True);assert compiled.returncode==0,(label,compiled.stderr)
  run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);log=run.stdout+run.stderr;(p/('native-'+label+'.txt')).write_text(log)
  assert run.returncode==(0 if good else 3),(label,run.returncode,log)
  row=dict(label=label,positive=good,exit_code=run.returncode,log=log.strip(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=3,effective_negatives=8,defined_descriptor_bytes=56,unwritten_bytes_uncredited=4,strict_aliasing=True,UBSan=True,runs=reports,fixture_sha256=hashlib.sha256(out).hexdigest(),c_match_credit=0)
 (p/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
