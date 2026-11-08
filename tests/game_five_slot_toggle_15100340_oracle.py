"""Five-slot callback, original dispatcher, bounded helper effects and native32."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,RNG,EVENT,MARK,WINDOW=0x15100340,0x150ADA20,0x151616D0,0x60000,0x15174A34
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    view:int=0
    states:tuple=(0,1,0,1,255)
    rolls:tuple=(0,69,35,70,0xFFFFFFFF)
    identifiers:tuple=(9,10,11,12,13)
    counter:int=255
    mode:int=0
    alias:int=0
    phase:int=0

def symbols(c=Case()):
    s=dict(D_80088BC0=0x80088BC0,D_800BE500=0x800BE500,D_800DD405=0x800DD405,func_150ADA20=RNG,func_151616D0=EVENT)
    local=STACK+c.phase-12
    if c.alias==1:s['D_800BE500']=s['D_80088BC0']
    elif c.alias==2:s['D_800DD405']=s['D_800BE500']+2
    elif c.alias==3:s['D_80088BC0']=local
    elif c.alias==4:s['D_800BE500']=local
    elif c.alias==5:s['D_800DD405']=s['D_80088BC0']+4
    return s

def fixture(c=Case(),s=None):
    s=symbols(c)if s is None else s;m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,512)}
    m.update({MARK+i:0xA5 for i in range(128)})
    for name,values in(('D_80088BC0',c.identifiers),('D_800BE500',c.states)):
        for i,v in enumerate(values):m[u32(s[name]+i)]=v
    m[s['D_800DD405']]=c.counter
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+528}

def helper_effect(m,c,s,target,index,stage,command=0):
    put(m,MARK+4*stage,0xA1700000+stage)
    if target==RNG:
        if c.mode&1:m[s['D_800BE500']+index]^=0x81
        if c.mode&2:m[s['D_800BE500']+(index+1)%5]^=0x7F
        if c.mode&4:
            for i in range(5):m[s['D_80088BC0']+i]^=(stage+i+0x29)&255
    else:
        if c.mode&8 and command==0x1C:m[STACK+c.phase-12+index]^=0x5A
        if c.mode&16:m[s['D_800BE500']+(index+1)%5]^=0x40

def reference(initial,c=Case(),s=None):
    s=symbols(c)if s is None else s;m=dict(initial);local=STACK+c.phase-12;calls=[]
    # Match the original word-plus-byte copy, before the view gate.
    put(m,local,read(m,s['D_80088BC0'],4));m[local+4]=m[s['D_80088BC0']+4]
    if not u32(c.view):
        m[s['D_800DD405']]=(m[s['D_800DD405']]+1)&255
        for i in range(5):
            chance=70 if m[s['D_800BE500']+i] else 35
            calls.append((RNG,()));helper_effect(m,c,s,RNG,i,len(calls)-1)
            if u32(c.rolls[i])%1000<chance:
                m[s['D_800BE500']+i]^=1
                commands=(0x18,)if m[s['D_800BE500']+i]else(0x1C,0x17)
                for command in commands:
                    args=(m[local+i],command,0);calls.append((EVENT,args));helper_effect(m,c,s,EVENT,i,len(calls)-1,command)
    return m,calls

def cases():
    rows=[];patterns=((0,)*5,(1,)*5,(0,1,0,1,0),(255,128,127,2,1))
    for view,states,counter,roll in itertools.product((0,1,-1,0x80000000),patterns,(0,255),(0,34,35,69,70,999,1000,1001,0x80000000,0xFFFFFFFF)):
        rows.append(Case(view,states,(roll,)*5,counter=counter))
    for byte,index in itertools.product(range(256),range(5)):
        states=list(patterns[2]);states[index]=byte;rows.append(Case(states=tuple(states),rolls=(0,)*5,identifiers=(0,127,128,254,255)))
    for rolls,states in itertools.product(itertools.product((0,35,70),repeat=5),patterns[:2]):rows.append(Case(states=states,rolls=rolls))
    rows.extend(Case(counter=i,rolls=(999,)*5)for i in range(256))
    for mode,alias,phase,states in itertools.product(range(32),range(6),(0,8),patterns[:2]):
        rows.append(Case(states=states,rolls=(0,)*5,mode=mode,alias=alias,phase=phase))
    return tuple(dict.fromkeys(rows))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols(c)if s is None else s,connected=connected,arguments=(u32(c.view),)if arguments is None else arguments)
        self.rng_index=0;self.before=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        counts={self.syms['func_150ADA20']:0,self.syms['func_151616D0']:3,ENTRY:1};assert t in counts,hex(t)
        a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        c=self.case;s=self.syms;logical=RNG if t==s['func_150ADA20']else EVENT
        assert t in(s['func_150ADA20'],s['func_151616D0']),hex(t)
        index=self.rng_index if logical==RNG else self.rng_index-1
        stage=sum(target!=ENTRY for target,args in self.calls)-1
        helper_effect(self.memory,c,s,logical,index,stage,self.calls[-1][1][1]if logical==EVENT else 0)
        value=c.rolls[index]if logical==RNG else 0xDEADBEEF
        if logical==RNG:self.rng_index+=1
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)

def programs(core,q,s):
    raw=list(core.bound_blob(q['raw'],q['refs'],s));truth=list(q['retail_words'])
    original=symbols()
    for off,name,high in((28,'D_80088BC0',True),(32,'D_80088BC0',False),(44,'D_800DD405',True),(56,'D_800DD405',False),(72,'D_800BE500',True),(76,'D_800BE500',False)):
        if s[name]!=original[name]:truth[off//4]=(truth[off//4]&0xFFFF0000)|(((s[name]+0x8000)>>16&65535)if high else(s[name]&65535))
    assert truth==raw
    return truth,raw

def guest(core,q):
    seen=set();count=0
    for c in cases():
        s=symbols(c);initial=fixture(c,s);wanted,calls=reference(initial,c,s);ms=[]
        for words in programs(core,q,s):
            m=Oracle(words,initial,c);m.run();assert(public(m.memory),m.calls)==(public(wanted),calls),c
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f[20:]==m.before_f[20:],c
            if c.alias in(3,4):assert bytes(m.memory[STACK+c.phase-12+i]for i in range(5))==bytes(wanted[STACK+c.phase-12+i]for i in range(5))
            ms.append(m)
        assert literal(ms[0])==literal(ms[1]),c;seen.update(ms[0].visits);count+=1
    missing=set(range(ENTRY,ENTRY+292,4))-seen;assert missing=={ENTRY+0x98},list(map(hex,missing))
    cuts=0
    for c in(Case(view=1),Case(),Case(states=(1,)*5,rolls=(0,)*5),Case(rolls=(999,)*5),Case(mode=31),Case(alias=4,mode=24)):
        s=symbols(c);initial=fixture(c,s);ps=programs(core,q,s);full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for p in ps:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing callback fault cut',cut))
                ms.append(m)
            assert literal(ms[0])==literal(ms[1]);cuts+=1
    return dict(cases=count,reachable_words=72,unreachable_words=['0x151003D8'],constant_nonzero_divisor=True,all_state_and_counter_bytes=True,alias_layouts=6,hostile_helper_clobbers=True,
      exact_literal_states_and_reads=True,executed_fault_cuts=cuts,helper_bodies_not_emulated=True,controlled_local_identifier_mutations_guest_only=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m,ends):super().__init__(code,m);self.m=m;self.ends=ends
    def __getitem__(self,pc):
        if pc in self.ends:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        assert t==ENTRY;wanted,calls=reference(self.memory,self.case);self.memory=wanted;self.calls.extend(calls);self.r[2]=0xF00DBAAD

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>13I',rom,0x1A1EE4);count=0
    assert struct.unpack_from('>I',rom,0x2317EC)[0]==ENTRY
    for view,states,mode,phase,feature in itertools.product((0,1,-1,0x80000000),((0,)*5,(1,)*5),(0,1,4,16),(0,8),(0,1)):
        c=Case(view,states,(0,)*5,mode=mode,phase=phase);initial=fixture(c);home=STACK+phase
        resource=0x70000;initial[resource+11]=10;initial[0x800BE616]=feature;put(initial,0x8008CD04+10*4,ENTRY);put(initial,home+0x1C,u32(view))
        def build(body=None):
            code={}if body is None else dict(zip(range(ENTRY,ENTRY+292,4),body));cls=ReferenceCaller if body is None else Oracle
            m=cls(window,initial,c,entry=WINDOW,connected=code);m.r[14]=resource;m.code=BoundaryCode(m.code,m,{0x15174A68,0x15174A78});return m
        wanted=build()
        try:wanted.run()
        except WindowBoundary:pass
        else:raise AssertionError('Missing reference dispatcher boundary')
        observe=lambda m:(m.boundary,public(m.memory),m.calls,m.r[16:24],m.r[29],m.r[31])
        for body in programs(core,q,symbols(c)):
            m=build(body)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing dispatcher boundary')
            assert observe(m)==observe(wanted),c
        count+=1
    return dict(cases=count,registration='D_8008CD04[10]',pointer_rom='0x2317EC',dispatcher='func_151749F8',window_words=13,original_JALR=True,original_return_branch=True,void_return_poisoned=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(stub='void func_15100340(s32 view){(void)view;}',ignore_view=body.replace('if (view == 0)','if (1)'),
      signed_roll=body.replace('if (random % 1000 < chance)','if ((s32)random % 1000 < (s32)chance)'),inclusive=body.replace('% 1000 < chance','% 1000 <= chance'),
      swap_chances=body.replace('? 70 : 35','? 35 : 70'),missing_increment=body.replace('D_800DD405++;',''),four_slots=body.replace('index != 5','index != 4'),
      wrong_modulus=body.replace('% 1000','% 100'),boolean_toggle=body.replace('*states ^= 1;','*states = !*states;'),
      stale_state=body.replace('    u32 random;','    u8 before;\n    u32 random;').replace('chance = *states','before = *states;\n            chance = before').replace('*states ^= 1;','*states = before ^ 1;'),
      live_global_ids=body.replace('identifiers.ids[index]','D_80088BC0.ids[index]').replace('identifiers = D_80088BC0;','identifiers = D_80088BC0;\n    (void)identifiers;'),wrong_second_command=body.replace('0x17','0x18'),
      reversed_off_commands=body.replace('0x1C','0x7F').replace('0x17','0x1C').replace('0x7F','0x17'))
    assert all(v!=body for v in controls.values());native_cases=[c for c in cases()if not(c.alias or c.phase or c.mode&8)]
    rows=[]
    for c in native_cases:
        wanted,calls=reference(fixture(c),c);events=[a for t,a in calls if t==EVENT]
        ids=tuple(wanted[symbols()['D_80088BC0']+i]for i in range(5));states=tuple(wanted[symbols()['D_800BE500']+i]for i in range(5))
        arr=lambda v:'{'+','.join(str(u32(x))+'u'for x in v)+'}'
        event_rows='{'+','.join(arr(a)for a in events)+'}'if events else'{{0}}'
        rows.append('{%su,%s,%s,%s,%su,%su,%s,%s,%su,%su,%su,%s}'%(u32(c.view),arr(c.states),arr(c.rolls),arr(c.identifiers),c.counter,c.mode,arr(states),arr(ids),wanted[symbols()['D_800DD405']],sum(t==RNG for t,a in calls),len(events),event_rows))
    code='#include <ultra64.h>\ntypedef struct SlotIdentifiers15100340{u8 ids[5];}SlotIdentifiers15100340;\nSlotIdentifiers15100340 D_80088BC0;u8 D_800BE500[5],D_800DD405;\n'
    code+='typedef struct{u32 view;u8 states[5];u32 rolls[5];u8 ids[5];u32 counter,mode;u8 out_states[5],out_ids[5];u32 out_counter,rng,event;u32 events[10][3];}Case;\n'
    code+='static const Case cases[]={'+',\n'.join(rows)+'};\nstatic const Case *current;static u32 rng_count,event_count,stage,packets[10][3];\n'
    code+='''_Static_assert(sizeof(void*)==4,"native32");_Static_assert(sizeof(SlotIdentifiers15100340)==5,"ids5");
    s32 func_150ADA20(void){u32 i,n=rng_count++;if(current->mode&1)D_800BE500[n]^=0x81;if(current->mode&2)D_800BE500[(n+1)%5]^=0x7F;
    if(current->mode&4)for(i=0;i<5;i++)D_80088BC0.ids[i]^=(u8)(stage+i+0x29);stage++;return(s32)current->rolls[n];}
    void func_151616D0(u8 a,u8 b,s32 c){u32 n=event_count++;if(n<10){packets[n][0]=a;packets[n][1]=b;packets[n][2]=(u32)c;}
    if(current->mode&16)D_800BE500[rng_count%5]^=0x40;stage++;}
    '''
    for j,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace('typedef struct SlotIdentifiers15100340 { u8 ids[5]; } SlotIdentifiers15100340;','').replace('func_15100340(','candidate_%d('%j)+'\n'
    code+='static void(*candidates[])(s32)={'+','.join('candidate_%d'%j for j in range(len(controls)+1))+'};\n'
    code+='''static int run(void){u32 n,j,i,k,killed=0,bad;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    for(i=0;i<5;i++){D_800BE500[i]=current->states[i];D_80088BC0.ids[i]=current->ids[i];}D_800DD405=(u8)current->counter;rng_count=event_count=stage=0;
    for(i=0;i<10;i++)for(k=0;k<3;k++)packets[i][k]=0xA5A5A5A5u;candidates[j]((s32)current->view);
    bad=D_800DD405!=current->out_counter||rng_count!=current->rng||event_count!=current->event;
    for(i=0;i<5;i++)bad|=D_800BE500[i]!=current->out_states[i]||D_80088BC0.ids[i]!=current->out_ids[i];
    for(i=0;i<current->event;i++)for(k=0;k<3;k++)bad|=packets[i][k]!=current->events[i][k];
    if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}}
    for(j=0;j<13;j++)if(!(killed&(1u<<j)))return 10+j;return killed==MASK?0:3;}
    '''.replace('MASK',str((1<<len(controls))-1)+'u')
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'toggle-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('toggle-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,pointer32_ids5=True,effective_controls=list(controls),all_globals_and_event_packets=True,guest_aliases_and_local_mutations_separate=True)
