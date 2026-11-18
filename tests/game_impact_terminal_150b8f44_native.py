"""Native SDK32 candidate versus independent retail transcripts, initialized bytes."""
from pathlib import Path
from dataclasses import replace
import hashlib,itertools,json,struct,subprocess
from tools.experiments import game_impact_terminal_150b8f44_screen as s
from tools.tests import game_impact_terminal_150b8f44_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
BURST_FIELDS=tuple(range(6))+tuple(range(8,0x48))+tuple(range(0x50,0x58))
SPRAY_FIELDS=tuple(range(0x2a))+tuple(range(0x2c,0x57))+tuple(range(0x58,0x73))+tuple(range(0x74,0x9a))+tuple(range(0x9c,0xa4))
assert(len(BURST_FIELDS),len(SPRAY_FIELDS))==(78,158)

def run(state):
 out=s.OUT/'native';out.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff)
 windows=((g.ACTOR,384),(g.SURFACE,64),(g.CONSTANTS[0],24),(g.SOUNDS,12))
 actor_fields=(0x14,*range(0x38,0x5c,4),0x128,0x140,0x14c,0x168)
 def native_bytes(m,a,n):
  raw=bytearray(g.data(m,a,n));fields=actor_fields if a==g.ACTOR else (0x14,0x18,0x1c)if a==g.SURFACE else range(0,n,4)
  for at in fields:raw[at:at+4]=raw[at:at+4][::-1]
  return raw
 cases=[]
 for index,(amplitude,vertical,tile,query,classify,success,mutation)in enumerate(itertools.product((6.,6.000001,60.),(-2.,0.,2.),(0,1),(0,1),(0,1),(0,1),(0,2,4,8,16,30))):
  flags=index%4;cases.append(g.Case(amplitude=g.g.bits(amplitude),vertical=g.g.bits(vertical),tile=tile,query=query,classify=classify,success=success,mutation=mutation,flags=flags,coordinate=index%3,randoms=(0xffffffff-flags,flags&1,flags>>1,0xffffff00|flags,flags&1)))
 fixture=bytearray(W(len(cases)));total=0
 for c in cases:
  initial=g.fixture(c);m=g.Oracle(state['retail_words'],c).run();want=g.reference(initial,c);assert(g.public(m.memory),m.calls,m.obs,m.r[2])==want
  for v in(c.flags,c.success,c.mutation,c.tile,c.query,c.classify,m.r[2]):fixture+=W(v)
  for a,n in windows:fixture+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(m.memory,a,n)
  fixture+=W(len(m.calls));total+=len(m.calls);obs=iter(m.obs);roles=g.layout(g.STACK,'retail');role_map={'burst':1,'spray':2,'extra':3,'context':4,'position':5,'hit':6};spans={'burst':88,'spray':164,'extra':8,'context':18,'position':12,'hit':4}
  def norm(v):
   for name,a in roles.items():
    if a<=v<a+spans[name]:return 0xffff0000+(role_map[name]<<12)+v-a
   return v
  for t,args in m.calls:
   observed=b''
   if t in(g.FACTORY,g.SPRAY,g.COPY):
    kind,blob=next(obs);fields=BURST_FIELDS if t==g.FACTORY else SPRAY_FIELDS if t==g.SPRAY else range(4);observed=bytes(blob[i]for i in fields)
   fixture+=W(t)+W(len(args))+W(len(observed))+b''.join(W(norm(v))for v in args)+observed
  assert next(obs,None)is None
 binary=out/'fixture.bin';binary.write_bytes(fixture);assembly=out/'fixture.s';obj=assembly.with_suffix('.o');assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_impact_terminal_150b8f44_native.c.in').read_text();decl=s.PIN['support_declarations']+'\n'+'\n'.join(v for v in s.PIN['declarations'].splitlines()if not v.startswith('extern '));body=s.PIN['body']
 controls=(('threshold','> 6.0f','> 7.0f'),('duration','% 31U + 40','% 31U + 39'),('burst-kind','burst.field02 = 0x3B02','burst.field02 = 0x3B03'),('extra-copy','&extra, 8','&extra, 4'),('metadata','spray.context = context;','spray.context = context; spray.context.field[0] ^= 1;'),('spray-kind','0x220005','0x220004'),('low-volume','D_8008873C, 64000','D_8008873C, 32000'),('low-return','    return 1;','    return 0;'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in controls:assert body.count(old)==1,label;variants.append(('negative-'+label,2,body.replace(old,new),False))
 rows=[]
 for label,opt,variant,good in variants:
  code=out/(label+'.c');exe=code.with_suffix('');code.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',variant));q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(code),str(obj),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True);assert q.returncode==0,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(out/(label+'.txt')).write_text(log);row=dict(label=label,positive=good,exit_code=q.returncode,log=log.strip(),source_sha256=hashlib.sha256(code.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True);assert q.returncode==(0 if good else 3),(label,q.returncode,log)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=3,effective_negatives=len(controls),provider_calls_per_positive_run=total,initialized_descriptor_bytes=[78,158],extra_initialized_bytes=4,unwritten_bytes_not_observed=True,public_windows=4,strict_aliasing=True,UBSan=True,guest_incoming_home_tests_separate=True,source_installed=False,c_match_credit=0,fixture_sha256=hashlib.sha256(fixture).hexdigest(),runs=rows)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
