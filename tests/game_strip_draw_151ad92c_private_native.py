"""Selected semantic C, SDK macros, all finite fixtures, native32 replay."""
from pathlib import Path
from dataclasses import asdict
import hashlib,importlib.util,json,struct,subprocess,sys
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import game_strip_draw_151ad92c_private_oracle as o
from tools.experiments import game_strip_draw_151ad92c_private_recovery as source
p=source.OUT
def main():
 source.check_inputs()
 label='selected';out=p/'native';out.mkdir(exist_ok=False)
 vectors=bytearray();count=0
 regions=((o.RECORD,128),(o.POINTS,480),(o.VERTICES,2560),(o.OTHER_VERTICES,2560),(o.OUTPUT,4096),(o.OTHER_OUTPUT,4096),(o.TABLE,672))
 assert sum(n for _,n in regions)+8==14600
 for c in o.cases():
  initial=o.fixture(c);expected,calls,answer=o.reference(initial,c);assert len(calls)==1
  vectors+=struct.pack('<10I',*asdict(c).values())
  for memory in(initial,expected):
   for base,size in regions:vectors+=bytes(memory[base+i]for i in range(size))
   vectors+=struct.pack('>2I',memory[o.BANK],o.o.read(memory,o.MODE))
  vectors+=struct.pack('<12I',*calls[0],answer);count+=1
 assert count==544 and len(vectors)==count*29288
 data=out/'fixtures.bin';data.write_bytes(vectors)
 asm='.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(data.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n'
 assembly=out/'fixtures.s';assembly.write_text(asm)
 run=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert run.returncode==0 and not run.stderr,run.stderr
 owner=(source.FROZEN/source.SOURCE).read_text();start=owner.index('typedef struct { f32 position[3]');end=owner.index('extern s32 D_800BE9F0;',start)
 template=Path(__file__).with_name('game_strip_draw_151ad92c_private_native.c.in').read_text().replace('@VIEWS@',owner[start:end]).replace('@DECLARATIONS@',(p/'declarations.txt').read_text()).replace('@COUNT@',str(count))
 body=source.PIN['body']
 controls={'wrong-zero-length-fallback':('normalX = 100.0f;','normalX = 1.0f;'),'wrong-texture-shift':('textureShift = 5;','textureShift = 4;'),'wrong-helper-tail':('0x100, 0x100, 0x3E','0x100, 0x100, 0x3D'),'reload-count-after-provider':('if (count - 1 > 0)', 'count = ((StripRecord151ACBD4 *)record)->count;\n    if (count - 1 > 0)')}
 forms=[('selected',body,opt)for opt in('-O0','-O2','-O3')]
 for name,(before,after)in controls.items():assert body.count(before)==1;forms.append((name,body.replace(before,after),'-O2'))
 rows=[]
 for name,variant,opt in forms:
  stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',variant))
  run=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
  (out/(stem+'-compile.txt')).write_text(run.stdout+run.stderr);assert run.returncode==0 and not run.stderr,run.stderr
  run=subprocess.run([str(exe)],capture_output=True,timeout=30);assert run.returncode==(0 if name=='selected'else 3),(name,opt,run.returncode,run.stderr)
  row=dict(name=name,opt=opt,exit_code=run.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
 report=dict(label=label,cases=count,runs=rows,passes=True,fixture_sha256=hashlib.sha256(vectors).hexdigest(),all_public_regions_and_eleven_arguments_checked=True,canonicalized_only_pointer_fields=True,strict_aliasing=True,UB_traps=True,source_installed=False,c_match_credit=0,domain='Finite disjoint SDK32 C objects and SSE single precision; no private frame or FCSR claim.')
 with(out/'native-report.json').open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
 source.check_inputs()
 print(json.dumps(dict(label=label,cases=count,native_executions=len(rows),passes=True)),flush=True)
if __name__=='__main__':main()
