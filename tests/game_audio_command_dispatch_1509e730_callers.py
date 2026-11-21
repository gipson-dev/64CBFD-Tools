from pathlib import Path
import hashlib,itertools,json,os,struct,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.tests import game_audio_command_dispatch_1509e730_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run(control=None):
    END,TARGETS,CURSOR=0x1555fff0,0x800884d4,0x72000
    rom=(root/'conker/conker.us.bin').read_bytes();fp=json.loads((out/'baseline/fingerprints.json').read_text())['inputs']
    assert hashlib.sha256(rom).hexdigest()==fp['conker/conker.us.bin']
    for n,d in json.loads((out/'extra-inputs.json').read_text()).items():
        assert hashlib.sha256((root/n).read_bytes()).hexdigest()==hashlib.sha256((out/'caller-baseline'/n).read_bytes()).hexdigest()==d,n
    obj=out/'qualified-source-screen/candidate.o';raw,rawtable=g.program(obj);normal,table=g.program(obj,True)
    retail=struct.unpack_from('>92I',rom,0xcbbe0);assert normal==retail
    windows={'varargs':(0x1509c0d8,0xc9588,18),'interpreter':(0x150ae12c,0xdb5dc,26)}
    streams={'retail':(retail,table),'compiled_C':(raw,rawtable),'normalized_C':(normal,table)}
    counts={};helper_calls=0
    controls={'varargs-missing-home-delay':('varargs',11,0xafa9001c),
     'varargs-missing-command-load':('varargs',9,0x8fa50038),
     'interpreter-missing-packet-delay':('interpreter',4,0x00803025),
     'interpreter-missing-handle-delay':('interpreter',22,0x014b2024)}
    if control:assert control in controls
    for label,(start,offset,length)in windows.items():
        if control and label!=controls[control][0]:continue
        body=struct.unpack_from('>%dI'%length,rom,offset);count=0
        if control:
            _,index,expected=controls[control];assert body[index]==expected
            body=list(body);body[index]=0
        for command,version,handle,retval,mutation,phase in itertools.product((0,1,2,3,4,5,6,7,0xffffffff),(0,3,5),(0x1234f123,0xffffffff),(0,0x80000000),range(2),(0,8)):
            models=[]
            for name,(words,case_table)in streams.items():
                initial,args=g.fixture(case_table,command,version,handle,retval,mutation,phase,0)
                packet=args[2]
                if label=='varargs':
                    packet=0x800d2f60
                    initial.update({packet+i:(i*29+0x51)&255 for i in range(32)})
                    for i,value in enumerate((0x13579bdf,command,0x80000fff,0xffffffff,0xabcdf123,0x7fffffff)):g.put(initial,packet+4*i,value)
                else:
                    packet=g.PACKET
                    initial.update({packet+i:(i*29+0x51)&255 for i in range(32)})
                    encoded=(handle&0xffff0fff)|0xa000
                    g.put(initial,packet,encoded);g.put(initial,packet+4,command);handle_arg=encoded&0xffff0fff
                args=(g.u32(handle if label=='varargs'else handle_arg),g.u32(command),packet)
                for i,value in enumerate(struct.unpack_from('>15I',rom,0x22cf94)):g.put(initial,TARGETS+4*i,value)
                g.put(initial,CURSOR,0x33445566)
                code=dict(zip(range(g.ENTRY,g.ENTRY+len(words)*4,4),words));code[END]=0
                m=g.Oracle(body,initial,args,retval,mutation,phase,entry=start,connected=code)
                sp=m.r[29];m.r[31]=END;m.r[5]=0x55555555;m.r[6]=0x73737373
                expected,calls,result=g.reference(initial,args,retval,mutation)
                if label=='varargs':
                    m.r[10]=9;m.r[14]=0x12345678;m.r[11]=CURSOR;m.r[9]=0x87654321;m.r[7]=g.u32(handle)
                    g.put(m.memory,sp+0x14,END);g.put(m.memory,sp+0x38,command)
                    g.put(expected,CURSOR,0x1234567a);g.put(expected,g.VERSION,0x87654321)
                    expected_sp=sp+0x30
                else:m.r[4]=packet;expected_sp=sp
                m.code=WindowCode(m.code,m);m.code.ends=(END,)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Caller did not reach its actual return')
                assert m.entry_observations==[args],(label,name,args,m.entry_observations)
                assert m.calls==[(g.ENTRY,args)]+calls,(label,name,command,m.calls,calls)
                assert(m.r[2],g.public(m.memory))==(result,g.public(expected)),(label,name,command,version,'effects')
                assert m.r[29]==expected_sp and m.r[31]==END,(label,name,'actual caller tail')
                if label=='interpreter':assert m.r[23]==END
                else:assert m.r[23]==m.initial_gprs[23]
                if models:
                    assert m.private_calls==models[0].private_calls,(label,name,'nested frame')
                    assert bytes(m.memory[sp+i]for i in range(-64,0))==bytes(models[0].memory[sp+i]for i in range(-64,0)),(label,name,'nested final memory')
                models.append(m)
            helper_calls+=len(calls);count+=1
        counts[label]=dict(cases_per_stream=count,original_window_words=length,original_jalr_and_delay=True,
                          actual_original_return_tail=True,full_caller_claim=False)
    report=dict(windows=counts,streams=3,helper_calls_per_stream=helper_calls,
     source_installed=recovery.installed(),matching_credit=0,limits='Bounded original windows with explicit supplied live registers and established caller frames; whole outer callers remain unrecovered.')
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
