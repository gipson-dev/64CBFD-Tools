"""Actor/list query, ordered reads, all original caller packets and native32 ABI."""
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,ACTOR,LIST0,LIST1,DESC0,DESC1,MARK=0x150229E4,0x30000,0x40000,0x50000,0x60000,0x70000,0x80000
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    pointer:int=ACTOR
    active:int=1
    actor_type:int=0
    slot:int=0
    identity:int=173
    count:int=4
    hit:int=2
    flag:int=1
    record_kind:int=2
    gate:int=1
    alias:int=0
    phase:int=0
def symbols(c=Case()):
    s=dict(D_800C35C8=0x800C35C8,D_800C363A=0x800C363A,D_800C35F0=0x800C35F0,D_800CBFDF=0x800CBFDF)
    if c.alias==1:s['D_800C363A']=ACTOR+0x3B
    elif c.alias==2:s['D_800C35F0']=s['D_800C35C8']
    elif c.alias==4:s['D_800CBFDF']=u32(ACTOR+0x3B-c.slot*812)
    elif c.alias==5:s['D_800C35C8']=ACTOR
    return s
def actor(c):return DESC0 if c.alias==3 else c.pointer
def fixture(c,s=None):
    s=symbols(c)if s is None else s;m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-256,256)}
    size=max(c.count,3)
    for base,n in((ACTOR,812),(LIST0,size*8+16),(LIST1,size*8+16),(DESC0,max(size*8,812)+16),(DESC1,size*8+16),(MARK,16)):
        for i in range(n):m[u32(base+i)]=(i*29+0x59)&255
    for group in range(2):
        flags=(LIST0,LIST1)[group];descriptors=(DESC0,DESC1)[group]
        for i in range(size):
            put(m,flags+i*2,(0,0x8000,0xFFFF)[i%3],2)
            put(m,descriptors+i*8,3 if i%3==1 else 2,2);put(m,descriptors+i*8+2,c.identity^0x80,1)
        if group==(1 if c.actor_type==4 else 0) and 0<=c.hit<c.count:
            put(m,flags+c.hit*2,c.flag,2);put(m,descriptors+c.hit*8,c.record_kind,2);put(m,descriptors+c.hit*8+2,c.identity,1)
    p=actor(c)
    if p:
        put(m,p,c.active);put(m,p+5,c.actor_type,1);put(m,p+0x65,c.slot,1);put(m,p+0x3B,c.identity if c.slot==0 else c.identity^0x55,1)
    put(m,s['D_800C35C8'],LIST0 if c.gate else 0);put(m,s['D_800C35C8']+4,LIST1)
    put(m,s['D_800C35F0'],DESC0);put(m,s['D_800C35F0']+4,DESC1)
    if c.alias==2:
        put(m,s['D_800C35C8'],LIST0 if c.gate else 0);put(m,s['D_800C35C8']+4,LIST1)
    put(m,s['D_800C363A'],c.count,1);put(m,s['D_800C363A']+1,c.count,1)
    put(m,u32(s['D_800CBFDF']+c.slot*812),c.identity,1)
    return m
def reference(m,c,s=None):
    s=symbols(c)if s is None else s;trace=[]
    def rd(p,n=4):
        p=u32(p);v=read(m,p,n);trace.append(('R',p,n,v));return v
    p=actor(c)
    if not p:return 0,trace
    if not rd(p):return 0,trace
    if not rd(s['D_800C35C8']):return 0,trace
    group=1 if rd(p+5,1)==4 else 0;slot=rd(p+0x65,1)
    identity=rd(s['D_800CBFDF']+812*slot,1)if slot else rd(p+0x3B,1)
    count=rd(s['D_800C363A']+group,1)
    if count:
        enabled=rd(s['D_800C35C8']+4*group)
        for index in range(count):
            if rd(enabled+2*index,2):
                table=rd(s['D_800C35F0']+4*group);row=u32(table+8*index)
                if rd(row,2)==2 and rd(row+2,1)==identity:return 2 if slot else 1,trace
    return 0,trace
