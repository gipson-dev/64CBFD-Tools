"""Seven-word sound selection ABI, modulo shifts, retry boundaries and native32."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,LOOKUP,BUSY,RNG,PLAY,ACTOR,MARK=0x1509F354,0x1505EEF4,0x10010894,0x150ADA20,0x10010344,0x30000,0x60000
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    first:int=100
    last:int=131
    mask:int=0
    volume:int=0x8000
    key:int=0xFEDCBA98
    distance:int=0xABCD8001
    far:int=0xF1234567
    lookup:int=ACTOR
    busy:int=0
    play:int=1
    rolls:tuple=(0xFFFFFFFF,0,1,31)
    mode:int=0
    phase:int=0

def symbols():return dict(func_1505EEF4=LOOKUP,func_10010894=BUSY,func_150ADA20=RNG,func_10010344=PLAY)
def args(c):return tuple(map(u32,(c.first,c.last,c.mask,c.volume,c.key,c.distance,c.far)))
def fixture(c=Case()):
    m={STACK+c.phase+i:(17*i+0xA5)&255 for i in range(-512,528)};m.update({MARK+i:0xA5 for i in range(96)})
    for i,v in enumerate(args(c)):put(m,STACK+c.phase+4*i,v)
    return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+544}
def effect(m,c,home,target,index,stage):
    put(m,MARK+4*stage,0xABCD0000+stage)
    kind={LOOKUP:1,BUSY:2,RNG:4,PLAY:0}[target]
    if c.mode&kind:
        first=u32(0xFFFF0010+index);put(m,home,first);put(m,home+4,first+63)
        put(m,home+12,0x80000005);put(m,home+20,0xDEAD7FFF-index);put(m,home+24,0xFADE0001+index)
    if c.mode&8 and target==RNG:put(m,home-4,ACTOR+64) # guest-only private spill alias

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase;calls=[];mask=u32(c.mask);actor=c.lookup
    # A0/A1/A3 homes are materialized by the original prologue.
    for off,val in((0,c.first),(4,c.last),(12,c.volume)):put(m,home+off,u32(val))
    def call(t,a,index=0):
        calls.append((s[next(n for n,v in symbols().items()if v==t)],tuple(map(u32,a))))
        effect(m,c,home,t,index,len(calls)-1)
    call(LOOKUP,(c.key,))
    if read(m,home+12)>=0x8000:put(m,home+12,0x7FFF)
    if not actor:return m,calls,mask,'return'
    put(m,home-4,actor);call(BUSY,(actor,))
    if c.busy:return m,calls,mask,'return'
    span=(read(m,home+4)-read(m,home)+1)&255
    if not mask:mask=0xFFFFFFFF>>((-span)&31)
    for i in range(8):
        call(RNG,(),i)
        if not span:return m,calls,mask,'break7'
        selected=u32(c.rolls[i%len(c.rolls)])%span
        if mask&(1<<(selected&31)):
            actor=read(m,home-4)
            a=((read(m,home)+selected)&65535,actor,read(m,home+12),u32(s16(read(m,home+20))),read(m,home+24))
            call(PLAY,a)
            if c.play:mask^=1<<(selected&31)
            return m,calls,mask,'return'
    return m,calls,mask,'retry'

def cases():
    rows=[]
    for span,first,volume,play in itertools.product((1,2,3,7,31,32,33,63,64,127,128,254,255),(0,0xFFFF,0x80000000,0xFFFFFFFF),(0,0x7FFF,0x8000,0x8001,0xFFFFFFFF),(0,1)):
        rows.append(Case(first=first,last=u32(first+span-1),volume=volume,play=play))
    for span in range(1,256):
        for roll in(0,span-1,0x80000000,0xFFFFFFFF):rows.append(Case(last=99+span,mask=0xFFFFFFFF,rolls=(roll,)))
    for bit in range(32):
        for play in(0,-1):rows.append(Case(last=163,mask=1<<bit,play=play,rolls=((bit+1)%32,bit)))
    for lookup,busy,mask,volume,distance,far in itertools.product((0,ACTOR),(0,1,-1),(0,1,0xFFFFFFFF),(0,0x7FFF,0x8000,0x80000000),(0,0x7FFF,0x8000,0xFFFF),(0,0x12345678)):
        rows.append(Case(lookup=lookup,busy=busy,mask=mask,volume=volume,distance=distance,far=far,rolls=(0,)))
    for mode,phase in itertools.product(range(16),(0,8)):rows.append(Case(mask=0xFFFFFFFF,mode=mode,phase=phase))
    rows.extend((Case(last=99),Case(last=355),Case(last=102,mask=0x80000000,rolls=(0,1,2))))
    return tuple(dict.fromkeys(rows))

class Break7(Exception):pass
class RetryBoundary(Exception):pass
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=args(c)if arguments is None else arguments)
        self.rng_index=0;self.stage=0;self.before=self.r[:];self.before_f=self.f[:];self.status='return'
    def record_call(self,t):
        counts={self.syms['func_1505EEF4']:1,self.syms['func_10010894']:1,self.syms['func_150ADA20']:0,self.syms['func_10010344']:5,ENTRY:7}
        assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def execute(self,w):
        if w>>26==0 and w&63 in(4,6):
            rs,rt,rd=w>>21&31,w>>16&31,w>>11&31;count=self.r[rs]&31
            self.r[rd]=u32(self.r[rt]<<count)if w&63==4 else self.r[rt]>>count;self.r[0]=0;return
        if w>>26==0 and w&63==38:
            self.r[w>>11&31]=self.r[w>>21&31]^self.r[w>>16&31];self.r[0]=0;return
        if w==0x0007000D:raise Break7
        if w&0xFC00003F==27 and self.r[w>>16&31]==0:
            # VR4300 DIVU by zero writes LO=all ones, HI=the dividend.
            self.lo=0xFFFFFFFF;self.hi=self.r[w>>21&31];self.r[0]=0;return
        return super().execute(w)
    def hook(self,t):
        c=self.case;s=self.syms;logical=next(v for n,v in symbols().items()if s[n]==t)
        if logical==RNG and self.rng_index==8:
            # Stop before recording a ninth sampled helper invocation.
            self.calls.pop();self.events.pop();raise RetryBoundary
        effect(self.memory,c,self.target_home,logical,self.rng_index,self.stage);self.stage+=1
        value={LOOKUP:c.lookup,BUSY:c.busy,PLAY:c.play}.get(logical,0)
        if logical==RNG:value=c.rolls[self.rng_index%len(c.rolls)];self.rng_index+=1
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
    def finish(self):
        try:self.run()
        except Break7:self.status='break7'
        except RetryBoundary:self.status='retry'
        return self

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.status)
def programs(core,q,s=None):
    s=symbols()if s is None else s
    normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));truth=list(q['retail_words'])
    for off,n in((32,'func_1505EEF4'),(84,'func_10010894'),(156,'func_150ADA20'),(248,'func_10010344')):truth[off//4]=(truth[off//4]&0xFC000000)|(s[n]>>2&0x3FFFFFF)
    assert truth==normal;return truth,normal,list(core.bound_blob(q['raw'],q['refs'],s))

def guest(core,q):
    seen=set();totals={'return':0,'break7':0,'retry':0};count=0
    for c in cases():
        initial=fixture(c);wanted,calls,value,status=reference(initial,c);ms=[]
        for words in programs(core,q):
            m=Oracle(words,initial,c).finish()
            assert(public(m.memory),m.calls,m.status)==(public(wanted),calls,status),(c,m.calls,calls,m.status,status)
            if status=='return':
                assert m.r[2]==value,(c,hex(m.r[2]),hex(value))
                assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f[20:]==m.before_f[20:]
            ms.append(m)
        assert literal(ms[0])==literal(ms[1]),c;seen.update(ms[0].visits);totals[status]+=1;count+=1
    assert seen==set(range(ENTRY,ENTRY+296,4)),[hex(x)for x in set(range(ENTRY,ENTRY+296,4))-seen]
    cuts=0
    for c in(Case(),Case(lookup=0),Case(busy=1),Case(last=99),Case(mask=2,rolls=(0,1)),Case(mode=15,mask=0xFFFFFFFF)):
        initial=fixture(c);ps=programs(core,q)[:2];full=Oracle(ps[0],initial,c).finish()
        for cut in range(full.all_accesses):
            ms=[]
            for p in ps:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.finish()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing memory cut',cut))
                ms.append(m)
            assert literal(ms[0])==literal(ms[1]);cuts+=1
    return dict(cases=count,reachable_words=74,statuses=totals,all_byte_spans=True,modulo32_shifts=True,raw_C_public_effects_equal=True,literal_normalized_states=True,executed_fault_cuts=cuts,late_home_and_private_spill_alias_modes=16,hostile_helpers=True,helper_bodies_not_emulated=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m):super().__init__(code,m);self.m=m;self.ends=()
    def __getitem__(self,pc):
        if pc==0x1509F240:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        assert t==ENTRY;m,calls,value,status=reference(self.memory,self.case);assert status=='return';self.memory=m;self.calls.extend(calls);self.r[2]=value

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>14I',rom,0xCC570);end=struct.unpack_from('>4I',rom,0xCC6E8);count=0
    for span,mask,volume,distance,far,outcome,phase in itertools.product((1,32,64),(0,1,0xFFFFFFFF),(0x7FFF,0x8000),(0x12348000,0xABCD7FFF),(0,0xFEDC1234),(0,1),(0,8)):
        c=Case(last=99+span,mask=mask,volume=volume,distance=distance,far=far,play=outcome,phase=phase,rolls=(0,));initial=fixture(c);home=STACK+phase;record=0x70000
        for off,val in((8,c.last|0xABCD0000),(12,mask),(16,volume),(24,distance),(28,far)):put(initial,record+off,val)
        put(initial,home+0x30,c.first);put(initial,home+0x2C,0xDEAD0000);put(initial,home+0x28,0x12345678)
        def build(body=None):
            code=dict(zip(range(0x1509F238,0x1509F248,4),end))
            if body is not None:code.update(zip(range(ENTRY,ENTRY+len(body)*4,4),body))
            cls=ReferenceCaller if body is None else Oracle;m=cls(window,initial,c,entry=0x1509F0C0,connected=code);m.r[16]=record;m.r[24]=u32(c.key);m.code=BoundaryCode(m.code,m);return m
        def run(m):
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original caller return boundary')
            return m
        wanted=run(build());observe=lambda m:(m.boundary,public(m.memory),m.calls,m.r[2],m.r[16],m.r[29],m.r[31])
        assert wanted.calls[0]==(ENTRY,args(c)),wanted.calls[0]
        assert(wanted.r[16],wanted.r[29],wanted.r[31])==(0x12345678,home+48,0xDEAD0000)
        for body in programs(core,q):assert observe(run(build(body)))==observe(wanted),c
        count+=1
    return dict(cases=count,original_window_words=14,original_epilogue_words=4,seven_word_packet=True,seventh_word_in_JAL_delay=True,full_word_distance_homes=True,mask_return_preserved_to_parent=True,parent_still_stub=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(stub='u32 func_1509F354(u32 a,u32 b,u32 c,u32 d,s32 e,s16 f,u32 g){return 0;}',
      no_cap=body.replace('if (volume >= 0x8000U) volume = 0x7FFF;',''),signed_cap=body.replace('volume >= 0x8000U','(s32)volume >= 0x8000'),exclusive_cap=body.replace('>= 0x8000U','> 0x8000U'),
      wrong_key=body.replace('func_1505EEF4(actorKey)','func_1505EEF4(actorKey + 1U)'),ignore_busy=body.replace('func_10010894(actor) == 0','func_10010894(actor) == 1'),
      wrong_sound=body.replace('first + selected','first - selected'),wrong_distance=body.replace('volume, distance, farDistance','volume, (s16)~distance, farDistance'),wrong_far=body.replace('volume, distance, farDistance','volume, distance, farDistance + 1U'),
      default_all_bits=body.replace('0xFFFFFFFFU >> ((0U - (u8)(last - first + 1)) & 31)','0xFFFFFFFFU'),no_retry=body.replace('while ((mask & (1U << (selected & 31))) == 0)','while (0)'),
      consume_failure=body.replace('farDistance) != 0','farDistance) == 0'),or_bit=body.replace('mask ^=','mask |='),wrong_return=body.replace('return mask;','return ~mask;'))
    assert all(v!=body for v in controls.values())
    rows=[]
    for c in cases():
        if c.mode or c.phase:continue
        _,calls,value,status=reference(fixture(c),c)
        if status!='return':continue
        arr=lambda vs:'{'+','.join(str(u32(x))+'u'for x in vs)+'}'
        packets=[]
        for t,a in calls:
            a=tuple((v&65535 if j==4 and t==PLAY else v)for j,v in enumerate(a));packets.append(arr((t,len(a),*a,*([0]*(5-len(a))))))
        packets+=['{0}']*(12-len(packets))
        rolls=c.rolls+tuple([0]*(4-len(c.rolls)))
        rows.append('{%s,%s,%su,%su,%su,%su,%su,{%s}}'%(arr(args(c)),arr(rolls),len(c.rolls),c.lookup,u32(c.busy),u32(c.play),value,','.join(packets)))
    code='#include <ultra64.h>\nstruct struct127{u32 unused;};\n_Static_assert(sizeof(void*)==4,"O32 native");\n'
    code+='typedef struct{u32 a[7],rolls[4],n,lookup,busy,play,value,packets[12][7];}Case;static const Case cases[]={'+',\n'.join(rows)+'};\n'
    code+='static const Case*current;static u32 rng,used,packets[12][7];\n'
    code+='''static void packet(u32 t,u32 n,u32 a,u32 b,u32 c,u32 d,u32 e){u32 i=used++;if(i<12){packets[i][0]=t;packets[i][1]=n;packets[i][2]=a;packets[i][3]=b;packets[i][4]=c;packets[i][5]=d;packets[i][6]=e;}}
    struct struct127*func_1505EEF4(s32 key){packet(LOOKUP,1,(u32)key,0,0,0,0);return(struct struct127*)current->lookup;}
    s32 func_10010894(struct struct127*a){packet(BUSY,1,(u32)a,0,0,0,0);return(s32)current->busy;}
    s32 func_150ADA20(void){packet(RNG,0,0,0,0,0,0);return(s32)current->rolls[(rng++)%current->n];}
    s32 func_10010344(u16 a,void*b,s32 c,s16 d,u16 e){packet(PLAY,5,a,(u32)b,(u32)c,(u32)(s32)d,e);return(s32)current->play;}
    '''.replace('LOOKUP',str(LOOKUP)+'u').replace('BUSY',str(BUSY)+'u').replace('RNG',str(RNG)+'u').replace('PLAY',str(PLAY)+'u')
    for i,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace('func_1509F354(','candidate_%d('%i)+'\n'
    code+='static u32(*candidates[])(u32,u32,u32,u32,s32,s16,u32)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='''static int run(void){u32 n,j,i,k,v,bad,killed=0;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    rng=used=0;for(i=0;i<12;i++)for(k=0;k<7;k++)packets[i][k]=0;
    v=candidates[j](current->a[0],current->a[1],current->a[2],current->a[3],(s32)current->a[4],(s16)current->a[5],current->a[6]);bad=v!=current->value||used>12;
    for(i=0;i<12;i++)for(k=0;k<7;k++)bad|=packets[i][k]!=current->packets[i][k];if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}}
    for(j=0;j<CONTROL_COUNT;j++)if(!(killed&(1u<<j)))return 10+j;return 0;}
    '''.replace('CONTROL_COUNT',str(len(controls)))
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'sound-mask-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('sound-mask-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True,timeout=20);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,effective_controls=list(controls),seven_word_native32=True,logical_last_argument_u16=True,guest_only_home_aliases_and_trap_retry_prefixes_separate=True)
