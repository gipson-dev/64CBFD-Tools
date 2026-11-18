"""Native32/UBSan source screen using independently predicted byte snapshots."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,sys,time
from tools.tests import game_owner_pool_update_151b0b88_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    p=g.p
    W=lambda n:struct.pack('<I',n&0xffffffff)
    windows=[(g.RECORD,256),(g.OWNER,512),(g.MATRIX,4096),(g.MARK,4),(g.POINTS,176),(g.ALT,176),(g.PALETTE,256),(g.TICKS,4),(g.TIME,4),(g.INV,4),(g.COEF,16)]
    windows += [(a,512)for i in range(11)for a in(g.child(i),g.output(i))]
    fields=[(g.RECORD+14,2),(g.STATE,4),(g.STATE+8,4),(g.STATE+144,4),(g.OWNER,4),(g.OWNER+468,4),(g.MARK,4),(g.TICKS,4),(g.TIME,4),(g.INV,4)]
    fields += [(g.STATE+12+i*12+off,4)for i in range(11)for off in(0,4,8)]
    fields += [(base+i*16+off,4)for base in(g.POINTS,g.ALT)for i in range(11)for off in(4,8,12)]
    fields += [(g.COEF+off,4)for off in(0,4,8,12)]
    fields += [(g.child(i)+off,4)for i in range(11)for off in(52,56,60,64,68,72,88,272,276,280)]
    fields += [(g.output(i)+272+off,4)for i in range(11)for off in(12,20,24,28,32)]
    assert len(fields)==len(set(fields))
    def native_bytes(m,a,n):
     result=bytearray(g.data(m,a,n))
     for at,width in fields:
      if a<=at and at+width<=a+n:result[at-a:at-a+width]=result[at-a:at-a+width][::-1]
     return bytes(result)
    def trace(calls):
     value=2166136261
     def word(n):
      nonlocal value
      value=((value^n)*16777619)&0xffffffff
     for target,args,observed in calls:
      word(target);word(len(args))
      for arg in args:word({'position':0xFFFFFF01,'request':0xFFFFFF02,'payload':0xFFFFFF03}[arg]if isinstance(arg,str)else arg)
      word(len(observed))
      for b in observed:word(b)
     return value

    all_cases=list(g.cases());fixture=p/'native-fixture.bin'
    out=bytearray(W(len(all_cases))+W(len(windows)))
    for c in all_cases:
     initial=g.fixture(c);expected,s=g.reference(initial,c)
     out+=W(c.seed)+W(c.failure)+W(c.mutation)+W(trace(s.calls))
     skipped={a+272+i for a in s.outputs for i in(*range(12),38,39)}
     for a,n in windows:
      out+=W(a)+W(n)+native_bytes(initial,a,n)+native_bytes(expected,a,n)+bytes(int(a+i not in skipped)for i in range(n))
    fixture.write_bytes(out)
    assembly=p/'native-fixture.s';fixture_object=p/'native-fixture.o'
    assembly.write_text('.section .rodata\n.balign 4\n.global fixture_rows,fixture_end\nfixture_rows:\n.incbin '+json.dumps(str(fixture.resolve()))+'\nfixture_end:\n.section .note.GNU-stack,"",@progbits\n')
    q=subprocess.run(['cc','-m32','-c',str(assembly),'-o',str(fixture_object)],capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
    base='byte-pre'
    decl=(p/(base+'.decl')).read_text();body=(p/(base+'.body')).read_text()
    decl='\n'.join(line for line in decl.splitlines()if not line.startswith('extern '))
    template=Path(__file__).with_name('game_owner_pool_update_151b0b88_native.c.in').read_text().replace('@DECLARATIONS@',decl).replace('@REQUEST_DEFINED@',','.join(map(str,g.REQ_DEFINED)))
    reports=[]
    variants=[('O0',0,body,True),('O2',2,body,True),('O3',3,body,True)]
    for label,old,new in (
     ('owner-word','*(u32 *)state->owner == 0','state->owner == NULL'),
     ('identity-width','state->identity != state->owner[0x3B]','*(u32 *)((u8 *)state + 4) != *(u32 *)(state->owner + 0x3B)'),
     ('expiry-boundary','slot->ticks < 0','slot->ticks <= 0'),
     ('slot-count','index != 11','index != 10'),
     ('threshold','state->accumulator > 1.0f','state->accumulator >= 1.0f'),
     ('duration-modulus','% 51U','% 50U'),
     ('short-copy','memcpy(freeHead->child + 0x110, &payload, 40)','memcpy(freeHead->child + 0x110, &payload, 36)'),
     ('selector-reload','payload.selector = state->selector;','payload.selector = state->selector;'),
    ):
     assert old in body,(label,old)
     changed=body.replace(old,new)
     if label=='selector-reload':changed=changed.replace('                        state->accumulator -= 1.0f;', '                        payload.selector = state->selector;\n                        state->accumulator -= 1.0f;')
     assert changed!=body,label
     variants.append((label,2,changed,False))
    for label,opt,code,good in variants:
     source=p/('native-'+label+'.c');binary=source.with_suffix('');source.write_text(template.replace('@BODY@',code))
     command=native_command('-O'+str(opt))+['-fstrict-aliasing','-fno-fast-math','-fno-builtin',str(source),str(fixture_object),'-o',str(binary)]
     result=subprocess.run(command,capture_output=True,text=True);assert result.returncode==0,(label,result.stderr)
     run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
     log=run.stdout+run.stderr;(p/('native-'+label+'.txt')).write_text(log)
     expected_exit=0 if good else(-4 if label=='identity-width'else 3)
     assert run.returncode==expected_exit,(label,run.returncode,log)
     row=dict(label=label,optimization=opt,passes=good,exit_code=run.returncode,log=log.strip(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
     reports.append(row);print(json.dumps(row),flush=True)
    report=dict(passes=True,source=base,cases_per_positive_run=len(all_cases),positive_runs=3,effective_negatives=len(variants)-3,strict_aliasing=True,UBSan=True,fixture_sha256=hashlib.sha256(out).hexdigest(),runs=reports,defined_request_bytes=67,defined_payload_bytes=26,padding_uncredited=True,c_match_credit=0)
    (p/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
