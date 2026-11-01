"""Spherical X/Z/Y offsets: bounded guest execution and finite reference.

Incoming-home mutation/alias cases qualify this emitted guest implementation,
not arbitrary portable C accesses to a compiler's formal homes. The paired
spill normalization is restricted to outputs outside the callee private frame.
FCSR exceptions, NaN payload propagation and hardware execution are not modeled.
"""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.game_rotation_matrix_leaf_oracle import trig,COEFFICIENTS
from tools.tests.game_fixed_matrix_oracle import integer
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

r=o=source=None
ENTRY,COS,SIN=0x1505A184,0x150AD780,0x150AD78C
OUTPUT=0x50000
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 mutation:int=0
 phase:int=0
 outputs:tuple|None=None
 arguments:tuple|None=None

def symbols(i=0):
 return dict(D_800994B8=(0x800994B8,0x3407FFC,0x2408000)[i],D_800994BC=(0x800994BC,0x3418000,0x2427FFC)[i],func_150AD780=(COS,0x17140000,0x17240000)[i],func_150AD78C=(SIN,0x17148000,0x17248000)[i])

def pointers(c,s):
 if c.outputs is not None:return c.outputs
 h=STACK+c.phase
 return ((OUTPUT,OUTPUT+4,OUTPUT+8),(OUTPUT,OUTPUT,OUTPUT),(OUTPUT,OUTPUT+4,OUTPUT),
  (s['D_800994B8'],s['D_800994BC'],s['D_800994BC']),
  (OUTPUT,OUTPUT+4,h),(OUTPUT,OUTPUT+4,h+8),
  (h+8,h,OUTPUT),(OUTPUT,h+8,s['D_800994B8']),
  (s['D_800994BC'],s['D_800994B8'],OUTPUT))[c.alias]

