"""Fresh SDK32 source executions and effective semantic controls."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,struct,subprocess
from tools.tests import game_actor_trail_151b01b8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
p=g.p
TOKENS={name:0xffffffe0+i for i,name in enumerate(('matrix1','matrix2','surface','actor','source','point','position','angles','trail'))}

def main():
    out=p/'native-qualified-v2';out.mkdir(exist_ok=False);blob=bytearray();count=0
    for c in g.cases():
        initial=g.fixture(c);final,calls=g.reference(initial,c);assert len(calls)<=4
        blob+=struct.pack('<10I',*asdict(c).values())
        for m in(initial,final):
            blob+=g.data(m,g.A,512)+g.data(m,g.S,32)+g.data(m,g.TABLE,320)+g.data(m,g.POINT,12)+g.data(m,g.COEF,20)+g.data(m,g.MARK,4)
        blob+=struct.pack('<I',len(calls))
        for target,args,observed in calls:
            args=[TOKENS.get(v,v)if isinstance(v,str)else v for v in args]
            blob+=struct.pack('<7I',target,len(args),*args,*([0]*(5-len(args))))+observed+bytes(112-len(observed))
        blob+=bytes(140*(4-len(calls)));count+=1
    assert count==912 and len(blob)==count*2404
    fixture=out/'fixtures.bin';fixture.write_bytes(blob)
    assembly=out/'fixtures.s';assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n')
    q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
    source=g.recovery.PIN['body'].replace('void func_151B01B8(', 'void invoke(',1)
    template=Path(__file__).with_name('game_actor_trail_151b01b8_native.c.in').read_text().replace('@DECLARATIONS@',g.recovery.PIN['declarations']).replace('@COUNT@',str(count))
    changes={
        'heading-no-byte-wrap':('    u8 heading;','    u32 heading;'),
        'heading-low-half':('actor + 0x7A) >> 8','actor + 0x7A) >> 0'),
        'disabled-type':('selected.record[14] != 2','selected.record[14] != 3'),
        'wrong-transform-matrix':('+ 0x180);','+ 0x184);'),
        'selector-always-zero':('trail.selector = 1;','trail.selector = 0;'),
        'wrong-duration':('trail.durationBase = 30;','trail.durationBase = 31;'),
        'wrong-slot':('(s32)&surface, 255, 1);','(s32)&surface, 254, 1);'),
        'missing-surface-call':('func_1504715C(&surface, (HeightActor71820 *)actor);',';'),
    }
    forms=[('selected',source,opt)for opt in('-O0','-O2','-O3')]
    for name,(before,after)in changes.items():
        assert source.count(before)==1,(name,before)
        forms.append((name,source.replace(before,after),'-O2'))
    runs=[]
    for name,body,opt in forms:
        stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',body))
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
        (out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr)
        assert q.returncode==0 and not q.stderr,(name,q.stderr)
        q=subprocess.run([str(exe)],capture_output=True,timeout=30)
        assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
        runs.append(dict(name=name,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()))
    report=dict(cases=count,runs=runs,passes=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),
                new_native_compilation=True,strict_aliasing=True,UB_traps=True,defined_trail_bytes=65,
                uncredited_trail_padding_bytes=3,defined_disjoint_outputs=True,c_match_credit=0)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=count,runs=len(runs),passes=True)),flush=True)
    return report
