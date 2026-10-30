"""Private rotated-origin callback: ordered float32 and bounded provider contracts."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests import test_game_trig_match as trig
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=Path(__file__).resolve().parent;F='func_150CEF60';ENTRY=0x150CEF60;ROM=0xFC410
LOOKUP,FIRST,SECOND,SET,PHASE=0x151149AC,0x150AD78C,0x150AD780,0x150A3444,0x151749A0
FACTOR,DEPTH,OBJECT,OUT=0x800A0830,0x800A0834,0x30000,0x33000
SYMS=dict(func_151149AC=LOOKUP,func_150AD78C=FIRST,func_150AD780=SECOND,func_150A3444=SET,func_151749A0=PHASE,D_800A0830=FACTOR,D_800A0834=DEPTH)
VALUES=(0,0x80000000,1,0x80000001,0x00800000,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x3F400000,0xBE800000)
ANGLES=VALUES+(0x42B40000,0xC3340000,0x7F7FFFFF,0x7F800000,0x7FC12345)
fp=trig.operation;half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 pattern:int=0
 mode:int=0
 phase:int=0
 alias:int=0
 depth:int=0x42C80000
 unused:int=0x87654321
def object_at(c):return(OBJECT,FACTOR-8,DEPTH-8,STACK+c.phase+56)[c.alias]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,size in((OBJECT-32,0x400),(OUT-32,0x200),(FACTOR-32,96),(s['D_800A0830']-32,96),(s['D_800A0834']-32,96)):
  for i in range(size):m.setdefault(base+i,0xA5)
 for at,value in((object_at(c)+8,ANGLES[c.pattern%len(ANGLES)]),(s['D_800A0830'],0x3C8EFA35),(s['D_800A0834'],c.depth)):
  put(m,at,value)
 return m
def output(c,ordinal):return VALUES[(c.pattern+ordinal*3)%len(VALUES)]
def mutation(m,c,ordinal,s=SYMS):
 if c.mode&1:put(m,object_at(c)+8,ANGLES[(c.pattern+ordinal+5)%len(ANGLES)])
 if c.mode&2:put(m,s['D_800A0830'],VALUES[(c.pattern+ordinal+2)%len(VALUES)])
 if c.mode&4:put(m,s['D_800A0834'],bits(float((c.pattern*131+ordinal*17)%60000-30000)))
 if c.mode&8 and ordinal==2:put(m,OUT+4,0x55A50002)
def convert(word):
 value=floating(word)
 # Guest-only invalid conversions use a bounded indefinite result. Native
 # cases below restrict casts to representable signed-halfword values.
 return half(math.trunc(value))if math.isfinite(value)and -(2**31)<=value<2**31 else 0
def origin(radians,a,b,z):
 dx=fp(bits(76.),bits(-1.),'sub');dy=fp(bits(241.),bits(44.),'sub')
 x=fp(fp(fp(dx,b,'mul'),fp(dy,a,'mul'),'sub'),bits(-1.),'add')
 y=fp(fp(fp(dx,a,'mul'),fp(dy,b,'mul'),'add'),bits(44.),'add')
 return(convert(x)&0xFFFFFFFF,convert(y)&0xFFFFFFFF,convert(z)&0xFFFFFFFF)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[]
 calls.append((s['func_151149AC'],(4,)));mutation(m,c,0,s)
 radians=fp(read(m,object_at(c)+8),read(m,s['D_800A0830']),'mul')
 for i,name in enumerate(('func_150AD78C','func_150AD780'),1):
  calls.append((s[name],radians));observations.append((radians,read(m,s['D_800A0834'])));mutation(m,c,i,s)
 a,b=output(c,1),output(c,2);xyz=origin(radians,a,b,read(m,s['D_800A0834']))
 calls.append((s['func_150A3444'],(2,*xyz)))
 for i,v in enumerate(xyz):put(m,OUT+i*2,v&65535,2)
 calls.append((s['func_151749A0'],(5,3)));m[OUT+16]=(c.pattern+c.mode)&255
 return m,calls,observations
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
class Oracle(trig.TrigOracle):
 def __init__(self,words,m,c=Case(),entry=ENTRY,s=SYMS,connected=None,args=None):
  self.c,self.s=c,s;self.trace=[];self.observations=[];self.root_entry,self.root_size=entry,len(words)*4;self.root_accesses=0;self.cut=None
  super().__init__(words,m,phase=c.phase,entry=entry,arguments=(c.unused,)if args is None else args,connected=connected)
 def execute(self,w):
  if w>>26==17 and(w>>21)&31==16 and w&63==36:
   v=floating(self.f[(w>>11)&31]);assert math.isfinite(v)and -(2**31)<=v<2**31;self.f[(w>>6)&31]=int(round(v))&0xFFFFFFFF
  elif w>>26==17 and(w>>21)&31==16 and w&63==13:
   v=floating(self.f[(w>>11)&31]);self.f[(w>>6)&31]=(math.trunc(v)&0xFFFFFFFF)if math.isfinite(v)and -(2**31)<=v<2**31 else 0x80000000
  else:super().execute(w)
 def access(self):
  if self.own_instruction and self.root_entry<=self.current_pc<self.root_entry+self.root_size:
   if self.root_accesses==self.cut:raise faults.AccessBoundary
   self.root_accesses+=1
 def get(self,a,n):
  v=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,v))
  return v
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(n*8))-1)))
 def record_call(self,target):
  if target in(self.s['func_150AD78C'],self.s['func_150AD780']):
   a=self.f[12];self.observations.append((a,read(self.memory,self.s['D_800A0834'])))
  else:a=self.arguments({self.s['func_151149AC']:1,self.s['func_150A3444']:4,self.s['func_151749A0']:2,ENTRY:1}[target])
  self.calls.append((target,a));self.events.append(('CALL',target,a))
 def hook(self,target):
  c,s=self.c,self.s
  if target==s['func_151149AC']:mutation(self.memory,c,0,s);result=object_at(c)
  elif target in(s['func_150AD78C'],s['func_150AD780']):
   ordinal=1 if target==s['func_150AD78C']else 2;mutation(self.memory,c,ordinal,s);value=output(c,ordinal);result=0xDEADBEEF
  elif target==s['func_150A3444']:
   args=self.calls[-1][1]
   for i,v in enumerate(args[1:]):put(self.memory,OUT+2*i,v&65535,2)
   result=0xDEADBEEF
  elif target==s['func_151749A0']:self.memory[OUT+16]=(c.pattern+c.mode)&255;result=0xDEADBEEF
  else:raise AssertionError(('unbounded helper',target))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result
  if target in(s['func_150AD78C'],s['func_150AD780']):self.f[0]=value
def linked(obj,label,at=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%at+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def images(label='guest',at=ENTRY,s=SYMS):return[linked(o/p,label+'-'+str(i),at,s)for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.observations,m.lo,m.hi,m.condition,m.current_pc,m.delay_of,m.root_accesses)
def compare(c,ims,at=ENTRY,s=SYMS):
 initial=fixture(c,s);want,calls,obs=reference(initial,c,s);ms=[]
 for ws in ims:
  m=Oracle(ws,initial,c,at,s).run();assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c;ms.append(m)
 assert state(ms[0])==state(ms[1])==state(ms[2]),c;return ms[0]
def guest_suite():
 ims=images();assert ims[0]==ims[1]==ims[2];count=0;visits=set()
 for pattern,mode,phase,alias in itertools.product(range(32),range(16),(0,8),range(3)):
  c=Case(pattern,mode,phase,alias,depth=bits(float((pattern*1919)%65536-32768)));visits.update(compare(c,ims).visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=visits
 homes=0
 for pattern,mode,phase in itertools.product((0,1,7,15),(0,7,15),(0,8)):
  c=Case(pattern,mode,phase,3);ms=[Oracle(ws,fixture(c),c).run()for ws in ims];assert state(ms[0])==state(ms[1])==state(ms[2]);homes+=1
 cuts=delays=0
 for c in(Case(),Case(7,15,8,1),Case(15,7,0,2)):
  full=compare(c,ims)
  for cut in range(full.root_accesses):
   ms=[]
   for ws in ims:
    m=Oracle(ws,fixture(c),c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('access cut missing')
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebases=0
 for j,(at,factor,depth)in enumerate(((0x17007FFC,0x90007FFC,0x90008004),(0x2500FFFC,0x90008000,0x9000FFFC),(0x15008000,0x9020FFFC,0x90208000))):
  s=dict(SYMS,D_800A0830=factor,D_800A0834=depth)
  for k,name in enumerate(('func_151149AC','func_150AD78C','func_150AD780','func_150A3444','func_151749A0')):s[name]=at+0x10000+16*k
  ims2=images('rebase-'+str(j),at,s)
  for pattern,mode,phase in itertools.product((0,1,7,15),(0,7,15),(0,8)):compare(Case(pattern,mode,phase),ims2,at,s);rebases+=1
 return dict(cases=count,executions=count*3,covered_words=56,guest_only_home_aliases=homes,access_prefix_cases=cuts,delay_slot_cuts=delays,GNU_layouts=3,rebased_cases=rebases,complete_state_and_access_trace_equal=True,late_depth_and_captured_angle=True,IEEE_FCSR_unmodeled=True,invalid_float_conversions_guest_only=True)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __contains__(self,pc):return pc==self.owner.window_end or super().__contains__(pc)
 def __getitem__(self,pc):
  if pc==self.owner.window_end:raise WindowBoundary
  return super().__getitem__(pc)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ptr=struct.pack('>I',ENTRY);jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ptr]==[0x2317DC];assert not[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]
 table=rom[0x2317C4:0x231834];assert len(table)==28*4 and struct.unpack_from('>I',table,24)[0]==ENTRY
 literal={int(a,16):int(w,16)for a,w in __import__('re').findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/'conker/asm/1A1E50.s').read_text())}
 start,end=0x15174A2C,0x15174A58;ws=[literal[pc]for pc in range(start,end,4)];assert ws==list(struct.unpack_from('>11I',rom,0x1A1EDC))
 assert 'typedef void (*FrameLayerCallback)(s32);'in(r/'conker/src/game/generated_1A1E50.c').read_text()
 ims=images('caller');count=0
 for pattern,mode,phase,selector,view in itertools.product((0,7,15),(0,15),(0,8),(0,6),(0,0xFFFFFFFF)):
  c=Case(pattern,mode,phase,unused=view);initial=fixture(c);object_base=0x35000;initial[object_base+0xB]=selector;put(initial,0x800B0DF0,object_base);put(initial,STACK+phase+0x1C,view)
  for i,v in enumerate(table):initial[0x8008CD04+i]=v
  want,calls,obs=reference(initial,c)if selector else(dict(initial),[],[]);ms=[]
  for body in ims:
   m=Oracle(ws,initial,c,start,connected={ENTRY+4*i:w for i,w in enumerate(body)},args=(view,));m.window_end=end;m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('window boundary missing')
   expected=[(ENTRY,(view,)),*calls]if selector else[];assert(public(m.memory),m.calls,m.observations)==(public(want),expected,obs);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,original_window_words=11,selector=6,table_words=28,indirect_call=hex(0x15174A50),unused_view_is_32_bit=True,return_ignored=True,earlier_and_later_parent_helpers_bounded=True,full_parent_claimed=False)

def controls():
 body=(o/'selected-semantic-input.c').read_text()
 changes={
 'lookup-id':('func_151149AC(4)','func_151149AC(5)'),
 'angle-offset':('func_151149AC(4) + 8','func_151149AC(4) + 12'),
 'angle-factor':('* D_800A0830','* 1.0f'),
 'first-provider':('first = func_150AD78C(radians)','first = func_150AD780(radians)'),
 'second-provider':('second = func_150AD780(radians)','second = func_150AD78C(radians)'),
 'origin-x':('originX = -1.0f','originX = 1.0f'),
 'origin-y':('originY = 44.0f','originY = 45.0f'),
 'point-x':('pointX = 76.0f','pointX = 75.0f'),
 'point-y':('pointY = 241.0f','pointY = 240.0f'),
 'x-sign':('dx * second - dy * first','dx * second + dy * first'),
 'y-sign':('dx * first + dy * second','dx * first - dy * second'),
 'setter-index':('func_150A3444(2,','func_150A3444(3,'),
 'phase-limit':('func_151749A0(5, 3)','func_151749A0(6, 3)'),
 'no-phase':('    func_151749A0(5, 3);',''),
 'wrong-depth':('(s16)D_800A0834','(s16)(D_800A0834 * 0.5f)'),
 }
 result={}
 for name,(a,b)in changes.items():assert a in body;result[name]=body.replace(a,b)
 result['early-depth']=body.replace('    f32 first;','    f32 first;\n    f32 capturedDepth;').replace('    first = func_150AD78C(radians);','    capturedDepth = D_800A0834;\n    first = func_150AD78C(radians);').replace('(s16)D_800A0834','(s16)capturedDepth')
 return result
def compiled_controls():
 out={}
 for name,text in controls().items():
  obj,diag=compile_owner(r,o,text,'negative-'+name);assert not diag;ws=linked(obj,'negative-linked-'+name);witness=None
  for pattern,mode in itertools.product(range(16),(0,15)):
   c=Case(pattern,mode);initial=fixture(c);want,calls,obs=reference(initial,c);m=Oracle(ws,initial,c).run()
   if(public(m.memory),m.calls,m.observations)!=(public(want),calls,obs):witness=[pattern,mode];break
  assert witness is not None,('Ineffective control',name);out[name]=witness
 return dict(count=len(out),effective_IDO_controls=out,compile_or_oracle_failures_not_accepted=True)

def native_suite():
 rows=[]
 for pattern,mode in itertools.product(range(64),range(16)):
  c=Case(pattern,mode,depth=bits(float((pattern*1919)%65536-32768)));initial=fixture(c);want,calls,obs=reference(initial,c)
  data=[pattern,mode,read(initial,OBJECT+8),read(initial,FACTOR),read(initial,DEPTH),read(want,OBJECT+8),read(want,FACTOR),read(want,DEPTH),calls[1][1],*calls[3][1][1:]]
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in data)+'}')
 body=(o/'selected-semantic-input.c').read_text();variants={'selected':body,**controls()};functions=[];parts=[]
 for name,text in variants.items():
  function='candidate_'+name.replace('-','_');functions.append(function);parts.append(text.replace(F,function))
 text='\n'.join(parts)+r'''
static const u32 rows[][12]={ROWS};
static const u32 values[]={VALUES};
static const u32 angles[]={ANGLES};
typedef void (*Callback)(s32);
static const u32 *row;static u32 ordinal,error;static s16 xyz[3];
static union{u32 w[64];u8 b[256];f32 f[64];} object;
f32 D_800A0830,D_800A0834;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void effect(u32 which){u32 p=row[0],mode=row[1];if(mode&1)object.w[2]=angles[(p+which+5)%(sizeof(angles)/sizeof(angles[0]))];if(mode&2)D_800A0830=real(values[(p+which+2)%(sizeof(values)/sizeof(values[0]))]);if(mode&4)D_800A0834=(f32)((s32)((p*131+which*17)%60000)-30000);}
u8 *func_151149AC(u8 id){if(id!=4||ordinal!=0)error=1;ordinal++;effect(0);return object.b;}
f32 func_150AD78C(f32 argument){if(ordinal!=1||!same(word(argument),row[8]))error=2;ordinal++;effect(1);return real(values[(row[0]+3)%(sizeof(values)/sizeof(values[0]))]);}
f32 func_150AD780(f32 argument){if(ordinal!=2||!same(word(argument),row[8]))error=3;ordinal++;effect(2);return real(values[(row[0]+6)%(sizeof(values)/sizeof(values[0]))]);}
void func_150A3444(s32 index,s16 x,s16 y,s16 z){if(ordinal!=3||index!=2)error=4;ordinal++;xyz[0]=x;xyz[1]=y;xyz[2]=z;}
void func_151749A0(s32 a,s32 b){if(ordinal!=4||a!=5||b!=3)error=5;ordinal++;}
static int one(Callback fn,const u32 *input){u32 i;row=input;ordinal=error=0;for(i=0;i<64;i++)object.w[i]=0xA5A5A5A5u;object.w[2]=row[2];D_800A0830=real(row[3]);D_800A0834=real(row[4]);xyz[0]=xyz[1]=xyz[2]=(s16)0x5A5A;
 fn((s32)0x87654321u);if(error||ordinal!=5)return 1;if(!same(object.w[2],row[5])||!same(word(D_800A0830),row[6])||!same(word(D_800A0834),row[7]))return 2;
 for(i=0;i<3;i++)if((u32)(s32)xyz[i]!=row[9+i])return 3;
 for(i=0;i<64;i++)if(i!=2&&object.w[i]!=0xA5A5A5A5u)return 4;return 0;}
static int run(void){Callback functions[]={FUNCTIONS};u32 n,i;for(n=0;n<sizeof(functions)/sizeof(functions[0]);n++){int rejected=0;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){int e=one(functions[n],rows[i]);if(n==0&&e)return e;if(e){rejected=1;break;}}if(n&&!rejected)return 50+n;}return 0;}
'''
 text=text.replace('ROWS',',\n'.join(rows)).replace('VALUES',','.join('0x%Xu'%v for v in VALUES)).replace('ANGLES',','.join('0x%Xu'%v for v in ANGLES)).replace('FUNCTIONS',','.join(functions))+START
 path=o/'native-origin.c';path.write_text(text);profiles={}
 for opt in('-O0','-O2','-O3'):
  binary=o/('native-origin'+opt);p=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],capture_output=True,text=True);binary.with_suffix('.diagnostics.txt').write_text(p.stdout+p.stderr);assert p.returncode==0 and not p.stderr,(opt,p.stdout,p.stderr);p=subprocess.run([str(binary)],capture_output=True,timeout=60);assert p.returncode==0,(opt,p.returncode);profiles[opt]=dict(exit=0,UBSan=True)
 return dict(cases_per_profile=len(rows),profiles=profiles,native_controls=len(functions)-1,all_effective=True,typed_lookup_trig_setter_counter_ABIs=True,late_depth_read_and_captured_angle=True,valid_allocated_nonalias_objects_only=True,NaN_payloads_not_asserted=True,casts_restricted_to_representable_s16=True)

def custom_sine(word,m):
 exponent=(word>>22)&511
 if exponent<0xE6:return word
 if exponent>=0x136:return 0
 def coefficient(at):return read(m,at)
 reduced=word;odd=0
 if exponent>=0xFF:
  scaled=fp(coefficient(0x8009F724),word,'mul');period=int(round(floating(scaled)));odd=period&1;period_word=bits(float(period))
  reduced=fp(reduced,fp(coefficient(0x8009F728),period_word,'mul'),'sub')
  reduced=fp(reduced,fp(coefficient(0x8009F72C),period_word,'mul'),'sub')
  coefficients=(0x8009F730,0x8009F734,0x8009F738,0x8009F73C)
 else:coefficients=(0x8009F714,0x8009F718,0x8009F71C,0x8009F720)
 squared=fp(reduced,reduced,'mul');poly=coefficient(coefficients[0])
 for at in coefficients[1:]:poly=fp(coefficient(at),fp(poly,squared,'mul'),'add')
 if exponent<0xFF:product=fp(poly,fp(squared,reduced,'mul'),'mul')
 else:product=fp(fp(poly,squared,'mul'),reduced,'mul')
 result=fp(product,reduced,'add');return result^(0x80000000 if odd else 0)

def provider_suite():
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();code={};identities={}
 providers=((LOOKUP,0x141E5C,28),(SECOND,0xDAC30,73),(SET,0xD08F4,28),(PHASE,0x1A1E50,22))
 for at,offset,n in providers:
  raw=rom[offset:offset+4*n];current=elf[elf_slot_offset(elf,at,n*4):elf_slot_offset(elf,at,n*4)+n*4];identities[hex(at)]=dict(words=n,current_byte_exact=current==raw)
  assert current==raw,('Provider differs from retail',hex(at))
  code.update({at+4*i:w for i,w in enumerate(struct.unpack('>%dI'%n,raw))})
 ims=images('actual-helpers');count=0;seen=set();LOOKUP_COUNT,LOOKUP_BASE,OUTPUT_BASE=0x800DBEF0,0x800DBEF4,0x800D3098
 angles=(0,0x80000000,1,0x3F800000,0xBF800000,bits(90.),bits(-180.),bits(10000.),0x7F7FFFFF,0x7F800000,0x7FC12345)
 for angle,slot,ticks,phase in itertools.product(angles,(0,1,3),(0,1,6,255),(0,8)):
  c=Case(phase=phase);initial=fixture(c);pool=0x50000;assert not STACK-1024<=pool<STACK+1024;put(initial,LOOKUP_COUNT,4);put(initial,LOOKUP_BASE,pool);put(initial,OUTPUT_BASE,OUT)
  for i in range(4):
   for j in range(160):initial[pool+i*160+j]=0xA5
   initial[pool+i*160+0x72]=4 if i==slot else 7;put(initial,pool+i*160+8,angle)
  for at in range(0x8009F710,0x8009F740,4):put(initial,at,struct.unpack('>I',elf[elf_slot_offset(elf,at,4):elf_slot_offset(elf,at,4)+4])[0])
  put(initial,0x800BE9E4,ticks);initial[0x800DD405]=slot;initial[0x800DD406]=slot+4
  want=dict(initial);radians=fp(angle,read(want,FACTOR),'mul');first=custom_sine(radians,want);second=custom_sine(fp(radians,read(want,0x8009F710),'add'),want);xyz=origin(radians,first,second,read(want,DEPTH));calls=[(LOOKUP,(4,)),(FIRST,radians),(SECOND,radians),(SET,(2,*xyz)),(PHASE,(5,3))]
  for i,v in enumerate(xyz):put(want,OUT+104+i*2,v&65535,2)
  timer=(slot+4+ticks)&255;want[0x800DD406]=timer
  if timer>5:want[0x800DD405]=0 if((slot+1)&255)>=3 else(slot+1)&255;want[0x800DD406]=0
  ms=[]
  for body in ims:
   m=Oracle(body,initial,c,connected=code).run();assert(public(m.memory),m.calls)==(public(want),calls),(hex(angle),slot,ticks,phase,m.calls,calls);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);seen.update(ms[0].visits&code.keys());count+=1
 return dict(cases=count,original_and_current_provider_identity=identities,visited_provider_words=len(seen),lookup_stride=160,output_stride=52,custom_cosine_falls_through_to_sine=True,default_nearest_even_reduction_only=True,IEEE_FCSR_hardware_not_claimed=True,lookup_missing_object_path_not_connected=True,provider_matching_credit=0)
