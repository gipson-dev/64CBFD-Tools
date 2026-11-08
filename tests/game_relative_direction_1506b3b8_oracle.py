"""Relative-heading ABI, signed byte categories, live globals and original callbacks."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,math,struct,subprocess
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

ENTRY,ROM,F=0x1506B3B8,0x98868,'func_1506B3B8'
def symbols(i=0):
 p=(0x800CC2D0,0x02337FFC,0x0343FFFC)[i];t=(0x80099A3C,0x02447FFE,0x0355FFFC)[i]
 return dict(D_800CC2D0=p,D_800D154C=(0x800D154C,0x02667FFC,0x0366FFFC)[i],D_80099A3C=t,D_80099A3E=t+2,D_80099A43=t+7,func_1505A630=(0x1505A630,0x1710FFFC,0x1E107FFC)[i])

@dataclass(frozen=True)
class Case:
 high:int=0
 low:int=0
 limits:tuple=(16,32,64)
 angle:int=0x4321
 offset:int=0
 mutation:int=0
 phase:int=0
 coords:tuple=(0x3F800000,0x40000000,0x40400000,0x40800000)

def cases(full=True):
 for h,l,lim in itertools.product(range(256),(0,1,127,255)if full else(0,),((0,64,128),(16,32,64),(255,0,255),(0,0,0))):
  yield Case(h,l,lim,(h*257+l*19)&65535,(h+l)&255,(h+l)%4,8 if h&1 else 0)

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for a in (0x30000,0x50000,s['D_800CC2D0']):m.update({a+i:(i*13+0xA5)&255 for i in range(0x32C)})
 for a,x,z in ((0x30000,c.coords[2],c.coords[3]),(s['D_800CC2D0'],c.coords[0],c.coords[1])):put(m,a+0x14,x);put(m,a+0x1C,z)
 put(m,s['D_800D154C'],0x30000)
 for i in range(256):m[s['D_80099A3C']+i]=(i*23+117)&255
 for at,v in zip((0,2,7),c.limits):m[s['D_80099A3C']+at]=v
 # The helper changes these values after observing the incoming coordinates.
 put(m,0x30000+0x7A,0x6789,2);m[0x30000+0x1FD]=0x91
 return m

def effect(m,c,s):
 a=0x50000 if c.mutation&1 else 0x30000
 put(m,s['D_800D154C'],a)
 facing=((c.high<<8)+c.low+c.angle-(c.offset<<8))&65535
 put(m,a+0x7A,facing,2);m[a+0x1FD]=c.offset
 if c.mutation&2:
  for at,v in zip((0,2,7),reversed(c.limits)):m[s['D_80099A3C']+at]=v
 return a

def public(m):return {a:v for a,v in m.items()if not STACK-256<=a<STACK+256}

def reference(c,s,initial):
 m=dict(initial);a=effect(m,c,s);t=s['D_80099A3C'];angle=(c.high<<8)|c.low;d=angle-65536 if angle&32768 else angle
 magnitude=abs(d>>8);choice=0
 if magnitude<m[t]:choice=1
 else:
  if m[t+7]<magnitude:choice=5
  elif m[t+2]<magnitude:choice=2
  choice=(choice+(4 if d<0 else 3))&255
 m[a+0x138]=0;put(m,read(m,s['D_800D154C'])+0x244,m[t+choice],2);put(m,read(m,s['D_800D154C'])+0x21C,20000,2)
 return public(m),choice

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},arguments=(0xDEADBEEF,0x87654321));self.before_f=self.f[:]
 def record_call(self,t):
  assert t==self.s['func_1505A630'],hex(t)
  self.calls.append((t,(self.f[12],self.f[14],self.r[6])))
 def hook(self,t):
  effect(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xBEEF0000|self.c.angle

def normalized_fp(v):return 0x7FC00000 if math.isnan(floating(v)) else v

def observed(c):return tuple(normalized_fp(bits(floating(c.coords[i])-floating(c.coords[j])))for i,j in ((0,2),(3,1)))+(0,)

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)

def programs(core,q,s):
    normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));raw=list(core.bound_blob(q['raw'],q['refs'],s))
    original=list(core.bound_blob(q['original'],q['original_refs'],s));assert original==normal
    return original,normal,raw

def mapped_fixture(c,syms):
    initial=fixture(c,syms);wanted,_=reference(c,syms,initial)
    for at in wanted:initial.setdefault(at,0xA5)
    return initial

def original_object(core,q,out):
    p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+(core.ROOT/'conker/asm/nonmatchings/game_981E0/func_1506B3B8.s').read_text()+'.size '+F+',.-'+F+'\n')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
    q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
    assert programs(core,q,symbols())[0]==list(q['retail_words'])

def guest(core,q):
    original_object(core,q,core.ROOT/core.BUILD);count=0;seen=set();layouts=[]
    for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
        syms=symbols(index);ps=programs(core,q,syms);rows=list(cases(index==0))
        if index==0:
            for values in((0,0x80000000,0x80000000,0),(0x7F7FFFFF,0xFF7FFFFF,0xFF7FFFFF,0x7F7FFFFF),(1,0x80000001,0,0),(0x7FC00011,0x7F800000,0x3F800000,0x7F800000)):rows.append(Case(255,255,coords=values))
        for c in rows:
            initial=fixture(c,syms);wanted,choice=reference(c,syms,initial);models=[]
            for body in ps:
                m=Oracle(body,initial,c,syms,entry).run();assert public(m.memory)==wanted,(index,c,choice)
                assert tuple(normalized_fp(v)for v in m.calls[0][1][:2])+(m.calls[0][1][2],)==observed(c)
                assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
                models.append(m)
            assert literal(models[0])==literal(models[1])
            assert(models[0].memory,models[0].calls,models[0].trace)==(models[2].memory,models[2].calls,models[2].trace)
            seen.update(pc-entry for pc in models[0].visits);count+=1
        layouts.append(dict(entry=entry,cases=len(rows)))
    assert seen==set(range(0,308,4))-{0xFC}
    alias_rows=[]
    for alias in(0,1,2):
        for h in(0,16,128,255):
            syms=symbols();table=0x30137 if alias==1 else syms['D_80099A3C'];syms.update(D_80099A3C=table,D_80099A3E=table+2,D_80099A43=table+7)
            if alias==2:syms['D_800D154C']=0x30244
            c=Case(h);initial=mapped_fixture(c,syms);wanted,_=reference(c,syms,initial);models=[Oracle(body,initial,c,syms,ENTRY).run()for body in programs(core,q,syms)]
            assert all(public(m.memory)==wanted for m in models);assert literal(models[0])==literal(models[1]);assert(models[0].memory,models[0].trace)==(models[2].memory,models[2].trace);alias_rows.append((c,syms))
    cuts=0
    for c,syms in([(Case(h),symbols())for h in(0,16,32,64,127,128,255)]+alias_rows[4:]):
        ps=programs(core,q,syms)[:2];initial=mapped_fixture(c,syms);full=Oracle(ps[0],initial,c,syms,ENTRY).run()
        for cut in range(full.all_accesses):
            models=[]
            for body in ps:
                m=Oracle(body,initial,c,syms,ENTRY);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing relative-heading cut',cut))
                models.append(m)
            assert literal(models[0])==literal(models[1]);cuts+=1
    return dict(cases=count,layouts=layouts,alias_cases=len(alias_rows),reachable_words=76,unreachable_preserved_offset=0xFC,raw_and_normalized_complete_memory_and_trace_equal=True,literal_original_normalized_states_equal=True,executed_fault_cuts=cuts,table_clear_and_live_actor_global_aliases=True,FP_edges_model_only=True,angle_helper_body_not_emulated=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m,end):super().__init__(code,m);self.m=m;self.end=end;self.ends=()
    def __getitem__(self,pc):
        if pc==self.end:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)

class CallerOracle(Oracle):
    def record_call(self,t):
        if t==ENTRY:self.calls.append((t,()));return
        super().record_call(t)

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();syms=symbols();wrapper=struct.unpack_from('>8I',rom,0x9899C);constructor=struct.unpack_from('>10I',rom,0x8B844);callback=struct.unpack_from('>15I',rom,0xA946C)
    assert callback[4]==0x8E190000 and callback[5]==0x0320F809 and callback[6]==0
    count=0;installed=0
    for h,low,mutation in itertools.product((0,15,16,31,32,63,64,127,128,129,255),(0,255),range(4)):
        c=Case(h,low,mutation=mutation);initial=fixture(c,syms);wanted,_=reference(c,syms,initial);models=[]
        for body in programs(core,q,syms):
            m=CallerOracle(wrapper,initial,c,syms,0x1506B4EC);m.code.update(zip(range(ENTRY,ENTRY+308,4),body));m.run();assert public(m.memory)==wanted and m.calls[0]==(ENTRY,())
            models.append((public(m.memory),m.calls,m.r[16:24],m.r[29],m.r[31]))
        assert models[0]==models[1]==models[2];count+=1
    for present in(0,1):
        for h,mutation in itertools.product((0,16,128,255),range(4)):
            c=Case(h,mutation=mutation);initial=fixture(c,syms);node,config=0x90000,0xA0000
            initial.update({node+i:0xA5 for i in range(64)});put(initial,node+0x28,0x13579);put(initial,config+2,31,2);put(initial,0x80086388,ENTRY)
            m=Oracle(constructor,initial,c,syms,0x1505E394);m.r[16]=node;m.r[7]=config if present else 0;m.code[0x1505E3BC]=0;m.code=BoundaryCode(m.code,m,0x1505E3BC)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original constructor boundary')
            assert read(m.memory,node)==(ENTRY if present else 0)and not m.calls;installed+=1
            if not present:continue
            initial=dict(m.memory);wanted,_=reference(c,syms,initial);models=[]
            for body in programs(core,q,syms):
                m=CallerOracle(callback,initial,c,syms,0x1507BFBC);m.r[16]=node;m.r[17]=0x30000;m.r[2]=0x13579;m.r[7]=0x2468;m.r[8]=0x81;m.f[12]=0x3F123456;m.code.update(zip(range(ENTRY,ENTRY+308,4),body));m.code[0x1507BFF8]=0;m.code=BoundaryCode(m.code,m,0x1507BFF8)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Missing original callback continuation')
                assert public(m.memory)==wanted and m.calls[0]==(ENTRY,())and m.r[2]==0x13579 and m.r[7]==0x2468 and m.r[8]==0x81 and m.f[12]==0x3F123456 and m.f[2]==0x3F800000 and m.f[14]==0
                models.append((public(m.memory),m.calls,m.r[16:24],m.r[29],m.r[31]))
            assert models[0]==models[1]==models[2]
    return dict(wrapper_cases=count,wrapper_words=8,constructor_cases=installed,constructor_words=10,callback_cases=installed//2,callback_words=15,original_table_slot=31,original_indirect_JALR=True,original_delay_NOP=True,original_postcall_home_reloads=True,full_parents_not_claimed=True)

def native(core,out):
    r=core.ROOT;o=out
    body='#include <ultra64.h>\n#include "structs.h"\nextern struct127 D_800CC2D0[26];\nextern struct127 *D_800D154C;\nextern s16 D_80099A3C[],D_80099A3E;\nextern u8 D_80099A43;\nu16 func_1505A630(f32,f32,s32);\n'+core.SELECTED
    variants=[('valid',body),
     ('stale_actor',body.replace('    angle = func_', '    actor = D_800D154C;\n    angle = func_').replace('    actor = D_800D154C;\n    difference =','    difference =')),
     ('threshold_inclusive',body.replace('magnitude < ((u8 *)D_80099A3C)[0]','magnitude <= ((u8 *)D_80099A3C)[0]')),
     ('negative_side',body.replace('choice += 4;','choice += 3;')),
     ('ignore_heading_offset',body.replace('(actor->unk1FD << 8)','0')),
     ('no_magnitude_fold',body.replace('magnitude = (u8)-highByte;','magnitude = (u8)highByte;')),
     ('halfword_lookup',body.replace('((u8 *)D_80099A3C)[choice]','D_80099A3C[choice]')),
     ('wrong_timeout',body.replace('= 20000;','= 20001;'))]
    assert all(s!=body for _,s in variants[1:])
    code='\n'.join(s.replace('void func_1506B3B8(void)','void candidate_%d(void)'%i)for i,(_,s)in enumerate(variants))
    code+='''
    struct127 D_800CC2D0[26], other;
    struct127 *D_800D154C;
    s16 D_80099A3C[512],D_80099A3E;
    u8 D_80099A43;
    typedef char actorSize[sizeof(struct127)==812?1:-1];
    typedef char facingOffset[__builtin_offsetof(struct127,unk7A)==0x7A?1:-1];
    typedef char offsetOffset[__builtin_offsetof(struct127,unk1FD)==0x1FD?1:-1];
    typedef char stateOffset[__builtin_offsetof(struct127,unk138)==0x138?1:-1];
    typedef char timeoutOffset[__builtin_offsetof(struct127,unk21C)==0x21C?1:-1];
    typedef char resultOffset[__builtin_offsetof(struct127,unk244)==0x244?1:-1];
    typedef struct {u32 high,low,t0,t2,t7,angle,offset,mutation,choice,value,dx,dz;} Test;
    static const Test tests[]={
    '''
    rows=[]
    for c in cases(True):
     s=symbols();expected,choice=reference(c,s,fixture(c,s));a=0x50000 if c.mutation&1 else 0x30000
     values=(c.high,c.low,*c.limits,c.angle,c.offset,c.mutation,choice,read(expected,a+0x244,2),*observed(c)[:2])
     rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    code+=',\n'.join(rows)+'''};
    static const Test *active;
    static u32 calls,failed;
    static u32 floatBits(f32 v){union {f32 f;u32 u;}x;x.f=v;return x.u;}
    static void limits(u32 a,u32 b,u32 c){((u8*)D_80099A3C)[0]=a;((u8*)D_80099A3C)[2]=b;((u8*)D_80099A3C)[7]=c;((u8*)&D_80099A3E)[0]=b;D_80099A43=c;}
    u16 func_1505A630(f32 x,f32 z,s32 zero){
     const Test*t=active;struct127*a=(t->mutation&1)?&other:&D_800CC2D0[1];
     calls++;if(calls!=1||floatBits(x)!=t->dx||floatBits(z)!=t->dz||zero)failed=1;
     D_800D154C=a;a->unk7A=((t->high<<8)+t->low+t->angle-(t->offset<<8))&65535;a->unk1FD=t->offset;
     if(t->mutation&2)limits(t->t7,t->t2,t->t0);return t->angle;
    }
    static void reset(const Test*t){
     u32 i;u8*p=(u8*)D_800CC2D0;for(i=0;i<sizeof(D_800CC2D0);i++)p[i]=0xA5;p=(u8*)&other;for(i=0;i<sizeof(other);i++)p[i]=0xA5;
     for(i=0;i<sizeof(D_80099A3C);i++)((u8*)D_80099A3C)[i]=0xA5;
     for(i=0;i<256;i++)((u8*)D_80099A3C)[i]=(i*23+117)&255;limits(t->t0,t->t2,t->t7);
     D_800CC2D0[0].x_position=1.0f;D_800CC2D0[0].z_position=2.0f;D_800CC2D0[1].x_position=3.0f;D_800CC2D0[1].z_position=4.0f;
     D_800CC2D0[1].unk7A=0x6789;D_800CC2D0[1].unk1FD=0x91;D_800D154C=&D_800CC2D0[1];calls=failed=0;active=t;
    }
    static u32 result(const Test*t){
     struct127*a=(t->mutation&1)?&other:&D_800CC2D0[1];u32 i;u8*p=(u8*)a;
     if(calls!=1||failed||D_800D154C!=a||a->unk138||((u16)a->unk244)!=t->value||a->unk21C!=20000)return 0;
     for(i=0;i<sizeof(*a);i++)if(i!=0x7A&&i!=0x7B&&i!=0x138&&i!=0x1FD&&i!=0x21C&&i!=0x21D&&i!=0x244&&i!=0x245&&!(a==&D_800CC2D0[1]&&((i>=0x14&&i<0x18)||(i>=0x1C&&i<0x20)))&&p[i]!=0xA5)return 0;
     return 1;
    }
    static int run(void){u32 i,j,killed=0;for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<8;j++){
     reset(&tests[i]);switch(j){case 0:candidate_0();break;case 1:candidate_1();break;case 2:candidate_2();break;case 3:candidate_3();break;case 4:candidate_4();break;case 5:candidate_5();break;case 6:candidate_6();break;default:candidate_7();break;}
     if(!result(&tests[i])){if(!j)return 10;killed|=1u<<(j-1);}}
     return killed==127?0:11;}
    '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=o/'native-relative-direction-v17.c';p.write_text(code);reports=[]
    for profile in ('-O0','-O2','-O3'):
     exe=o/('native-relative-direction-v17'+profile)
     q=subprocess.run(native_command(profile)+['-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
     (o/('native-relative-direction-v17'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
     q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
     reports.append(dict(profile=profile,cases=len(rows),UBSan=True,controls=[k for k,_ in variants[1:]],all_seven_controls_effective=True,helper_float_arguments_and_postcall_retargeting=True,background_canaries=True,overlapping_table_aliases_seeded_consistently=True))
    return dict(cases_per_executable=len(rows),profiles=reports,effective_controls=7,actual_SDK_layout=True,trapping_UBSan=True)
