"""Exact native provider transcripts from independently executed retail instructions."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_actor_bound_burst_150b7b40_match as source
from tools.tests import game_actor_bound_burst_150b7b40_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
p=source.OUT;out=p/'native'
CHILD_FIELDS=tuple(range(0x59))+tuple(range(0x5c,0x69))+(0x6a,)+tuple(range(0x6c,0x71))+tuple(range(0x72,0x76))
SPRAY_FIELDS=tuple(range(0x3b))+tuple(range(0x3c,0x57))+tuple(range(0x58,0x7e))+tuple(range(0x80,0x88))
assert len(CHILD_FIELDS)==112 and len(SPRAY_FIELDS)==132
def main():
 source.check_inputs();out.mkdir(exist_ok=False)
 windows=((g.ACTOR,512),(g.MODEL,256),(0x8009fd30,56));actor_fields=[(v,4)for v in(0x14,0x18,0x1c,0x3c,0x40,0xb8,0xc4,0x14c,0x150,0x184,0x1d4)]+[(0x76,2)]
 def native_bytes(m,a,n):
  result=bytearray(g.data(m,a,n));fields=actor_fields if a==g.ACTOR else[(v,4)for v in range(0,n,4)]if a==0x8009fd30 else[]
  for at,size in fields:result[at:at+size]=result[at:at+size][::-1]
  return result
 W=lambda v:struct.pack('<I',v&0xffffffff);cases=list(g.cases());fixture=bytearray(W(len(cases)));words=source.programs()[0][1];total=0
 for c in cases:
  initial=g.fixture(c);m=g.Oracle(words,c).run();assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
  for v in(c.model,c.zero,c.floor,c.profile,c.mutation,c.phase,c.seed,c.null):fixture+=W(v)
  for a,n in windows:fixture+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(m.memory,a,n)
  fixture+=W(len(m.calls));total+=len(m.calls)
  for t,args,data in m.calls:
   data=bytes(data)
   if t in(g.CHILD,g.SPRAY):data=bytes(data[i]for i in(CHILD_FIELDS if t==g.CHILD else SPRAY_FIELDS))
   fixture+=W(t)+W(len(args))+W(len(data))+b''.join(W(v)for v in args)+data
 binary=out/'fixture.bin';binary.write_bytes(fixture);assembly=out/'fixture.s';obj=assembly.with_suffix('.o')
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_actor_bound_burst_150b7b40_native.c.in').read_text();decl='\n'.join(v for v in source.PIN['declarations'].splitlines()if not v.startswith('extern '))
 variants=[('recovered-O'+str(opt),opt,source.PIN['body'],True)for opt in(0,2,3)]
 body=source.PIN['body']
 for label,old,new in(('heading','& 127;','& 63;'),('pitch','pitch = -32 -','pitch = -31 -'),('floor-depth','- 2000.0f','- 2048.0f'),('child-duration','child.field54 = 300;','child.field54 = 299;'),('spray-kind','0x220005;','0x220004;'),('spray-damping','spray.field18 = D_8009FD64;','spray.field18 = D_8009FD60;'),('clamp-upper','if (factorX > 1.0f) factorX = 1.0f;','if (factorX > 1.0f) factorX = 2.0f;'),('loop-count','while (index < 2);','while (index < 1);')):
  assert old in body;variants.append(('negative-'+label,2,body.replace(old,new),False))
 runs=[]
 for label,opt,body,good in variants:
  code=out/(label+'.c');exe=code.with_suffix('');code.write_text(template.replace('@DECLARATIONS@',decl).replace('@BODY@',body))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-ffp-contract=off','-fno-builtin',str(code),str(obj),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True);assert q.returncode==0,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(out/(label+'.txt')).write_text(log)
  row=dict(label=label,positive=good,exit_code=q.returncode,log=log.strip(),source_sha256=hashlib.sha256(code.read_bytes()).hexdigest());runs.append(row);print(json.dumps(row),flush=True)
  assert q.returncode==(0 if good else 3),(label,q.returncode,log)
 source.check_inputs();report=dict(passes=True,cases_per_positive_run=len(cases),provider_calls_per_positive_run=total,positive_runs=3,effective_negatives=8,exact_event_arguments_and_initialized_observations=True,descriptor_initialized_bytes=[112,132],unwritten_descriptor_bytes_not_read=True,public_memory_windows=3,strict_aliasing=True,UBSan=True,children_and_other_providers_modeled=True,private_relation_separate=True,hardware_runtime_unclaimed=True,source_installed=source.installed(),c_match_credit=0,runs=runs,fixture_sha256=hashlib.sha256(fixture).hexdigest())
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
