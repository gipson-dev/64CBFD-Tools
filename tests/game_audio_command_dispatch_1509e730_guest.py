"""Independent command effects against raw compiled C, normalized C and retail."""
from pathlib import Path
from collections import Counter
import hashlib,itertools,json,struct,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.tests.game_audio_command_dispatch_1509e730_normalizer import ORDER,emit
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,TABLE,VERSION,PACKET,MARK=0x1509E730,0x8009F3D0,0x800D3840,0x30000,0x70000
COUNTS={0x1000D96C:3,0x1000DE1C:2,0x1000DF68:3,0x1000E46C:4,0x1000E654:4,0x1000E054:2}
u32=lambda value:value&0xffffffff

def program(obj,normalized=False):
    blob,refs=payload(obj,'func_1509E730');pool,relocations=normalized_pools(obj)['.rodata']
    assert len(pool)==32 and len(relocations)==7 and pool==bytes(32)
    table=[ENTRY+r[2]for r in relocations]
    if normalized:
        blob,refs,_=emit(blob,refs)
        table=[ENTRY+4*ORDER.index((value-ENTRY)//4)for value in table]
    anchors={n:int(n.split('_')[1],16)for entries in refs.values()for _,n in entries if n!='.rodata'}
    anchors['.rodata']=TABLE
    return tuple(bound_blob(blob,refs,anchors)),tuple(table)

def fixture(table,command,version,handle,retval,mutation,phase,alias):
    for start,size in((PACKET-16,80),(VERSION-16,80),(MARK,16),(TABLE,32)):
        assert start+size<=STACK-128 or start>=STACK+128,('fixture overlaps stack',start,size)
    memory={STACK+i:u32(i*17+0xa5)&255 for i in range(-128,128)}
    for base,size in((PACKET-16,80),(VERSION-16,80),(MARK,16),(TABLE,32)):
        memory.update({base+i:(i*29+0x51)&255 for i in range(size)})
    packet=VERSION-8 if alias else PACKET
    for i,value in enumerate((0x13579bdf,0x2468ace0,0x80000fff,0xffffffff,0xabcdf123,0x7fffffff)):
        put(memory,packet+4*i,value)
    put(memory,VERSION,version)
    for i,value in enumerate(table):put(memory,TABLE+4*i,value)
    if command>=7 and command&1:packet=0
    return memory,(u32(handle),u32(command),packet)

def provider_effect(memory,args,retval,mutation):
    handle,command,packet=args
    put(memory,MARK,u32(retval^handle^command))
    if mutation:
        put(memory,VERSION,read(memory,VERSION)^0xdeadbeef)
        if packet:
            put(memory,packet+8,read(memory,packet+8)^0x55aa55aa)
            put(memory,packet+12,read(memory,packet+12)^0xa5a55a5a)

def reference(initial,args,retval,mutation):
    memory=initial.copy();handle,command,packet=args;handle&=0xfff
    if command>=7:return memory,[],0
    version=read(memory,VERSION)
    if command==0:target,values=0x1000D96C,(handle,read(memory,packet+8),read(memory,packet+12))
    elif command==1:target,values=0x1000DE1C,(handle,read(memory,packet+8))
    elif command==2:target,values=0x1000DF68,(handle,read(memory,packet+8),0)
    elif command==3:target,values=0x1000E46C,(handle,read(memory,packet+8),read(memory,packet+12),read(memory,packet+16)if version==5 else 60)
    elif command==4:target,values=0x1000E654,(handle,read(memory,packet+8),read(memory,packet+12),(read(memory,packet+16)&0xfff)if version==5 else handle)
    elif command==5:target,values=0x1000DF68,(handle,read(memory,packet+8),1)
    else:target,values=0x1000E054,(handle,read(memory,packet+8)if version==3 else 1)
    provider_effect(memory,args,retval,mutation)
    return memory,[(target,values)],u32(retval)if command in(3,4)else 1

class Oracle(TimingOracle):
    def __init__(self,words,memory,args,retval,mutation,phase,entry=ENTRY,connected=None):
        self.call_result,self.mutation,self.source_args=retval,mutation,args
        super().__init__(words,memory.copy(),phase=phase,entry=entry,arguments=args,connected=connected)
        self.trace=[];self.private_calls=[];self.entry_observations=[];self.initial_gprs=self.r[:];self.initial_fprs=self.f[:]
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def record_call(self,target):
        if target==ENTRY:
            values=tuple(map(u32,self.arguments(3)));self.calls.append((target,values));self.entry_observations.append(values)
            assert values==self.source_args,('original caller argument transfer',values,self.source_args)
            return
        assert target in COUNTS,hex(target)
        self.calls.append((target,tuple(map(u32,self.arguments(COUNTS[target])))))
        sp=self.r[29];self.private_calls.append(bytes(self.memory[sp+i]for i in range(44)))
    def hook(self,target):
        provider_effect(self.memory,self.source_args,self.call_result,self.mutation)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)]
        self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(self.call_result)

