"""Plane-response gates, live callback reloads, packets and bounded FP semantics."""
from dataclasses import dataclass,replace
import itertools,math,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_sine_effect_updater_150f7e20_oracle import mul,add,sub
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY,BOUNDS,HEIGHT,CALLBACK=0x151319C4,0x1514672C,0x15046C80,0x15131B7C
CLASSIFY,DELEGATE=0x15047004,0x1504697C
CB1,CB2=0x17018000,0x17028000
RECORD,PLANE,RESPONSE,ALTPLANE,ALTRESPONSE,MARK=0x30000,0x60000,0x50000,0x61000,0x51000,0x70000
u32=lambda n:n&0xFFFFFFFF
signed8=lambda n:(n^128)-128
@dataclass(frozen=True)
class Case:
 flags:int=1
 index:int=0
 y:int=0x40800000
 plane_y:int=0x41000000
 extent:int=0x40000000
 x:int=0x3FA00000
 z:int=0xC0600000
 bounded:int=1
 hit:int=1
 reply:int=0x1234ABCD
 mode:int=0
 home_mode:int=0
 phase:int=0
 seed:int=0
 alias:int=0
 null:int=0
 vy:int=0xC0C00000
 damping:int=0x3F000000
def symbols(i=0,c=Case()):
 table,scale,bounds,height=((0x80089874,0x800A3844,BOUNDS,HEIGHT),(0x80027FFC,0x80038004,0x1701FFFC,0x17118000),(0x9000FFF0,0x90018000,0x1E17FFFC,0x1E288000))[i]
 scale={1:RECORD+0x44,2:RECORD+0x3C,3:RECORD+0x80}.get(c.alias,scale)
 return dict(D_80089874=table,D_800A3844=scale,func_1514672C=bounds,func_15046C80=height)
