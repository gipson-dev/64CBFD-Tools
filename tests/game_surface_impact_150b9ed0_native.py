"""SDK32 native C checked against independent, retail-executed guest transcripts."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_surface_impact_150b9ed0_screen as s
from tools.tests import game_surface_impact_150b9ed0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def run(state,attempt='native'):
 assert Path(attempt).name==attempt
 out=s.OUT/attempt;out.mkdir(exist_ok=False);W=lambda v:struct.pack('<I',v&0xffffffff)
 cases=[c for c in g.cases()if c.phase==0];blob=bytearray(W(len(cases)));calls=0
 for c in cases:
  initial=g.fixture(c);want=g.reference(initial,c);m=g.compare(state['retail_words'],c,'retail');assert(g.public(m.memory),m.calls,m.obs)==want
  final,events,obs=want;roles=g.layout(g.STACK,'retail');spans=dict(burst=40,context=18,position=12,hit=4,spray=116);ids=dict(burst=1,context=2,position=3,hit=4,spray=5)
  def norm(v):
   for n,p in roles.items():
    if p<=v<p+spans[n]:return 0xffff0000+(ids[n]<<12)+v-p
   return v
  for v in(c.path,c.corrupt,c.mutation,c.coords,c.mode,c.tag,c.seed,c.flag,len(events)):blob+=W(v)
  observations=iter(obs)
  for target,args in events:
   packet=b''
   if target in(g.FACTORY,g.SPRAY):
    t,data=next(observations);assert t==target;fields=g.BURST_FIELDS if t==g.FACTORY else g.SPRAY_FIELDS;packet=bytes(data[i]for i in fields)
   blob+=W(target)+W(len(args))+W(len(packet))+b''.join(W(norm(v))for v in args)+packet;calls+=1
  assert next(observations,None)is None
  for v in(final[g.FLAG],*(g.read(final,g.POINT+0x14+4*i)for i in range(3)),*(g.read(final,at)for at in g.CONSTANTS)):blob+=W(v)
 binary=out/'fixture.bin';binary.write_bytes(blob);assembly=out/'fixture.s';obj=assembly.with_suffix('.o')
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(binary.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(obj)],capture_output=True,text=True);assert not q.returncode and not q.stderr,q.stderr
 template=Path(__file__).with_name('game_surface_impact_150b9ed0_native.c.in').read_text();body=s.PIN['body'];decl=s.PIN['declarations']
 controls=(('checksum','checksum += ~*cursor++','checksum += *cursor++'),('gate-subtype','func_150A3058(2,','func_150A3058(3,'),('direction','dx = -(','dx = ('),('duration','% 51U + 100','% 51U + 99'),('color','% 101U + 155','% 101U + 154'),('random-byte','firstRandom & 255','firstRandom & 254'),('negative-zero','spray.direction.y = -dy','spray.direction.y = dy'),('late-constant','spray.field30 = D_8009FE10','spray.field30 = 0.25f'),('mode','func_151511FC(&spray, mode, tag)','func_151511FC(&spray, mode + 1, tag)'),('tag','func_151511FC(&spray, mode, tag)','func_151511FC(&spray, mode, tag + 1)'))
 variants=[('recovered-O'+str(opt),opt,body,True)for opt in(0,2,3)]
 for label,old,new in controls:assert old in body,label;variants.append(('negative-'+label,2,body.replace(old,new),False))
 rows=[]
 for label,opt,variant,good in variants:
  code=out/(label+'.c');exe=code.with_suffix('');code.write_text(template.replace('@DECLARATIONS@',decl).replace('@CODE_WORDS@',','.join(hex(w)+'u'for w in s.checksum_words())).replace('@BODY@',variant))
  q=subprocess.run(native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(code),str(obj),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
  (out/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert not q.returncode,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);(out/(label+'-run.txt')).write_text(q.stdout+q.stderr);row=dict(label=label,positive=good,exit_code=q.returncode,source_sha256=hashlib.sha256(code.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
  assert q.returncode==(0 if good else 3),(label,q.returncode,q.stdout,q.stderr)
 report=dict(passes=True,cases_per_positive_run=len(cases),positive_runs=3,effective_negatives=len(controls),provider_calls_per_run=calls,initialized_descriptor_bytes=[32,110],unwritten_bytes_not_observed=True,strict_aliasing=True,UBSan=True,source_installed=False,c_match_credit=0,fixture_sha256=hashlib.sha256(blob).hexdigest(),runs=rows)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
