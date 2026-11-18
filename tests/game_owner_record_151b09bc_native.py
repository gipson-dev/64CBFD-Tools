"""Fresh native32 constructor execution with effective ABI/content/return controls."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,struct,subprocess
from tools.tests import game_owner_record_151b09bc_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
p=g.p
TOKENS={name:0xffffffe0+i for i,name in enumerate(('source','binding','output+40','payload'))}

def image(m):
    return g.data(m,g.A,512)+g.data(m,g.S,32)+g.data(m,g.ALT,512)+g.data(m,g.O,256)+g.data(m,g.TABLE,320)+g.data(m,g.MARK,4)

def main():
    out=p/'native';out.mkdir(exist_ok=False);blob=bytearray();count=0
    for c in g.cases():
        initial=g.fixture(c);final,calls,answer=g.reference(initial,c);assert len(calls)<=4
        blob+=struct.pack('<14I',*(g.u32(v)for v in asdict(c).values()))+image(initial)
        expected=dict(final)
        if answer:
            for i in g.HOLES:expected[answer+40+i]=0
        blob+=image(expected)+struct.pack('<2I',answer,len(calls))
        for target,args,observed in calls:
            args=[TOKENS.get(v,v)if isinstance(v,str)else v for v in args]
            blob+=struct.pack('<10I',target,len(args),*args,*([0]*(8-len(args))))+observed+bytes(152-len(observed))
        blob+=bytes(192*(4-len(calls)));count+=1
    assert count==928 and len(blob)==count*4104
    fixture=out/'fixtures.bin';fixture.write_bytes(blob);assembly=out/'fixtures.s'
    assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\n.section .note.GNU-stack,"",@progbits\n')
    q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(out/'fixtures.o')],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
    source=g.recovery.PIN['body'].replace('u8 *func_151B09BC(', 'u8 *invoke(',1)
    template=Path(__file__).with_name('game_owner_record_151b09bc_native.c.in').read_text().replace('@DECLARATIONS@',g.recovery.PIN['declarations']).replace('@COUNT@',str(count))
    changes={
        'duration-sentinel':('duration == -1','duration == 0'),
        'default-duration':('chosenDuration = 300;','chosenDuration = 301;'),
        'binding-owner-reuse':('record.owner = owner;','record.owner = binding.owner;'),
        'wrong-selector':('record.selector = 1;','record.selector = 0;'),
        'missing-group-component':('record.groups[i][2] = 0;','record.groups[i][2] = 1;'),
        'negative-zero':('record.zero90 = 0.0f;','record.zero90 = -0.0f;'),
        'wrong-channel':('sizeof(record), channel, context);','sizeof(record), (u8)duration, context);'),
        'short-copy':('memcpy(created + 0x28, &record, sizeof(record));','memcpy(created + 0x28, &record, sizeof(record)-4);'),
        'return-copy-destination':('if (created != NULL) memcpy(','if (created != NULL) created = memcpy('),
    }
    forms=[('selected',source,opt)for opt in('-O0','-O2','-O3')]
    for name,(before,after)in changes.items():assert source.count(before)==1,(name,before);forms.append((name,source.replace(before,after),'-O2'))
    runs=[]
    for name,body,opt in forms:
        stem=name+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(template.replace('@BODY@',body))
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(src),str(out/'fixtures.o'),'-o',str(exe)],capture_output=True,text=True)
        (out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,(name,q.stderr)
        q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
        runs.append(dict(name=name,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()))
    report=dict(cases=count,runs=runs,passes=True,fixture_sha256=hashlib.sha256(blob).hexdigest(),
                new_native_compilation=True,strict_aliasing=True,UB_traps=True,defined_payload_bytes=146,
                uncredited_payload_padding_bytes=6,binding_defined_bytes=5,modeled_allocator=True,c_match_credit=0)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(runs),passes=True)),flush=True);return report
