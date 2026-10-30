"""XZ pivot rotation: independent ordered FP equations, alias and callback model."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,re,struct,subprocess
from tools.tests import test_game_trig_match as trig
from tools.tests import test_game_cosine_match as cosine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-xz-pivot-rotation-1508EF80-match';F='func_1508EF80';ENTRY=0x1508EF80;COS,SIN,FACTOR=0x15047C00,0x15047D60,0x8009DC80;SYMS=dict(cosf=COS,sinf=SIN,D_8009DC80=FACTOR);fp=trig.operation
VALUES=(0,0x80000000,0x3F800000,0xBF800000,0x3E800000,0xC0200000,0x42B40000,0xC3340000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC54321,0x7F810001)
@dataclass(frozen=True)
class Case:
 pattern:int=0
 alias:int=0
 mode:int=0
 phase:int=0
 p:int=0
 b:int=0
 q:int=0
 angle:int=-1

def addresses(c):
 if c.p:return(c.p,c.b,c.q)
 p,b,q=0x30020,0x30120,0x30220
 return [(p,b,q),(p,b,p),(p,b,b),(p,p,q),(p,p,p),(p,b,p+4),(p,p+4,p+8),(p,b,b-4),(FACTOR,b,q),(p,b,FACTOR)][c.alias]
def degree(c):return c.angle if c.angle>=0 else VALUES[(c.pattern*5+6)%len(VALUES)]
def fixture(c,factor=FACTOR):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
 for base,length in((0x30000,0x280),(FACTOR-32,96),(factor-32,96)):
  for i in range(length):m.setdefault(base+i,(i*13+0x5A)&255)
 p,b,q=addresses(c)
 for j,at in enumerate((p,p+4,p+8,b,b+4,b+8)):
  for i in range(4):m.setdefault(at+i,0xA5)
  put(m,at,VALUES[(c.pattern*(2*j+1)+j+2)%len(VALUES)])
 put(m,factor,0x3C8EFA35)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-0x600<=a<STACK+0x180}
def observed(m,c,factor):
 p,b,q=addresses(c);return tuple(read(m,a)for a in(p,p+4,p+8,b,b+4,b+8,q,q+4,q+8,factor))
def provider(c,ordinal):return VALUES[(c.pattern+ordinal*3+2)%len(VALUES)]
def effect(m,c,ordinal,factor):
 p,b,q=addresses(c)
 if c.mode&1:put(m,p+(0 if ordinal&1 else 8),VALUES[(ordinal+c.pattern+7)%len(VALUES)])
 if c.mode&2:put(m,b+(8 if ordinal&1 else 0),VALUES[(ordinal+c.pattern+10)%len(VALUES)])
 if c.mode&4:put(m,factor,VALUES[(ordinal+c.pattern+4)%len(VALUES)])
 if c.mode&8:put(m,q+4,0x55000000+ordinal)
def reference(initial,c,factor=FACTOR,s=SYMS,actual=False,call_base=0):
 m=dict(initial);p,b,q=addresses(c);dx=fp(read(m,p),read(m,b),'sub');radians=fp(degree(c),read(m,factor),'mul');dz=fp(read(m,p+8),read(m,b+8),'sub');calls=[];obs=[]
 def call(target):
  ordinal=call_base+len(calls);calls.append((target,radians));obs.append(observed(m,c,factor))
  value=(cosine.reference(radians)if target==s['cosf']else trig.reference(radians))if actual else provider(c,ordinal)
  if not actual:effect(m,c,ordinal,factor)
  return value
 co=call(s['cosf']);si=call(s['sinf']);cx=fp(co,dx,'mul');pz=read(m,b);sx=fp(si,dz,'mul');x=fp(fp(sx,cx,'add'),pz,'add');si=call(s['sinf']);co=call(s['cosf']);nx=fp(si^0x80000000,dx,'mul');pz=read(m,b+8);cz=fp(co,dz,'mul');z=fp(fp(cz,nx,'add'),pz,'add');put(m,q,x);put(m,q+8,z);return m,calls,obs

class Oracle(trig.TrigOracle):
 def __init__(self,words,initial,c,entry=ENTRY,s=SYMS,connected=None,fault=None,arguments=None):
  p,b,q=addresses(c);super().__init__(words,initial,phase=c.phase,entry=entry,arguments=arguments or(p,b,degree(c),q),connected=connected);self.c=c;self.s=s;self.factor=s['D_8009DC80'];self.cut=fault;self.root_accesses=0;self.observations=[]
 def access(self):
  if self.own_instruction and ENTRY<=self.current_pc<ENTRY+220:
   if self.root_accesses==self.cut:raise faults.AccessBoundary
   self.root_accesses+=1
 def execute(self,w):
  # The shared oracle already handles exact float32 add/mul/sub/neg, SRA,
  # truncation and even/odd SDK doubleword save/restore pairing.
  if w>>26==17 and(w>>21)&31==16 and w&63==5:
   self.f[(w>>6)&31]=self.f[(w>>11)&31]&0x7FFFFFFF
  else:return super().execute(w)
 def record_call(self,target):
  if target in(self.s['cosf'],self.s['sinf']):
   args=self.f[12];self.calls.append((target,args));self.events.append(('CALL',target,args));self.observations.append(observed(self.memory,self.c,self.factor))
  elif target==ENTRY:self.callbacks.append(tuple(self.arguments(4)))
  else:raise AssertionError(('Unqualified provider',hex(target)))
 def hook(self,target):
  assert target in(self.s['cosf'],self.s['sinf']);value=provider(self.c,len(self.calls)-1);effect(self.memory,self.c,len(self.calls)-1,self.factor)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def images(label,s=SYMS,entry=ENTRY):return[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.condition,m.lo,m.hi,m.observations)
def compare(c,ws,s=SYMS,entry=ENTRY,connected=None,initial=None,actual=False):
 initial=fixture(c,s['D_8009DC80'])if initial is None else initial;want,calls,obs=reference(initial,c,s['D_8009DC80'],s,actual);ms=[]
 for words in ws:
  m=Oracle(words,initial,c,entry,s,connected).run();assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),(c,m.calls,calls,m.observations,obs);ms.append(m)
 assert all(state(m)==state(ms[0])for m in ms[1:]),c
 return ms[0]
def guest_suite():
 ws=images('guest');assert ws[0]==ws[2]and ws[0]!=ws[1];visits=set();count=0
 for pattern,alias,mode,phase in itertools.product(range(32),range(8),range(16),(0,8)):
  c=Case(pattern,alias,mode,phase);m=compare(c,ws);visits.update(m.visits);count+=1
 extras=0
 for c in (Case(4,8,15),Case(8,9,15)):compare(c,ws);extras+=1
 assert set(range(ENTRY,ENTRY+220,4))<=visits;cuts=delays=0
 for c in(Case(),Case(8,1,15),Case(17,6,7)):
  full=compare(c,ws)
  for cut in range(full.root_accesses):
   ms=[]
   for words in ws:
    m=Oracle(words,fixture(c),c,fault=cut)
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Missing cut')
    ms.append(m)
   # Normalized and original have identical fault state. Raw scheduling
   # is compared for precise memory/call effects, not transient FP registers.
   assert state(ms[0])==state(ms[2]);assert(ms[0].memory,ms[0].events,ms[0].calls,ms[0].observations)==(ms[1].memory,ms[1].events,ms[1].calls,ms[1].observations)
   cuts+=1;delays+=ms[0].delay_of is not None
 rebase=0
 for j,(at,factor)in enumerate(((0x16088004,0x90007FFC),(0x17088008,0x90008000),(0x1808800C,0x9000FFFC))):
  s=dict(D_8009DC80=factor,cosf=at+0x10004,sinf=at+0x20008);rebased=images('rebase-'+str(j),s,at)
  for p,a,mode in itertools.product((0,3,15,18),(0,1,6),(0,7,15)):compare(Case(p,a,mode),rebased,s,at);rebase+=1
 return dict(cases=count,executions=3*count,guest_only_global_alias_cases=extras,covered_words=55,alignment_words=1,access_prefix_cases=cuts,delay_slot_cuts=delays,raw_fault_transient_FP_equality_claimed=False,normalized_full_fault_state_equal=True,rebased_cases=rebase,GNU_layouts=3,alias_layouts=8,complete_final_state_and_trace_equal=True,frame=64,RA_offset=28,saved_f20_offset=16,all_saved_registers_preserved=True)
def helper_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 code={};names={COS:(0x750B0,85),SIN:(0x75210,104)}
 for at,(offset,n)in names.items():
  raw=rom[offset:offset+n*4];assert elf[elf_slot_offset(elf,at,n*4):elf_slot_offset(elf,at,n*4)+n*4]==raw;code.update({at+4*i:w for i,w in enumerate(struct.unpack('>%dI'%n,raw))})
 globals=dict(trig.GLOBALS,**{})
 globals.update(trig.COS_GLOBALS);count=0;seen=set();ws=images('providers')
 for p,alias,phase in itertools.product(range(32),(0,1,2,4,6),(0,8)):
  c=Case(p,alias,0,phase);initial=fixture(c)
  for address,value in globals.items():put(initial,address,value)
  m=compare(c,ws,connected=code,initial=initial,actual=True);seen.update(m.visits&code.keys());count+=1
 return dict(cases=count,original_and_current_cosine_words=85,original_and_current_sine_words=104,visited_provider_words=len(seen),helper_matching_credit=0,actual_polynomials_connected=True,IEEE_exception_flags_or_hardware_claimed=False)
def controls(body):
 return dict(wrong_dx=body.replace('point[0] - pivot[0]','point[0] + pivot[0]'),wrong_dz=body.replace('point[2] - pivot[2]','point[2] + pivot[2]'),wrong_scale=body.replace('degrees * D_8009DC80','degrees * 1.0f'),wrong_first=body.replace('cachedValue = cosf(radians);','cachedValue = sinf(radians);'),wrong_second=body.replace('providerValue = sinf(radians);','providerValue = cosf(radians);'),wrong_third=body.replace('cachedValue = sinf(radians);','cachedValue = cosf(radians);'),wrong_fourth=body.replace('providerValue = cosf(radians);','providerValue = sinf(radians);'),wrong_x_sign=body.replace('providerValue * dz + cachedValue * dx','providerValue * dz - cachedValue * dx'),wrong_z_sign=body.replace('(-cachedValue) * dx','cachedValue * dx'),wrong_pivot_x=body.replace('x += pivot[0]','x += pivot[2]'),wrong_pivot_z=body.replace('z += pivot[2]','z += pivot[0]'),wrong_output_x=body.replace('output[0] = x','output[1] = x'),wrong_output_z=body.replace('output[2] = z','output[1] = z'),early_output=body.replace('    cachedValue = sinf(radians);','    output[0] = x;\n    cachedValue = sinf(radians);').replace('    output[0] = x;\n    output[2] = z;','    output[2] = z;'))
def control_suite():
 body=(o/'selected-semantic-input.c').read_text();out={}
 for name,bad in controls(body).items():
  assert bad!=body,name;obj,diag=compile_owner(r,o,bad,'negative-'+name);assert not diag;ws=linked(obj,'negative-linked-'+name);found=None
  for p,alias,mode in itertools.product(range(19),(0,1,2,6),(0,15)):
   c=Case(p,alias,mode);initial=fixture(c);want,calls,obs=reference(initial,c);m=Oracle(ws,initial,c).run()
   if(public(m.memory),m.calls,m.observations)!=(public(want),calls,obs):found=[p,alias,mode];break
  assert found is not None,('Ineffective compiled control',name);out[name]=found
 return dict(count=len(out),compiled_effective_controls=out,compile_or_oracle_failures_accepted=False)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __contains__(self,pc):return pc==self.owner.window_end or super().__contains__(pc)
 def __getitem__(self,pc):
  if pc==self.owner.window_end:raise WindowBoundary
  return super().__getitem__(pc)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();call=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));pointer=struct.pack('>I',ENTRY);assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==call]==[0x152CD4,0x152CF8,0x152D8C,0x152DB4,0x158488,0x1598A4,0x15A978,0x15A9F0];assert not[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer]
 ws=images('caller');counts=[];parents=[]
 for start,offset,n,parent,assembly in[(0x1512AFD4,0x158484,3,'func_1512AD54','157840'),(0x1512C39C,0x15984C,25,'func_1512C20C','157840'),(0x1512D4B4,0x15A964,7,'func_1512D390','15A840'),(0x1512D53C,0x15A9EC,3,'func_1512D390','15A840')]:
  window=list(struct.unpack_from('>%dI'%n,rom,offset));literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/('conker/asm/'+assembly+'.s')).read_text())};assert window==[literal[start+4*i]for i in range(n)];count=0
  for pattern,mode,angle,phase in itertools.product((0,3,7),(0,7,15),(-90.,-5.,-0.,0.,5.,34.,35.,90.),(0,8)):
   ang=bits(angle);routed=True;child_angle=ang
   p,b,q=addresses(Case(alias=1))
   if n==25:routed=abs(angle)<35.;child_angle=bits(5. if angle<=0. else -5.)
   if n==7:b=p-0x54
   c=Case(pattern,1,mode,phase,p,b,q,child_angle);initial=fixture(c);put(initial,STACK+phase+0x28,b);put(initial,STACK+phase+0x6C,0x12345678);want,calls,obs=reference(initial,c)if routed else(dict(initial),[],[]);ms=[]
   for target in ws:
    m=Oracle(window,initial,c,entry=start,connected={ENTRY+4*i:w for i,w in enumerate(target)},arguments=(p,b,ang,q));m.r[17]=p;m.r[16]=p-0x2F8;m.f[0]=ang;m.f[2]=ang;m.f[4]=bits(2.5)if n==7 else ang;m.f[16]=bits(angle*2.5);m.window_end=start+n*4;m.code=WindowCode(dict(m.code),m)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller window boundary')
    assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),(hex(start),c,m.calls,calls)
    if routed:assert m.callbacks==[(p,b,child_angle,q)],m.callbacks
    ms.append(m)
   assert all(state(m)==state(ms[0])for m in ms[1:]);count+=1
  counts.append(dict(parent=parent,start=hex(start),words=n,cases=count));parents.append(parent)
 # Two additional real call pairs live in a legacy nonmatchings owner;
 # a text-only top-level asm search misses them. Qualify their point/pivot
 # exchange, saved argument lifetimes and two successive in-place rotations.
 pair_counts=[]
 for start,offset,n in[(0x15125804,0x152CB4,19),(0x151258D8,0x152D88,13)]:
  window=list(struct.unpack_from('>%dI'%n,rom,offset));asm=(r/'conker/asm/nonmatchings/game_14FF90/func_151256BC.s').read_text();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};assert window==[literal[start+4*i]for i in range(n)];count=0
  for pattern,mode,angle,phase in itertools.product((0,3,7),(0,7,15),(-90.,-5.,-0.,0.,5.,34.,35.,90.),(0,8)):
   p=0x30020;b=p-0x3C;c=Case(pattern,1,mode,phase,p,b,p,bits(angle));initial=fixture(c);want,call1,obs1=reference(initial,c);second=Case(pattern,1,mode,phase,b,p,b,fp(bits(angle),bits(20.),'mul'));want,call2,obs2=reference(want,second,call_base=4);ms=[]
   for target in ws:
    m=Oracle(window,initial,c,entry=start,connected={ENTRY+4*i:w for i,w in enumerate(target)},arguments=(p,b,degree(c),p));m.r[16]=p-0x2F8;m.r[17]=p;m.r[18]=b;m.f[0]=bits(1.);m.f[2]=bits(20.);m.f[12]=degree(c);m.window_end=start+n*4;m.code=WindowCode(dict(m.code),m)
    # The second call changes the public point/pivot identity. Keep helper
    # observations/effects bound to the actual current target arguments.
    original_record=m.record_call
    def record(target,model=m,callback=original_record):
     if target==ENTRY:
      aa=tuple(model.arguments(4));model.c=Case(pattern,1,mode,phase,aa[0],aa[1],aa[3],aa[2])
     return callback(target)
    m.record_call=record
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing paired caller boundary')
    assert(public(m.memory),m.calls,m.observations)==(public(want),call1+call2,obs1+obs2),(hex(start),c,m.calls,call1+call2)
    assert m.callbacks==[(p,b,degree(c),p),(b,p,degree(second),b)];ms.append(m)
   assert all(state(m)==state(ms[0])for m in ms[1:]);count+=1
  pair_counts.append(dict(parent='func_151256BC',start=hex(start),words=n,cases=count,target_calls=2))
 for parent,source in[('func_1512AD54','conker/src/game/generated_157840.c'),('func_1512C20C','conker/src/game/generated_157840.c'),('func_1512D390','conker/src/game/generated_15A840.c')]:assert 's32 '+parent+'() {\n    return 0;\n}'in(r/source).read_text()
 assert 's32 func_151256BC(s32 arg0) {\n    return 0;\n}'in(r/'conker/src/game_14FF90.c').read_text()
 return dict(aligned_JALs=8,function_pointer_literals=0,windows=counts,paired_windows=pair_counts,total_cases=sum(x['cases']for x in counts+pair_counts),original_callers_only=True,gate_and_signed_clamp_connected=True,point_pivot_swap_connected=True,current_C_parents_still_stubs=True,whole_parent_acceptance=False)

def native_source(body):
 text='#include <ultra64.h>\n'+body.replace('#include <ultra64.h>\n','').replace('void '+F+'(', '__attribute__((noinline,noclone)) void selected(')
 for name,bad in controls(body).items():text+='\n'+bad.replace('#include <ultra64.h>\n','').replace('void '+F+'(', '__attribute__((noinline,noclone)) void '+name+'(')
 text+=r'''
typedef char FloatWidth[(sizeof(f32)==4)?1:-1];
typedef char PointerWidth[(sizeof(void*)==4)?1:-1];
typedef union { f32 f; u32 u; } FloatWord;
static u32 values[]={0,0x80000000,0x3F800000,0xBF800000,0x3E800000,0xC0200000,0x42B40000,0xC3340000,1,0x80000001,0x007FFFFF,0x00800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0xFFC54321,0x7F810001};
static f32 arena[160], expected[160];
f32 D_8009DC80;
static u32 pattern,mode,ordinal,failed,po,bo,qo,expectedFactor;
static u32 observations[4][10],calls[4][2];
static f32 from(u32 w){FloatWord a;a.u=w;return a.f;}
static u32 word(f32 f){FloatWord a;a.f=f;return a.u;}
static u32 canonical(u32 w){return (w&0x7FFFFFFF)>0x7F800000 ? 0x7FC00000:w;}
static f32 add(f32 a,f32 b){volatile f32 c=a+b;return c;}
static f32 sub(f32 a,f32 b){volatile f32 c=a-b;return c;}
static f32 mul(f32 a,f32 b){volatile f32 c=a*b;return c;}
static void effect(f32 *a,u32 n,f32 *factor){
 if(mode&1)a[po+((n&1)?0:2)]=from(values[(n+pattern+7)%19]);
 if(mode&2)a[bo+((n&1)?2:0)]=from(values[(n+pattern+10)%19]);
 if(mode&4)*factor=from(values[(n+pattern+4)%19]);
 if(mode&8)a[qo+1]=from(0x55000000+n);
}
static void snapshot(f32 *a,f32 factor,u32 *out){u32 i;for(i=0;i<3;i++){out[i]=word(a[po+i]);out[i+3]=word(a[bo+i]);out[i+6]=word(a[qo+i]);}out[9]=word(factor);}
static f32 give(u32 target,f32 radians){u32 i,s[10];if(ordinal>=4){failed=1;return 0;}
 if(calls[ordinal][0]!=target||canonical(calls[ordinal][1])!=canonical(word(radians)))failed=1;
 snapshot(arena,D_8009DC80,s);for(i=0;i<10;i++)if(canonical(s[i])!=canonical(observations[ordinal][i]))failed=1;
 effect(arena,ordinal,&D_8009DC80);return from(values[(pattern+ordinal++*3+2)%19]);}
__attribute__((noinline,noclone)) f32 cosf(f32 radians){return give(0,radians);}
__attribute__((noinline,noclone)) f32 sinf(f32 radians){return give(1,radians);}
static void reference(f32 angle){f32 dx,dz,radians,co,si,x=0,z,cx,sx,nx,cz,factor=from(0x3C8EFA35);u32 n;
 dx=sub(expected[po],expected[bo]);radians=mul(angle,factor);dz=sub(expected[po+2],expected[bo+2]);
 for(n=0;n<4;n++){
  calls[n][0]=(n==0||n==3)?0:1;calls[n][1]=word(radians);snapshot(expected,factor,observations[n]);effect(expected,n,&factor);
  if(n==1){co=from(values[(pattern+2)%19]);si=from(values[(pattern+5)%19]);cx=mul(co,dx);sx=mul(si,dz);x=add(add(sx,cx),expected[bo]);}
 }
 si=from(values[(pattern+8)%19]);co=from(values[(pattern+11)%19]);nx=mul(from(word(si)^0x80000000),dx);cz=mul(co,dz);z=add(add(cz,nx),expected[bo+2]);expected[qo]=x;expected[qo+2]=z;expectedFactor=word(factor);
}
typedef void(*Rotation)(f32*,f32*,f32,f32*);
static int check(Rotation fn,int good){u32 alias,i,j;f32 angle;
 for(pattern=0;pattern<64;pattern++)for(alias=0;alias<8;alias++)for(mode=0;mode<16;mode++){
  po=8;bo=72;qo=136;if(alias==1)qo=po;if(alias==2)qo=bo;if(alias==3)bo=po;if(alias==4)bo=qo=po;if(alias==5)qo=po+1;if(alias==6){bo=po+1;qo=po+2;}if(alias==7)qo=bo-1;
  for(i=0;i<160;i++)arena[i]=from(0x3F000000+i*97);
  for(j=0;j<6;j++){i=(j<3?po+j:bo+j-3);arena[i]=from(values[(pattern*(2*j+1)+j+2)%19]);}
  for(i=0;i<160;i++){expected[i]=arena[i];}angle=from(values[(pattern*5+6)%19]);reference(angle);
  D_8009DC80=from(0x3C8EFA35);ordinal=failed=0;fn(arena+po,arena+bo,angle,arena+qo);
  for(i=0;i<160;i++)if(canonical(word(arena[i]))!=canonical(word(expected[i])))failed=1;
  if(ordinal!=4||canonical(word(D_8009DC80))!=canonical(expectedFactor)){failed=1;}if(failed){if(good)return 0;return 1;}
 }
 return good;
}
int run(void){f32(*co)(f32)=cosf;f32(*si)(f32)=sinf;if(!co||!si)return 97;if(!check(selected,1))return 1;
'''
 for i,name in enumerate(controls(body),2):text+='if(!check('+name+',0))return '+str(i)+';\n'
 return text+'return 0;}\n'+START
def native_suite():
 body=(o/'selected-semantic-input.c').read_text();profiles={}
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_source(body));binary=p.with_suffix('');flags=[f for f in native_command(opt)if not f.startswith('-Wno-')];q=subprocess.run(flags+['-mstackrealign','-fno-builtin',str(p),'-o',str(binary)],cwd=r,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr;z=subprocess.run([str(binary)],timeout=60);assert z.returncode==0,(opt,z.returncode);profiles[opt]=dict(exit=0,UBSan=True,cases=8192)
 return dict(cases_per_profile=8192,SDK_float_and_pointer_assertions=True,typed_trig_ABI=True,pre_provider_observations=True,negative_controls=14,finite_inf_signed_zero_and_nan_cases=True,native_nan_payloads_canonicalized=True,all_valid_array_aliases=True,warning_suppressions=0,profiles=profiles)


def opening(words,bindings):
 regs={i:('R',i)for i in range(32)};fp={i:('F',i)for i in range(32)};trace=[];operations=[]
 def signed(n):return n-65536 if n&32768 else n
 def address(at,rs,imm):
  rel=bindings.get(at,[])
  if rel:
   assert len(rel)==1 and rel[0]==('R_MIPS_LO16','D_8009DC80');return('symbol','D_8009DC80')
  return('address',regs[rs],signed(imm))
 for at in range(0,76,4):
  w=words[at//4];op,rs,rt,rd,fn,imm=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,w&63,w&65535
  if op==9:
   regs[rt]=('add',regs[rs],signed(imm))
  elif op==15:
   assert bindings.get(at)==[('R_MIPS_HI16','D_8009DC80')];regs[rt]=('hi','D_8009DC80')
  elif op==17:
   if rs==4:fp[rd]=regs[rt]
   else:
    assert rs==16;ft,fs,fd=rt,rd,(w>>6)&31
    if fn in(1,2):
     value=('sub'if fn==1 else'mul',fp[fs],fp[ft]);fp[fd]=value;operations.append(value)
    elif fn==6:fp[fd]=fp[fs]
    else:raise AssertionError(hex(w))
  elif op in(49,57,43,61):
   addr=address(at,rs,imm)
   if op==49:fp[rt]=('read',addr);trace.append(('read',4,addr))
   elif op==57:trace.append(('write',4,addr,fp[rt]))
   elif op==43:trace.append(('write',4,addr,regs[rt]))
   else:trace.append(('write',8,addr,fp[rt],fp[rt+1]))
  elif op==3:
   assert at==68 and bindings.get(at)==[('R_MIPS_26','cosf')]
   # This audit includes its delay slot; provider execution is a later gate.
   regs[31]=('return',76)
  else:raise AssertionError((at,hex(w)))
 return regs,fp,trace,operations

def guard_suite():
 import csv,io,sys
 import tools.pad_generated_object as _pad
 sys.modules.setdefault('pad_generated_object',_pad)
 from tools.pad_c_object import emit_padded_assembly
 guards=json.loads((o/'new-guard-rows.json').read_text());before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();assert len(guards)==8
 def write(rows,name):
  stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=tuple(guards[0]),lineterminator='\n').writerows(rows);p=o/name;p.write_bytes(before+stream.getvalue().encode());return p
 count=0
 for i,row in enumerate(guards):
  rows=[dict(x)for x in guards];rows[i]['expected']='0x%08X'%(int(row['expected'],16)^1);p=write(rows,'negative-guard-'+str(i)+'.csv')
  try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_BC430',word_patches_path=p)
  except ValueError:count+=1
  else:raise AssertionError(('Accepted guard preimage',i))
 for i in (0,1):
  rows=[dict(x)for x in guards];rows[i]['expected_relocations']='R_MIPS_LO16:func_1508EF80';p=write(rows,'negative-binding-'+str(i)+'.csv')
  try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_BC430',word_patches_path=p)
  except ValueError:count+=1
  else:raise AssertionError(('Accepted guard binding',i))
 rows=[dict(x)for x in guards];rows[0]['function']='foreign';p=write(rows,'negative-function.csv')
 try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_BC430',word_patches_path=p)
 except ValueError:count+=1
 else:raise AssertionError('Accepted foreign function')
 assert emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_BC430',word_patches_path=o/'proposed-guards.csv')==(o/'qualified-padded.s').read_text()
 raw,rr=payload(o/'selected-final.o',F);truth,tr=payload(o/('original-'+F+'.o'),F);a=list(struct.unpack('>55I',raw));b=list(struct.unpack('>55I',truth));x,y=opening(a,rr),opening(b,tr);assert x[0]==y[0]and x[2:]==y[2:]
 different=[i for i in range(32)if x[1][i]!=y[1][i]];assert different==[4,10,16,18];pending=set(different);overwrites={}
 for at in range(76,220,4):
  w=a[at//4];op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;reads=[];writes=[]
  if op==17:
   if rs==16:reads=[rd]+([rt]if fn in(0,1,2,3)else[]);writes=[w>>6&31]
   elif rs==4:writes=[rd]
  elif op==49:writes=[rt]
  elif op==57:reads=[rt]
  elif op==53:writes=[rt,rt+1]
  assert not pending&set(reads),(at,pending,reads)
  for f in pending&set(writes):overwrites[f]=at
  pending-=set(writes)
 assert not pending
 mutations={32:3,36:1<<16,40:4,44:3,48:8,52:8,60:1<<11,72:4};negatives=0
 for at,mask in mutations.items():
  altered=list(b);altered[at//4]^=mask;z=opening(altered,tr);assert z[0]!=y[0]or z[2:]!=y[2:],at;negatives+=1
 return dict(guards=8,actual_padder_rejections=count,word_preimage_rejections=8,relocation_rejections=2,function_scope_rejections=1,closed_opening=[0,76],ordered_memory_trace_equal=True,ordered_FP_expression_sequence_equal=True,all_GPR_expressions_equal=True,differing_volatile_FP_registers=different,differing_values_overwritten_before_read=overwrites,opening_semantic_controls=negatives,FP_commutation_or_reassociation_used=False,insertions=0,omissions=0,inherited_prefix_preserved=True)
