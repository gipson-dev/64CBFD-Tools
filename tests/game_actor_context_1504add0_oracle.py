"""Actor-context selection, live controller data, bounded helpers and native32."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,ZERO,UPDATE,ACTORS,TABLE0,TABLE1,INPUTS,WINDOW=0x1504ADD0,0x100226F0,0x150ED578,0x30000,0x40000,0x40100,0x50000,0x15019218
FOLLOW=0x1510F800
u32=lambda n:n&0xFFFFFFFF
s8=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
    disable:int=0
    limit:int=25
    pattern:int=0
    selected:int=0
    value:int=1
    kind:int=0x28
    mode:int=0
    alias:int=0
    phase:int=0

def symbols(c=Case()):
    s=dict(D_800C35EA=0x800C35EA,D_800CC2D0=ACTORS,D_800BE728=0x800BE728,D_8008FD8C=0x8008FD8C,D_800C3E78=0x800C3E78,D_800D154C=0x800D154C,D_800CC284=0x800CC284,bzero=ZERO,func_150ED578=UPDATE)
    if c.alias==1:s['D_8008FD8C']=s['D_800C3E78']
    elif c.alias==2:s['D_800D154C']=ACTORS+24*812+4
    elif c.alias==3:s['D_800CC284']=s['D_800D154C']
    elif c.alias==4:s['D_8008FD8C']=s['D_800C35EA']
    elif c.alias==5:s['D_800C3E78']=STACK+c.phase-16
    return s

def actor_fields(c,i):
    if i==25:return 1,0x28
    if c.pattern==0:return(c.value,c.kind)if i==c.selected else(0,0)
    if c.pattern==1:return c.value,(0x28,0x77,0,255)[i%4]
    if c.pattern==2:return(c.value if i&1 else 0),(0x77 if i%3 else 1)
    return c.value,c.kind

def fixture(c=Case(),s=None):
    s=symbols(c)if s is None else s;m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,512)}
    for i in range(26):
        state,kind=actor_fields(c,i);put(m,s['D_800CC2D0']+812*i,u32(state));put(m,s['D_800CC2D0']+812*i+4,kind,1)
        for j in range(5,8):m[s['D_800CC2D0']+812*i+j]=0xA5
    for table,base in((TABLE0,INPUTS+16),(TABLE1,INPUTS+80)):
        for i in range(4):put(m,table+4*i,base+16*i)
    for i in range(160):m[INPUTS+i]=(i*29+0x31)&255
    m[s['D_800C35EA']]=c.disable;m[s['D_8008FD8C']]=c.limit&255;m[s['D_800C3E78']]=0xA7
    put(m,s['D_800D154C'],s['D_800CC2D0']+25*812);put(m,s['D_800BE728'],TABLE0);put(m,s['D_800CC284'],INPUTS)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+528}
def packet(m,s):
    p=read(m,s['D_800CC284']);return bytes(m[p+i]for i in range(6))
def observation(m,s):return(m[s['D_800C3E78']],read(m,s['D_800D154C']),read(m,s['D_800CC284']),packet(m,s))

def effect(m,c,s,actor):
    i=(actor-s['D_800CC2D0'])//812
    if c.mode&1:
        p=s['D_800CC2D0']+((i+1)%25)*812;put(m,p,read(m,p)^1);m[p+4]=0x28
    if c.mode&2:m[s['D_8008FD8C']]=255 if i&1 else 127
    if c.mode&4:
        p=read(m,s['D_800CC284'])
        if p==STACK+c.phase-16:
            for j in range(6):m[p+j]=(i+j+0x51)&255
    if c.mode&8:put(m,s['D_800BE728'],TABLE1 if read(m,s['D_800BE728'])==TABLE0 else TABLE0)
    if c.mode&16:put(m,actor,0);m[actor+4]=3
    if c.mode&32:
        m[s['D_800C35EA']]=1;m[s['D_800C3E78']]=255;put(m,s['D_800D154C'],s['D_800CC2D0']+25*812);put(m,s['D_800CC284'],INPUTS)

def reference(initial,c=Case(),s=None):
    s=symbols(c)if s is None else s;m=dict(initial);calls=[];observations=[];local=STACK+c.phase-16
    if m[s['D_800C35EA']]!=1:
        for i in range(25):
            actor=s['D_800CC2D0']+812*i
            if read(m,actor):
                m[s['D_800C3E78']]=i;put(m,s['D_800D154C'],actor)
                if i<s8(m[s['D_8008FD8C']]):
                    if i<4:put(m,s['D_800CC284'],read(m,read(m,s['D_800BE728'])+4*i))
                    else:
                        calls.append((ZERO,(local,6)))
                        for j in range(6):m[local+j]=0
                        put(m,s['D_800CC284'],local)
                if m[actor+4]in(0x28,0x77):
                    calls.append((UPDATE,(actor,)));observations.append(observation(m,s));effect(m,c,s,actor)
    return m,calls,observations

def cases():
    rows=[]
    for value,kind,index in itertools.product((0,1,0x80000000,0xFFFFFFFF),(0,0x28,0x77,255),(0,3,4,24)):
        rows.append(Case(selected=index,value=value,kind=kind))
    for value in range(256):rows.extend((Case(disable=value,pattern=1),Case(limit=value,pattern=1)))
    for index in range(25):rows.append(Case(selected=index));rows.append(Case(selected=index,kind=0x77,limit=4))
    for mode,pattern,alias,phase in itertools.product((0,1,2,4,8,16,32,63),(1,2,3),range(6),(0,8)):
        rows.append(Case(pattern=pattern,mode=mode,alias=alias,phase=phase))
    return tuple(dict.fromkeys(rows))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None):
        super().__init__(words,memory,c,entry=entry,s=symbols(c)if s is None else s,connected=connected,arguments=(0x12345678,))
        self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
    def record_call(self,t):
        counts={self.syms['bzero']:2,self.syms['func_150ED578']:1,ENTRY:0,FOLLOW:1};assert t in counts,hex(t)
        args=tuple(self.arguments(counts[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==self.syms['func_150ED578']:self.observations.append(observation(self.memory,self.syms))
    def hook(self,t):
        s=self.syms;a=self.calls[-1][1]
        if t==s['bzero']:
            assert a[1]==6
            for i in range(6):self.memory[u32(a[0]+i)]=0
        elif t==FOLLOW:assert a==(0,)
        else:
            assert t==s['func_150ED578'];effect(self.memory,self.case,s,a[0])
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations)
def bound_programs(core,q,s):
    raw=list(core.bound_blob(q['raw'],q['refs'],s));normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));truth=list(q['retail_words'])
    original={n:int(n.split('_')[1],16)for n in symbols()if n.startswith('D_')}
    specs=((44,'D_800C35EA',True),(48,'D_800C35EA',False),(64,'D_800CC2D0',True),(100,'D_800CC2D0',False),(68,'D_800BE728',True),(96,'D_800BE728',False),
      (72,'D_8008FD8C',True),(92,'D_8008FD8C',False),(76,'D_800C3E78',True),(88,'D_800C3E78',False),(80,'D_800CC284',True),(84,'D_800CC284',False),(120,'D_800D154C',True),(136,'D_800D154C',False))
    for off,name,hi in specs:
        if s[name]!=original[name]:truth[off//4]=(truth[off//4]&0xFFFF0000)|(((s[name]+0x8000)>>16&65535)if hi else(s[name]&65535))
    assert truth==normal
    return truth,normal,raw

def guest(core,q):
    seen=set();count=0
    for c in cases():
        s=symbols(c);initial=fixture(c,s);wanted,calls,observations=reference(initial,c,s);ms=[]
        for k,words in enumerate(bound_programs(core,q,s)):
            m=Oracle(words,initial,c);m.run();assert(public(m.memory),m.calls,m.observations)==(public(wanted),calls,observations),c
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f[20:]==m.before_f[20:],c
            if c.alias==5:assert m.memory[STACK+c.phase-16]==wanted[STACK+c.phase-16]
            if k<2:ms.append(m)
            else:assert(m.memory,m.trace)==(ms[0].memory,ms[0].trace),c
        assert literal(ms[0])==literal(ms[1]),c;seen.update(ms[0].visits);count+=1
    assert seen==set(range(ENTRY,ENTRY+292,4)),list(map(hex,set(range(ENTRY,ENTRY+292,4))-seen))
    cuts=0
    for c in(Case(disable=1),Case(),Case(limit=255,pattern=1),Case(limit=127,pattern=3),Case(mode=63,pattern=1),Case(alias=5,mode=4,pattern=3)):
        s=symbols(c);initial=fixture(c,s);ps=bound_programs(core,q,s);full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for p in ps[:2]:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing context fault cut',cut))
                ms.append(m)
            assert literal(ms[0])==literal(ms[1]);cuts+=1
    return dict(cases=count,reachable_words=73,all_disable_and_signed_limit_bytes=True,all_25_slots=True,alias_layouts=6,hostile_helper_clobbers=True,
      exact_memory_reads_all_three_bodies=True,normalized_literal_states=True,executed_fault_cuts=cuts,raw_fault_schedule_not_claimed=True,helper_bodies_not_emulated=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m,ends):super().__init__(code,m);self.m=m;self.ends=ends
    def __getitem__(self,pc):
        if pc in self.ends:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        if t==FOLLOW:return super().hook(t)
        assert t==ENTRY;wanted,calls,observations=reference(self.memory,self.case);self.memory=wanted;self.calls.extend(calls);self.observations.extend(observations);self.r[2]=0xF00DBAAD

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>4I',rom,0x466C8);count=0
    # Include the following call and its explicit delay-slot zero argument;
    # the target's poisoned void result must not become that argument.
    for disable,pattern,mode,phase in itertools.product((0,1,255),(0,1,3),(0,2,4,8,63),(0,8)):
        c=Case(disable=disable,pattern=pattern,mode=mode,phase=phase);initial=fixture(c)
        def build(body=None):
            code={}if body is None else dict(zip(range(ENTRY,ENTRY+292,4),body));cls=ReferenceCaller if body is None else Oracle
            m=cls(words,initial,c,entry=WINDOW,connected=code);m.code=BoundaryCode(m.code,m,{WINDOW+16});return m
        expected=build()
        try:expected.run()
        except WindowBoundary:pass
        else:raise AssertionError('Missing caller boundary')
        observe=lambda m:(m.boundary,public(m.memory),m.calls,m.observations,m.r[16:24],m.r[29],m.r[31],m.r[4])
        for body in bound_programs(core,q,symbols(c)):
            m=build(body)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing actor-context caller boundary')
            assert observe(m)==observe(expected),c
        count+=1
    return dict(cases=count,caller='func_15019130',JAL_rom='0x466C8',window_words=4,following_zero_argument_qualified=True,void_return_poisoned=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(stub='void func_1504ADD0(void){}',gate=body.replace('D_800C35EA != 1','D_800C35EA == 0'),
      ignore_inactive=body.replace('actor->interaction_state != 0','1'),unsigned_limit=body.replace('slot < D_8008FD8C','slot < (u8)D_8008FD8C'),
      first_three=body.replace('slot < 4','slot < 3'),wrong_table_index=body.replace('D_800BE728)[slot]','D_800BE728)[(slot + 1) & 3]'),
      missing_actor=body.replace('D_800D154C = actor;',''),missing_slot=body.replace('D_800C3E78 = slot;',''),
      wrong_actor=body.replace('&D_800CC2D0[slot]','&D_800CC2D0[(slot + 1) % 26]'),twenty_six_slots=body.replace('slot != 25','slot != 26'),
      wrong_first_kind=body.replace('0x28','0x29'),wrong_second_kind=body.replace('0x77','0x78'),
      byte_state=body.replace('actor->interaction_state != 0','(u8)actor->interaction_state != 0'),
      cached_limit=body.replace('    s32 slot;','    s32 limit = D_8008FD8C;\n    s32 slot;').replace('slot < D_8008FD8C','slot < limit'),
      cached_table=body.replace('    s32 slot;','    s32 *table = *(s32 **)D_800BE728;\n    s32 slot;').replace('(*(s32 **)D_800BE728)[slot]','table[slot]'))
    assert all(v!=body for v in controls.values());rows=[]
    for c in cases():
        if c.alias or c.phase:continue
        s=symbols(c);wanted,calls,observations=reference(fixture(c),c,s);frames=[];oi=0
        def code(p):
            if p==INPUTS:return 0
            if p==STACK-16:return 99
            if INPUTS+16<=p<=INPUTS+64 and(p-INPUTS)%16==0:return 9+(p-INPUTS)//16
            if INPUTS+80<=p<=INPUTS+128 and(p-INPUTS)%16==0:return 15+(p-INPUTS)//16
            raise AssertionError(hex(p))
        for t,a in calls:
            if t==ZERO:frames.append((0,99,6,*([0]*8)))
            else:
                slot,actor,input_pointer,packet_bytes=observations[oi];oi+=1
                frames.append((1,(a[0]-ACTORS)//812,slot,(actor-ACTORS)//812,code(input_pointer),*packet_bytes))
        arr=lambda v:'{'+','.join(str(u32(x))+'u'for x in v)+'}'
        records='{'+','.join(arr(v)for v in frames)+'}'if frames else'{{0}}'
        states=[read(wanted,ACTORS+i*812)for i in range(26)];kinds=[wanted[ACTORS+i*812+4]for i in range(26)]
        fields=(c.disable,c.limit&255,c.pattern,c.selected,c.value,c.kind,c.mode,wanted[s['D_800C3E78']],(read(wanted,s['D_800D154C'])-ACTORS)//812,
          code(read(wanted,s['D_800CC284'])),int(read(wanted,s['D_800BE728'])==TABLE1),wanted[s['D_800C35EA']],wanted[s['D_8008FD8C']],len(frames))
        rows.append('{'+','.join(str(u32(x))+'u'for x in fields)+','+arr(states)+','+arr(kinds)+','+records+'}')
    code_text='#include <ultra64.h>\n#include "structs.h"\n'
    code_text+='struct127 D_800CC2D0[26],*D_800D154C;u8 D_800C35EA,D_800C3E78;s8 D_8008FD8C;s32 D_800BE728[1],D_800CC284;\n'
    code_text+='typedef struct{u32 disable,limit,pattern,selected,value,kind,mode,out_slot,out_actor,out_input,out_table,out_disable,out_limit,count;u32 states[26],kinds[26],calls[50][11];}Case;\n'
    code_text+='static const Case cases[]={'+',\n'.join(rows)+'};\n'
    code_text+='''_Static_assert(sizeof(void*)==4,"native32");_Static_assert(sizeof(struct127)==812,"actor812");
    _Static_assert(__builtin_offsetof(struct127,interaction_state)==0,"state0");_Static_assert(__builtin_offsetof(struct127,id)==4,"kind4");
    static s32 tables[2][4];static u8 inputs[9][6];static const Case *current;static u32 calls[64][11],call_count,zero_word;
    static u32 input_code(s32 word){u32 i;if((u32)word==zero_word&&zero_word)return 99;for(i=0;i<9;i++)if((u32)word==(u32)inputs[i])return i==0?0:i<5?i+9:i+15;return 0xFFFFFFFFu;}
    void bzero(void*dst,int count){u32 n=call_count++,i;zero_word=(u32)dst;if(n<64){calls[n][0]=0;calls[n][1]=99;calls[n][2]=(u32)count;}for(i=0;i<(u32)count;i++)((u8*)dst)[i]=0;}
    void func_150ED578(struct127 *actor){u32 i=(u32)(actor-D_800CC2D0),n=call_count++,j,kind=input_code(D_800CC284);u8 *p=(u8*)D_800CC284;
    if(n<64){calls[n][0]=1;calls[n][1]=i;calls[n][2]=D_800C3E78;calls[n][3]=(u32)(D_800D154C-D_800CC2D0);calls[n][4]=kind;for(j=0;j<6;j++)calls[n][5+j]=p[j];}
    if(current->mode&1){struct127 *next=&D_800CC2D0[(i+1)%25];next->interaction_state=(s32)((u32)next->interaction_state^1u);next->id=0x28;}
    if(current->mode&2)D_8008FD8C=(s8)(i&1?255:127);
    if((current->mode&4)&&kind==99)for(j=0;j<6;j++)p[j]=(u8)(i+j+0x51);
    if(current->mode&8)D_800BE728[0]=D_800BE728[0]==(s32)tables[0]?(s32)tables[1]:(s32)tables[0];
    if(current->mode&16){actor->interaction_state=0;actor->id=3;}
    if(current->mode&32){D_800C35EA=1;D_800C3E78=255;D_800D154C=&D_800CC2D0[25];D_800CC284=(s32)inputs[0];}}
    '''
    for j,(_,b)in enumerate(dict(selected=body,**controls).items()):code_text+=b.replace('func_1504ADD0(','candidate_%d('%j)+'\n'
    code_text+='static void(*candidates[])(void)={'+','.join('candidate_%d'%j for j in range(len(controls)+1))+'};\n'
    code_text+='''static int run(void){u32 n,j,i,k,t,state,kind,killed=0,bad;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    for(i=0;i<26;i++){for(k=0;k<812;k++)((u8*)&D_800CC2D0[i])[k]=0xA5;state=0;kind=0;
    if(i==25){state=1;kind=0x28;}else if(current->pattern==0){if(i==current->selected){state=current->value;kind=current->kind;}}
    else if(current->pattern==1){static const u8 kinds[4]={0x28,0x77,0,255};state=current->value;kind=kinds[i%4];}
    else if(current->pattern==2){state=i&1?current->value:0;kind=i%3?0x77:1;}else{state=current->value;kind=current->kind;}
    D_800CC2D0[i].interaction_state=(s32)state;D_800CC2D0[i].id=(u8)kind;}
    for(i=0;i<9;i++)for(k=0;k<6;k++)inputs[i][k]=(u8)((16*i+k)*29+0x31);
    for(t=0;t<2;t++)for(i=0;i<4;i++)tables[t][i]=(s32)inputs[1+4*t+i];
    D_800BE728[0]=(s32)tables[0];D_800CC284=(s32)inputs[0];D_800C35EA=(u8)current->disable;D_8008FD8C=(s8)current->limit;D_800C3E78=0xA7;D_800D154C=&D_800CC2D0[25];
    call_count=zero_word=0;for(i=0;i<64;i++)for(k=0;k<11;k++)calls[i][k]=0;candidates[j]();
    bad=D_800C3E78!=current->out_slot||(u32)(D_800D154C-D_800CC2D0)!=current->out_actor||input_code(D_800CC284)!=current->out_input||
    (D_800BE728[0]==(s32)tables[1])!=current->out_table||D_800C35EA!=current->out_disable||(u8)D_8008FD8C!=current->out_limit||call_count!=current->count;
    for(i=0;i<26;i++){bad|=(u32)D_800CC2D0[i].interaction_state!=current->states[i]||D_800CC2D0[i].id!=current->kinds[i];
    if(!j)for(k=5;k<812;k++)bad|=((u8*)&D_800CC2D0[i])[k]!=0xA5;}
    for(i=0;i<current->count;i++)for(k=0;k<11;k++)bad|=calls[i][k]!=current->calls[i][k];if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}}
    for(j=0;j<15;j++)if(!(killed&(1u<<j)))return 10+j;return killed==MASK?0:3;}
    '''.replace('MASK',str((1<<len(controls))-1)+'u')
    code_text+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');path=out/'context-native.c';path.write_text(code_text)
    for opt in('-O0','-O2','-O3'):
        exe=out/('context-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,pointer32_actor812=True,exact_context_and_input_packets=True,
      actor_canaries_unchanged=True,effective_controls=list(controls),stack_aliases_guest_only=True)
