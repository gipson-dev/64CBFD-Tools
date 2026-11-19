"""SDK32 C evaluated against transcripts independently checked on retail MIPS."""
from pathlib import Path
import json,struct,subprocess,hashlib
from tools.experiments import game_attached_accumulator_150ba55c_recovery as s
from tools.tests import game_attached_accumulator_150ba55c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def run(state,attempt='native'):
 out=s.OUT/attempt;out.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff)
 rows=[]
 for c in g.cases():
  if c.phase:continue
  initial=g.fixture(c);final,service,prefix=g.reference(initial,c)
  if prefix:continue
  g.verify(state['retail_words'],c,'retail');rows.append((c,initial,final,service))
 blob=bytearray(W(len(rows)));ids=dict(actor=0xffff0001,origin=0xffff0010,radius=0xffff0011,height=0xffff0012,position=0xffff0013,rotation=0xffff0014,velocity=0xffff0015,acceleration=0xffff0016)
 for c,initial,final,service in rows:
  for v in(c.seed,c.route,c.mutation,g.read(initial,g.RECORD+48),g.read(initial,g.ACTOR+0xf0),*(g.read(initial,at)for at in g.CONSTANTS),len(service.calls)):blob+=W(v)
  for target,args,observed in service.calls:
   blob+=W(target)+W(len(args))+b''.join(W(ids.get(v,v))for v in args)
   for _,data in observed:
    blob+=b''.join(W(v)for v in struct.unpack('>3I',data))
  for v in(g.read(final,g.RECORD+48),g.read(final,g.RECORD+14,2),final[g.RECORD+12],final[g.RECORD+1],g.read(final,g.RECORD+40),*(g.read(final,g.ACTOR+off)for off in(0xf0,0x14c,0x150)),g.read(final,g.ACTOR+0x76,2),*(g.read(final,at)for at in g.CONSTANTS),g.read(final,g.DT)):blob+=W(v)
 binary=out/'fixture.bin';binary.write_bytes(blob);assembly=out/'fixture.s';obj=assembly.with_suffix('.o')
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_attached_accumulator_150ba55c_native.c.in').read_text();body=s.PIN['body']
 controls=(('identity-byte','payload->sourceByte != source[0x3B]','payload->sourceByte == source[0x3B]'),('ready-offset','source + 0x1D4','source + 0x0'),('initial-rate','D_8009FE30 + sample * D_8009FE34','D_8009FE34 + sample * D_8009FE30'),('first-modulus','firstRandom % 127U','firstRandom % 126U'),('second-modulus','secondRandom % 31U','secondRandom % 30U'),('rotation-scale','* 360.0f','* 359.0f'),('spread-range','sample * D_8009FE40','sample * D_8009FE44'),('persistent-y','        acceleration.y = 0.0f;',''),('duration','durationRandom % 41U + 60','durationRandom % 41U + 59'),('late-mode','effect[0xC], effect[1]','effect[1], effect[0xC]'),('decrement','payload->value -= 1.0f','payload->value -= 2.0f'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for name,old,new in controls:
  assert old in body,name
  # Moving Y to the loop tests its lifetime without reading an uninitialized local.
  changed=body.replace(old,new)
  if name=='persistent-y':changed=changed.replace('        do {','        do {\n            acceleration.y = 0.0f;')
  variants.append(('negative-'+name,2,changed,False))
 reports=[]
 for label,opt,code,good in variants:
  file=out/(label+'.c');exe=file.with_suffix('');file.write_text(template.replace('@DECLARATIONS@',s.PIN['declarations']).replace('@BODY@',code))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(file),str(obj),'-o',str(exe)],capture_output=True,text=True,cwd=s.ROOT)
  (out/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert not q.returncode,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);(out/(label+'-run.txt')).write_text(q.stdout+q.stderr)
  report=dict(label=label,positive=good,exit=q.returncode,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest());reports.append(report);print(json.dumps(report),flush=True)
  assert q.returncode==(0 if good else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(rows),positive_runs=3,effective_negatives=len(controls),strict_aliasing=True,UBSan=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),runs=reports,source_installed=False,c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