def inputs(c):
 if c.arguments is not None:return c.arguments
 yaw=(0,1,0x7FFF,0x8000,0xFFFF,0x1234,0x8001,0xFFFE)[c.index%8]
 yaw|=(0xABCD0000 if c.index&1 else 0)
 distance=(0.,-0.,0.5,-1.,17.25,-1024.,0.125,4096.)[(c.index//2)%8]
 pitch=(-720.,-90.,-0.,0.,0.01,30.,90.,360.)[(c.index//4)%8]
 pitch_word=bits(pitch) if c.index<128 else (1,0x80000001,0x71800000,0xF1800000)[c.index%4]
 return yaw,bits(distance),pitch_word

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 m.update({OUTPUT+i:0xA5 for i in range(-16,64)})
 for n in ('D_800994B8','D_800994BC'):put(m,s[n],0x3C8EFA35)
 x,z,y=pointers(c,s);h=STACK+c.phase
 put(m,h+16,z);put(m,h+20,y)
 return m

def public(m,c):
 h=STACK+c.phase
 return {a:b for a,b in m.items() if not h-48<=a<h}

def returned(c,j):return bits((0.,-0.,1.,-1.,0.25,-0.5,0.75,-0.125)[(c.index+3*j)%8])

def effect(m,c,s,j):
 h=STACK+c.phase
 if c.mutation&1:
  put(m,s['D_800994B8'],bits((j+1)*0.125));put(m,s['D_800994BC'],bits((j-2)*0.25))
  for k in range(3):put(m,OUTPUT+4*k,bits((j+1)*(k-1.5)))
 if c.mutation&2:
  # Providers may observe/write incoming homes in the guest-only adversarial set.
  put(m,h,(0xD00D8001+j*17)&0xFFFFFFFF);put(m,h+8,bits((j-1)*0.25))
  put(m,h+12,OUTPUT+12);put(m,h+16,OUTPUT+16);put(m,h+20,OUTPUT+20)

def reference(initial,c,s,actual=False):
 m=dict(initial);h=STACK+c.phase;yaw,distance,pitch=inputs(c)
 put(m,h,yaw);put(m,h+12,pointers(c,s)[0])
 distance=fp(distance,bits(0.5),'mul');pitch=fp(pitch,read(m,s['D_800994B8']),'mul')
 put(m,h+8,pitch);calls=[];observations=[]
 constants={a:read(m,a) for a in range(COEFFICIENTS,COEFFICIENTS+48,4)} if actual else {}
 def call(j,arg):
  target=(s['func_150AD78C'],s['func_150AD780'],s['func_150AD780'],s['func_150AD78C'])[j]
  calls.append((target,(arg,)));observations.append(tuple(read(m,OUTPUT+4*k) for k in range(6)))
  value=trig(arg,(SIN,COS,COS,SIN)[j],constants) if actual else returned(c,j)
  if not actual:effect(m,c,s,j)
  return value
 sine=call(0,pitch)
 y=read(m,h+20);second_pitch=read(m,h+8)
 put(m,y,fp(sine,distance^0x80000000,'mul'))
 cosine=call(1,second_pitch)
 distance=fp(cosine,distance,'mul')
 yaw_angle=fp(bits(float(read(m,h+2,2))),read(m,s['D_800994BC']),'mul')
 cosine=call(2,yaw_angle);sine=call(3,yaw_angle)
 put(m,read(m,h+12),fp(cosine,distance,'mul'))
 put(m,read(m,h+16),fp(sine^0x80000000,distance,'mul'))
 return public(m,c),calls,observations

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},arguments=(*inputs(c),pointers(c,s)[0]),connected=connected)
  self.before_f=self.f[:];self.call_outputs=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==36:self.f[w>>6&31]=integer(self.f[w>>11&31],0)
  elif w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  j=len(self.calls);assert j<4 and t==(self.s['func_150AD78C'],self.s['func_150AD780'],self.s['func_150AD780'],self.s['func_150AD78C'])[j]
  self.calls.append((t,(self.f[12],)))
  self.call_outputs.append(tuple(read(self.memory,OUTPUT+4*k) for k in range(6)))
 def hook(self,t):
  j=len(self.calls)-1;effect(self.memory,self.c,self.s,j)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in (1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=returned(self.c,j);self.hi,self.lo=0xA5000010,0xA5000011

def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s)
 assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v) for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>51I',sections(p.with_suffix('.elf'))['.text'][1][:204]))

def programs(i):
 s=symbols(i);entry=(ENTRY,0x17038000,0x1F00FFFC)[i]
 names=('original-'+source.FUNCTION+'.o','qualified-padded.o','make-shadow/src/game_83300.c.o','selected-final.o')
 roots=[link(o/n,'sphere-root-%d-%d'%(i,j),entry,s) for j,n in enumerate(names)]
 assert roots[0]==roots[1]==roots[2]
 differences=[j*4 for j,(a,b) in enumerate(zip(roots[0],roots[3])) if a!=b];assert differences==[0x8C,0x90],differences
 return s,entry,roots

def state(m):return (m.memory,m.r,m.f,m.calls,m.call_outputs,m.trace,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)

def compare(c,p,initial=None,mathcode=None):
 s,entry,roots=p;initial=fixture(c,s) if initial is None else initial
 expected,calls,observations=reference(initial,c,s,mathcode is not None);models=[]
 for root in roots:
  m=Oracle(root,initial,c,s,entry,mathcode).run()
  assert (public(m.memory,c),m.calls,m.call_outputs)==(expected,calls,observations),(c,m.calls,calls,[(hex(a),m.memory.get(a),expected.get(a)) for a in expected if m.memory.get(a)!=expected[a]][:12],m.call_outputs,observations)
  assert all(m.r[k]==m.before[k] for k in (*range(16,24),28,29,30,31)) and m.f[20:]==m.before_f[20:]
  models.append(m)
 assert state(models[0])==state(models[1])==state(models[2])
 raw=models[3];a=models[0]
 assert (raw.r,raw.f,raw.calls,raw.call_outputs,raw.hi,raw.lo,raw.condition)==(a.r,a.f,a.calls,a.call_outputs,a.hi,a.lo,a.condition)
 # These are the only permitted raw/normalized final-memory differences.
 h=STACK+c.phase;slots=set(range(h-48+0x20,h-48+0x28))
 assert {k:v for k,v in a.memory.items() if k not in slots}=={k:v for k,v in raw.memory.items() if k not in slots}
 return a

def guest():
 n=0;seen=set();ps=[]
 for i in range(3):
  p=programs(i);ps.append(p)
  for index,alias,mode in itertools.product(range(64 if i==0 else 32),range(9),range(4) if i==0 else (0,3)):
   c=Case(index,alias,mode,8 if index&1 else 0);m=compare(c,p);seen.update(m.visits);n+=1
 # The lhu result is nonnegative: the unsigned correction is unreachable by proof.
 unreachable={ENTRY+x for x in (0x70,0x74,0x78)}
 assert set(range(ENTRY,ENTRY+204,4))-seen==unreachable,set(range(ENTRY,ENTRY+204,4))-seen
 return dict(cases=n,executions=n*4,rebases=3,alias_layouts=9,reachable_root_words=48,unreachable_unsigned_correction_words=3,all_three_normalized_programs_full_state_trace_equal=True,raw_C_public_state_equal=True,raw_private_difference_only_two_four_byte_slots=True,preserved_GPR_FPR_and_stack=True,guest_incoming_home_mutations=True),ps[0]

def faults(p):
 count=0
 for c in (Case(4),Case(7,4,3,8),Case(9,3,1),Case(6,5,2)):
  full=compare(c,p);s,entry,roots=p
  for cut in range(full.all_accesses):
   models=[]
   for root in roots[:3]:
    m=Oracle(root,fixture(c,s),c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing fault prefix')
    models.append(state(m))
   assert models[0]==models[1]==models[2];count+=1
 return dict(prefixes=count,executions=count*3,normalized_programs_complete_machine_state_and_trace_equal=True,guest_access_order_only=True)

def connected(p):
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes()
 words=struct.unpack_from('>76I',before,source.elf_slot_offset(before,COS,304));assert words==struct.unpack_from('>76I',rom,0xDAC30)
 code=dict(zip(range(COS,COS+304,4),words));constants={a:struct.unpack_from('>I',before,source.elf_slot_offset(before,a,4))[0] for a in range(COEFFICIENTS,COEFFICIENTS+48,4)}
 n=0;seen=set()
 for index,alias in itertools.product(range(256),range(9)):
  c=Case(index,alias,0,8 if index&1 else 0);initial=fixture(c,p[0])
  for a,v in constants.items():put(initial,a,v)
  m=compare(c,p,initial,code);seen.update(m.visits);n+=1
 return dict(cases=n,executions=n*4,original_trig_span_words=76,original_trig_words_executed=sum(COS+4*j in seen for j in range(76)),retail_code_and_12_coefficient_words_pinned=True,finite_polynomial_reference=True,full_FCSR_and_NaN_payloads_not_modeled=True)

"""Finite portable-domain native32/UBSan checks; guest formal-home aliases excluded."""
import itertools,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native(r,o,source,oracle):
 selected=source.SELECTED
 controls=(
  ('wrong-distance-scale',selected.replace('distance *= 0.5f','distance *= 1.0f')),
  ('wrong-vertical-sign',selected.replace('* -distance','* distance')),
  ('signed-yaw',selected.replace('(f32)(u32)yaw','(f32)(s16)yaw')),
  ('wrong-yaw-coefficient',selected.replace('yaw * D_800994BC','yaw * D_800994B8')),
  ('swapped-X-Z',selected.replace('*x = cosine * distance','*z = cosine * distance').replace('*z = -sine * distance','*x = -sine * distance')),
  ('wrong-Z-sign',selected.replace('*z = -sine','*z = sine')),
  ('early-X-store',selected.replace('    sine = func_150AD78C(yawAngle);','    *x = cosine * distance;\n    sine = func_150AD78C(yawAngle);').replace('    *x = cosine * distance;\n    *z =','    *z =')),
  ('reloaded-yaw-coefficient',selected.replace('func_150AD78C(yawAngle)','func_150AD78C((f32)(u32)yaw * D_800994BC)')),
  ('rescaled-pitch',selected.replace('func_150AD780(pitch)','func_150AD780(pitch * D_800994B8)')))
 assert all(value!=selected for _,value in controls)
 rows=[]
 def array(values):return '{'+','.join('0x%Xu'%v for v in values)+'}'
 for index,alias,mode in itertools.product(range(128),(0,1,2,3,8),(0,1)):
  c=oracle.Case(index,alias,mode);s=oracle.symbols();initial=oracle.fixture(c,s)
  expected,calls,observations=oracle.reference(initial,c,s)
  addresses=oracle.pointers(c,s)
  pointer_map={oracle.OUTPUT+4*k:k for k in range(6)}
  pointer_map.update({s['D_800994B8']:6,s['D_800994BC']:7})
  assert set(addresses)<=pointer_map.keys(),'Guest-only home alias entered native corpus'
  ptrs=[pointer_map[a] for a in addresses]
  assert all(0<=p<=7 for p in ptrs)
  fields=[array(oracle.inputs(c)),str(mode),array(ptrs),array([a[1][0] for a in calls]),
   array([oracle.returned(c,j) for j in range(4)]),'{'+','.join(array(v) for v in observations)+'}',
   array([oracle.read(expected,oracle.OUTPUT+4*k) for k in range(6)]),
   array([oracle.read(expected,s[n]) for n in ('D_800994B8','D_800994BC')])]
  rows.append('{'+','.join(fields)+'}')
 code='#include <ultra64.h>\n'+r'''
struct Case{u32 input[3],mode,ptr[3],args[4],returns[4],observations[4][6],expected[6],coefficients[2];};
static const struct Case cases[]={ROWS};
static const struct Case *current;
static f32 storage[10];
f32 D_800994B8,D_800994BC;
static u32 count,error;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
static f32 *pointer(u32 n){return n<6?&storage[n+2]:n==6?&D_800994B8:&D_800994BC;}
static f32 call(f32 x,u32 kind){
 u32 j=count++,k;
 if(j>=4){error=1;return 0.0f;}
 if(kind!=(j==0||j==3)||bits(x)!=current->args[j])error=1;
 for(k=0;k<6;k++)if(bits(storage[k+2])!=current->observations[j][k])error=1;
 if(current->mode){
  D_800994B8=(f32)(j+1)*0.125f;D_800994BC=((f32)j-2.0f)*0.25f;
  for(k=0;k<3;k++)storage[k+2]=(f32)(j+1)*((f32)k-1.5f);
 }
 return floating(current->returns[j]);
}
f32 func_150AD780(f32 x){return call(x,0);}
f32 func_150AD78C(f32 x){return call(x,1);}
'''.replace('ROWS',',\n'.join(rows))
 for j,(_,value) in enumerate((('valid',selected),)+controls):code+=value.replace('func_1505A184(','root_%d('%j)+'\n'
 code+='static void (*roots[])(u16,f32,f32,f32*,f32*,f32*)={'+','.join('root_%d'%j for j in range(10))+'};\n'
 code+=r'''
static int run(void){
 u32 n,j,k,killed=0,failed;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<10;j++){
  current=&cases[n];count=error=0;
  for(k=0;k<10;k++)storage[k]=floating(0xA5A5A5A5u);
  D_800994B8=floating(0x3C8EFA35u);D_800994BC=D_800994B8;
  roots[j]((u16)current->input[0],floating(current->input[1]),floating(current->input[2]),pointer(current->ptr[0]),pointer(current->ptr[1]),pointer(current->ptr[2]));
  failed=error||count!=4;
  for(k=0;k<10;k++)if(bits(storage[k])!=(k>=2&&k<8?current->expected[k-2]:0xA5A5A5A5u))failed=1;
  if(bits(D_800994B8)!=current->coefficients[0]||bits(D_800994BC)!=current->coefficients[1])failed=1;
  if(!j&&failed)return 2;
  if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==511u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 result=[]
 for opt in ('-O0','-O2','-O3'):
  p=o/('sphere-native-'+opt[1:]);p.with_suffix('.c').write_text(code)
  q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  result.append(dict(profile=opt,cases=len(rows),executions=len(rows)*10,controls=[n for n,_ in controls],all_nine_controls_effective=True,UBSan=True,canaries=True,alias_layouts=5,guest_formal_homes_excluded=True,finite_inputs=True))
 (o/'native-runtime.json').write_text(json.dumps(result,indent=2)+'\n');return result

"""Original 29 JAL/delay pairs with bounded output-pointer provenance.

The complete actor wrapper is qualified separately. These are call-boundary
windows, not execution of all large parent routines or proof of all paths to
each site. The original caller pointer definitions are retained in the receipt.
"""
from functools import lru_cache
import itertools,json,struct
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def callers(r,o,source,g):
 g.r,g.o,g.source=r,o,source
 p=g.programs(0);s,entry,roots=p
 rom=(r/'conker/conker.us.bin').read_bytes();census=json.loads((o/'caller-census.json').read_text())
 assert len(census['callers'])==29 and not census['aligned_ROM_Js'] and not census['aligned_ROM_pointer_literals']
 word=lambda pc:struct.unpack_from('>I',rom,pc-0x15000000+0x2D4B0)[0]
 signed=lambda n:((n&65535)^32768)-32768
 rows=[];count=0
 for caller in census['callers']:
  pc=int(caller['VA'],0);start=int(caller['start'],0);delay=word(pc+4)
  @lru_cache(None)
  def value(reg,at,depth=0):
   if reg==29:return ('stack',0)
   if reg==0:return ('constant',0)
   assert depth<12,('pointer depth',hex(pc),reg,hex(at))
   for address in range(at-4,start-4,-4):
    w=word(address);op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
    if op==3 and address!=pc and reg in (1,2,3,*range(4,16),24,25):return ('call-clobbered',reg,hex(address))
    writes=(rd if op==0 and fn in (0,2,3,4,6,7,9,16,18,32,33,34,35,36,37,38,39,42,43) else rt if op in (8,9,10,11,12,13,14,15,32,33,35,36,37,39) or op==17 and rs==0 else None)
    if writes!=reg:continue
    if op==9:
     base=value(rs,address,depth+1);off=signed(w)
     return (base[0],base[1]+off) if base[0] in ('stack','constant') else ('add',base,off)
    if op==35:return ('load',value(rs,address,depth+1),signed(w))
    if op==0 and fn in (33,37):
     if rt==0:return value(rs,address,depth+1)
     if rs==0:return value(rt,address,depth+1)
    if op==15:return ('constant',(w&65535)<<16)
    return ('unsupported-write',hex(address),hex(w))
   return ('unresolved-register',reg,hex(at))
  def home(offset):
   for address in range(pc+4,start-4,-4):
    w=word(address)
    if w>>26==43 and w>>21&31==29 and signed(w)==offset:return value(w>>16&31,address)
   raise AssertionError(('Missing outgoing home',hex(pc),offset))
  expressions=(value(7,pc+8),home(16),home(20))
  def valid(expr):
   if expr[0]=='stack':return expr[1]>=24 and expr[1]%4==0
   if expr[0]=='load':return expr[1][0]=='stack' and expr[2]>=24 and expr[2]%4==0
   if expr[0]=='add':return valid(expr[1]) and expr[2]%4==0
   return False
  assert all(valid(e) for e in expressions),(hex(pc),expressions)
  def evaluate(expr,h,m):
   if expr[0]=='stack':return h+expr[1]
   if expr[0]=='add':return evaluate(expr[1],h,m)+expr[2]
   if expr[0]=='load':return g.read(m,evaluate(expr[1],h,m)+expr[2])
   raise AssertionError(expr)
  for index,phase,mode in itertools.product(range(32),(0,8),(0,1)):
   h=g.STACK+phase;pre=g.Case(index,phase=phase)
   # External pointer-valued caller locals are bounded independent fixtures.
   initial=g.fixture(pre,s)
   for off in (0x44,0x88,0x8C,0x90):g.put(initial,h+off,g.OUTPUT+((off//4)%3)*4)
   outs=tuple(evaluate(e,h,initial) for e in expressions)
   assert all(a>=h+24 or g.OUTPUT<=a<g.OUTPUT+24 for a in outs)
   yaw,distance,pitch=g.inputs(pre);yaw&=65535
   c=g.Case(index,0,mode,phase,outs,(yaw,distance,pitch))
   g.put(initial,h+16,outs[1]);g.put(initial,h+20,outs[2])
   expected_initial=dict(initial)
   op,rs,rt=delay>>26,delay>>21&31,delay>>16&31;offset=signed(delay)
   if op==43:
    assert rs==29 and offset in (16,20)
    g.put(expected_initial,h+offset,outs[1 if offset==16 else 2])
   elif op==57:
    assert rs==29 and offset>=24
    g.put(expected_initial,h+offset,g.bits(0.5))
   elif op==37:
    assert rs==29 and rt==4
    g.put(initial,h+offset,yaw,2);expected_initial=dict(initial)
   else:assert delay==0 or op==9 and rs==29 and rt==7 or op==12 and rt==4 or op==0 and delay&63==37,hex(delay)
   expected,calls,observations=g.reference(expected_initial,c,s);models=[]
   class PairOracle(g.Oracle):
    def record_call(self,t):
     if t==entry:self.boundary_calls.append(tuple(self.arguments(6)))
     else:super().record_call(t)
   for root in roots:
    code=dict(zip(range(entry,entry+204,4),root));code[pc+8]=0
    m=PairOracle((word(pc),delay),initial,c,s,pc,code);m.boundary_calls=[]
    if op==43:m.r[rt]=outs[1 if offset==16 else 2]
    elif op==57:m.f[rt]=g.bits(0.5)
    elif op==12:m.r[rs]=yaw
    elif op==0 and delay:m.r[rs]=yaw
    m.before=m.r[:];m.before_f=m.f[:]
    m.code=WindowCode(m.code,m);m.code.ends=(pc+8,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller return boundary')
    assert m.boundary_calls==[(yaw,distance,pitch,*outs)],(hex(pc),m.boundary_calls,(yaw,distance,pitch,*outs))
    assert (g.public(m.memory,c),m.calls,m.call_outputs)==(expected,calls,observations),(hex(pc),index,phase,mode,[(hex(a),m.memory.get(a),v) for a,v in expected.items() if m.memory.get(a)!=v][:6])
    assert all(m.r[k]==m.before[k] for k in (*range(16,24),28,29,30)) and m.r[31]==pc+8 and m.f[20:]==m.before_f[20:]
    models.append(m)
   assert g.state(models[0])==g.state(models[1])==g.state(models[2])
   count+=1
  rows.append(dict(caller=caller,output_pointer_provenance=expressions,delay_word=hex(delay),six_argument_boundary_qualified=True))
 report=dict(success=True,private_only=True,matching_credit=0,cases=count,executions=count*4,original_JAL_delay_pairs=29,original_delay_words_executed=True,all_output_pointers_outside_callee_private_frame=True,three_normalized_programs_full_state_trace_equal=True,raw_C_public_results_equal=True,callee_saved_registers_and_return_PC=True,complete_parent_routines_emulated=False,rows=rows)
 (o/'caller-runtime.json').write_text(json.dumps(report,indent=2)+'\n');return report

from types import SimpleNamespace
import sys

def wrapper_runtime(r,o,core,g):
 p=g.programs(0);s,entry,roots=p
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes()
 WRAPPER,ACTOR=0x150593C4,0x30000
 wrapper=struct.unpack_from('>32I',rom,0x86874)
 # Pin original wrapper bytes to the independently retained retail layout span.
 assert wrapper[0]==0x27BDFFD0 and wrapper[13]>>26==3 and (wrapper[13]&0x3FFFFFF)*4==entry&0xFFFFFFF
 (o/'original-wrapper.bin').write_bytes(struct.pack('>32I',*wrapper))
 class WrapperOracle(g.Oracle):
  def __init__(self,root,initial,c,args,outer):
   self.c,self.s=c,s;self.wrapper_calls=[]
   code=dict(zip(range(entry,entry+204,4),root))
   FactoryOracle.__init__(self,wrapper,initial,SimpleNamespace(phase=outer),entry=WRAPPER,s={},arguments=args,connected=code)
   self.before_f=self.f[:];self.call_outputs=[]
  def record_call(self,t):
   if t==entry:self.wrapper_calls.append(tuple(self.arguments(6)))
   else:super().record_call(t)

 n=0;seen=set()
 for index,outer,mode in itertools.product(range(128),(0,8),(0,1)):
  outer_home=STACK+outer;home=outer_home-48
  yaw,distance,_=g.inputs(g.Case(index));yaw&=65535
  gain=bits((0.,-0.,0.125,0.5,1.,-1.,2.,0.05999999865889549)[index%8])
  c=g.Case(index,0,mode,outer-48,(home+44,home+40,home+36),(yaw,distance,0))
  initial=g.fixture(c,s);initial.update({ACTOR+i:0xA5 for i in range(0x180)})
  put(initial,ACTOR+0x16C,bits((index-31)*0.25));put(initial,ACTOR+0x170,bits((17-index)*0.5))
  # The wrapper saves its incoming actor/yaw/gain before preparing its child call.
  put(initial,outer_home,ACTOR);put(initial,outer_home+4,yaw);put(initial,outer_home+12,gain)
  expected,calls,observations=g.reference(initial,c,s)
  # reference() omits the child's private frame; restore its local outputs for
  # independent wrapper arithmetic, then compare the wrapper's public state.
  work=dict(initial);work.update(expected)
  x,z=read(work,home+44),read(work,home+40)
  oldx,oldz=read(work,ACTOR+0x16C),read(work,ACTOR+0x170)
  put(work,ACTOR+0x16C,fp(oldx,fp(fp(x,oldx,'sub'),gain,'mul'),'add'))
  put(work,ACTOR+0x170,fp(oldz,fp(fp(z,oldz,'sub'),gain,'mul'),'add'))
  public=lambda memory:{a:b for a,b in memory.items() if not outer_home-128<=a<outer_home}
  expected=public(work);models=[]
  for root in roots:
   m=WrapperOracle(root,initial,c,(ACTOR,yaw,distance,gain),outer).run()
   assert (public(m.memory),m.calls,m.call_outputs)==(expected,calls,observations),(index,outer,mode,[(hex(a),m.memory.get(a),v) for a,v in expected.items() if m.memory.get(a)!=v][:8])
   assert m.wrapper_calls==[(yaw,distance,0,home+44,home+40,home+36)]
   assert all(m.r[k]==m.before[k] for k in (*range(16,24),28,29,30,31)) and m.f[20:]==m.before_f[20:]
   models.append(m);seen.update(m.visits)
  assert g.state(models[0])==g.state(models[1])==g.state(models[2])
  n+=1
 assert all(WRAPPER+4*j in seen for j in range(32))
 report=dict(success=True,private_only=True,matching_credit=0,cases=n,executions=n*4,original_wrapper_words=32,all_original_wrapper_words_executed=True,original_wrapper_ROM=hex(0x86874),six_argument_X_Z_Y_ABI=True,signed_zero_and_float32_smoothing=True,output_order_and_coefficient_mutations=True,preserved_registers_and_stack=True)
 (o/'wrapper-runtime.json').write_text(json.dumps(report,indent=2)+'\n');return report

def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core
 fingerprint=core.sha(Path(__file__).read_bytes()+core.SELECTED.encode()+core.RAW_SHA.encode()+core.SNAPSHOT_SHA.encode()+b''.join((o/n).read_bytes() for n in ('qualified-padded.o','selected-final.o','first-linked.elf')))
 saved=o/'runtime-qualification.json'
 if saved.exists():
  old=json.loads(saved.read_text())
  if old.get('fingerprint')==fingerprint:return old
 g,p=guest();module=sys.modules[__name__]
 q=dict(fingerprint=fingerprint,private_only=True,installed=False,matching_credit=0,guest=g,faults=faults(p),connected=connected(p),native=native(r,o,core,module),callers=callers(r,o,core,module),wrapper=wrapper_runtime(r,o,core,module))
 saved.write_text(json.dumps(q,indent=2)+'\n');return q