def fixture(c=Case(),s=None):
 s=symbols(c=c)if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
 for p,n in((RECORD-32,0x200),(PLANE,64),(ALTPLANE,64),(RESPONSE,32),(ALTRESPONSE,32),(MARK,32)):
  m.update({p+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for index in range(-128,128):put(m,u32(s['D_80089874']+4*index),CALLBACK if index==c.index and not c.null else 0)
 for off,w in((0x3C,c.extent),(0x40,c.x),(0x44,c.y),(0x48,c.z),(0x58,bits(2.)),(0x5C,c.vy),(0x60,bits(3.)),(0x64,bits(-0.5)),(0x68,0x87654327),(0x80,bits(7.))):put(m,RECORD+off,w)
 for p in(PLANE,ALTPLANE):put(m,p+4,c.plane_y if p==PLANE else bits(30.))
 for p in(RESPONSE,ALTRESPONSE):m[p]=c.flags;m[p+1]=c.index&255;put(m,p+4,c.damping)
 put(m,s['D_800A3844'],0x3D75C290)
 for p,w in((0x800A56C4,0x46985800),(0x800A56C8,0xC6147000),(0x800A3848,0x3D75C290),(0x800A384C,0x3FFF9DB3)):put(m,p,w)
 return m
def homes(m,sp):
 for i in range(4):put(m,sp+4*i,0xB5000000+i)
def packet(m,p):return tuple(read(m,p+4*i)for i in range(3))
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def effect(m,c,s,stage,home,record=RECORD):
 sp=home-64;point=sp+48
 if stage==1:
  for i in range(36):m[record+0x80+i]=(i*7+0x35)&255
  put(m,record+0x80,bits(5.25))
 if c.mode&(1<<stage):
  if stage==0:
   put(m,record+0x3C,bits(3.5));put(m,record+0x44,bits(6.));put(m,point,bits(12.25));put(m,point+8,bits(-7.5));put(m,s['D_800A3844'],bits(0.125))
   m[RESPONSE+1]=1;put(m,s['D_80089874']+4,CB1)
  elif stage==1:
   put(m,record+0x80,bits(4.25));put(m,point,bits(-2.5));put(m,point+8,bits(9.75))
   m[read(m,sp+72)+1]=2;put(m,s['D_80089874']+8,CB2)
  else:
   put(m,record+0x44,bits(99.));m[read(m,sp+72)]^=0x80;put(m,sp+40,bits(-42.))
  put(m,MARK+4*stage,0xA1700000+stage)
 if stage==0:
  if c.home_mode&1:put(m,sp+68,ALTPLANE)
  if c.home_mode&2:put(m,sp+72,ALTRESPONSE);put(m,s['D_80089874']+4,CB1);m[ALTRESPONSE+1]=1
 if stage in(0,1)and c.home_mode&4:m[sp+63]=0xA3+stage
def reference(initial,c=Case(),s=None,home=None,arguments=(RECORD,PLANE,RESPONSE),saved=0,ra=0xDEAD0000,real_bounds=False):
 s=symbols(c=c)if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;sp=home-64;record,plane,response=arguments
 put(m,sp+24,saved);put(m,sp+28,ra);calls=[];result=1
 if not m[response]&1:return m,calls,result
 index=signed8(m[response+1])
 if index==-1 or not read(m,u32(s['D_80089874']+index*4)):return m,calls,result
 if not floating(read(m,record+0x44))<floating(read(m,plane+4)):return m,calls,result
 for off,word in((48,read(m,record+0x40)),(52,read(m,plane+4)),(56,read(m,record+0x48))):put(m,sp+off,word)
 put(m,sp+72,response);put(m,sp+68,plane);m[sp+63]=result
 calls.append((s['func_1514672C'],(sp+48,),packet(m,sp+48)))
 if real_bounds:
  x,y,z=map(floating,packet(m,sp+48));ok=not(abs(x)>19500. or abs(z)>19500. or y>19500. or y<-9500.)
 else:effect(m,c,s,0,home,record);homes(m,sp);ok=c.bounded
 result=m[sp+63]
 if not ok:return m,calls,0
 m[sp+63]=result;threshold=sub(read(m,record+0x44),mul(read(m,record+0x3C),read(m,s['D_800A3844'])))
 calls.append((s['func_15046C80'],(sp+48,0,threshold,record+0x80),packet(m,sp+48)))
 effect(m,c,s,1,home,record);homes(m,sp);result=m[sp+63]
 if c.hit:
  response=read(m,sp+72);put(m,sp+36,read(m,sp+48));put(m,sp+44,read(m,sp+56));put(m,sp+40,read(m,record+0x80))
  target=read(m,u32(s['D_80089874']+4*signed8(m[response+1])));a=(record,read(m,sp+68),sp+36,response)
  calls.append((target,a,packet(m,sp+36)));effect(m,c,s,2,home,record);homes(m,sp);result=c.reply&255
 return m,calls,result
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None):
  super().__init__(words,memory,c,entry=entry,s=symbols(c=c)if s is None else s,connected=connected,arguments=(RECORD,PLANE,RESPONSE)if arguments is None else arguments)
  self.target_record=RECORD;self.target_arguments=(RECORD,PLANE,RESPONSE);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(5,7):self.f[w>>6&31]=self.f[w>>11&31]&(0x7FFFFFFF)if w&63==5 else self.f[w>>11&31]^0x80000000;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:
   self.target_home=self.r[29];self.target_arguments=tuple(map(u32,self.arguments(3)));self.target_record=self.r[4];args=self.target_arguments;data=()
  else:
   counts={self.syms['func_1514672C']:1,self.syms['func_15046C80']:4,CALLBACK:4,CB1:4,CB2:4,CLASSIFY:3,DELEGATE:4,0x15131958:2,0x15131918:2}
   assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));p=args[2]if t in(CALLBACK,CB1,CB2)else args[0];data=packet(self.memory,p)if t not in(0x15131958,0x15131918)else()
  self.calls.append((t,args,data));self.events.append(('CALL',t,args,data))
 def hook(self,t):
  if t in(self.syms['func_1514672C'],self.syms['func_15046C80'],CALLBACK,CB1,CB2):
   stage=0 if t==self.syms['func_1514672C']else 1 if t==self.syms['func_15046C80']else 2
   effect(self.memory,self.case,self.syms,stage,self.target_home,self.target_record);value=(self.case.bounded,self.case.hit,self.case.reply)[stage]
  else:raise AssertionError(('Provider not selected',hex(t)))
  homes(self.memory,self.r[29])
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(value);self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def original_object(core,q,out):
 text=(out/'frozen/conker/asm/15D730.s').read_text();body=re.search(r'^glabel func_151319C4\n.*?(?=^glabel |\Z)',text,re.M|re.S).group();p=out/'original-reference.s'
 p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+body+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True);q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s):
 values=[list(core.bound_blob(q[n],q[r],s))for n,r in(('original','original_refs'),('raw','refs'),('normal','normal_refs'))]
 assert values[0]==values[2]and sum(a!=b for a,b in zip(values[0],values[1]))==8;return values
