"""SDK32 native C against independently guest-checked retail transcripts."""
from pathlib import Path
import hashlib,itertools,json,struct,subprocess
from tools.experiments import game_target_terminal_150b963c_screen as s
from tools.tests import game_target_terminal_150b963c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
BURST_FIELDS=tuple(range(6))+tuple(range(8,0x48))+tuple(range(0x50,0x58))
SPRAY_FIELDS=tuple(range(0x3b))+tuple(range(0x3c,0x57))+tuple(range(0x58,0x7e))+tuple(range(0x80,0x88))
assert(len(BURST_FIELDS),len(SPRAY_FIELDS))==(78,132)

def run(state):
 out=s.OUT/'native';out.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff)
 windows=((g.ACTOR,384),(g.FIRST,128),(g.SECOND,128),(g.ALTERNATE,128),(g.CACHE2,36),(g.CONSTANTS[0],36))
 actor_fields=tuple(sorted({0x10,*range(0x20,0x2c,4),*range(0x38,0x50,4),0x60,*range(0x110,0x134,4),0x128,0x14c,0x168}))
 def native_bytes(m,a,n):
  raw=bytearray(g.data(m,a,n));fields=actor_fields if a==g.ACTOR else (0,0x14,0x18,0x1c,0x3c)if a in(g.FIRST,g.SECOND,g.ALTERNATE)else range(0,n,4)
  for at in fields:raw[at:at+4]=raw[at:at+4][::-1]
  if a==g.ACTOR:raw[0x64:0x66]=raw[0x64:0x66][::-1]
  if a in(g.FIRST,g.SECOND,g.ALTERNATE):raw[0x76:0x78]=raw[0x76:0x78][::-1]
  return raw
 cases=[]
 for i,(distance,speed,bit,query,success,mutation)in enumerate(itertools.product((10.,50.,100.),(15.,20.),(0,1),(0,1),(0,1),(0,1,2,4,8,16,32,63))):
  cases.append(g.Case(distance=g.g.bits(distance),speed=g.g.bits(speed),random_bit=bit,query=query,success=success,mutation=mutation,flags=i%4,first_mode=(i//2)%4,second_mode=(i//8)%4,resolve_first=(i//32)%2,resolve_second=(i//64)%2))
 fixture=bytearray(W(len(cases)));total=0
 for c in cases:
  initial=g.fixture(c);machine=g.Oracle(state['retail_words'],c).run();want=g.reference(initial,c);assert(g.public(machine.memory),machine.calls,machine.obs,machine.r[2])==want
  for value in(c.flags,c.success,c.mutation,c.query,c.first_mode,c.resolve_first,c.resolve_second,c.random_bit,machine.r[2]):fixture+=W(value)
  for at,n in windows:fixture+=W(at)+W(n)+native_bytes(initial,at,n)+native_bytes(machine.memory,at,n)
  fixture+=W(len(machine.calls));total+=len(machine.calls);obs=iter(machine.obs);roles=g.layout(g.STACK,'retail');ids={'burst':1,'spray':2,'extra':3,'position':5};spans={'burst':88,'spray':136,'extra':8,'position':12}
  def norm(value):
   for name,at in roles.items():
    if at<=value<at+spans[name]:return 0xffff0000+(ids[name]<<12)+value-at
   return value
  for target,args in machine.calls:
   observed=b''
   if target in(g.FACTORY,g.SPRAY,g.COPY):
    label,blob=next(obs);fields=BURST_FIELDS if target==g.FACTORY else SPRAY_FIELDS if target==g.SPRAY else range(4);observed=bytes(blob[i]for i in fields)
   fixture+=W(target)+W(len(args))+W(len(observed))+b''.join(W(norm(value))for value in args)+observed
  assert next(obs,None)is None
 binary=out/'fixture.bin';binary.write_bytes(fixture);assembly=out/'fixture.s';obj=assembly.with_suffix('.o');assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_target_terminal_150b963c_native.c.in').read_text();decl=s.PIN['support_declarations']+'\n'+'\n'.join(row for row in s.PIN['declarations'].splitlines()if not row.startswith('extern '));body=s.PIN['body']
 controls=(('refresh','    target = D_80088730;','    /* missing refresh */'),('valid-tag','target[0x3B] != 1','target[0x3B] == 1'),('radius','+ D_8009FDE0','- D_8009FDE0'),('bounce-speed','> 15.0f','> 21.0f'),('duration','% 31U + 40','% 31U + 39'),('burst-kind','burst.field02 = 0x3B02','burst.field02 = 0x3B03'),('extra-copy','&extra, 8','&extra, 4'),('spray-byte','spray.field55 = 154','spray.field55 = 153'),('volume','D_80088740, 25000','D_80088740, 24000'),('steering','D_8009FE00 *','-D_8009FE00 *'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in controls:assert old in body,label;variants.append(('negative-'+label,2,body.replace(old,new),False))
 rows=[]
 for label,opt,variant,good in variants:
  code=out/(label+'.c');exe=code.with_suffix('');code.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',variant));q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(code),str(obj),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True);assert q.returncode==0,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(out/(label+'.txt')).write_text(log);row=dict(label=label,positive=good,exit_code=q.returncode,log=log.strip(),source_sha256=hashlib.sha256(code.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True);assert q.returncode==(0 if good else 3),(label,q.returncode,log)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=3,effective_negatives=len(controls),provider_calls_per_positive_run=total,initialized_descriptor_bytes=[78,132],extra_initialized_bytes=4,unwritten_bytes_not_observed=True,public_windows=6,strict_aliasing=True,UBSan=True,source_installed=False,c_match_credit=0,fixture_sha256=hashlib.sha256(fixture).hexdigest(),runs=rows)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
