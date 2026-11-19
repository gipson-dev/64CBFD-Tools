"""Native SDK32 source, with the known caller's ignored-result contract."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_actor_attached_emitter_150bb760_match as s
from tools.tests import game_actor_attached_emitter_150bb760_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def run(supplied=None,attempt='native'):
 o=s.OUT/attempt;o.mkdir(exist_ok=False);W=lambda n:struct.pack('<I',n&0xffffffff);rows=[c for c in g.cases()if c.phase==0];blob=bytearray(W(len(rows)))
 for c in rows:
  initial=g.fixture(c);final,calls,obs=g.reference(initial,c)
  for v in(c.seed,c.heading,c.gate,c.success,c.mutation,*(g.read(initial,a)for a in g.GLOBALS)):blob+=W(v)
  for i in range(512):blob+=W(initial[c.actor+i])
  blob+=W(len(calls))
  for t,args in calls:
   a=list(args);seen=[]
   if t==g.FACTORY:a[0]=0xffff0010;seen=[0 if g.unspecified(i)else v for i,v in enumerate(obs[0])]
   blob+=W(t)+W(len(a))+b''.join(W(v)for v in a)+W(len(seen))+b''.join(W(v)for v in seen)
  for a in g.GLOBALS:blob+=W(g.read(final,a))
  for i in range(512):blob+=W(final[c.actor+i])
  for i in range(512):blob+=W(0 if c.gate==3 and c.success and 16<=i<140 and g.unspecified(i-16)else final[g.OUTPUT+i])
 binary=o/'fixture.bin';binary.write_bytes(blob);asm=o/'fixture.s';obj=asm.with_suffix('.o');asm.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(asm),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_actor_attached_emitter_150bb760_native.c.in').read_text();body=s.PIN['body'];decl=s.PIN['declarations']
 controls=(('type','actor[4] != 32','actor[4] != 31'),('active','*(s32 *)actor != 0','*(s32 *)actor == 0'),('model','*(s32 *)(actor + 0x1D4) != 0','*(s32 *)(actor + 0x1D4) == 0'),('width','width = *(s16 *)(actor + 0xE4)','width = *(s16 *)(actor + 0xE6)'),('heading','>> 8) + 64','>> 8) + 63'),('drift','* headingSine) * 0.5f','* headingSine) * 0.25f'),('resource','resource = 1','resource = 2'),('channel','field70 = actor[0x3B]','field70 = actor[0x3A]'),('offset-sign','-radialCosine * radius','radialCosine * radius'),('spread','(angle & 63U) - 32U','(angle & 63U) - 31U'),('speed','* 5.0f + 3.0f','* 4.0f + 3.0f'),('size','* D_8009FE94','* D_8009FE98'),('owner','descriptor.owner = actor','descriptor.owner = 0'),('position','+ 4.0f','+ 5.0f'),('flags','flags = 0x29E9','flags = 0x29E8'),('duration','& 31U','& 15U'),('factory-channel','&descriptor, 3, 255, 0, 255, 0','&descriptor, 3, 255, 0, 254, 0'),('factory-resource','&descriptor, 3, 255, 0, 255, 0','&descriptor, 2, 255, 0, 255, 0'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for name,old,new in controls:assert old in body,name;variants.append(('negative-'+name,2,body.replace(old,new),False))
 reports=[]
 for label,opt,variant,good in variants:
  source=o/(label+'.c');exe=source.with_suffix('');source.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',variant))
  # C permits falling off a non-void function when its value is unused. The
  # actual caller ignores it; suppress only that expected compiler diagnostic.
  q=subprocess.run(native_command('-O'+str(opt))+['-Wno-return-type','-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(source),str(obj),'-o',str(exe)],capture_output=True,text=True,cwd=s.ROOT);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert not q.returncode,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);(o/(label+'-run.txt')).write_text(q.stdout+q.stderr);row=dict(label=label,positive=good,exit=q.returncode,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True);assert q.returncode==(0 if good else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(rows),positive_runs=3,effective_negatives=len(controls),strict_aliasing=True,UBSan=True,typed_actor_backing=True,descriptor_bytes=124,unspecified_bytes_not_compared=12,guest_endian_fields_compared=True,non_null_actor_domain=True,return_value_unused=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),runs=reports,source_installed=s.installed(),c_match_credit=0)
 (o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='runs'}),flush=True);return report
