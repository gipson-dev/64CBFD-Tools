"""Fresh native32 source builds, complete call words and finite zero controls."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,struct,subprocess
from tools.tests import game_snapshot_trail_151b0050_oracle as o
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
p=o.p

def main():
 out=p/'native';out.mkdir(exist_ok=False);vectors=bytearray();count=0
 for c in o.cases():
  if c.pattern not in(0,2,4)or c.mutation&2:continue
  initial=o.fixture(c);expected,calls,packets=o.reference(initial,c);assert len(calls)==8 and len(packets)==1
  vectors+=struct.pack('<10I',*asdict(c).values())
  for memory in(initial,expected):
   vectors+=bytes(memory[o.OUTPUT+i]for i in range(128))
   for at in o.GLOBALS:vectors+=bytes(memory[at+i]for i in range(4))
  for target,args in calls:
   args=[0x60000 if x=='POSITION'else 0x60010 if x=='DIRECTION'else x for x in args]
   vectors+=struct.pack('<20I',target,len(args),*args,*([0]*(18-len(args))))
  vectors+=struct.pack('<6I',*packets[0][0],*packets[0][1]);count+=1
 assert count==640 and len(vectors)==count*1000
 fixture=out/'fixtures.bin';fixture.write_bytes(vectors);assembly=out/'fixtures.s';assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 source=o.source.PIN['body'];declarations=o.source.PIN['declarations'];template=Path(__file__).with_name('game_snapshot_trail_151b0050_native.c.in').read_text().replace('@COUNT@',str(count)).replace('@DECLARATIONS@',declarations)
 changes={'folded-zero-multiply':('captures.extentSample * (f32)(s32)0 + D_800AA294','D_800AA294'),'wrong-snapshot-X':('position.x = x;','position.x = y;'),'signed-duration-remainder':('captures.durationSample % 20U','(s32)captures.durationSample % 20'),'swapped-angles':('func_15143794(heading, pitch,','func_15143794(pitch, heading,'),'wrong-channel':('0, slot, 1);','0, (u8)heading, 1);'),'wrong-eighteenth-argument':('0, slot, 1);','0, slot, 0);'),'wrong-return':('    return 1;','    return 0;')}
 forms=[('selected',source,opt)for opt in('-O0','-O2','-O3')]
 for name,(before,after)in changes.items():assert source.count(before)==1,(name,before);forms.append((name,source.replace(before,after),'-O2'))
 rows=[]
 for name,variant,opt in forms:
  stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',variant))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
  (out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
  rows.append(dict(name=name,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()))
 report=dict(cases=count,runs=rows,passes=True,fixture_sha256=hashlib.sha256(vectors).hexdigest(),new_native_compilation=True,finite_and_signed_zero_only=True,all18_arguments_and_both_vectors_checked=True,strict_aliasing=True,UB_traps=True,c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(rows),passes=True)),flush=True)
 return report

if __name__=='__main__':main()