def verify(m,initial,c,s,real_bounds=False):
 wanted,calls,result=reference(initial,c,s,saved=m.before[16],real_bounds=real_bounds)
 assert(m.memory,m.calls,m.r[2])==(wanted,calls,result),(c,[(hex(a),m.memory.get(a),v)for a,v in wanted.items()if m.memory.get(a)!=v][:8],m.calls,calls,m.r[2],result)
 assert m.f[20:]==m.before_f[20:]
def cases():
 rows=[Case(flags=f,index=i,y=y,bounded=b,hit=h,reply=r,mode=m,phase=p)for f,i,y,b,h,r,m,p in itertools.product((0,1,2,3,255),(-128,-2,-1,0,1,127),(bits(4.),bits(8.),bits(9.),0x7FC12345),(0,1),(0,1),(0,0x1234ABCD),(0,3),(0,))]
 rows +=[Case(home_mode=h,mode=m,phase=p)for h,m,p in itertools.product(range(8),range(8),(0,8))]
 rows +=[Case(null=1),Case(plane_y=0x7FC12345),Case(y=0x80000000,plane_y=0),Case(y=bits(-1.),plane_y=0x80000000)]
 rows +=[Case(reply=r,mode=m)for r,m in itertools.product((0,1,255,256,0xFFFFFFFF,0x80000000),range(8))]
 return rows
def guest(core,q):
 original_object(core,q,core.ROOT/core.BUILD);rows=[(c,symbols(c=c),ENTRY)for c in cases()];seen=set()
 rows +=[(Case(mode=m,home_mode=h),symbols(i),0x17508000 if i==1 else 0x1F007FFC)for i,m,h in itertools.product((1,2),(0,1,2,7),(0,3,7))]
 for c,s,entry in rows:
  initial=fixture(c,s);models=[Oracle(w,initial,c,entry=entry,s=s).run()for w in programs(core,q,s)]
  for m in models:verify(m,initial,c,s)
  assert literal(models[0])==literal(models[2]);assert all((public(m.memory),m.calls,m.r[2])==(public(models[0].memory),models[0].calls,models[0].r[2])for m in models)
  seen.update(pc-entry for pc in models[0].visits)
 assert seen==set(range(0,312,4)),sorted(set(range(0,312,4))-seen)
 aliases=0
 for c in(Case(alias=a,mode=m,home_mode=h)for a,m,h in itertools.product((1,2,3),(0,3,7),(0,3,7))):
  s=symbols(c=c);initial=fixture(c,s);models=[Oracle(w,initial,c,s=s).run()for w in programs(core,q,s)]
  for m in models:verify(m,initial,c,s)
  assert literal(models[0])==literal(models[2]);aliases+=1
 cuts=0
 for c in(Case(flags=0),Case(index=-1),Case(null=1),Case(y=0x7FC12345),Case(bounded=0),Case(hit=0,home_mode=4),Case(mode=7,home_mode=7),Case(alias=3,mode=3)):
  s=symbols(c=c);initial=fixture(c,s);ps=programs(core,q,s);full=Oracle(ps[0],initial,c,s=s).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in(ps[0],ps[2]):
    m=Oracle(w,initial,c,s=s);m.cut=cut
    try:m.run();raise AssertionError('Unfired plane callback access cut')
    except AccessBoundary:pass
    models.append(m)
   assert literal(models[0])==literal(models[1]);cuts+=1
 return dict(cases=len(rows),reached_words=78,alias_cases=aliases,fault_prefix_cuts=cuts,independent_complete_memory=True,
  original_normalized_literal_state=True,raw_public_semantics_under_valid_record_frame_disjointness=True,
  raw_scratch_and_private_fault_identity_not_claimed=True,signed_descriptor_index_guest_full_byte_domain=True,
  helper_global_point_home_and_result_mutation_probes=True,complete_hardware_FCSR_not_claimed=True)

