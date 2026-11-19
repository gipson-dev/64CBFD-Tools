"""SDK32 execution against independently retail-checked descriptor transcripts."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_extended_emitter_150bb498_match as s
from tools.tests import game_extended_emitter_150bb498_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def run(state=None,attempt='native'):
 p=Path(__file__).resolve().parent;o=s.OUT/attempt;o.mkdir(exist_ok=False)
 W=lambda n:struct.pack('<I',n&0xffffffff);rows=[c for c in g.cases()if c.phase==0];blob=bytearray(W(len(rows)))
 for c in rows:
  initial=g.fixture(c);final,calls,obs=g.reference(initial,c)
  for v in(c.seed,c.angle,c.slot,c.success,c.mutation,c.coords,*(g.read(initial,a)for a in g.GLOBALS),len(calls)):blob+=W(v)
  for t,args in calls:
   a=list(args);seen=[]
   if t==g.FACTORY:a[0]=0xffff0010;seen=[0 if g.unspecified(i)else v for i,v in enumerate(obs[0])]
   blob+=W(t)+W(len(a))+b''.join(W(v)for v in a)+W(len(seen))+b''.join(W(v)for v in seen)
  for v in(1,*(g.read(final,a)for a in g.GLOBALS)):blob+=W(v)
  for i in range(512):blob+=W(0 if c.success and 16<=i<140 and g.unspecified(i-16)else final[g.OUTPUT+i])
 binary=o/'fixture.bin';binary.write_bytes(blob);asm=o/'fixture.s';obj=asm.with_suffix('.o');asm.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(asm),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=(p/'game_extended_emitter_150bb498_native.c.in').read_text();body=s.PIN['body'];decl=s.PIN['declarations']
 controls=(('heading','heading - 64U','heading - 63U'),('coordinate','position[2] = z','position[2] = y'),('pitch','% 13U - 52U','% 13U - 51U'),('speed','* 9.0f','* 8.0f'),('vertical-sign','-speed * pitchCosine','speed * pitchCosine'),('offset','* 50.0f + -25.0f','* 50.0f + -24.0f'),('duration','% 68U','% 67U'),('late-field','* D_8009FE80','* D_8009FE7C'),('resource','resource = 31','resource = 30'),('flags','flags = 0x9E8','flags = 0x9E9'),('factory','&descriptor, 3, 255, 0, context, 0','&descriptor, 2, 255, 0, context, 0'),('return','    return 1;','    return 0;'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for name,old,new in controls:assert old in body,name;variants.append(('negative-'+name,2,body.replace(old,new),False))
 reports=[]
 for label,opt,variant,good in variants:
  source=o/(label+'.c');exe=source.with_suffix('');source.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',variant))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(source),str(obj),'-o',str(exe)],capture_output=True,text=True,cwd=g.ROOT);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert not q.returncode,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);(o/(label+'-run.txt')).write_text(q.stdout+q.stderr);row=dict(label=label,positive=good,exit=q.returncode,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest());reports.append(row);assert q.returncode==(0 if good else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(rows),positive_runs=3,effective_negatives=len(controls),strict_aliasing=True,UBSan=True,descriptor_bytes=124,unspecified_bytes_not_compared=12,guest_endian_fields_compared=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),runs=reports,source_installed=s.installed(),c_match_credit=0)
 (o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='runs'}),flush=True);return report
