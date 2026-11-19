"""SDK32 source semantics against an independent retail-executed transcript."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_actor_height_effect_150baa14_match as s
from tools.tests import game_actor_height_effect_150baa14_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def run(state,attempt='native'):
 out=s.OUT/attempt;out.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff);rows=[c for c in g.cases()if c.phase==0];blob=bytearray(W(len(rows)));ids=dict(position=0xffff0010,surface=0xffff0011,actor=0xffff0001)
 for c in rows:
  initial=g.fixture(c);final,service=g.reference(initial,c);g.verify(state['retail_words'],c)
  for v in(c.seed,c.ready,c.status,c.mutation,c.selector,c.unused,c.coords,g.read(initial,g.MARK),len(service.calls)):blob+=W(v)
  for target,args,observed in service.calls:blob+=W(target)+W(len(args))+b''.join(W(ids.get(v,v))for v in args)+b''.join(W(v)for v in observed)
  for v in(g.read(final,g.BASE_PTR),g.read(final,g.INDEX),g.read(final,g.SCALE),g.read(final,g.ACTOR+468),g.read(final,g.MARK),*(g.read(final,base+i*0x9a0+0x380)for base in(g.BASE,g.ALT)for i in range(3))):blob+=W(v)
 binary=out/'fixture.bin';binary.write_bytes(blob);assembly=out/'fixture.s';obj=assembly.with_suffix('.o');assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_actor_height_effect_150baa14_native.c.in').read_text();body=s.PIN['body']
 controls=(('ready-gate','actor + 0x1D4) == 0','actor + 0x1D4) != 0'),('status-width','    u8 hit;','    u32 hit;'),('prep-bound','1307.0f','1306.0f'),('command-flags','0x4022','0x4023'),('record-index','[(u32)D_80082FA4]','[0]'),('record-scale','* D_8009FE64','* 1.0f'),('event-y','position[1] + 6.0f','position[1] + 5.0f'),('effect-scale','sample * 50.0f','sample * 49.0f'),('angle-plus','angle + 60U','angle + 59U'),('duration','random % 11U','random % 10U'),('signed-rng','random % 11U','(s32)random % 11'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for name,old,new in controls:assert old in body,name;variants.append(('negative-'+name,2,body.replace(old,new),False))
 reports=[]
 for label,opt,variant,good in variants:
  file=out/(label+'.c');exe=file.with_suffix('');file.write_text(template.replace('@DECLARATIONS@',s.PIN['declarations']).replace('@BODY@',variant))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(file),str(obj),'-o',str(exe)],capture_output=True,text=True,cwd=s.ROOT);(out/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert not q.returncode,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);(out/(label+'-run.txt')).write_text(q.stdout+q.stderr);row=dict(label=label,positive=good,exit=q.returncode,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True);assert q.returncode==(0 if good else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(rows),positive_runs=3,effective_negatives=len(controls),strict_aliasing=True,UBSan=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),runs=reports,source_installed=s.installed(),c_match_credit=0);(out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
