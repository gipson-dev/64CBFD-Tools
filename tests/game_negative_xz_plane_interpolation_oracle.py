"""X=-Z interpolation and complete original polygon caller within a finite domain."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,random,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import game_polygon_plane_clip_oracle as geometry
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections
ENTRY,F=0x1518557C,'func_1518557C'
PARENT,CLASS0=0x15185DD4,0x1518567C
TABLE,CLASSES=0x8008D498,0x8008D4C0
A,B,OUT=0x20000,0x20014,0x20028
POLYOUT=0x30000
@dataclass(frozen=True)
class Case:
 phase:int=0
def vertex(x=1,y=-3,z=7,attrs=(-32768,-1,32767),padding=(0xA5,0x5A)):
 return struct.pack('>IIIhhhBB',bits(x),bits(y),bits(z),*attrs,*padding)
def corpus():
 rows=[]
 for da,db in ((1,-1),(2,-6),(-3,1),(0,4),(-0.0,-8),(7,0),(0.125,-4096)):
  for attrs in ((-32768,-1,32767),(-17,13,97),(32767,0,-32768)):
   az=da*.25+2;bz=db*.5-1
   rows.append((vertex(da-az,1.0e8,az,attrs),vertex(db-bz,-1.0e8,bz,tuple(reversed(attrs)))))
 rng=random.Random(0x1518557C)
 for i in range(128):
  da=2.0**rng.randrange(-8,13);db=-2.0**rng.randrange(-8,13)
  if i&1:da,db=-da,-db
  az=da*.25+2;bz=db*.5-1
  rows.append((vertex(da-az,rng.uniform(-1e6,1e6),az,tuple(rng.randrange(-32768,32768)for _ in range(3))),vertex(db-bz,rng.uniform(-1e6,1e6),bz,tuple(rng.randrange(-32768,32768)for _ in range(3)))))
 return rows

def fixture(a,b,phase=0):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,512)}
 m.update({A+i:(i*29+0x59)&255 for i in range(-16,512)})
 for p,data in ((A,a),(B,b)):
  for i,v in enumerate(data):m[p+i]=v
 return m
f32=lambda x:floating(bits(x))
def half(m,p):return ((read(m,p,2)^32768)-32768)
def reference(initial,a=A,b=B,out=OUT):
 m=dict(initial);cursor=geometry.interpolate(m,a,b,out,1)
 return m,cursor

class Oracle(FactoryOracle):
 def __init__(self,program,initial,args=(A,B,OUT),phase=0,entry=ENTRY,connected=None,target=ENTRY):
  self.target=target;super().__init__(program,initial,Case(phase),entry=entry,s={},connected=connected,arguments=args);self.before_f=self.f[:]
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==7:
   self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
  elif word>>26==17 and word>>21&31==16 and word&63==13:
   value=floating(self.f[word>>11&31]);assert math.isfinite(value)and -2147483648<=math.trunc(value)<=2147483647,'Outside bounded truncation domain'
   self.f[word>>6&31]=math.trunc(value)&0xFFFFFFFF
  else:super().execute(word)
 def record_call(self,t):
  assert t in (self.target,CLASS0),hex(t);self.calls.append((t,tuple(self.arguments(3 if t==self.target else 1))))
 def hook(self,t):raise AssertionError(('Unowned helper',hex(t)))
def state(m):return m.memory,m.r,m.f,m.trace,m.calls
def check_saved(m):
 assert all(m.r[i]==m.before[i]for i in (*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
def linked(obj,label,entry=ENTRY):
 p=o/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
 return list(struct.unpack('>64I',sections(p.with_suffix('.elf'))['.text'][1][:256]))
def configure(root,output,obj):
 global r,o,rom,objects,programs
 r,o=root,output;rom=(r/'conker/conker.us.bin').read_bytes();objects=(r/'conker/build/game-negative-xz-plane-interpolation-1518557C-match/original-func_1518557C.o',obj);programs=[linked(p,'root-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]
def run_suite():
 count=0;seen=set()
 for (a,b),phase,out in itertools.product(corpus(),(0,8),(OUT,A,B)):
  initial=fixture(a,b,phase);expected,cursor=reference(initial,out=out);pair=[]
  for program in programs:
   m=Oracle(program,initial,(A,B,out),phase);m.run();check_saved(m)
   assert m.memory==expected and m.r[2]==cursor and not m.calls
   assert [t[1]for t in m.trace if t[0]=='W']==[out+i for i in (0,8,4,12,14,16)]
   seen.update(m.visits);pair.append(state(m))
  assert pair[0]==pair[1];count+=1
 assert seen==set(range(ENTRY,ENTRY+256,4))
 return dict(cases=count,executions=count*2,reachable_words=64,frame=0,output_store_order=[0,8,4,12,14,16],retained_bytes_preserved=True,legal_input_output_aliases=True,return_cursor_stride=20,finite_opposite_side_or_endpoint_domain=True,hardware_FCSR_NaN_invalid_conversion_or_denormal_traps_claimed=False)
def caller_code(program,target=ENTRY):
 code=dict(zip(range(target,target+256,4),program))
 for entry,off,n in ((PARENT,0x1B3284,84),(CLASS0,0x1B2B2C,11)):code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,off)))
 return code
def polygon_fixture(xs,index,phase=0,target=ENTRY):
 initial=fixture(vertex(),vertex(),phase);initial.update({POLYOUT+i:(i*13+0xA7)&255 for i in range(-16,512)})
 for i,x in enumerate(xs):
  v=vertex(x-2,i*13.25-47,2,(-32768+i*1234,-17+i,32767-i*876),(i+31,i+63))
  for j,value in enumerate(v):initial[A+i*20+j]=value
 for table,off in ((TABLE,0x231F58),(CLASSES,0x231F80)):
  for i in range(10):put(initial,table+i*4,struct.unpack_from('>I',rom,off+4*i)[0])
 put(initial,TABLE+index*4,target);return initial
def polygon_reference(initial,count,index,target=ENTRY):
 m=dict(initial);cursor=POLYOUT;calls=[];classify=CLASS0
 def inside(p):
  return floating(read(m,p)) < -floating(read(m,p+8))
 for i in range(max(0,count)):
  cur=A+i*20;prev=A+((i-1)%count)*20;cur_in,prev_in=inside(cur),inside(prev)
  calls.extend(((classify,(cur,)),(classify,(prev,))))
  if cur_in!=prev_in:
   calls.append((target,(prev,cur,cursor)));m,cursor=reference(m,prev,cur,cursor)
  if cur_in:
   data=bytes(m[cur+j]for j in range(20))
   for j,v in enumerate(data):m[cursor+j]=v
   cursor+=20
 return m,cursor,calls
def run_callers():
 seen=set();callsites=set();count=0;polygons=[(),(-3,), (4,),(-3,4),(4,-3),(-3,-1,-7),(1,2,3),(-2,3,-4,5),(-1,0,2,0),(0.0,-0.0,1,-1)]
 for xs,index,phase in itertools.product(polygons,(1,),(0,8)):
  initial=polygon_fixture(xs,index,phase);expected,cursor,calls=polygon_reference(initial,len(xs),index);pair=[]
  for program in programs:
   code=caller_code(program);m=Oracle([code[PARENT+i*4]for i in range(84)],initial,(A,len(xs),index,POLYOUT),phase,PARENT,code);m.run();check_saved(m)
   public=lambda mem:{a:v for a,v in mem.items()if not STACK-256<=a<STACK+512}
   assert public(m.memory)==public(expected)and m.r[2]==cursor and m.calls==calls,(xs,index,cursor,m.r[2])
   seen.update(m.visits);callsites.update(m.visits&{0x15185E90,0x15185EDC});pair.append(state(m))
  assert pair[0]==pair[1];count+=1
 # Negative counts perform no vertex accesses, in both original and recovered code.
 for index in (1,):
  initial=polygon_fixture((),index)
  for program in programs:
   code=caller_code(program);m=Oracle([code[PARENT+i*4]for i in range(84)],initial,(A,0xFFFFFFFF,index,POLYOUT),entry=PARENT,connected=code);m.run();assert m.r[2]==POLYOUT and not m.calls
  count+=1
 assert set(range(PARENT,PARENT+336,4))<=seen and callsites=={0x15185E90,0x15185EDC}
 return dict(cases=count,executions=count*2,complete_parent_words=84,parent_reachable_words=84,original_classifier_words=11,table_slots=[1],owned_indirect_callsites=[hex(x)for x in sorted(callsites)],no_external_service_models=True,whole_vertex_copy_including_retained_bytes=True,positive_empty_and_negative_counts=True)
def run_prefixes_and_rebases():
 prefixes=rebases=0
 for out in (OUT,A,B):
  a,b=corpus()[1];initial=fixture(a,b);full=Oracle(programs[0],initial,(A,B,out));full.run()
  for cut in range(full.all_accesses):
   pair=[]
   for program in programs:
    m=Oracle(program,initial,(A,B,out));m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Prefix failed to fire')
    pair.append(state(m))
   assert pair[0]==pair[1];prefixes+=1
 for i,entry in enumerate((0x1ABC0000,0x15007FFC)):
  ps=[linked(p,'rebase-%d-%d'%(i,k),entry)for k,p in enumerate(objects)];assert ps[0]==ps[1]
  for index in (1,):
   xs=(-3,1,-1,7);initial=polygon_fixture(xs,index,target=entry);expected,cursor,calls=polygon_reference(initial,len(xs),index,entry)
   for program in ps:
    code=caller_code(program,entry);m=Oracle([code[PARENT+j*4]for j in range(84)],initial,(A,len(xs),index,POLYOUT),entry=PARENT,connected=code,target=entry);m.run();assert m.r[2]==cursor and m.calls==calls
    assert all(m.memory[a]==v for a,v in expected.items()if not STACK-256<=a<STACK+512);rebases+=1
 return dict(fired_prefix_cases=prefixes,relocated_code_profiles=2,relocated_table_caller_executions=rebases,target_relocations=0,portable_C_fault_claimed=False)