def cases():
    rows=[]
    for count,kind,slot in itertools.product(range(256),(0,4),(0,24)):
        rows.append(Case(count=count,actor_type=kind,slot=slot,hit=count-1))
    for pointer,active,kind,slot,gate in itertools.product((0,ACTOR),(0,1,0x80000000),(0,3,4,255),(0,1,255),(0,1)):
        rows.append(Case(pointer,active,kind,slot,gate=gate))
    for identity,flag,record_kind,hit in itertools.product((0,127,128,255),(0,1,0x8000,0xFFFF),(0,2,0x102,0x8002),(-1,0,3)):
        rows.append(Case(identity=identity,flag=flag,record_kind=record_kind,hit=hit))
    for alias,slot,kind,phase in itertools.product(range(6),(0,1,24),(0,4),(0,8)):
        rows.append(Case(alias=alias,slot=slot,actor_type=kind,phase=phase))
    return tuple(dict.fromkeys(rows))
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(actor(c),)if arguments is None else arguments)
        self.before=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        assert t==ENTRY,hex(t);a=(self.r[4],);self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):raise AssertionError(('Unexpected query helper',hex(t)))
def state(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def programs(core,q,s):
    normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));raw=list(core.bound_blob(q['raw'],q['refs'],s))
    truth=list(struct.unpack('>73I',(core.ROOT/'conker/conker.us.bin').read_bytes()[core.ROM:core.ROM+292]))
    original=symbols()
    if s==original:assert truth==normal
    else:
        # Independent original words retain their instruction fields; rebind
        # only the ten original symbolic address halves for alias layouts.
        specs={20:('D_800C35C8',True),40:('D_800C35C8',False),44:('D_800C363A',True),72:('D_800CBFDF',True),80:('D_800C35C8',True),148:('D_800CBFDF',False),156:('D_800C363A',False),172:('D_800C35F0',True),176:('D_800C35C8',False),180:('D_800C35F0',False)}
        for off,(name,hi)in specs.items():truth[off//4]=(truth[off//4]&0xFFFF0000)|(((s[name]+0x8000)>>16&65535)if hi else(s[name]&65535))
        assert truth==normal
    return truth,normal,raw
def guest(core,q):
    count=0;seen=set();returns=set()
    for c in cases():
        s=symbols(c);initial=fixture(c,s);value,trace=reference(initial,c,s);ms=[]
        for k,p in enumerate(programs(core,q,s)):
            m=Oracle(p,initial,c);m.run();assert(m.r[2],m.memory,m.trace,m.calls)==(value,initial,trace,[]),c
            assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31]and m.f==m.before_f,c
            if k<2:ms.append(m)
        assert state(ms[0])==state(ms[1]),c
        seen.update(ms[0].visits);returns.add(value);count+=1
    missing=set(range(ENTRY,ENTRY+292,4))-seen;assert missing=={0x15022A24,0x15022AEC},list(map(hex,missing));assert returns=={0,1,2}
    cuts=0
    for c in(Case(pointer=0),Case(active=0),Case(gate=0),Case(count=0),Case(),Case(slot=24),Case(hit=-1),Case(flag=0),Case(record_kind=0x102),Case(alias=2),Case(alias=5)):
        s=symbols(c);initial=fixture(c,s);ps=programs(core,q,s);full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for p in ps[:2]:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing query fault cut',cut))
                ms.append(m)
            assert state(ms[0])==state(ms[1]);cuts+=1
    return dict(cases=count,reachable_words=71,unreachable_words=['0x15022A24','0x15022AEC'],returns=[0,1,2],all_count_bytes=True,guest_alias_layouts=6,
      exact_ordered_reads_all_three_bodies=True,memory_unchanged=True,normalized_literal_states=True,executed_fault_cuts=cuts,raw_fault_schedule_not_claimed=True)
