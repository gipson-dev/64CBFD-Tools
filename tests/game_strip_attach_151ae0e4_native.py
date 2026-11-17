"""Compile new native32 C at O0/O2/O3; mapped finite fixtures and controls."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.tests import game_strip_attach_151ae0e4_oracle as o
from tools.tests.test_game_projected_packet_draw import native_command
p=o.p
REGIONS=((o.ACTOR,1024),(o.RECORD,88),(o.OTHER_RECORD,88),(o.CHILD,192),(o.OTHER_CHILD,192),(o.REQUEST,64),(o.POINTS-32*24,6912),(o.OTHER_POINTS-32*24,6912),(o.CUTOFF,4))
def main():
 out=p/'native';out.mkdir(exist_ok=False);vectors=bytearray();count=0
 for c in o.cases():
  initial=o.fixture(c);expected,calls,spin=o.reference(initial,c)
  if spin:continue
  vectors+=struct.pack('<10I',c.seed,c.key,c.count,o.o.bits(c.spacing),o.o.bits(c.fraction),c.gate,c.mutation,c.phase,c.threshold,c.nan_point)
  for memory in(initial,expected):
   for base,size in REGIONS:vectors+=bytes(memory[base+i]for i in range(size))
  args=[]
  for target,a in calls:args.extend((target,*a,*([0]*(5-len(a)))))
  args.extend([0]*(12-len(args)));vectors+=struct.pack('<13I',*args,len(calls));count+=1
 assert len(vectors)==count*31044
 fixture=out/'fixtures.bin';fixture.write_bytes(vectors);assembly=out/'fixtures.s'
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 owner=o.source.recover((o.source.FROZEN/o.source.SOURCE).read_text());start=owner.index('typedef struct { f32 position[3]');end=owner.index('extern s32 D_800BE9F0;',start)
 template=Path(__file__).with_name('game_strip_attach_151ae0e4_native.c.in').read_text().replace('@VIEWS@',owner[start:end]).replace('@COUNT@',str(count));body=o.source.PIN['body']
 controls={'wrong-status-width':('record->status == 0','*(s8 *)&record->status == 0'),'wrong-fifth-Z-argument':('*(f32 *)(actor + 0x1C));','0.0f);'),'wrong-span':('record->spacing) - 1','record->spacing) - 2'),'wrong-NaN-distance-branch':('!(D_800A9290 < dz * dz + (dx * dx + dy * dy))','(dz * dz + (dx * dx + dy * dy) <= D_800A9290)')}
 forms=[('selected',body,opt)for opt in('-O0','-O2','-O3')]
 for name,(before,after)in controls.items():assert body.count(before)==1,(name,before);forms.append((name,body.replace(before,after),'-O2'))
 rows=[]
 for name,variant,opt in forms:
  stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',variant))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
  (out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
  row=dict(name=name,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
 report=dict(cases=count,runs=rows,passes=True,fixture_sha256=hashlib.sha256(vectors).hexdigest(),new_native_compilation=True,all_public_regions_and_five_arguments=True,null_spin_excluded_from_native=True,strict_aliasing=True,UB_traps=True,source_installed=False,c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(rows),passes=True)),flush=True)
if __name__=='__main__':main()
