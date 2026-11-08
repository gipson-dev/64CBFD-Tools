"""Actor resource refresh snapshots, helper clobbers, FP payloads and O32 caller."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,RESET,SPAWN,ACTORS,AUX,AUX2,CAMERA,CAMERA2,LINK0,LINK1,LINK2,MARK=0x15063254,0x15060F28,0x15082A44,0x800CC2D0,0x30000,0x30100,0x40000,0x41000,0x70000,0x70100,0x70200,0x80000
PATTERNS=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,0xFF812345,0xFFFFFFFF)
FP=(0x14,0x18,0x1C,0xB8,0x40,0xC4);RESTORED=(0x14,0x18,0x1C,0xB8,0x40,0xC4,0x2C,0x30,0x1CC,0x34)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
    offset:int=0
    field4:int=0x12345678
    field3:int=0x87654321
    value:int=0x3F800000
    identifier:int=0xFE
    facing:int=0x8001
    seed:int=0
    mode:int=7
    alias:int=0
    phase:int=0

def symbols():return dict(D_800CC2D0=ACTORS,func_15060F28=RESET,func_15082A44=SPAWN)
def actor(c,s=None):return u32((symbols()if s is None else s)['D_800CC2D0']+c.offset)
def auxiliary(c,s=None):
    a=actor(c,s);return{0:AUX,1:u32(a-12),2:u32(a+0x13C),3:CAMERA+0x3B0,4:u32(a+0x2F8),5:AUX,6:STACK+c.phase}.get(c.alias,AUX)
def camera(c,s=None):return u32(actor(c,s)-0x3C0)if c.alias==5 else CAMERA
def value(c):return camera(c)if c.alias==4 else u32(c.value)
def args(c,s=None):return(actor(c,s),u32(c.field4),u32(c.field3),value(c))
def fixture(c=Case(),s=None):
    a=actor(c,s);aux=auxiliary(c,s);cam=camera(c,s);m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,512)}
    for base,n in((u32(a-64),0x3AC),(aux,40),(AUX2,40),(cam,1024),(CAMERA2,1024),(MARK,32)):
        for i in range(n):m.setdefault(u32(base+i),0xA5)
    for i,off in enumerate(FP):put(m,u32(a+off),PATTERNS[(c.seed+i)%len(PATTERNS)])
    m[u32(a+0x13F)]=c.identifier&255;put(m,u32(a+0x76),c.facing,2);put(m,u32(a+0x7A),c.facing^0x55AA,2)
    put(m,u32(a+0x144),aux);put(m,u32(a+0x318),cam);put(m,u32(a+0x31C),LINK0)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+528}
def observe(m,c,s=None):
    a=actor(c,s);aux=auxiliary(c,s);cam=camera(c,s)
    return tuple(read(m,u32(a+off))for off in RESTORED)+(read(m,u32(a+0x76),2),read(m,u32(a+0x7A),2),m[u32(a+0x13F)],read(m,u32(a+0x144)),read(m,u32(a+0x318)),read(m,u32(a+0x31C)))+tuple(m[u32(aux+i)]for i in(2,3,4))+(read(m,u32(aux+0x20)),read(m,u32(aux+0x24)),read(m,u32(cam+0x3D4)),read(m,CAMERA2+0x3D4),m[u32(a+5)])

def effect(m,c,s,stage):
    a=actor(c,s);aux=auxiliary(c,s);home=STACK+c.phase;put(m,MARK+4*stage,0xA1700000+stage)
    if c.mode&(1<<stage):
        for i,off in enumerate(FP):put(m,u32(a+off),read(m,u32(a+off))^u32(0x80800001+i*0x101+stage))
        m[u32(a+0x13F)]=(m[u32(a+0x13F)]+0x55+stage)&255;put(m,u32(a+0x76),read(m,u32(a+0x76),2)^(0x8001+stage),2);put(m,u32(a+0x7A),0x1234+stage,2)
        put(m,u32(a+0x144),AUX2);put(m,u32(a+0x318),CAMERA2);put(m,u32(a+0x31C),LINK1 if stage==0 else LINK2);m[u32(a+5)]^=0x10<<stage
    if c.mode&4:
        for i in(2,3,4):m[u32(aux+i)]^=(0xA1+stage+i)&255
        put(m,u32(aux+0x20),read(m,u32(aux+0x20))^0x80000001);put(m,u32(aux+0x24),read(m,u32(aux+0x24))^0x007FFFFF)
    if c.mode&8:put(m,home-20,0x7FA54321+stage);put(m,home-44,0x8001+stage)
    if c.mode&16:
        put(m,home-8,0xDEAD0080+stage);put(m,home-16,CAMERA2);put(m,home-40,0xFF812345+stage)

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);a=actor(c,s);aux=read(m,u32(a+0x144));home=STACK+c.phase;identifier=m[u32(a+0x13F)];put(m,home-8,identifier)
    m[u32(aux+4)]=c.field4&255;m[u32(aux+3)]=c.field3&255;put(m,u32(aux+0x20),value(c));put(m,u32(aux+0x24),value(c));m[u32(aux+2)]=0
    cam=read(m,u32(a+0x318));put(m,home-16,cam)
    # These private homes are part of the original guest layout, so synthetic
    # helper aliases can alter their later reloads without changing the model.
    for off,dest in((0x1C,-28),(0x14,-20),(0x18,-24),(0xB8,-32),(0x40,-36),(0xC4,-40)):
        put(m,home+dest,read(m,u32(a+off)))
    put(m,home-44,read(m,u32(a+0x76),2));calls=[(s['func_15060F28'],(a,0))];observations=[observe(m,c,s)];effect(m,c,s,0)
    delta=signed(u32(a-s['D_800CC2D0']));index=(abs(delta)//812)*(-1 if delta<0 else 1)+1
    calls.append((s['func_15082A44'],(aux,read(m,home-8),0,0,u32(index))));observations.append(observe(m,c,s));effect(m,c,s,1)
    facing=read(m,home-44);x=read(m,home-20);y=read(m,home-24);cam=read(m,home-16)
    put(m,u32(a+0x14),x);put(m,u32(a+0x18),y);put(m,u32(a+0x318),cam)
    z=read(m,home-28);liveY=read(m,u32(a+0x18));link=read(m,u32(a+0x31C));put(m,u32(a+0x1C),z)
    b8=read(m,home-32);liveZ=read(m,u32(a+0x1C));put(m,u32(a+0xB8),b8);put(m,u32(a+0x40),read(m,home-36));c4=read(m,home-40)
    put(m,u32(a+0x76),facing,2);put(m,u32(a+0x7A),facing,2);put(m,u32(a+0x2C),x);put(m,u32(a+0x30),y);put(m,u32(a+0x1CC),liveY);put(m,u32(a+0x34),liveZ);put(m,u32(a+0xC4),c4);put(m,u32(cam+0x3D4),link)
    return m,calls,observations

def cases():
    rows=[]
    for slot,seed,mode in itertools.product((0,1,24,25),range(16),(0,1,2,3,4,7)):
        rows.append(Case(slot*812,0x12340000+seed,0xABCD805A+seed,PATTERNS[(seed+5)%16],identifier=seed*17,facing=seed*0x1111,seed=seed,mode=mode))
    for alias,phase,mode,seed in itertools.product(range(1,7),(0,8),(0,1,2,4,7,8,16,31),(0,12)):
        rows.append(Case(value=PATTERNS[(seed+3)%16],seed=seed,alias=alias,phase=phase,mode=mode))
    for offset in(-812,-4,4,808,816,-0x80000000,0x7FFFFFFC):rows.append(Case(offset=offset,seed=13,mode=7))
    return tuple(dict.fromkeys(rows))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=args(c,s)if arguments is None else arguments)
        self.before=self.r[:];self.before_f=self.f[:];self.observations=[];self.stage=0
    def record_call(self,t):
        counts={self.syms['func_15060F28']:2,self.syms['func_15082A44']:5,ENTRY:4};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t in(self.syms['func_15060F28'],self.syms['func_15082A44']),hex(t);self.observations.append(observe(self.memory,self.case,self.syms));effect(self.memory,self.case,self.syms,self.stage);self.stage+=1
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0x7FA00000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations)
def programs(core,q,s=None):
    s=symbols()if s is None else s;normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));truth=list(q['retail_words'])
    if s==symbols():assert normal==truth
    else:
        for off,name,high in((132,'D_800CC2D0',True),(136,'D_800CC2D0',False)):truth[off//4]=(truth[off//4]&0xFFFF0000)|(((s[name]+0x8000)>>16&65535)if high else(s[name]&65535))
        for off,name in((124,'func_15060F28'),(176,'func_15082A44')):truth[off//4]=(truth[off//4]&0xFC000000)|(s[name]>>2&0x3FFFFFF)
        assert truth==normal
    return truth,normal,list(core.bound_blob(q['raw'],q['refs'],s))

def guest(core,q):
    seen=set();count=0;raw_cases=0
    for c in cases():
        initial=fixture(c);wanted,calls,observations=reference(initial,c);ms=[]
        for body in programs(core,q)[:2]:
            m=Oracle(body,initial,c);m.run();assert(public(m.memory),m.calls,m.observations)==(public(wanted),calls,observations),c
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f[20:]==m.before_f[20:];ms.append(m)
        assert literal(ms[0])==literal(ms[1]),c;seen.update(ms[0].visits);count+=1
        if not c.alias and not(c.mode&24):
            m=Oracle(programs(core,q)[2],initial,c);m.run();assert(public(m.memory),m.calls,m.observations)==(public(wanted),calls,observations),c;raw_cases+=1
    assert seen==set(range(ENTRY,ENTRY+304,4)),list(map(hex,set(range(ENTRY,ENTRY+304,4))-seen))
    cuts=0
    for c in(Case(mode=0),Case(mode=7),Case(alias=1,mode=7),Case(alias=4,mode=7),Case(alias=5,mode=7),Case(alias=6,mode=31),Case(mode=24)):
        initial=fixture(c);ps=programs(core,q)[:2];full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for body in ps:
                m=Oracle(body,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing actor snapshot cut',cut))
                ms.append(m)
            assert literal(ms[0])==literal(ms[1]);cuts+=1
    return dict(cases=count,raw_C_disjoint_cases=raw_cases,reachable_words=76,FP_payload_patterns=16,all_six_snapshots_and_live_coordinate_copies=True,alias_layouts=7,private_home_mutations_guest_only=True,executed_fault_cuts=cuts,hostile_FP_and_GPR_helpers=True,exact_original_normalized_states_and_traces=True,helper_bodies_not_emulated=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m):super().__init__(code,m);self.m=m;self.ends=()
    def __getitem__(self,pc):
        if pc==0x15099C00:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        assert t==ENTRY;wanted,calls,observations=reference(self.memory,self.case,self.syms);self.memory=wanted;self.calls.extend(calls);self.observations.extend(observations);self.r[2]=0xF00DBAAD

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>5I',rom,0xC6E0C);count=0
    for slot,seed,mode,phase in itertools.product((0,1,24),range(16),(0,1,2,7),(0,8)):
        c=Case(offset=812*slot,seed=seed,mode=mode,value=PATTERNS[(seed+7)%16],phase=phase);initial=fixture(c)
        def build(body=None):
            code={0x15099C00:0}
            if body is not None:code.update(zip(range(ENTRY,ENTRY+len(body)*4,4),body))
            cls=ReferenceCaller if body is None else Oracle;m=cls(window,initial,c,entry=0x1509995C,connected=code);m.f[0]=value(c);m.r[7]=0xA5A5A5A5;m.code=BoundaryCode(m.code,m);return m
        def run(m):
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original actor callback continuation')
            return m
        wanted=run(build());observe_result=lambda m:(m.boundary,public(m.memory),m.calls,m.observations,m.r[16:24],m.r[29],m.r[31],m.r[2])
        assert wanted.calls[0]==(ENTRY,args(c));assert wanted.r[2]==1
        for body in programs(core,q):assert observe_result(run(build(body)))==observe_result(wanted),c
        count+=1
    return dict(cases=count,original_window_words=5,original_MFC1_A3=True,full_four_word_packet=True,original_JAL_delay_NOP=True,void_target_result_poisoned=True,original_branch_delay_result_one=True,upstream_integer_to_float_multiply_not_emulated=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(
      swapped_bytes=body.replace('auxiliary->unk4 = field4;','auxiliary->unk4 = field3;'),
      missing_value=body.replace('auxiliary->unk24 = value;',''),
      missing_clear=body.replace('auxiliary->unk2 = 0;',''),
      late_identifier=body.replace('identifier, 0, 0,','actor->unk13F, 0, 0,').replace('identifier = actor->unk13F;','identifier = actor->unk13F; (void)identifier;'),
      live_auxiliary=body.replace('(u8 *)auxiliary, identifier','(u8 *)actor->unk144, identifier'),
      zero_based_slot=body.replace('/ (s32)sizeof(struct127) + 1','/ (s32)sizeof(struct127)'),
      wrong_stride=body.replace('/ (s32)sizeof(struct127)', '/ 816'),
      missing_x=body.replace('actor->x_position = x;',''),
      missing_motion=body.replace('actor->unkB8 = fieldB8;','(void)fieldB8;'),
      missing_camera=body.replace('actor->camera = camera;',''),
      missing_second_facing=body.replace('actor->unk7A = facing;',''),
      wrong_old_y=body.replace('actor->old_y_position = y;','actor->old_y_position = x;'),
      wrong_live_y=body.replace('actor->unk1CC = actor->y_position;','actor->unk1CC = actor->z_position;'),
      missing_c4=body.replace('actor->unkC4 = fieldC4;','(void)fieldC4;'),
      stale_link=body.replace('u32 facing;','u32 facing;\n    struct126 *link;').replace('facing = actor->unk76;','facing = actor->unk76;\n    link = actor->unk31C;').replace('(struct127 *)actor->unk31C','(struct127 *)link'))
    assert all(v!=body for v in controls.values())
    selected=[c for c in cases()if c.alias==0 and c.offset in(0,812,24*812,25*812)]
    arr=lambda vs:'{'+','.join(str(u32(v))+'u'for v in vs)+'}'
    rows=[]
    for c in selected:
        wanted,_,observations=reference(fixture(c),c)
        rows.append('{%s,%s,%s,%s}'%(arr((c.offset//812,c.field4,c.field3,value(c),c.identifier,c.facing,c.seed,c.mode)),arr(observe(wanted,c)),arr(observations[0]),arr(observations[1])))
    code='''#include <ultra64.h>
    #include "structs.h"
    struct127 D_800CC2D0[26]; static struct129 aux[2];static struct108 cams[2];
    void *memset(void*p,int v,unsigned n){volatile u8*q=p;unsigned i;for(i=0;i<n;i++)q[i]=(u8)v;return p;}
    static struct126 links[3];static u32 calls,badpacket,observations[2][24];
    typedef struct{u32 input[8],final[24],first[24],second[24];}Case;
    '''+'static const Case cases[]={'+',\n'.join(rows)+'};static const Case *current;\n'
    code+='''_Static_assert(sizeof(void*)==4,"native32");
    _Static_assert(sizeof(struct127)==812,"actor");_Static_assert(sizeof(struct129)==40,"auxiliary");
    _Static_assert(__builtin_offsetof(struct127,camera)==0x318,"camera field");
    _Static_assert(__builtin_offsetof(struct127,unk1CC)==0x1CC,"live coordinate");
    _Static_assert(__builtin_offsetof(struct108,unk3D4)==0x3D4,"camera owner");
    static const u32 patterns[]={PATTERNS};
    static const u32 fp[]={0x14,0x18,0x1C,0xB8,0x40,0xC4};
    static const u32 restored[]={0x14,0x18,0x1C,0xB8,0x40,0xC4,0x2C,0x30,0x1CC,0x34};
    static u32 rd(const void*p){u32 x;__builtin_memcpy(&x,p,4);return x;}
    static void wr(void*p,u32 x){__builtin_memcpy(p,&x,4);}
    static u32 tag(const void*p){if(p==&aux[0])return 0x30000;if(p==&aux[1])return 0x30100;
      if(p==&cams[0])return 0x40000;if(p==&cams[1])return 0x41000;
      if(p==&links[0])return 0x70000;if(p==&links[1])return 0x70100;if(p==&links[2])return 0x70200;return(u32)p;}
    static void observe(u32 *out){struct127*a=&D_800CC2D0[current->input[0]];u32 i;
      for(i=0;i<10;i++)out[i]=rd((u8*)a+restored[i]);out[10]=a->unk76;out[11]=a->unk7A;out[12]=a->unk13F;
      out[13]=tag(a->unk144);out[14]=tag(a->camera);out[15]=tag(a->unk31C);
      out[16]=aux[0].unk2;out[17]=aux[0].unk3;out[18]=aux[0].unk4;out[19]=rd(&aux[0].unk20);out[20]=rd(&aux[0].unk24);
      out[21]=tag(cams[0].unk3D4);out[22]=tag(cams[1].unk3D4);out[23]=*((u8*)a+5);}
    static void effect(u32 stage){struct127*a=&D_800CC2D0[current->input[0]];u32 i,mode=current->input[7];
      if(mode&(1u<<stage)){for(i=0;i<6;i++)wr((u8*)a+fp[i],rd((u8*)a+fp[i])^(0x80800001u+i*0x101u+stage));
      a->unk13F+=0x55u+stage;a->unk76^=0x8001u+stage;a->unk7A=0x1234u+stage;
      a->unk144=&aux[1];a->camera=&cams[1];a->unk31C=&links[stage+1];*((u8*)a+5)^=0x10u<<stage;}
      if(mode&4){aux[0].unk2^=0xA3u+stage;aux[0].unk3^=0xA4u+stage;aux[0].unk4^=0xA5u+stage;
      wr(&aux[0].unk20,rd(&aux[0].unk20)^0x80000001u);wr(&aux[0].unk24,rd(&aux[0].unk24)^0x007FFFFFu);}}
    void func_15060F28(struct127*a,s32 zero){badpacket|=calls!=0||a!=&D_800CC2D0[current->input[0]]||zero!=0;
      observe(observations[0]);effect(0);calls++;}
    s32 func_15082A44(u8*p,s32 id,s32 zero,s32 other,s32 slot){badpacket|=calls!=1||p!=(u8*)&aux[0]||(u32)id!=current->input[4]||zero!=0||other!=0||(u32)slot!=current->input[0]+1;
      observe(observations[1]);effect(1);calls++;return(s32)0xDEADBEEFu;}
    '''.replace('PATTERNS',','.join(str(v)+'u'for v in PATTERNS))
    for i,b in enumerate([body,*controls.values()]):code+=b.replace('func_15063254(','candidate_%d('%i)+'\n'
    code+='static void(*candidates[])(struct127*,u32,u32,f32)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='''static int run(void){u32 n,j,i,k,bad,killed=0,result[24];struct127*a;union{u32 u;f32 f;}v;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
      __builtin_memset(D_800CC2D0,0xA5,sizeof(D_800CC2D0));__builtin_memset(aux,0xA5,sizeof(aux));__builtin_memset(cams,0xA5,sizeof(cams));
      a=&D_800CC2D0[current->input[0]];for(i=0;i<6;i++)wr((u8*)a+fp[i],patterns[(current->input[6]+i)%16]);
      a->unk13F=current->input[4];a->unk76=current->input[5];a->unk7A=current->input[5]^0x55AA;
      a->unk144=&aux[0];a->camera=&cams[0];a->unk31C=&links[0];calls=badpacket=0;
      v.u=current->input[3];candidates[j](a,current->input[1],current->input[2],v.f);observe(result);bad=badpacket||calls!=2;
      for(i=0;i<24;i++)bad|=result[i]!=current->final[i]||observations[0][i]!=current->first[i]||observations[1][i]!=current->second[i];
      for(i=0;i<sizeof(D_800CC2D0);i++){u32 off=i-current->input[0]*812u,skip=off==5||off==0x13F||(off>=0x76&&off<0x78)||(off>=0x7A&&off<0x7C)||(off>=0x144&&off<0x148)||(off>=0x318&&off<0x320);
        for(k=0;k<10;k++)skip|=off>=restored[k]&&off<restored[k]+4;if(!skip)bad|=((u8*)D_800CC2D0)[i]!=0xA5;}
      for(i=0;i<sizeof(aux);i++)if(!(i>=2&&i<=4)&&!(i>=0x20&&i<0x28))bad|=((u8*)aux)[i]!=0xA5;
      for(i=0;i<sizeof(cams);i++)if(!(i>=0x3D4&&i<0x3D8))bad|=((u8*)cams)[i]!=0xA5;
      if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);
    }}for(j=0;j<CONTROL_COUNT;j++)if(!(killed&(1u<<j)))return 10+j;return 0;}
    '''.replace('CONTROL_COUNT',str(len(controls)))
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'snapshot-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('snapshot-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True,timeout=30);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,SDK_struct_layout_assertions=True,bit_exact_FP_payloads=True,all_actor_array_auxiliary_and_camera_canaries=True,effective_controls=list(controls),synthetic_aliases_and_private_home_mutations_guest_only=True)
