"""New native32 finite-input qualification and semantic corruption controls."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.tests import game_strip_follow_151ae3a8_oracle as o
from tools.tests.test_game_projected_packet_draw import native_command
p=o.p
REGIONS=((o.ACTOR,1024),(o.OTHER_ACTOR,1024),(o.RECORD,88),(o.OTHER_RECORD,88),(o.CHILD,192),(o.OTHER_CHILD,192),(o.INPUT,64),(o.POINTS-40*24,7680),(o.OTHER_POINTS-40*24,7680))
def main():
 out=p/'native';out.mkdir(exist_ok=False);vectors=bytearray();count=0
 for c in o.cases():
  if c.pattern not in(0,2):continue
  initial=o.fixture(c);expected,calls=o.reference(initial,c);assert len(calls)==3
  vectors+=struct.pack('<8I',c.seed,c.count,o.o.bits(c.spacing),o.o.bits(c.progress),c.heading,c.mutation,c.phase,c.pattern)
  for m in(initial,expected):
   for base,size in REGIONS:vectors+=bytes(m[base+i]for i in range(size))
  vectors+=struct.pack('<7I',*(value for target,args in calls for value in(target,*args)),len(calls));count+=1
 assert len(vectors)==count*36124
 fixture=out/'fixtures.bin';fixture.write_bytes(vectors);assembly=out/'fixtures.s'
 assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n')
 q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 owner=o.source.recover((o.source.FROZEN/o.source.SOURCE).read_text());start=owner.index('typedef struct { f32 position[3]');end=owner.index('extern s32 D_800BE9F0;',start)
 template=Path(__file__).with_name('game_strip_follow_151ae3a8_native.c.in').read_text().replace('@VIEWS@',owner[start:end]).replace('@COUNT@',str(count));body=o.source.PIN['body']
 controls={'wrong-angle-bias':('local.angle - 0x40','local.angle - 0x20'),'wrong-next-Z':('byteOffset + 32','byteOffset + 28'),'reload-mutated-record':('record = local.record;','record = *(StripRecord151ACBD4 **)(*(u8 **)(actor + 0x31C) + 0x9C);'),'wrong-forward-offset':('offsetZ = scale * forward;','offsetZ = scale * local.side;')}
 forms=[('selected',body,opt)for opt in('-O0','-O2','-O3')]
 for name,(before,after)in controls.items():assert body.count(before)==1,(name,before);forms.append((name,body.replace(before,after),'-O2'))
 rows=[]
 for name,variant,opt in forms:
  stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',variant))
  q=subprocess.run(native_command(opt)+['-Wno-unused-but-set-variable','-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
  (out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
  row=dict(name=name,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
 report=dict(cases=count,runs=rows,passes=True,fixture_sha256=hashlib.sha256(vectors).hexdigest(),new_native_compilation=True,finite_and_signed_zero_inputs_only=True,all_public_regions_and_three_calls=True,strict_aliasing=True,UB_traps=True,source_installed=False,c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(rows),passes=True)),flush=True)
if __name__=='__main__':main()
