"""New native32 finite/signed-zero trail emission and argument controls."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,struct,subprocess
from tools.tests import game_random_trail_151aeab4_oracle as o
from tools.tests.test_game_projected_packet_draw import native_command
p=o.p;REGIONS=((o.POSITION,64),(o.OUTPUT,128),(o.ACTOR,256),*((at,4)for at in o.GLOBALS))
def main():
 out=p/'native';out.mkdir(exist_ok=False);vectors=bytearray();count=0
 for c in o.cases():
  if c.pattern not in(0,2):continue
  initial=o.fixture(c);expected,calls,packets=o.reference(initial,c);assert len(calls)==13 and len(packets)==1
  vectors+=struct.pack('<11I',*asdict(c).values())
  for memory in(initial,expected):
   for base,size in REGIONS:vectors+=bytes(memory[base+i]for i in range(size))
  for row in calls:
   target,args=row[:2];args=[0x60000 if x=='VELOCITY'else x for x in args];vectors+=struct.pack('<20I',target,len(args),*args,*([0]*(18-len(args))))
  vectors+=struct.pack('<3I',*packets[0]);count+=1
 assert len(vectors)==count*2024
 fixture=out/'fixtures.bin';fixture.write_bytes(vectors);assembly=out/'fixtures.s';assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 body=o.source.PIN['body'];template=Path(__file__).with_name('game_random_trail_151aeab4_native.c.in').read_text().replace('@COUNT@',str(count))
 changes={'wrong-pitch-mask':('& 0x7F','& 0x3F'),'signed-lifetime-remainder':('local.firstValue % 41U','(s32)local.firstValue % 41'),'wrong-velocity-Z':('local.velocity[2] = horizontal * local.azimuthValue;','local.velocity[2] = horizontal * local.azimuthQuarter;'),'wrong-eighteenth-argument':('0xF, 0, (u8)channel, 1','0xF, 0, (u8)channel, 0')}
 forms=[('selected',body,opt)for opt in('-O0','-O2','-O3')]
 for name,(before,after)in changes.items():assert body.count(before)==1,(name,before);forms.append((name,body.replace(before,after),'-O2'))
 rows=[]
 for name,variant,opt in forms:
  stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',variant))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
  (out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
  row=dict(name=name,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
 report=dict(cases=count,runs=rows,passes=True,fixture_sha256=hashlib.sha256(vectors).hexdigest(),new_native_compilation=True,finite_and_signed_zero_only=True,all18_arguments_and_velocity_checked=True,strict_aliasing=True,UB_traps=True,source_installed=False,c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(rows),passes=True)),flush=True)
if __name__=='__main__':main()