def bounce(memory,record,response,contact):
 m=dict(memory);put(m,record+0x44,add(read(m,contact+4),mul(read(m,record+0x3C),read(m,0x800A3848))))
 for off,negative in((0x58,False),(0x5C,True),(0x60,False)):
  damping=read(m,response+4)^(0x80000000 if negative else 0);put(m,record+off,mul(read(m,record+off),damping))
 if abs(floating(read(m,record+0x5C)))<floating(read(m,0x800A384C)):
  for off in(0x58,0x5C,0x60,0x64):put(m,record+off,0)
  m[response]&=254;put(m,record+0x68,read(m,record+0x68)&0xFFFFFFF9)
 return m
class ConnectedOracle(Oracle):
 def __init__(self,*a,query=0,**kw):super().__init__(*a,**kw);self.query=query
 def hook(self,t):
  if t not in(CLASSIFY,DELEGATE,0x15131958,0x15131918):return super().hook(t)
  if t in(CLASSIFY,DELEGATE):
   effect(self.memory,self.case,self.syms,1,self.target_home,self.target_record);value=self.query if t==CLASSIFY else self.case.hit
  else:
   point,factor=self.calls[-1][1]
   for i in((0,1,2)if t==0x15131958 else(0,2)):put(self.memory,point+4*i,mul(read(self.memory,point+4*i),factor))
   value=0xDEADBEEF
  homes(self.memory,self.r[29])
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.r[2]=u32(value);self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def connections(core,q):
 rom=(core.ROOT/'conker/conker.us.bin').read_bytes();code={};helpers=((BOUNDS,0x173BDC,30),(HEIGHT,0x74130,32),(CALLBACK,0x15F02C,44));seen=set();count=0
 for entry,offset,n in helpers:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
 rows=[Case(vy=bits(v),damping=bits(d),hit=h,reply=1)for v,d,h in itertools.product((-6.,-3.994000196456909,-1.,-0.,0.,1.,3.994000196456909,6.),(0.,0.25,0.5,1.),(0,1))]
 rows +=[Case(x=bits(v),reply=1)for v in(-19500.1,-19500.,0.,19500.,19500.1)]
 rows +=[Case(z=bits(v),reply=1)for v in(-19500.1,-19500.,0.,19500.,19500.1)]
 rows +=[Case(y=bits(-20000.),plane_y=bits(v),reply=1)for v in(-9501.,-9500.,0.,19500.,19501.)]
 for c,query in itertools.product(rows,(0,1,2)):
  # Wrapper classifier outcomes 1/2 are fixed miss/hit. Outcome0 delegates.
  c=replace(c,hit=c.hit if query==0 else int(query==2));s=symbols();initial=fixture(c);models=[]
  for w in programs(core,q,s):
   m=ConnectedOracle(w,initial,c,connected=code,query=query).run();models.append(m);seen.update(m.visits)
   wanted,calls,result=reference(initial,c,s,saved=m.before[16],real_bounds=True)
   if calls and calls[-1][0]==CALLBACK:wanted=bounce(wanted,RECORD,RESPONSE,calls[-1][1][2])
   actual=[row for row in m.calls if row[0]in(BOUNDS,HEIGHT,CALLBACK)]
   assert(public(m.memory),actual,m.r[2])==(public(wanted),calls,result),(c,query,m.calls,calls)
  assert literal(models[0])==literal(models[2]);count+=1
 for entry,offset,n in helpers:
  wanted=set(range(entry,entry+4*n,4))
  if entry==HEIGHT:wanted-={HEIGHT+off for off in(68,72,108)}
  assert wanted<=seen,(hex(entry),sorted(wanted-seen))
 caller_rows=((0x151319A4,0x15EE54,8,0xA8,0,0x151319B4),(0x15131AFC,0x15EFAC,16,0xB0,0x15131958,0x15131B2C),(0x15131B3C,0x15EFEC,16,0xB0,0x15131918,0x15131B6C));cc=0
 for entry,offset,n,desc_off,scale,ret in caller_rows:
  body=struct.unpack_from('>%dI'%n,rom,offset)
  for c in(Case(flags=f,index=i,bounded=b,hit=h,reply=r,phase=p)for f,i,b,h,r,p in itertools.product((0,1,255),(-1,0),(0,1),(0,1),(0,0x1234ABCD),(0,8))):
   s=symbols();initial=fixture(c);home=STACK+c.phase;response=RECORD+desc_off
   initial[response]=c.flags;initial[response+1]=c.index&255;put(initial,response+4,c.damping)
   if scale:put(initial,RECORD+0xA8,bits(0.5))
   models=[]
   for w in programs(core,q,s):
    target=dict(zip(range(ENTRY,ENTRY+312,4),w));m=ConnectedOracle(body,initial,c,entry=entry,connected=target,arguments=(RECORD,PLANE)).run();models.append(m)
    before=dict(initial);put(before,home-4,0xDEAD0000);expected=[]
    if scale:
     put(before,home,RECORD);put(before,home+4,PLANE);factor=read(before,RECORD+0xA8)
     expected.append((scale,(RECORD+0x58,factor),()))
     for i in((0,1,2)if scale==0x15131958 else(0,2)):put(before,RECORD+0x58+4*i,mul(read(before,RECORD+0x58+4*i),factor))
     homes(before,home-24)
    wanted,calls,result=reference(before,c,s,home=home-24,arguments=(RECORD,PLANE,response),saved=m.before[16],ra=ret)
    expected +=[(ENTRY,(RECORD,PLANE,response),()),*calls]
    assert(m.memory,m.calls,m.r[2])==(wanted,expected,result),(hex(entry),c,m.calls,expected)
   assert literal(models[0])==literal(models[2]);cc+=1
 return dict(original_bounds_words=30,original_height_wrapper_words=32,original_bounce_callback_words=44,connected_real_helper_cases=count,
  all_helper_words_reachable_under_classifier_012=True,height_wrapper_unreached_offsets=[68,72,108],height_wrapper_classifier_domain=[0,1,2],real_table_has_one_callback=True,
  complete_original_callers=3,caller_words=[8,16,16],caller_cases=cc,caller_results_ignored=True,caller_scale_providers_bounded=True,
  height_classifier_and_delegate_are_bounded_providers=True,complete_terrain_or_hardware_not_claimed=True)

