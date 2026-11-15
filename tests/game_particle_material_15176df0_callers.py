"""Eight registry slots and the real display-callback-to-material connection."""
import itertools,json,struct
from tools.tests import game_particle_material_15176df0_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
PARENT=0x151770c8

class Connected(g.Oracle):
    def __init__(self,words,initial,c,entry,connected,raw=False):
        super().__init__(words,initial,c,entry=entry,connected=connected)
        self.raw=raw;self.root_home=g.home(c);self.entries=[]
    def record_call(self,t):
        if t in (g.source.ENTRY,PARENT):
            self.entries.append((t,tuple(self.arguments(3))))
            if t==g.source.ENTRY:self.entered=self.r[29]
            return
        if t==g.CULL:
            a=tuple(self.arguments(10));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append(())
        else:super().record_call(t)
    def hook(self,t):
        if t!=g.CULL:return super().hook(t)
        a=self.calls[-1][1];g.effects(self.memory,self.case,t,a,len(self.calls),self.root_home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=g.u32(self.case.reject)

def parent_reference(initial,c):
    m=dict(initial);a=(g.u32(0x800d9c10+g.half(c.view)*64),*(g.read(m,g.RECORD+off) for off in (0x98,0x9c,0xa0)),g.read(m,0x800d9b20),0x457a0000,g.read(m,0x800d35e0),g.read(m,0x800d35e4),0,0)
    calls=[(g.CULL,a)];g.effects(m,c,g.CULL,a,1,g.home(c))
    if c.reject:return m,calls,[()],g.commands(c),[]
    assert m[g.RECORD+0x91]!=0
    entry=(g.source.ENTRY,(g.commands(c),g.RECORD,g.u32(g.half(g.read(m,g.home(c)+8)))))
    memory,calls,obs,result=g.reference(m,c,g.home(c)-0x90,calls,[()])
    return memory,calls,obs,result,[entry]

def main():
    source=g.source;rom=(source.ROOT/'conker/conker.us.bin').read_bytes()
    programs=[source.bound(*g.payload(source.OUT/name,source.NAME)) for name in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    slots=json.loads((source.OUT/'raw-report.json').read_text())['registry_slots'];start,end=0x15167898,0x151678b8;window=struct.unpack_from('>8I',rom,0x194d48)
    callbacks=0
    for slot,present,enabled,mode,phase in itertools.product(slots,(0,1),(0,1),(0,1,3),(0,8)):
        assert struct.unpack_from('>I',rom,0x22ff68+(slot-0x8008b4a8))[0]==source.ENTRY
        c=g.Case(present=present,enabled=enabled,mutation=mode,phase=phase,variant=callbacks%4,seed=callbacks%17)
        initial=g.fixture(c);g.put(initial,g.TRACK,0x12345678);g.put(initial,g.RECORD+8,0x87654321)
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words));code[end]=0
            m=Connected(window,initial,c,start,code,len(words)==181)
            m.r[16],m.r[17],m.r[19],m.r[22],m.r[25]=g.RECORD,g.TRACK,g.commands(c),g.u32(c.view),source.ENTRY
            m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing registry return boundary')
            expected=dict(initial);g.put(expected,g.TRACK,0x87654321);g.verify(m,expected,c)
            assert m.entries==[(source.ENTRY,g.args(c))]
        callbacks+=1
    parent=list(struct.unpack_from('>101I',rom,0x1a4578));connected_cases=0
    for present,enabled,reject,mode,phase,alias in itertools.product((0,1),(0,1),(0,1),(0,1,3),(0,8),(0,1)):
        c=g.Case(present=present,enabled=enabled,reject=reject,mutation=mode,phase=phase,alias=alias,seed=connected_cases%17)
        initial=g.fixture(c);want,calls,obs,result,entries=parent_reference(initial,c)
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
            m=Connected(parent,initial,c,PARENT,code,len(words)==181);m.run()
            assert (g.public(m.memory),m.calls,m.observations,m.r[2])==(g.public(want),calls,obs,result),c
            assert m.entries==entries,(c,m.entries,entries)
            assert m.r[16:24]==m.before_r[16:24] and m.r[29]==m.before_r[29] and m.f[20:]==m.before_f[20:]
        connected_cases+=1
    controls=[]
    for label,pc,change,c in (('missing-blue-copy',0x238,0,g.Case()),('wrong-red-home',0x264,None,g.Case(private_colors=True)),('wrong-alpha-field',0x278,None,g.Case(seed=7))):
        words=programs[0][:]
        if label=='wrong-red-home':change=words[pc//4]&0xffff0000|0x4c
        elif label=='wrong-alpha-field':change=words[pc//4]&0xffff0000|0xed
        assert words[pc//4]!=change;words[pc//4]=change;initial=g.fixture(c)
        try:m=g.Oracle(words,initial,c);m.run();g.verify(m,initial,c)
        except AssertionError as e:assert e.args==(c,),(label,e.args)
        else:raise AssertionError('Ineffective emitted semantic control: '+label)
        controls.append(label)
    report=dict(registry_cases=callbacks,registry_slots=slots,connected_parent_cases=connected_cases,actual_parent_words=101,streams=3,emitted_controls=controls,providers_bounded=True)
    (source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
