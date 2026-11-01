"""Actor transform/world-position query, ordered guest aliases and original helpers."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import PointOracle,put,read,STATUS,DIAGNOSTIC,FLAG,CONVERT,TRANSFORM,TRANSLATE
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

r=o=source=None
ENTRY,HELPER=0x1507E1D0,0x15143134
ACTOR,OUTPUT,MATRIX=0x30000,0x44000,0x50000
@dataclass(frozen=True)
class Case:
 index:int=0
 present:int=1
 state:int=0
 alias:int=0
 mode:int=0
 phase:int=0
 fixed:int=0
 output_tuple:tuple|None=None

def symbols(i=0):return {'func_15143134':(HELPER,0x17140000,0x1727FFFC)[i]}
def outputs(c):
 if c.output_tuple is not None:return c.output_tuple
 h=STACK+c.phase;p=h-56+28
 return ((OUTPUT,OUTPUT+4,OUTPUT+8),(OUTPUT,OUTPUT,OUTPUT),
  (ACTOR+24,ACTOR+28,ACTOR+20),(ACTOR+468,ACTOR+336,ACTOR),
  (h+4,h+8,h+12),(p+4,p+8,p),(OUTPUT,ACTOR+24,OUTPUT+4))[c.alias]
def matrix(c):return MATRIX+(0x300 if c.state==1 else 0xC0 if c.state==30 else 0)
def scale(c):return (0,0x80000000,bits(0.125),bits(-0.25),bits(1.),bits(4.),bits(-7.),bits(1024.))[c.index%8]
def returned(c):return tuple(bits(v) for v in ((c.index-3)*0.25,(5-c.index)*0.5,(c.index+1)*-0.125))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-768,768)}
 for base,size in ((ACTOR,0x400),(OUTPUT,64),(MATRIX,0x400),(STATUS-4,40),(FLAG,4)):m.update({base+i:0xA5 for i in range(size)})
 put(m,ACTOR,c.state&0xFFFFFFFF);put(m,ACTOR+468,MATRIX if c.present else 0);put(m,ACTOR+336,scale(c))
 for j in range(3):put(m,ACTOR+20+4*j,bits((c.index-j)*0.5))
 vals=[0.0]*16;vals[0],vals[5],vals[10],vals[15]=0.5,1.,2.,1.;vals[12:15]=3.,-4.,5.
 if c.fixed:
  ints=[int(v*65536)&0xFFFFFFFF for v in vals];data=struct.pack('>32H',*[v>>16 for v in ints],*[v&65535 for v in ints])
 else:data=struct.pack('>16I',*[bits(v) for v in vals])
 for off in (0,0xC0,0x300):m.update({MATRIX+off+i:v for i,v in enumerate(data)})
 m[FLAG]=c.fixed;return m
def public(m,c):
 h=STACK+c.phase
 return {a:b for a,b in m.items() if not h-768<=a<h}
def effect(m,c):
 h=STACK+c.phase
 if c.mode&1:
  put(m,ACTOR+468,0);put(m,ACTOR+336,bits(-17.));put(m,ACTOR,30)
  for j in range(3):put(m,ACTOR+20+4*j,bits((j+1)*3.5))
 if c.mode&2:
  for j in range(3):put(m,h+4+4*j,OUTPUT+12+4*j)
def reference(initial,c,s,actual=False):
 m=dict(initial);h=STACK+c.phase;x,y,z=outputs(c);put(m,h+4,x);put(m,h+8,y);calls=[];points=[]
 if c.present:
  p,q=h-16,h-28;point=(0,fp(scale(c),bits(30.),'mul'),0)
  for j,v in enumerate(point):put(m,p+4*j,v)
  put(m,h+12,z);calls=[(s['func_15143134'],(p,q,matrix(c)))];points=[point]
  if actual:
   values=(bits(3.),fp(point[1],bits(-4.),'add'),bits(5.))
   put(m,STATUS,0)
   if floating(point[1])!=0.:
    for j,v in enumerate(point):put(m,STATUS+8+4*j,v)
    put(m,DIAGNOSTIC,matrix(c))
  else:values=returned(c)
  for j,v in enumerate(values):put(m,q+4*j,v)
  if not actual:effect(m,c)
  # Retail restores z before the first public store; y is reloaded afterward.
  x,z=read(m,h+4),read(m,h+12)
  put(m,x,read(m,q));y=read(m,h+8);put(m,y,read(m,q+4));put(m,z,read(m,q+8))
 else:
  put(m,x,read(m,ACTOR+20));y=read(m,h+8);put(m,y,read(m,ACTOR+24));put(m,z,read(m,ACTOR+28))
 return public(m,c),calls,points

class Oracle(PointOracle,FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;self.points=[];self.root_calls=[]
  FactoryOracle.__init__(self,words,memory,c,entry=entry,s={},arguments=(ACTOR,*outputs(c)),connected=connected)
  self.before_f=self.f[:];self.input_args=None;self.mutate=False
 def record_call(self,t):
  if t==self.s['func_15143134']:
   args=tuple(self.arguments(3));self.input_args=args;point=tuple(read(self.memory,args[0]+4*j) for j in range(3))
   self.calls.append((t,args));self.root_calls.append((t,args));self.points.append(point)
  else:PointOracle.record_call(self,t)
 def hook(self,t):
  if t!=self.s['func_15143134']:return PointOracle.hook(self,t)
  point,out,matrix_arg=self.input_args
  for j,v in enumerate(returned(self.c)):put(self.memory,out+4*j,v)
  effect(self.memory,self.c)
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for k in (1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v) for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>53I',sections(p.with_suffix('.elf'))['.text'][1][:212]))
def programs(i):
 s=symbols(i);entry=(ENTRY,0x17038000,0x1F00FFFC)[i]
 names=('original-'+source.FUNCTION+'.o','selected-final.o','qualified-padded.o','make-shadow/src/game_A9D90.c.o')
 roots=[link(o/n,'actor-position-root-%d-%d'%(i,j),entry,s) for j,n in enumerate(names)];assert all(v==roots[0] for v in roots)
 return s,entry,roots
def state(m):return (m.memory,m.r,m.f,m.calls,m.points,m.trace,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p,connected=None):
 s,entry,roots=p;initial=fixture(c);expected,calls,points=reference(initial,c,s,connected is not None);models=[]
 for root in roots:
  m=Oracle(root,initial,c,s,entry,connected).run()
  assert (public(m.memory,c),m.root_calls,m.points)==(expected,calls,points),(c,m.root_calls,calls,[(hex(a),m.memory.get(a),v) for a,v in expected.items() if m.memory.get(a)!=v][:12])
  assert all(m.r[k]==m.before[k] for k in (*range(16,24),28,29,30,31)) and m.f[20:]==m.before_f[20:]
  models.append(m)
 assert all(state(m)==state(models[0]) for m in models)
 return models[0]
def guest():
 count=0;seen=set();ps=[]
 for i in range(3):
  p=programs(i);ps.append(p)
  for index,present,status,alias,mode in itertools.product(range(8),(0,1),(0,1,30,-1),range(7),range(4) if i==0 else (0,3)):
   c=Case(index,present,status,alias,mode,8 if index&1 else 0);m=compare(c,p);seen.update(m.visits);count+=1
 assert set(range(ENTRY,ENTRY+212,4))-seen=={ENTRY+100}
 return dict(cases=count,executions=count*4,rebases=3,alias_layouts=7,reachable_words=52,unreachable_duplicate_constant_words=1,four_programs_complete_state_trace_equal=True,live_null_path_positions_and_y_home_reloaded=True,z_home_captured_before_stores=True,all_matrix_selectors=True,saved_state_and_stack=True),ps[0]
def faults(p):
 count=0
 for c in (Case(present=0,alias=2),Case(state=1),Case(state=30,alias=5),Case(mode=3,phase=8)):
  full=compare(c,p);s,entry,roots=p
  for cut in range(full.all_accesses):
   models=[]
   for root in roots:
    m=Oracle(root,fixture(c),c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing guest access prefix')
    models.append(state(m))
   assert all(v==models[0] for v in models);count+=1
 return dict(prefixes=count,executions=count*4,complete_machine_state_and_access_order=True,guest_fault_model_only=True)
def helpers(p):
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 original=list(struct.unpack_from('>98I',rom,0x1705E4));retained=list(struct.unpack_from('>98I',before,source.elf_slot_offset(before,HELPER,392)))
 lower={};pins=[]
 for entry,at,n in ((CONVERT,0x21D368,46),(TRANSFORM,0xD4E10,40),(TRANSLATE,0x16F7C4,49)):
  words=struct.unpack_from('>%dI'%n,rom,at);lower.update(zip(range(entry,entry+n*4,4),words));pins.append(dict(entry=hex(entry),words=n,SHA256=source.sha(rom[at:at+n*4])))
 count=0;seen=set()
 for helper in (original,retained):
  connected=dict(lower);connected.update(zip(range(HELPER,HELPER+392,4),helper))
  for index,present,status,fixed,alias in itertools.product(range(8),(0,1),(0,1,30,-1),(0,1,255),(0,1,2,6)):
   c=Case(index,present,status,alias,0,8 if index&1 else 0,fixed);m=compare(c,p,connected);seen.update(m.visits);count+=1
 assert set(range(TRANSFORM,TRANSFORM+160,4))<=seen and set(range(TRANSLATE,TRANSLATE+196,4))<=seen
 return dict(cases=count,executions=count*4,original_and_retained_helper_words=98,lower_helpers=pins,original_fixed_converter_transform_translation=True,all_transform_and_translation_words_executed=True,zero_offset_and_float_fixed_routes=True,full_FCSR_and_hardware_not_modeled=True)
"""Defined finite native32 actor/query semantics; guest private aliases excluded."""
import itertools,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def native(r,o,source,g):
 body=source.SELECTED
 controls=(('wrong-height-scale',body.replace('y_scale * 30.0f','y_scale * 20.0f')),
  ('wrong-state-1-matrix',body.replace('matrix += 0x300','matrix += 0xC0')),
  ('wrong-state-30-matrix',body.replace('matrix += 0xC0','matrix += 0x300')),
  ('wrong-fallback-y',body.replace('*y = actor->y_position','*y = actor->x_position')),
  ('wrong-transformed-z',body.replace('*z = position.unk8','*z = position.unk4')),
  ('cached-fallback-y',body.replace('    u8 *matrix;','    u8 *matrix;\n    f32 worldY = actor->y_position;').replace('*y = actor->y_position','*y = worldY')),
  ('wrong-offset-x',body.replace('offset.unk0 = 0.0f','offset.unk0 = 1.0f')))
 assert all(v!=body for _,v in controls)
 def array(values):return '{'+','.join('0x%Xu'%v for v in values)+'}'
 rows=[]
 for index,present,state,alias,mode in itertools.product(range(32),(0,1),(0,1,30,-1),(0,1,2,6),(0,1)):
  c=g.Case(index,present,state,alias,mode);initial=g.fixture(c);expected,_,_=g.reference(initial,c,g.symbols())
  fields=[str(present),'0x%Xu'%(state&0xFFFFFFFF),str(alias),str(mode),'0x%Xu'%g.scale(c),array(g.returned(c)),
   array([g.read(initial,g.ACTOR+20+4*j) for j in range(3)]),array([g.read(expected,g.ACTOR+20+4*j) for j in range(3)]),
   array([g.read(expected,g.OUTPUT+4*j) for j in range(6)]),'0x%Xu'%g.read(expected,g.ACTOR),
   '0x%Xu'%g.read(expected,g.ACTOR+336),str(int(g.read(expected,g.ACTOR+468)!=0))]
  rows.append('{'+','.join(fields)+'}')
 code=source.HEADERS+r'''
struct Case{u32 present,state,alias,mode,scale,returned[3],initial[3],expected[3],out[6],finalState,finalScale,finalMatrix;};
static const struct Case cases[]={ROWS};static const struct Case *current;
static struct{u32 before[4];struct127 actor;u32 after[4];} storage;
static f32 out[10];static u8 matrices[1024];static u32 count,error;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
void func_15143134(f32 *point,f32 *position,u8 *matrix){
 u32 j,offset=current->state==1?768u:current->state==30?192u:0u;count++;
 if(matrix!=matrices+offset||bits(point[0])!=0||bits(point[1])!=bits(floating(current->scale)*30.0f)||bits(point[2])!=0)error=1;
 for(j=0;j<3;j++)position[j]=floating(current->returned[j]);
 if(current->mode){storage.actor.unk1D4=0;storage.actor.y_scale=-17.0f;storage.actor.interaction_state=30;
 storage.actor.x_position=3.5f;storage.actor.y_position=7.0f;storage.actor.z_position=10.5f;}
}
'''.replace('ROWS',',\n'.join(rows))
 for j,(_,value) in enumerate((('valid',body),)+controls):code+=value.replace('func_1507E1D0(','root_%d('%j)+'\n'
 code+='static void (*roots[])(struct127*,f32*,f32*,f32*)={'+','.join('root_%d'%j for j in range(8))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;f32 *x,*y,*z;u8 *bytes;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<8;j++){
  current=&cases[n];count=error=0;bytes=(u8*)&storage;
  for(k=0;k<sizeof(storage);k++)bytes[k]=0xA5;
  for(k=0;k<10;k++)out[k]=floating(0xA5A5A5A5u);
  storage.actor.interaction_state=current->state;storage.actor.unk1D4=current->present?(void*)matrices:0;storage.actor.y_scale=floating(current->scale);
  storage.actor.x_position=floating(current->initial[0]);storage.actor.y_position=floating(current->initial[1]);storage.actor.z_position=floating(current->initial[2]);
  if(current->alias==0){x=&out[2];y=&out[3];z=&out[4];}
  else if(current->alias==1)x=y=z=&out[2];
  else if(current->alias==2){x=&storage.actor.y_position;y=&storage.actor.z_position;z=&storage.actor.x_position;}
  else{x=&out[2];y=&storage.actor.y_position;z=&out[3];}
  roots[j](&storage.actor,x,y,z);failed=error||count!=current->present;
  if(bits(storage.actor.x_position)!=current->expected[0]||bits(storage.actor.y_position)!=current->expected[1]||bits(storage.actor.z_position)!=current->expected[2])failed=1;
  if((u32)storage.actor.interaction_state!=current->finalState||bits(storage.actor.y_scale)!=current->finalScale||storage.actor.unk1D4!=(current->finalMatrix?(void*)matrices:0))failed=1;
  for(k=0;k<10;k++)if(bits(out[k])!=(k>=2&&k<8?current->out[k-2]:0xA5A5A5A5u))failed=1;
  bytes=(u8*)&storage.actor;
  for(k=0;k<sizeof(storage.actor);k++)if(!(k<4||(k>=20&&k<32)||(k>=336&&k<340)||(k>=468&&k<472))&&bytes[k]!=0xA5)failed=1;
  for(k=0;k<4;k++)if(storage.before[k]!=0xA5A5A5A5u||storage.after[k]!=0xA5A5A5A5u)failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==127u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 result=[]
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code)
  q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  result.append(dict(profile=opt,cases=len(rows),executions=len(rows)*8,controls=[n for n,_ in controls],all_seven_controls_effective=True,UBSan=True,whole_actor_and_output_canaries=True,portable_float_field_aliases=4,private_and_incoming_home_aliases_excluded=True))
 (o/'native-runtime.json').write_text(json.dumps(result,indent=2)+'\n');return result

"""Both original caller windows: real setup, gates, consumers and void-return poisons."""
import itertools,json,struct
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def callers(r,o,s,g):
 g.r,g.o,g.source=r,o,s;p=g.programs(0);syms,entry,roots=p
 rom=(r/'conker/conker.us.bin').read_bytes();census=json.loads((o/'caller-census.json').read_text())
 assert census['aligned_ROM_JALs']==[0xAA030,0x152344] and not census['aligned_ROM_Js'] and not census['aligned_ROM_pointer_literals']
 FLAG,ATTACHED,OWNER,MARK,CONSUMER=0x8008FDBC,0x60000,0x61000,0x70000,0x1517F814
 count=0;seen=set()
 windows=((0x1507CB5C,0x1507CBA0,0x1507CB88,(0x68,0x64,0x60)),(0x15124E84,0x15124EAC,0x15124E9C,(0x40,0x44,0x48)))
 for which,(start,end,returned_pc,offsets) in enumerate(windows):
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0)
  for index,present,status,mode,phase,gate,poison in itertools.product(range(4),(0,1),(0,1,30,-1),(0,3),(0,8),(0,1),(0,1,0x80000000,0xFFFFFFFF)):
   h=g.STACK+phase;c=g.Case(index,present,status,0,mode,phase,0,tuple(h+off for off in offsets));initial=g.fixture(c)
   for base,size in ((FLAG,4),(ATTACHED,0x140),(OWNER,0x400),(MARK,4)):initial.update({base+i:0xA5 for i in range(size)})
   g.put(initial,FLAG,0x80 if gate else 0,2);g.put(initial,g.ACTOR+0x31C,ATTACHED);g.put(initial,OWNER+0x3D0,g.ACTOR)
   called=which==0 or gate;prepared=dict(initial)
   if which==0 and gate:prepared[ATTACHED+0x122]=0
   if called:
    expected,calls,points=g.reference(prepared,c,syms);expected=dict(expected)
   else:expected,calls,points=g.public(prepared,c),[],[]
   if which==0:
    consumer_args=(0,*(g.read(expected,h+off) for off in offsets),0x89ABCDEF)
    g.put(expected,h+16,0x89ABCDEF);g.put(expected,MARK,poison)
   models=[]
   for root in roots:
    code=dict(zip(range(entry,entry+212,4),root));code[end]=0;code[0x15124ECC]=0
    class CallerOracle(g.Oracle):
     def record_call(self,t):
      if t==entry:self.boundary_calls.append(tuple(self.arguments(4)))
      elif t==CONSUMER:self.consumer_calls.append(tuple(self.arguments(5)))
      else:super().record_call(t)
     def hook(self,t):
      if t!=CONSUMER:return super().hook(t)
      g.put(self.memory,MARK,poison)
      for k in (1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
      self.f[:20]=[0xA5000000+k for k in range(20)];self.r[2]=poison
    m=CallerOracle(words,initial,c,syms,start,code);m.boundary_calls=[];m.consumer_calls=[]
    m.r[16]=OWNER;m.r[17]=g.ACTOR;m.r[18]=0x89ABCDEF;m.r[24]=gate
    m.before=m.r[:];m.before_f=m.f[:]
    class CallerCode(WindowCode):
     def __getitem__(self,pc):
      if pc==returned_pc:self.owner.r[2]=poison
      return super().__getitem__(pc)
    m.code=CallerCode(m.code,m);m.code.ends=(end,0x15124ECC)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing original caller boundary')
    assert (g.public(m.memory,c),m.root_calls,m.points)==(expected,calls,points),(which,c,gate,hex(poison),[(hex(a),m.memory.get(a),v) for a,v in expected.items() if m.memory.get(a)!=v][:8])
    assert m.boundary_calls==([(g.ACTOR,*g.outputs(c))] if called else [])
    assert m.consumer_calls==([consumer_args] if which==0 else [])
    if which==1 and called:assert m.r[4]==OWNER+0x2C0 and m.r[5]==g.read(expected,h+offsets[1]) and m.r[2]==poison
    assert all(m.r[k]==m.before[k] for k in (*range(16,24),28,29,30)) and m.f[20:]==m.before_f[20:]
    models.append(m);seen.update(m.visits)
   assert all(g.state(m)==g.state(models[0]) for m in models);count+=1
 reachable=sum(start+4*j in seen for start,end,_,_ in windows for j in range((end-start)//4))
 assert reachable==27,reachable
 report=dict(success=True,private_only=True,matching_credit=0,cases=count,executions=count*4,original_windows=2,reachable_caller_words=reachable,return_poisons=4,void_return_ignored=True,actual_argument_setup_branch_gates_and_output_consumers=True,all_four_programs_full_state_equal=True,complete_parent_routines_emulated=False)
 (o/'caller-runtime.json').write_text(json.dumps(report,indent=2)+'\n');return report

import sys

def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core
 fingerprint=core.sha(Path(__file__).read_bytes()+core.SELECTED.encode()+core.RAW_SHA.encode()+core.SNAPSHOT_SHA.encode()+b''.join((o/n).read_bytes() for n in ('qualified-padded.o','selected-final.o','first-linked.elf')))
 saved=o/'runtime-qualification.json'
 if saved.exists():
  old=json.loads(saved.read_text())
  if old.get('fingerprint')==fingerprint:return old
 g,p=guest();module=sys.modules[__name__]
 q=dict(fingerprint=fingerprint,private_only=True,installed=False,matching_credit=0,guest=g,faults=faults(p),helpers=helpers(p),native=native(r,o,core,module),callers=callers(r,o,core,module))
 saved.write_text(json.dumps(q,indent=2)+'\n');return q