_native=None
def native_rows():
 global _native
 if _native is not None:return _native
 rows=[]
 for c in(c for c in cases()if not(c.phase or c.home_mode or c.alias)and c.index>=-1):
  initial=fixture(c);wanted,calls,result=reference(initial,c);record=bytearray(wanted[RECORD-32+i]for i in range(512));plane=bytearray(wanted[PLANE+i]for i in range(64));response=bytearray(wanted[RESPONSE+i]for i in range(32))
  for off in(0x3C,0x40,0x44,0x48,0x58,0x5C,0x60,0x64,0x68,0x80):record[32+off:36+off]=read(wanted,RECORD+off).to_bytes(4,'little')
  plane[4:8]=read(wanted,PLANE+4).to_bytes(4,'little');response[4:8]=read(wanted,RESPONSE+4).to_bytes(4,'little')
  args=[]
  for stage in range(3):
   if stage<len(calls):args.extend((*calls[stage][2],calls[stage][1][2]if stage==1 else 0))
   else:args.extend((0,0,0,0))
  callback={CALLBACK:0,CB1:1,CB2:2}.get(calls[-1][0],0)if calls else 0
  numeric=(c.x,c.y,c.z,c.plane_y,c.extent,c.vy,c.damping,c.flags,u32(c.index),c.null,c.bounded,c.hit,c.reply,c.mode,c.seed,result,len(calls),callback,read(wanted,symbols()['D_800A3844']))
  arrays=[record,plane,response,args,[read(wanted,MARK+4*i)for i in range(3)],[read(initial,MARK+4*i)for i in range(3)]]
  rows.append('{'+','.join('0x%Xu'%v for v in numeric)+','+','.join('{'+','.join('0x%X'%v for v in a)+'}'for a in arrays)+'}')
 _native=(',\n'.join(rows),len(rows));return _native
