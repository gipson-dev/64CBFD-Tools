"""Native32 C checked against independent retail transcripts and initialized bytes."""
from pathlib import Path
import hashlib,itertools,json,struct,subprocess
from tools.experiments import game_amplitude_terminal_150b89e0_screen as s
from tools.tests import game_amplitude_terminal_150b89e0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
BURST_FIELDS=tuple(range(6))+tuple(range(8,0x48))+tuple(range(0x50,0x58))
SPRAY_FIELDS=tuple(range(0x3b))+tuple(range(0x3c,0x57))+tuple(range(0x58,0x7e))+tuple(range(0x80,0x88))
assert(len(BURST_FIELDS),len(SPRAY_FIELDS))==(78,132)

def run(state):
 s.check_inputs();out=s.OUT/'native';out.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff)
 windows=((g.ACTOR,384),(g.K0,12),(g.SOUNDS,12));actor_fields=(0x10,0x14,0x20,0x24,0x28,0x38,0x3c,0x40,*range(0x44,0x5c,4),0x60,0x128,0x140,0x14c,0x168)
 def data(m,a,n):return bytes(m[a+i]for i in range(n))
 def native_bytes(m,a,n):
  raw=bytearray(data(m,a,n));fields=actor_fields if a==g.ACTOR else range(0,n,4)
  for at in fields:raw[at:at+4]=raw[at:at+4][::-1]
  return raw
 cases=[g.Case(amplitude=a,success=success,mutation=mutation,flags=flags,randoms=(0xffffffff-flags,flags&1,flags>>1,0xffffff00|flags,flags&1))for a,success,mutation,flags in itertools.product((g.g.bits(-1.),g.g.bits(0.),g.g.bits(15.),g.g.bits(15.000001),g.g.bits(30.),g.g.bits(30.000002),g.g.bits(60.),0x7fc00001,0x7f800000),(0,1),(0,1,8,9),range(4))]
 fixture=bytearray(W(len(cases)));total=0
 for c in cases:
  initial=g.fixture(c);m=g.Oracle(state['retail_words'],c).run();want=g.reference(initial,c);assert(g.public(m.memory),m.calls,m.obs,m.r[2])==want
  for v in(c.flags,c.success,c.mutation,m.r[2]):fixture+=W(v)
  for a,n in windows:fixture+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(m.memory,a,n)
  fixture+=W(len(m.calls));total+=len(m.calls);obs=iter(m.obs);h=g.STACK+c.phase
  roles={h-88:0xffffff01,h-232:0xffffff02,h-296:0xffffff03,h-96:0xffffff04}
  for t,args in m.calls:
   observed=b''
   if t in(g.FACTORY,g.SPRAY,g.TRANSFORM):
    kind,blob=next(obs);observed=bytes(blob[i]for i in(BURST_FIELDS if t==g.FACTORY else SPRAY_FIELDS))if t!=g.TRANSFORM else blob
   elif t==g.COPY:observed=data(m.memory,h-96,4)
   fixture+=W(t)+W(len(args))+W(len(observed))+b''.join(W(roles.get(v,v))for v in args)+observed
  assert next(obs,None)is None
 binary=out/'fixture.bin';binary.write_bytes(fixture);assembly=out/'fixture.s';obj=assembly.with_suffix('.o');assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_amplitude_terminal_150b89e0_native.c.in').read_text();decl='\n'.join(v for v in s.PIN['declarations'].splitlines()if not v.startswith('extern '));body=s.PIN['body']
 controls=(('low-threshold','> 15.0f','> 16.0f'),('high-threshold','> 30.0f','> 31.0f'),('duration','% 31U + 40','% 31U + 39'),('burst-kind','burst.field02 = 0x3B02','burst.field02 = 0x3B03'),('burst-flags','0xC5C0001','0xC5C0000'),('extra','* 80.0f + 50.0f','* 81.0f + 50.0f'),('extra-copy','&extra, 8','&extra, 4'),('spray-count','spray.field24 = 6','spray.field24 = 5'),('spray-kind','0x220005','0x220004'),('sound-height','y + 25.0f','y + 24.0f'),('reset-mask','0xFFFFFF00U','0xFFFFFF01U'),('terminal-return','            return 0;','            return 1;'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in controls:assert body.count(old)==1,label;variants.append(('negative-'+label,2,body.replace(old,new),False))
 rows=[]
 for label,opt,variant,good in variants:
  code=out/(label+'.c');exe=code.with_suffix('');code.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',variant));q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(code),str(obj),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True);assert q.returncode==0,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(out/(label+'.txt')).write_text(log);row=dict(label=label,positive=good,exit_code=q.returncode,log=log.strip(),source_sha256=hashlib.sha256(code.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True);assert q.returncode==(0 if good else 3),(label,q.returncode,log)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=3,effective_negatives=len(controls),provider_calls_per_positive_run=total,initialized_descriptor_bytes=[78,132],extra_initialized_bytes=4,unwritten_bytes_not_read=True,public_windows=3,strict_aliasing=True,UBSan=True,guest_incoming_alias_tests_separate=True,source_installed=False,c_match_credit=0,fixture_sha256=hashlib.sha256(fixture).hexdigest(),runs=rows)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');s.check_inputs();return report
