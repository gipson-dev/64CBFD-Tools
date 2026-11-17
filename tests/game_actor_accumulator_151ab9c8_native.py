from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_actor_accumulator_151ab9c8_recovery as source
from tools.tests import game_actor_accumulator_151ab9c8_oracle as g
R,P=source.ROOT,source.OUT
def main():
 out=P/'native-v28';out.mkdir(exist_ok=False);blob=bytearray();count=0
 tokens={'surface':0xffffffe0,'position':0xffffffe1,'velocity':0xffffffe2}
 for c in g.cases():
  initial=g.fixture(c);final,calls,truncated=g.reference(initial,c)
  if truncated:continue
  assert len(calls)<=50;blob+=struct.pack('<5I',*g.asdict(c).values())
  for mem in(initial,final):
   for at in(g.RECORD,g.ACTOR,g.OTHER):blob+=g.data(mem,at,512)
   blob+=struct.pack('<4I',*(g.read(mem,a)for a in(g.DT,g.C0,g.C1,g.MARK)))
  blob+=struct.pack('<I',len(calls))
  for t,args,observed in calls:
   a=[tokens.get(v,v)if isinstance(v,str)else v for v in args]
   blob+=struct.pack('<18I',t,len(a),*a,*([0]*(16-len(a))))+observed+bytes(60-len(observed))
  blob+=bytes((50-len(calls))*132);count+=1
 data=out/'fixtures.bin';data.write_bytes(blob)
 assembly='.pushsection .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin "'+str(data)+'"\n.popsection\n'
 template=Path(__file__).with_suffix('.c').read_text().replace('@DECLARATIONS@',(P/'declarations-v28.txt').read_text()).replace('@COUNT@',str(count))
 template+='\n__asm__('+json.dumps(assembly)+');\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 body=(P/'body-v28.txt').read_text().replace('func_151AB9C8','invoke',1)
 controls={'snapshot-width':('*(u16 *)(state->actor + 0x84)','(u32)*(s16 *)(state->actor + 0x84)'), 'threshold-equality':('state->time > 1.0f','state->time >= 1.0f'),'wrong-selector':('state->selector,','state->identity,'),'wrong-rate':('sample * state->rateRange','sample * state->rateBase'),'wrong-loop-update':('state->time -= 1.0f','state->time -= 2.0f')}
 runs=[]
 for label,variant in [('v28',body)]+[(label,body.replace(a,b))for label,(a,b)in controls.items()]:
  assert label=='v28'or variant!=body
  for opt in(('-O0','-O2','-O3')if label=='v28'else('-O2',)):
   name=label+opt;src=out/(name+'.c');exe=src.with_suffix('');src.write_text(template.replace('@BODY@',variant));start=time.monotonic()
   q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-builtin',str(src),'-o',str(exe)],cwd=R,capture_output=True,text=True);assert q.returncode==0,q.stderr
   result=subprocess.run([str(exe)],cwd=R,capture_output=True,timeout=30);expected=0 if label=='v28'else 3;assert result.returncode==expected,(name,result.returncode,expected,result.stderr.hex())
   record=dict(label=label,opt=opt,exit_code=result.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),seconds=round(time.monotonic()-start,3));runs.append(record);print(json.dumps(record),flush=True)
 report=dict(cases=count,runs=runs,passes=True,strict_aliasing=True,UB_traps=True,nonterminating_cases_excluded_from_native=True,source_installed=source.installed(),c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(runs),passes=True)),flush=True)
if __name__=='__main__':main()