def controls(core):
 s=core.SELECTED;changes={
  'wrong_flag_mask':('response->flags & 1','response->flags & 2'),
  'wrong_disabled_index':('response->kind != -1','response->kind != 0'),
  'wrong_height_gate':('record->position[1] < ((f32 *)surface)[1]','record->position[1] > ((f32 *)surface)[1]'),
  'wrong_plane_component':('((f32 *)surface)[1]','((f32 *)surface)[0]'),
  'wrong_point_z':('point[2] = record->position[2]','point[2] = record->position[0]'),
  'wrong_rejected_return':('                return 0;','                return 1;'),
  'wrong_query_selector':('func_15046C80(point, 0,','func_15046C80(point, 1,'),
  'wrong_threshold_sign':('record->position[1] - record->extent','record->position[1] + record->extent'),
  'wrong_threshold_scale':('record->extent * D_800A3844','record->extent * 1.0f'),
  'wrong_contact_height':('((HeightResult71820 *)((u8 *)record + 0x80))->height','point[1]'),
  'unmasked_callback_return':('u8 result = 1','u32 result = 1'),
  'wrong_default_return':('u8 result = 1','u8 result = 2'),
  'cached_callback':('    u8 result = 1;','    s32 (*cached)(BounceRecord15D730 *, void *, f32 *, BounceResponse15D730 *) = NULL;\n    u8 result = 1;'),
  'stub':('    u8 result = 1;','    return 0;\n    u8 result = 1;')}
 assert all(a in s for a,b in changes.values());bad={n:s.replace(a,b)for n,(a,b)in changes.items()}
 bad['cached_callback']=bad['cached_callback'].replace('            point[0] =','            cached = D_80089874[response->kind];\n            point[0] =').replace('result = D_80089874[response->kind](', 'result = cached(')
 return bad
