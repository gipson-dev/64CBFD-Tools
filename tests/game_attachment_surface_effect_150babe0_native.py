"""SDK32 semantic source against retail transcripts, with unspecified holes masked."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_attachment_surface_effect_150babe0_match as s
from tools.tests import game_attachment_surface_effect_150babe0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
def run(state=None,attempt='native'):
 p=Path(__file__).resolve().parent;o=s.OUT/attempt;o.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff)
 rows=[c for c in g.cases()if c.phase==0];blob=bytearray(W(len(rows)));ids=dict(position=0xffff0010,surface=0xffff0011,probe=0xffff0012,descriptor=0xffff0013,vertices=0xffff0014)
 for c in rows:
  initial=g.fixture(c);final,service=g.reference(initial,c)
  for v in(c.seed,c.gate,c.selector,c.context,c.hit,c.created,c.appended,c.mutation,g.read(initial,g.MARK),len(service.calls)):blob+=W(v)
  for target,args,observed in service.calls:
   observed=list(observed)
   if target==g.MATRIX:observed[:3]=[0]*3
   if target==g.PREP:observed[-9:]=[0]*9
   if target==g.CREATE:observed[33:40]=[0]*7
   blob+=W(target)+W(len(args))+b''.join(W(ids.get(v,v))for v in args)+W(len(observed))+b''.join(W(v)for v in observed)
  for v in(g.read(final,g.BASE_PTR),g.read(final,g.INDEX),g.read(final,g.SCALE),g.read(final,g.ACTOR),g.read(final,g.ACTOR+468),g.read(final,g.ACTOR+384),g.read(final,g.MARK),*(g.read(final,base+i*0x9a0+0x380)for base in(g.BASE,g.ALT)for i in range(3))):blob+=W(v)
 binary=o/'fixture.bin';binary.write_bytes(blob);assembly=o/'fixture.s';obj=assembly.with_suffix('.o');assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=(p/'game_attachment_surface_effect_150babe0_native.c.in').read_text();body=s.PIN['body'];decl=s.PIN['declarations']
 controls=(('active-gate','*(s32 *)actor == 8','*(s32 *)actor == 7'),('attachment','attachment = 17','attachment = 16'),('angle-scale','* D_8009FE70','* 1.0f'),('command-flags','0x4022','0x4023'),('event-y','position[1] + 6.0f','position[1] + 5.0f'),('first-duration','% 11U','% 10U'),('descriptor-flags','0x7340','0x7341'),('descriptor-mode','descriptor.mode = 13','descriptor.mode = 12'),('color-mask','first & 0xFFU','first & 0x7FU'),('failed-append','effect, 1) == 0','effect, 1) != 0'),('last-duration','% 7U','% 6U'),('angle-plus','angle + 60U','angle + 59U'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for name,old,new in controls:assert old in body,name;variants.append(('negative-'+name,2,body.replace(old,new),False))
 reports=[]
 for label,opt,variant,good in variants:
  file=o/(label+'.c');exe=file.with_suffix('');file.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',variant))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(file),str(obj),'-o',str(exe)],capture_output=True,text=True,cwd=g.ROOT);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert not q.returncode,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);(o/(label+'-run.txt')).write_text(q.stdout+q.stderr);row=dict(label=label,positive=good,exit=q.returncode,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest());reports.append(row);print(json.dumps(row),flush=True);assert q.returncode==(0 if good else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(rows),positive_runs=3,effective_negatives=len(controls),strict_aliasing=True,UBSan=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),unspecified_descriptor_tail_not_compared=True,unspecified_preoutput_bytes_not_compared=True,runs=reports,source_installed=s.installed(),c_match_credit=0)
 (o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='runs'}),flush=True)
 return report
