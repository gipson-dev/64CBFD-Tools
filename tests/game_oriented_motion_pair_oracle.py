"""Oriented displacement pair: finite semantics, aliases, reloads and retail trig."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.game_rotation_matrix_leaf_oracle import trig,COEFFICIENTS
from tools.tests.game_fixed_matrix_oracle import integer
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,CALLER,COS,SIN=0x15115E0C,0x15115EDC,0x150AD780,0x150AD78C
STATE,TARGET=0x30000,0x50000
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 mutation:int=0
 phase:int=0
 wrapper:int=0

def symbols(i=0):
 return dict(D_800A2FA0=(0x800A2FA0,0x3407FFC,0x2408000)[i],D_800A2FA4=(0x800A2FA4,0x3418000,0x2427FFC)[i],func_150AD780=(COS,0x17140000,0x17240000)[i],func_150AD78C=(SIN,0x17148000,0x17248000)[i],func_15115E0C=(ENTRY,0x17038000,0x1F00FFFC)[i])
def target(c):return (TARGET,STATE,STATE+0x68,STATE+0x64)[c.alias]
def public(m):return {a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base in(STATE,TARGET):m.update({base+i:0xA5 for i in range(-16,192)})
 for n in('D_800A2FA0','D_800A2FA4'):put(m,s[n],0x3C8EFA35)
 vals=(-32768,-1,0,32767)
 put(m,STATE+4,bits((-720.,-0.,0.,0.01,30.,45.,90.,360.)[c.index%8]))
 put(m,STATE+0x10,vals[c.index%4]&65535,2);put(m,STATE+0x14,vals[(c.index//4)%4]&65535,2)
 m[STATE+0x4F]=(0,1,4,5,0x80,0x84,0xFB,0xFF)[c.index%8]
 put(m,STATE+0x7C,bits((c.index-31)*0.25));put(m,STATE+0x80,bits((19-c.index)*0.5))
 t=target(c);put(m,t+0x14,bits((c.index-17)*0.75));put(m,t+0x1C,bits((31-c.index)*0.125));put(m,t+0x84,(0,0x4B,0x804B,0xFFFF)[(c.index//2)%4],2)
 return m
def returned(c,ordinal):return bits((0.,-0.,1.,-1.,0.25,-0.5,0.75,-0.125)[(c.index+3*ordinal)%8])
def effect(m,c,s,ordinal):
 t=target(c)
 if ordinal==0:
  if c.mutation&1:put(m,STATE+4,bits(-45.));put(m,s['D_800A2FA4'],bits(0.5))
  if c.mutation&2:
   put(m,STATE+0x10,0x8001,2);put(m,STATE+0x14,0x7FFE,2);put(m,t+0x14,bits(-17.25));put(m,t+0x1C,bits(6.5));m[STATE+0x4F]^=4
 else:
  if c.mutation&1:
   put(m,STATE+0x7C,bits(3.5));put(m,STATE+0x80,bits(-7.25));put(m,t+0x84,0x4B,2)
  if c.mutation&2:put(m,t+0x84,0,2);m[STATE+0x4F]^=4
def reference(initial,c,s,actual=False):
 m=dict(initial);t=target(c);oldx,oldz=read(m,STATE+0x7C),read(m,STATE+0x80);calls=[];values=[]
 if c.wrapper:calls.append((s['func_15115E0C'],(STATE,t)))
 constants={a:read(m,a) for a in range(COEFFICIENTS,COEFFICIENTS+48,4)} if actual else {}
 for j,(name,scale) in enumerate((('func_150AD780','D_800A2FA0'),('func_150AD78C','D_800A2FA4'))):
  arg=fp(read(m,STATE+4),read(m,s[scale]),'mul');calls.append((s[name],(arg,)))
  values.append(trig(arg,(COS,SIN)[j],constants) if actual else returned(c,j))
  if not actual:effect(m,c,s,j)
 cosine,sine=values
 signed=lambda n:((n&65535)^32768)-32768
 dx=fp(read(m,t+0x14),bits(float(signed(read(m,STATE+0x10,2)))),'sub')
 dz=fp(read(m,t+0x1C),bits(float(signed(read(m,STATE+0x14,2)))),'sub')
 if m[STATE+0x4F]&4:
  x=fp(read(m,STATE+0x7C),fp(fp(sine,dx,'mul'),fp(cosine,dz,'mul'),'add'),'add')
  z=fp(read(m,STATE+0x80),fp(fp(sine,dz,'mul'),fp(cosine,dx,'mul'),'add'),'sub')
  put(m,STATE+0x7C,x);put(m,STATE+0x80,z)
 if c.wrapper and read(m,t+0x84,2)==0x4B:
  x,z=read(m,STATE+0x7C),read(m,STATE+0x80)
  put(m,STATE+0x7C,fp(x,fp(fp(x,oldx,'sub'),bits(4.),'mul'),'add'))
  put(m,STATE+0x80,fp(z,fp(fp(z,oldz,'sub'),bits(4.),'mul'),'add'))
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},arguments=(STATE,target(c)),connected=connected)
  self.before_f=self.f[:]
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==36:self.f[word>>6&31]=integer(self.f[word>>11&31],0)
  elif word>>26==17 and word>>21&31==16 and word&63==7:self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
  else:super().execute(word)
 def record_call(self,t):
  if t==self.s['func_15115E0C']:a=tuple(self.arguments(2))
  else:assert t in(self.s['func_150AD780'],self.s['func_150AD78C']),hex(t);a=(self.f[12],)
  self.calls.append((t,a))
 def hook(self,t):
  j=0 if t==self.s['func_150AD780'] else 1
  assert t in(self.s['func_150AD780'],self.s['func_150AD78C'])
  effect(self.memory,self.c,self.s,j)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=returned(self.c,j);self.hi,self.lo=0xA5000010,0xA5000011

def link(obj,function,label,entry,s,size):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[function],relocs,function,s)
 assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(size//4),sections(p.with_suffix('.elf'))['.text'][1][:size]))
def programs(i):
 s=symbols(i);entry=s['func_15115E0C'];caller=(CALLER,0x17048000,0x1F01FFFC)[i]
 objects=('qualified-padded.o','make-shadow/src/game/generated_142560.c.o','selected-final.o')
 roots=[link(o/('original-'+source.FUNCTION+'.o'),source.FUNCTION,'motion-root-%d-0'%i,entry,s,208)]
 wrappers=[link(o/('original-'+source.CALLER+'.o'),source.CALLER,'motion-caller-%d-0'%i,caller,s,140)]
 for j,n in enumerate(objects,1):
  roots.append(link(o/n,source.FUNCTION,'motion-root-%d-%d'%(i,j),entry,s,208));wrappers.append(link(o/n,source.CALLER,'motion-caller-%d-%d'%(i,j),caller,s,140))
 assert all(x==roots[0] for x in roots) and all(x==wrappers[0] for x in wrappers)
 return s,entry,caller,roots,wrappers
def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,program,initial=None,mathcode=None):
 s,entry,caller,roots,wrappers=program;initial=fixture(c,s) if initial is None else initial
 expected,calls=reference(initial,c,s,mathcode is not None);models=[]
 for root,wrap in zip(roots,wrappers):
  connected=dict(mathcode or {});connected.update(zip(range(entry,entry+208,4),root))
  m=Oracle(wrap if c.wrapper else root,initial,c,s,caller if c.wrapper else entry,connected).run()
  assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls,[(hex(a),m.memory.get(a),expected.get(a)) for a in set(m.memory)&set(expected) if m.memory[a]!=expected[a]][:8])
  assert all(m.r[k]==m.before[k] for k in(*range(16,24),28,29,30,31)) and m.f[20:]==m.before_f[20:]
  models.append(m)
 assert all(state(m)==state(models[0]) for m in models)
 return models[0]
def guest():
 count=0;seen=set();ps=[]
 for i in range(3):
  p=programs(i);ps.append(p)
  for index,alias,mode,wrapper in itertools.product(range(64 if i==0 else 32),range(4),range(4) if i==0 else(0,3),(0,1)):
   m=compare(Case(index,alias,mode,8 if index&1 else 0,wrapper),p);seen.update(m.visits);count+=1
 assert all(ENTRY+4*j in seen for j in range(52)) and all(CALLER+4*j in seen for j in range(35))
 return dict(cases=count,executions=count*4,rebases=3,all_52_root_and_35_caller_words_executed=True,all_four_programs_full_state_and_trace_equal=True,alias_layouts=4,reloaded_second_angle_scale_and_post_helper_fields=True,wrapper_precall_snapshot_and_live_type_gate=True),ps[0]
def faults(p):
 s,entry,caller,roots,wrappers=p;count=0
 for c in(Case(2),Case(7,2,3),Case(3,3,1,8,1),Case(6,0,0,0,1)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   models=[]
   for root,wrap in zip(roots,wrappers):
    code=dict(zip(range(entry,entry+208,4),root));m=Oracle(wrap if c.wrapper else root,initial,c,s,caller if c.wrapper else entry,code);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing fault prefix')
    models.append(state(m))
   assert all(x==models[0] for x in models);count+=1
 return dict(prefixes=count,executions=count*4,all_machine_states_equal=True,guest_access_order_only=True)
def connected(p):
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes()
 words=struct.unpack_from('>76I',before,source.elf_slot_offset(before,COS,304));assert words==struct.unpack_from('>76I',rom,0xDAC30)
 code=dict(zip(range(COS,COS+304,4),words));constants={a:struct.unpack_from('>I',before,source.elf_slot_offset(before,a,4))[0] for a in range(COEFFICIENTS,COEFFICIENTS+48,4)}
 count=0;seen=set()
 for index,alias,wrapper in itertools.product(range(128),range(4),(0,1)):
  c=Case(index,alias,0,8 if index&1 else 0,wrapper);m=fixture(c,p[0])
  for a,v in constants.items():put(m,a,v)
  # Include the tiny and huge finite argument paths as well as ordinary angles.
  put(m,STATE+4,(bits((index-64)*17.25),1,0x71800000,0x80000001)[(index//16)%4])
  result=compare(c,p,m,code);seen.update(result.visits);count+=1
 return dict(cases=count,executions=count*4,original_trig_span_words=76,original_trig_words_executed=sum(COS+4*j in seen for j in range(76)),retail_code_and_12_coefficient_words_pinned=True,finite_polynomial_reference=True,full_FCSR_and_NaN_payloads_not_modeled=True)
def census():
 rom=(r/'conker/conker.us.bin').read_bytes();rows={}
 for name,va in((source.FUNCTION,ENTRY),(source.CALLER,CALLER)):
  words=struct.unpack_from('>%dI'%(len(rom)//4),rom);calls=[4*i for i,w in enumerate(words) if w>>26==3 and (w&0x3FFFFFF)*4==(va&0x0FFFFFFF)];jumps=[4*i for i,w in enumerate(words) if w>>26==2 and (w&0x3FFFFFF)*4==(va&0x0FFFFFFF)];ptrs=[4*i for i,w in enumerate(words) if w==va]
  rows[name]=dict(aligned_ROM_JALs=calls,aligned_ROM_Js=jumps,aligned_ROM_pointer_literals=ptrs)
 assert rows[source.FUNCTION]==dict(aligned_ROM_JALs=[0x1433AC],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[]),rows
 assert rows[source.CALLER]==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22D790]),rows
 rows.update(callback_table='D_80088C90',callback_byte_offset=0x40,callback_VA='0x80088CD0',root_ABI='void(u8 *state,u8 *target)',caller_ABI='void(u8 *state,u8 *target)')
 (o/'caller-census.json').write_text(json.dumps(rows,indent=2)+'\n');return rows

def native():
 selected=source.SELECTED;caller=source.CALLER_SELECTED
 controls=(('wrong-first-scale',selected.replace('* D_800A2FA0','* 0.5f'),caller),
  ('cached-angle',selected.replace('    sine =','    sine =').replace('*(f32 *)(state + 4) * D_800A2FA4','savedAngle * D_800A2FA4').replace('    cosine =','    f32 savedAngle = *(f32 *)(state + 4);\n    cosine ='),caller),
  ('unsigned-origin',selected.replace('(s16 *)(state + 0x10)','(u16 *)(state + 0x10)'),caller),
  ('wrong-flag',selected.replace('(state[0x4F] & 4) == 4','state[0x4F] != 0'),caller),
  ('wrong-z-sign',selected.replace('0x80) -=','0x80) +='),caller),
  ('wrong-x-coefficient',selected.replace('sine * deltaX + cosine * deltaZ','cosine * deltaX + sine * deltaZ'),caller),
  ('wrong-wrapper-gain',selected,caller.replace('* 4.0f','* 2.0f')),
  ('cached-target-type',selected,caller.replace('    old_x =','    u16 savedType = *(u16 *)(arg1 + 0x84);\n    old_x =',1).replace('*(u16 *) (arg1 + 0x84)','savedType')))
 assert all(a!=selected or b!=caller for _,a,b in controls)
 def array(values):return '{'+','.join('0x%Xu'%v for v in values)+'}'
 def image(m,base,fields):
  v=bytearray(m[base+j] for j in range(160))
  for at,n in fields:v[at:at+n]=v[at:at+n][::-1]
  return list(v)
 sf=((4,4),(0x10,2),(0x14,2),(0x7C,4),(0x80,4));tf=((0x14,4),(0x1C,4),(0x84,2));rows=[]
 for index,mode,wrapper in itertools.product(range(128),range(4),(0,1)):
  c=Case(index,0,mode,0,wrapper);s=symbols();initial=fixture(c,s);expected,calls=reference(initial,c,s)
  rows.append('{%d,%d,%d,%s,%s,%s,%s,%s,%s}'%(index,mode,wrapper,array(image(initial,STATE,sf)),array(image(initial,TARGET,tf)),array(image(expected,STATE,sf)),array(image(expected,TARGET,tf)),array([v[1][0] for v in calls if v[0] in(COS,SIN)]),array([returned(c,0),returned(c,1)])))
 code=source.HEADERS+r'''
typedef struct{u32 index,mode,wrapper;u8 state[160],target[160],expectedState[160],expectedTarget[160];u32 args[2],returns[2];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[48];u8 bytes[192];}Record;
static Record stateData,targetData;static u8 *state,*target;static Case *current;static u32 callCount,error;
f32 D_800A2FA0,D_800A2FA4;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
static f32 call(f32 x,u32 ordinal){u32 mode=current->mode;callCount++;if(callCount!=ordinal+1||bits(x)!=current->args[ordinal])error=1;
 if(ordinal==0){
  if(mode&1){*(f32*)(state+4)=-45.0f;D_800A2FA4=0.5f;}
  if(mode&2){*(s16*)(state+0x10)=-32767;*(s16*)(state+0x14)=32766;*(f32*)(target+0x14)=-17.25f;*(f32*)(target+0x1C)=6.5f;state[0x4F]^=4;}
 }else{
  if(mode&1){*(f32*)(state+0x7C)=3.5f;*(f32*)(state+0x80)=-7.25f;*(u16*)(target+0x84)=0x4B;}
  if(mode&2){*(u16*)(target+0x84)=0;state[0x4F]^=4;}
 }
 return floating(current->returns[ordinal]);
}
f32 func_150AD780(f32 x){return call(x,0);}
f32 func_150AD78C(f32 x){return call(x,1);}
'''
 for j,(_,a,b) in enumerate((('valid',selected,caller),)+controls):
  code+=(a+'\n'+b).replace('func_15115E0C(', 'root_%d('%j).replace('func_15115EDC(', 'wrapper_%d('%j)+'\n'
 code+='static void (*roots[])(u8*,u8*)={'+','.join('root_%d'%j for j in range(9))+'};\n'
 code+='static void (*wrappers[])(u8*,u8*)={'+','.join('wrapper_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  current=&cases[n];state=stateData.bytes+16;target=targetData.bytes+16;callCount=error=0;D_800A2FA0=floating(0x3C8EFA35u);D_800A2FA4=D_800A2FA0;
  for(k=0;k<192;k++){stateData.bytes[k]=0xA5;targetData.bytes[k]=0xA5;}
  for(k=0;k<160;k++){state[k]=current->state[k];target[k]=current->target[k];}
  if(current->wrapper)wrappers[j](state,target);else roots[j](state,target);
  failed=error||callCount!=2;
  for(k=0;k<192;k++)if(stateData.bytes[k]!=(k>=16&&k<176?current->expectedState[k-16]:0xA5)||targetData.bytes[k]!=(k>=16&&k<176?current->expectedTarget[k-16]:0xA5))failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==255u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code)
  q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  result.append(dict(profile=opt,cases=len(rows),controls=[v[0]for v in controls],all_eight_controls_effective=True,UBSan=True,canaries=True,finite_inputs=True))
 return result
def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core
 paths=[o/('before-'+source.SOURCE.replace('/','_')),o/'qualified-padded.o',o/'first-linked.elf']
 fingerprint=source.sha(b''.join(p.read_bytes() for p in paths)+Path(__file__).read_bytes()+source.SELECTED.encode()+source.CALLER_SELECTED.encode())
 saved=o/'runtime-qualification.json'
 if saved.exists():
  q=json.loads(saved.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census();g,p=guest();q=dict(fingerprint=fingerprint,guest=g,faults=faults(p),connected=connected(p),native=native())
 saved.write_text(json.dumps(q,indent=2)+'\n');return q