def native_text(core):
 rows,n=native_rows();code=core.ISOLATED_HEADER+'\n'+'\n'.join(body.replace('func_151319C4','test_'+name)for name,body in {'selected':core.SELECTED,**controls(core)}.items())
 code+=r'''
typedef struct{BounceRecord15D730 record;u8 pad6C[0x14];HeightResult71820 height;u8 tail[0x200-32-0xA4];}Body;
typedef struct{u8 before[32];Body data;}Object;
typedef struct{BounceResponse15D730 item;u8 tail[24];}Response;
typedef char Layout[(sizeof(void*)==4&&sizeof(Object)==512&&sizeof(Response)==32&&sizeof(HeightResult71820)==0x24&&__builtin_offsetof(Body,height)==0x80)?1:-1];
typedef struct{u32 x,y,z,planeY,extent,vy,damping,flags,index,null,bounded,hit,reply,mode,seed,result,calls,callback,scale;u8 record[512],plane[64],response[32];u32 args[12],markers[3],initialMarkers[3];}Case;
static const Case cases[]={
__ROWS__
};
typedef s32(*Callback)(BounceRecord15D730*,void*,f32*,BounceResponse15D730*);
Callback D_80089874[128];f32 D_800A3844;
static Object object;static Response response;static f32 plane[16];static u32 markers[3];static unsigned calls,error;static const Case*c;
static void bytes(void*d,const void*s,unsigned n){u8*p=d;const u8*q=s;unsigned i;for(i=0;i<n;i++)p[i]=q[i];}
static f32 number(u32 w){f32 f;bytes(&f,&w,4);return f;}
static u32 word(f32 f){u32 w;bytes(&w,&f,4);return w;}
static int equal(const void*a,const void*b,unsigned n){const u8*p=a,*q=b;unsigned i;for(i=0;i<n;i++)if(p[i]!=q[i])return 0;return 1;}
static void packet(unsigned stage,const f32*p){unsigned i;if(stage!=calls++||stage>=c->calls)error=1;for(i=0;i<3;i++)if(word(p[i])!=c->args[stage*4+i])error=1;}
static s32 callback(unsigned kind,BounceRecord15D730*r,void*s,f32*p,BounceResponse15D730*d){
 packet(2,p);if(kind!=c->callback||r!=&object.data.record||s!=plane||d!=&response.item)error=1;
 if(c->mode&4){r->position[1]=99.0f;d->flags^=0x80;p[1]=-42.0f;markers[2]=0xA1700002;}
 return(s32)c->reply;
}
static s32 cb0(BounceRecord15D730*r,void*s,f32*p,BounceResponse15D730*d){return callback(0,r,s,p,d);}
static s32 cb1(BounceRecord15D730*r,void*s,f32*p,BounceResponse15D730*d){return callback(1,r,s,p,d);}
static s32 cb2(BounceRecord15D730*r,void*s,f32*p,BounceResponse15D730*d){return callback(2,r,s,p,d);}
s32 func_1514672C(struct17*point){
 packet(0,(f32*)point);
 if(c->mode&1){object.data.record.extent=3.5f;object.data.record.position[1]=6.0f;point->unk0=12.25f;point->unk8=-7.5f;D_800A3844=0.125f;response.item.kind=1;D_80089874[1]=cb1;markers[0]=0xA1700000;}
 return(s32)c->bounded;
}
s32 func_15046C80(f32*point,u16 selector,f32 threshold,HeightResult71820*result){
 unsigned i;packet(1,point);if(selector!=0||word(threshold)!=c->args[7]||result!=&object.data.height)error=1;
 for(i=0;i<sizeof(*result);i++)((u8*)result)[i]=(u8)(i*7+0x35);result->height=5.25f;
 if(c->mode&2){result->height=4.25f;point[0]=-2.5f;point[2]=9.75f;response.item.kind=2;D_80089874[2]=cb2;markers[1]=0xA1700001;}
 return(s32)c->hit;
}
typedef s32(*Update)(BounceRecord15D730*,void*,BounceResponse15D730*);
static int check(Update fn){unsigned i,j;int answer;
 for(i=0;i<__COUNT__;i++){
  c=cases+i;calls=error=0;
  for(j=0;j<sizeof(object);j++)((u8*)&object)[j]=(u8)(j*29+c->seed*11+0x5A);
  for(j=0;j<sizeof(plane);j++)((u8*)plane)[j]=(u8)(j*29+c->seed*11+0x5A);
  for(j=0;j<sizeof(response);j++)((u8*)&response)[j]=(u8)(j*29+c->seed*11+0x5A);
  object.data.record.extent=number(c->extent);object.data.record.position[0]=number(c->x);object.data.record.position[1]=number(c->y);object.data.record.position[2]=number(c->z);
  object.data.record.velocity[0]=2.0f;object.data.record.velocity[1]=number(c->vy);object.data.record.velocity[2]=3.0f;object.data.record.verticalAcceleration=-0.5f;object.data.record.flags=0x87654327;
  object.data.height.height=7.0f;plane[1]=number(c->planeY);response.item.flags=(u8)c->flags;response.item.kind=(s8)c->index;response.item.damping=number(c->damping);
  for(j=0;j<128;j++)D_80089874[j]=NULL;if(!c->null&&(s32)c->index>=0)D_80089874[c->index]=cb0;
  for(j=0;j<3;j++)markers[j]=c->initialMarkers[j];D_800A3844=number(0x3D75C290);
  answer=fn(&object.data.record,plane,&response.item);
  if(calls!=c->calls||error||(u32)answer!=c->result||word(D_800A3844)!=c->scale)return 1;
  if(!equal(&object,c->record,sizeof(object))||!equal(plane,c->plane,sizeof(plane))||!equal(&response,c->response,sizeof(response))||!equal(markers,c->markers,sizeof(markers)))return 2;
 }
 return 0;
}
static int run(void){if(check(test_selected))return 1;
'''.replace('__ROWS__',rows).replace('__COUNT__',str(n))
 for i,name in enumerate(controls(core)):code+='if(!check(test_'+name+'))return '+str(i+2)+';\n'
 return code+'return 0;}\n'+START
def native(core,out):
 p=out/'native.c';p.write_text(native_text(core));reports=[]
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);build=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
  assert build.returncode==0 and not build.stdout and not build.stderr,(opt,build.stdout,build.stderr)
  run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);assert run.returncode==0 and not run.stdout and not run.stderr,(opt,run.returncode,run.stderr)
  reports.append(dict(profile=opt,exit=0))
 return dict(cases_per_profile=native_rows()[1],profiles=reports,trapping_UBSan=True,effective_controls=len(controls(core)),typed_reused_record_response_and_height_layouts=True,
  whole_object_plane_response_and_marker_canaries=True,precomputed_numeric_packets_and_little_endian_expectations=True,
  native_descriptor_table_domain='-1 sentinel or 0..127 in a synthetic 128-entry provider table',negative_signed_indices_below_minus1_guest_only=True,
  actual_retail_table_has_one_entry=True,complete_hardware_FCSR_or_terrain_not_claimed=True)