def public(memory):
    # The only fixture difference is the independently qualified code-pointer
    # representation in this read-only seven-entry compiler/retail table.
    return{a:b for a,b in memory.items()if not(STACK-128<=a<STACK+128 or TABLE<=a<TABLE+28)}

def trace(machine,table):
    mapping={value:i for i,value in enumerate(table)};result=[]
    for event,address,size,value in machine.trace:
        if STACK-128<=address<STACK+128:continue
        if TABLE<=address<TABLE+28:
            assert event=='R'and size==4 and value in mapping
            result.append((event,address,size,('case',mapping[value])))
        else:result.append((event,address,size,value))
    return result

def corpus():
    handles=(0,1,0xfff,0x1000,0x1234f123,0x80000fff,0xffffffff)
    versions=(0,3,4,5,0xffffffff,0x7fffffff)
    returns=(0,1,0xffffffff,0x80000000,0x13579bdf)
    commands=tuple(range(256))+(0xffffffff,0x80000000,0x7fffffff,0x10007,0x80000006)
    for i,command in enumerate(commands):
        for j,version in enumerate(versions):
            yield(command,version,handles[(i+j)%7],returns[(i+j)%5],i%2,8*(j%2),(i+j)%2)
    for command,version,handle,retval,mutation,phase in itertools.product(range(7),versions,handles,returns,range(2),(0,8)):
        yield(command,version,handle,retval,mutation,phase,(command+version+handle)&1)

def compare(streams,case):
    command,version,handle,retval,mutation,phase,alias=case;models=[];expected_trace=None
    for label,(words,table)in streams.items():
        initial,args=fixture(table,*case)
        expected,calls,result=reference(initial,args,retval,mutation)
        model=Oracle(words,initial,args,retval,mutation,phase)
        try:model.run()
        except AssertionError as error:
            raise AssertionError((label,case,str(error),model.r[16:18],model.before[16:18],list(model.trace[-6:])))from error
        assert(model.calls,model.r[2],public(model.memory))==(calls,result,public(expected)),(label,case,model.calls,calls,hex(model.r[2]),hex(result))
        for i,value in enumerate(table):assert read(model.memory,TABLE+4*i)==value
        for reg in(*range(16,24),28,29,30,31):assert model.r[reg]==model.initial_gprs[reg],(label,case,reg)
        assert model.f[20:]==model.initial_fprs[20:]
        current=trace(model,table)
        if expected_trace is None:expected_trace=current
        else:assert current==expected_trace,(label,case,'ordered public reads')
        if models:
            assert model.private_calls==models[0].private_calls,(label,case,'call frames')
            assert model.memory==models[0].memory or public(model.memory)==public(models[0].memory)
            sp=model.initial_gprs[29]
            assert bytes(model.memory[sp+i]for i in range(-32,12))==bytes(models[0].memory[sp+i]for i in range(-32,12)),(label,case,'return frame')
        models.append(model)
    return models

def run():
    obj=out/'qualified-source-screen/candidate.o';raw,rawtable=program(obj);normal,table=program(obj,True)
    rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>92I',rom,0xCBBE0)
    assert normal==retail
    streams={'retail':(retail,table),'compiled_C':(raw,rawtable),'normalized_C':(normal,table)}
    visits={name:set()for name in streams};counts=Counter();cases=0
    for case in corpus():
        models=compare(streams,case)
        for name,model in zip(streams,models):visits[name].update(model.visits)
        counts[case[0]if case[0]<7 else'default']+=1;cases+=1
    assert all(v==set(range(ENTRY,ENTRY+368,4))for v in visits.values()),{n:len(v)for n,v in visits.items()}
    controls={}
    for label,offset,word,table_defect in(
        ('wrong-handle-mask',56,0x322400ff,False),('wrong-default-result',344,0x24020001,False),
        ('missing-command-six',24,0x2ca10006,False),('wrong-legacy-fade',168,0x24070000,False),
        ('wrong-helper-case-table',0,None,True)):
        changed=list(retail);altered_table=list(table)
        if table_defect:altered_table[1],altered_table[2]=altered_table[2],altered_table[1]
        else:assert changed[offset//4]!=word;changed[offset//4]=word
        caught=False
        for command,version in itertools.product(range(8),(3,5,0)):
            case=(command,version,0x1234f123,0x80000000,1,8,0)
            try:compare({'defect':(changed,altered_table)},case)
            except (AssertionError,KeyError):caught=True;break
        assert caught,label;controls[label]=True
    report=dict(cases_per_stream=cases,streams=3,commands={str(k):v for k,v in counts.items()},
        visited_words={n:len(v)for n,v in visits.items()},frame_bytes=32,incoming_bytes=12,
        full_public_RAM_equal=True,ordered_public_reads_equal=True,all_private_call_and_return_bytes_equal=True,
        qualified_readonly_code_pointer_table_bytes=28,ABI_preserved=True,checked_negative_controls=controls,
        source_installed=recovery.installed(),matching_credit=0,limits='Mapped ordinary RAM and opaque o32 providers; no full caller, hardware, fault or native-C qualification yet.')
    (out/'guest-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