class BoundaryCode(WindowCode):
    def __init__(self,code,m,ends):super().__init__(code,m);self.m=m;self.ends=ends
    def __getitem__(self,pc):
        if pc in self.ends:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):self.r[2]=reference(self.memory,self.case)[0]
def caller_suite(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes()
    sites=(0x4B360,0x4C050,0x50CB0,0x59720,0x59E8C,0x5BA18,0x7FAD4,0x84004,0x8BB48,0x8F954,0xA976C)
    rows=[dict(rom=hex(p),va=hex(0x15000000+p-0x2D4B0),words=list(struct.unpack_from('>7I',rom,p)))for p in sites]
    count=0;covered=[]
    for index,row in enumerate(rows):
        va=int(row['va'],16);words=row['words'];length=7 if index==8 else 4;body=words[:length]
        branch_index=5 if index==8 else 2;branch=body[branch_index];op=branch>>26;assert op in(4,5,20,21)
        target=va+4*(branch_index+1+((branch&65535)^32768)-32768);ends={target,va+length*4}
        for c in(Case(pointer=0),Case(active=0),Case(hit=-1),Case(slot=0),Case(slot=1),Case(slot=24,actor_type=4)):
            c=replace(c,phase=8 if count&1 else 0);initial=fixture(c);put(initial,STACK+c.phase+0x48,actor(c));put(initial,STACK+c.phase+0x40,0x12345678);put(initial,STACK+c.phase+0x4E,0xABCD,2)
            def build(p=None):
                cls=ReferenceCaller if p is None else Oracle;code={}if p is None else dict(zip(range(ENTRY,ENTRY+292,4),p))
                m=cls(body,initial,c,entry=va,connected=code);m.r[4]=actor(c);m.r[16]=actor(c);m.r[17]=7 if index==0 else actor(c);m.r[19]=MARK;m.r[20]=actor(c)
                m.r[8]=812*7;m.r[9]=u32(actor(c)-812*7);m.f[12]=0x3F400000
                m.code=BoundaryCode(m.code,m,ends);return m
            expected=build()
            try:expected.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing reference caller boundary')
            observed=lambda m:(m.boundary,m.memory,m.calls,m.r[16:24],m.r[29],m.r[31])
            for p in programs(core,q,symbols(c)):
                m=build(p)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Missing query caller boundary')
                assert observed(m)==observed(expected),(row,c)
            covered.append(row['va']);count+=1
    return dict(cases=count,original_sites=11,body_variants=3,all_argument_packets=True,original_return_branches=True,windows=[4]*8+[7,4,4],full_parents_not_claimed=True)
def native(core,out):
    body=core.SELECTED
    controls=dict(stub='s32 func_150229E4(struct127 *actor){(void)actor;return 9;}',
      ignored_state=body.replace('if (actor->interaction_state == 0) return 0;',''),
      ignored_group1_gate=body.replace('D_800C35C8[0] == NULL','D_800C35C8[0] == NULL && actor->unk5 != 4'),
      wrong_group=body.replace('actor->unk5 == 4','actor->unk5 == 3'),
      wrong_link_stride=body.replace('ownerSlot * sizeof(struct127)','ownerSlot * (sizeof(struct127) - 4)'),
      wrong_link_index=body.replace('ownerSlot * sizeof(struct127)','(ownerSlot - 1) * sizeof(struct127)'),
      wrong_link_identity=body.replace('D_800CBFDF[ownerSlot * sizeof(struct127)]','actor->unique_id'),
      ignore_enables=body.replace('*enabled != 0','1'),
      signed_enables=body.replace('*enabled != 0','*(s16 *)enabled > 0'),
      byte_kind=body.replace('record->kind == 2','(u8)record->kind == 2'),
      wrong_row_stride=body.replace('index * 8','index * 4'),
      wrong_link_return=body.replace('return 2;','return 1;'),
      signed_count=body.replace('D_800C363A[group]','(s8)D_800C363A[group]'))
    assert all(v!=body for v in controls.values());rows=[]
    for c in cases():
        if c.alias or c.phase or c.slot>=25:continue
        value=reference(fixture(c),c)[0]
        rows.append('{%du,0x%Xu,%du,%du,%du,%du,%d,%du,%du,%du,%du}'%(bool(c.pointer),c.active,c.actor_type,c.slot,c.identity,c.count,c.hit,c.flag,c.record_kind,c.gate,value))
    code='#include <ultra64.h>\n#include "structs.h"\n'
    code+='typedef struct GroupActorRecord15022528{u16 kind;u8 actorId;u8 reserved03[5];}GroupActorRecord15022528;\n'
    code+='u16 *D_800C35C8[2];u8 *D_800C35F0[2];u8 D_800C363A[2],D_800CBFDF[25*812];\n'
    code+='_Static_assert(sizeof(struct127)==812,"actor812");_Static_assert(sizeof(void*)==4,"native32");_Static_assert(sizeof(GroupActorRecord15022528)==8,"row8");\n'
    for j,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace('func_150229E4(','candidate_%d('%j)+'\n'
    code+='typedef struct{u32 pointer,active,type,slot,id,count;s32 hit;u32 flag,kind,gate,value;}Case;\nstatic const Case cases[]={'+',\n'.join(rows)+'};\n'
    code+='static s32(*candidates[])(struct127*)={'+','.join('candidate_%d'%j for j in range(len(controls)+1))+'};\n'
    code+='''static struct127 actor;static u16 flags[2][256];static GroupActorRecord15022528 records[2][256];
    static u32 hash(const void*p,u32 n){const u8*b=p;u32 h=2166136261u,i;for(i=0;i<n;i++)h=(h^b[i])*16777619u;return h;}
    static u32 digest(void){return hash(&actor,sizeof(actor))^hash(flags,sizeof(flags))^hash(records,sizeof(records))^hash(D_800CBFDF,sizeof(D_800CBFDF))^hash(D_800C35C8,sizeof(D_800C35C8))^hash(D_800C35F0,sizeof(D_800C35F0))^hash(D_800C363A,sizeof(D_800C363A));}
    static int run(void){u32 n,j,g,k,killed=0,before;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
    for(k=0;k<sizeof(actor);k++)((u8*)&actor)[k]=(u8)(k*29+0x59);actor.interaction_state=(s32)cases[n].active;actor.unk5=cases[n].type;actor.unk65=cases[n].slot;actor.unique_id=cases[n].slot?cases[n].id^0x55:cases[n].id;
    for(g=0;g<2;g++){D_800C35C8[g]=flags[g];D_800C35F0[g]=(u8*)records[g];D_800C363A[g]=cases[n].count;
    for(k=0;k<256;k++){flags[g][k]=k%3==0?0:k%3==1?0x8000:0xFFFF;records[g][k].kind=k%3==1?3:2;records[g][k].actorId=cases[n].id^0x80;}
    if(g==(cases[n].type==4?1u:0u)&&cases[n].hit>=0&&cases[n].hit<(s32)cases[n].count){k=cases[n].hit;flags[g][k]=cases[n].flag;records[g][k].kind=cases[n].kind;records[g][k].actorId=cases[n].id;}}
    if(!cases[n].gate)D_800C35C8[0]=0;D_800CBFDF[cases[n].slot*812]=(u8)cases[n].id;before=digest();
    for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){s32 value=candidates[j](cases[n].pointer?&actor:0);if(!j){if(value!=(s32)cases[n].value||digest()!=before)return 2;}else if(value!=(s32)cases[n].value)killed|=1u<<(j-1);}}
    for(j=0;j<13;j++)if(!(killed&(1u<<j)))return 10+j;return killed==MASK?0:3;}
    '''.replace('MASK',str((1<<len(controls))-1)+'u')
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'query-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('query-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,actor812_row8_pointer32=True,full_input_digests_unchanged=True,effective_controls=list(controls),native_slots_0_through_24=True,guest_aliases_separate=True)
