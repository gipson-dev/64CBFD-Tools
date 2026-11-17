from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,sys,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_strip_constructor_151acbd4_private_recovery as source
from tools.tests import game_strip_constructor_151acbd4_private_oracle as g
R,P=source.ROOT,source.OUT
def main():
 out=P/'native-v7';out.mkdir(exist_ok=False);blob=bytearray();count=0
 for c in g.cases():
  initial=g.fixture(c);final,calls,result=g.reference(initial,c)
  assert len(calls)<=4;blob+=struct.pack('<8I',*(v&0xffffffff for v in g.asdict(c).values()))
  for mem in(initial,final):
   for at,n in g.REGIONS[:5]:blob+=g.data(mem,at,n)
   blob+=struct.pack('<2I',g.read(mem,g.CATEGORY),g.read(mem,g.MARK))
  blob+=struct.pack('<I',len(calls))
  for t,args in calls:blob+=struct.pack('<8I',t,len(args),*args,*([0]*(6-len(args))))
  blob+=bytes((4-len(calls))*32);count+=1
 data=out/'fixtures.bin';data.write_bytes(blob)
 assembly='.pushsection .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin "'+str(data)+'"\n.popsection\n'
 template=Path(__file__).with_suffix('.c.in').read_text().replace('@DECLARATIONS@',(P/'declarations.txt').read_text()).replace('@COUNT@',str(count))
 for key,value in {'CREATE':g.CREATE,'ALLOC':g.ALLOC,'COPY':g.COPY}.items():template=template.replace('@'+key+'@',hex(value))
 template+='\n__asm__('+json.dumps(assembly)+');\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 body=(P/'body-v7.txt').read_text().replace('func_151ACBD4','invoke',1)
 controls={'signed-interpolation-overflow':('(f32)(s32)((u32)((s32)((u32)delta * (u32)i) / 19) + (u32)endY)','(f32)(delta * i / 19 + endY)'), 'wrong-texture':('record->texture = 54','record->texture = 53'),'wrong-class':('D_800BE9F0 == 0x2C','D_800BE9F0 == 0x2D'),'wrong-UV':('u1 = (0x100 + textureStep) << 5','u1 = (0x100 + textureStep) << 4'),'clobbered-position':('record->vertices[bank * 80 + i * 4].v.flag = 0;','record->vertices[bank * 80 + i * 4].v.ob[0] = 0;\n            record->vertices[bank * 80 + i * 4].v.flag = 0;')}
 runs=[]
 for label,variant in [('v7',body)]+[(label,body.replace(a,b))for label,(a,b)in controls.items()]:
  assert label=='v7'or variant!=body
  for opt in(('-O0','-O2','-O3')if label=='v7'else('-O2',)):
   name=label+opt;src=out/(name+'.c');exe=src.with_suffix('');src.write_text(template.replace('@BODY@',variant));start=time.monotonic()
   q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-builtin','-Wno-unused-function',str(src),'-o',str(exe)],cwd=R,capture_output=True,text=True);assert q.returncode==0,q.stderr
   result=subprocess.run([str(exe)],cwd=R,capture_output=True,timeout=30);expected=(0,)if label=='v7'else(3,-4)if label=='signed-interpolation-overflow'else(3,);assert result.returncode in expected,(name,result.returncode,expected,result.stderr.hex())
   row=dict(label=label,opt=opt,exit_code=result.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),seconds=round(time.monotonic()-start,3));runs.append(row);print(json.dumps(row),flush=True)
 report=dict(cases=count,runs=runs,passes=True,strict_aliasing=True,UB_traps=True,source_installed=False,c_match_credit=0,FP_status_not_checked_by_native=True)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(runs),passes=True)),flush=True)
if __name__=='__main__':main()
