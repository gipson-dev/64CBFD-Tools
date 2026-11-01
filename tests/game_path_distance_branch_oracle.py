"""Strict path-distance callback, float32 operations and complete script helper."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,HELPER,ACTOR,OTHER,TABLE,ROW,SCRIPT,MARK,DISPATCH=0x150781F4,0x15075400,0x30000,0x40000,0x50000,0x60000,0x70000,0x80000,0x80086730
NAMES=('D_800D1890','D_800D1891','D_800D1892','D_800D1893')
half=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
 index:int=0
 kind:int=0
 alias:int=0
 phase:int=0
 override:int=-1

def symbols(i=0,alias=0):
 if not i:s=dict(D_800D154C=0x800D154C,D_800D2104=0x800D2104,func_15075400=HELPER,**dict(zip(NAMES,range(0x800D1890,0x800D1894))))
 else:
  base=(0x2737FFC,0x3438000)[i-1];commands=(0x2747FFE,0x3447FFF)[i-1]
  s=dict(D_800D154C=base,D_800D2104=(0x2758000,0x3457FFC)[i-1],func_15075400=(0x17048000,0x1F01FFFC)[i-1],**dict(zip(NAMES,range(commands,commands+4))))
 if alias==1:s['D_800D2104']=ACTOR+0x14
 if alias==2:s[NAMES[3]]=ACTOR+0x14
 if alias==3:s[NAMES[2]]=s[NAMES[1]]
 return s

def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for a in(ACTOR,OTHER):
  m.update({a+i:0xA5 for i in range(-16,0x340)});m[a+0x13F]=(c.index*3)&255;put(m,a+0x218,SCRIPT)
 m.update({SCRIPT+i:0 for i in range(-8,1024)});put(m,MARK,0)
 command=(c.index*37+247)&255;node=(c.index*17)&255;radius=(c.index*3+3)&255;mode=c.index&255 if c.override<0 else c.override
 for name,v in zip(NAMES,(command,node,mode,radius)):m[s[name]]=v
 x=(-32768,-1,0,32767)[c.index%4];z=(32767,0,-1,-32768)[c.index%4]
 radius_value=float(radius*8)
 if c.kind==0:d=0.
 elif c.kind==1:d=radius_value
 elif c.kind==2:d=max(0.,radius_value-0.5)
 elif c.kind==3:d=radius_value+0.5
 else:d=(math.inf,-math.inf,math.nan,1e20)[c.index%4]
 put(m,ACTOR+0x14,bits(float(x)-d));put(m,ACTOR+0x1C,bits(float(z)))
 put(m,s['D_800D154C'],ACTOR);put(m,s['D_800D2104'],TABLE)
 # Input aliases can change the node or mode; lay out the actual selected row.
 for name,v in zip(NAMES,(command,node,mode,radius)):
  if not(c.alias==2 and name==NAMES[3]):m[s[name]]=v
 actual_node=m[s[NAMES[1]]];group=m[ACTOR+0x13F];put(m,TABLE+group*4,ROW)
 for n in{actual_node,max(0,actual_node-1),min(256,actual_node+1)}:
  for off,value in((0,x),(2,123),(4,z),(6,-321)):put(m,ROW+(n+1)*8+off,value&65535,2)
 # Mix normal packets and sentinels; a matching sentinel backs up five bytes
 # after its one-byte advance, exactly as the original typed-pointer helper.
 pattern=c.index%5
 if pattern==1:m[SCRIPT]=command if command>=247 else 247
 elif pattern==2:m[SCRIPT]=248 if command!=248 else 249;m[SCRIPT+1]=0;m[SCRIPT+6]=command if command>=247 else 255
 elif pattern==4:
  for j in range(100):m[SCRIPT+j*5]=249 if command!=249 else 250
 return m

def effect(m,c,s):
 if c.index&1:
  a=read(m,s['D_800D154C']);put(m,a+0x20,0x12345678);put(m,s['D_800D154C'],OTHER);put(m,s['D_800D2104'],TABLE)
  for name in NAMES:m[s[name]]=0xA7
 put(m,MARK,0xCA110000|c.index)

def branch_info(m,s):
 a=read(m,s['D_800D154C']);group=m[a+0x13F];node=m[s[NAMES[1]]]+1;row=read(m,read(m,s['D_800D2104'])+group*4)+node*8
 dx=fp(bits(float(half(read(m,row,2)))),read(m,a+0x14),'sub');dz=fp(bits(float(half(read(m,row+4,2)))),read(m,a+0x1C),'sub')
 total=fp(fp(dx,dx,'mul'),fp(dz,dz,'mul'),'add');distance=floating(bits(math.sqrt(floating(total))))
 radius=float(m[s[NAMES[3]]]*8);mode=m[s[NAMES[2]]]
 return (distance<radius if mode==0 else radius<distance),m[s[NAMES[0]]]

def helper_reference(m,s,arg):
 a=read(m,s['D_800D154C'])
 if arg<247:put(m,a+0x218,(read(m,a+0x218)+5*arg)&0xFFFFFFFF);return
 for _ in range(100):
  a=read(m,s['D_800D154C']);cursor=read(m,a+0x218);opcode=m[cursor];put(m,a+0x218,cursor+(5 if opcode<247 else 1))
  if opcode>=247 and opcode==arg:
   a=read(m,s['D_800D154C']);put(m,a+0x218,(read(m,a+0x218)-5)&0xFFFFFFFF);break

def reference(initial,c,s,connected=False):
 m=dict(initial);take,arg=branch_info(m,s);calls=[]
 if take:
  calls=[(s['func_15075400'],(arg,))]
  if connected:helper_reference(m,s,arg)
  else:effect(m,c,s)
 return public(m),calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},arguments=(),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==4:self.f[w>>6&31]=bits(math.sqrt(floating(self.f[w>>11&31])));self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t in(ENTRY,self.s['func_15075400']),hex(t);self.calls.append((t,tuple(self.arguments(0 if t==ENTRY else 1))))
 def hook(self,t):
  assert t==self.s['func_15075400'];effect(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,0xDEADBEEF

def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 raw=sections(p.with_suffix('.elf'))['.text'][1];return list(struct.unpack('>%dI'%(len(raw)//4),raw))[:54]

def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17007FFC,0x1F007FFC)[i];paths=('original-func_150781F4.o','qualified-padded.o','make-shadow/src/game_A28B0.c.o','selected-final.o')
 ps=[link(o/n,'distance-program-%d-%d-%d'%(i,alias,j),entry,s)for j,n in enumerate(paths)];assert all(v==ps[0]for v in ps);return s,entry,ps
def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p,code=None):
 s,entry,ps=p;initial=fixture(c,s);expected,calls=reference(initial,c,s,code is not None);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,code).run();assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 assert all(state(v)==state(models[0])for v in models);return models[0]

def guest():
 count=0;seen=set();taken=set();p0=None
 for i,alias in itertools.product(range(3),range(4)):
  p=programs(i,alias)
  if not i and not alias:p0=p
  for index,kind,phase in itertools.product(range(256 if i==0 else 64),range(4),(0,8)):
   m=compare(Case(index,kind,alias,phase),p);seen.update(m.visits);taken.add(bool(m.calls));count+=1
 for index in range(4):compare(Case(index,4),p0);count+=1
 assert set(range(ENTRY,ENTRY+216,4))<=seen and taken=={False,True}
 return dict(cases=count,executions=count*4,rebases=3,alias_layouts=4,all_54_words_executed=True,all_256_input_bytes=True,nonfinite_guest_cases=4,four_programs_full_state_equal=True),p0

def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(0,0),Case(0,3),Case(255,3,phase=8)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing distance access boundary')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,complete_states_equal=True)

def connected():
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>38I',rom,0xA28B0)
 assert words==struct.unpack_from('>38I',before,source.elf_slot_offset(before,HELPER,152));code=dict(zip(range(HELPER,HELPER+152,4),words));p=programs(0);count=0;seen=set()
 for index,kind,phase in itertools.product(range(256),(0,3),(0,8)):
  c=Case(index,kind,phase=phase,override=0 if kind==0 else 1);m=compare(c,p,code);seen.update(m.visits);count+=1
 assert set(range(HELPER,HELPER+152,4))<=seen
 return dict(cases=count,executions=count*4,original_helper_words=38,all_helper_words_executed=True,fast_advance_and_100_scan_and_matching_sentinel=True,matching_sentinel_net_cursor_minus_4=True,no_nested_providers=True)

class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1507BD68:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)

def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes();va=0x1507BD00;body=struct.unpack_from('>29I',rom,va-0x15000000+0x2D4B0)
 assert body==struct.unpack_from('>29I',before,source.elf_slot_offset(before,va,116));count=0;seen=set();s,entry,ps=programs(0)
 for index,opcode,poison,phase in itertools.product((0,1,127,250,255),(161,247,255),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
  c=Case(index,3,phase=phase);initial=fixture(c,s);packet=[opcode,*[initial[s[n]]for n in NAMES]]
  for j,v in enumerate(packet):initial[SCRIPT+j]=v
  put(initial,ACTOR+0x218,SCRIPT);put(initial,DISPATCH+161*4,ENTRY);expected=dict(initial)
  if opcode==161:
   for name,v in zip(NAMES,packet[1:]):expected[s[name]]=v
   expected,calls=reference(expected,c,s);put(expected,ACTOR+0x218,SCRIPT+5)
  else:calls=[];put(expected,ACTOR+0x218,SCRIPT+1)
  for words in ps:
   code=dict(zip(range(entry,entry+216,4),words));m=Oracle(body,initial,c,s,va,code);m.r[16]=ACTOR
   for reg,name in zip((17,18,19,20),NAMES):m.r[reg]=s[name]
   m.r[21]=DISPATCH;m.before=m.r[:];m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=(0x1507BD74,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing script window boundary')
   assert public(m.memory)==public(expected)and m.calls==([(ENTRY,())]+calls if opcode==161 else[])and m.poison_hits==int(opcode==161)
   seen.update(m.visits)
  count+=1
 assert set(range(va,va+116,4))-seen=={va+0x20}
 return dict(cases=count,executions=count*4,original_window_words=29,reachable_words=28,return_poisons=4,void_return_ignored=True,packet_advance_5_or_1=True,full_dispatcher_emulation=False)

class WrapperPoison(WindowCode):
 def __getitem__(self,pc):
  if pc==0x15079918:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)

def wrapper():
 va=0x150798F8;rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes();words=struct.unpack_from('>12I',rom,0xA6DA8)
 assert words==struct.unpack_from('>12I',before,source.elf_slot_offset(before,va,48));s,entry,ps=programs(0);count=0;seen=set()
 for index,kind,phase,poison in itertools.product((0,1,127,255),(0,3),(0,8),(0,1,0x80000000,0xFFFFFFFF)):
  c=Case(index,kind,phase=phase);initial=fixture(c,s);initial[ACTOR+0x21E]=initial[s[NAMES[1]]];initial[s[NAMES[1]]]^=0x55
  expected=dict(initial);expected[s[NAMES[1]]]=expected[ACTOR+0x21E];expected,calls=reference(expected,c,s)
  models=[]
  for root in ps:
   code=dict(zip(range(entry,entry+216,4),root));m=Oracle(words,initial,c,s,va,code);m.poison=poison;m.poison_hits=0;m.code=WrapperPoison(m.code,m);m.code.ends=();m.run()
   assert(public(m.memory),m.calls)==(expected,[(ENTRY,())]+calls)and m.poison_hits==1
   assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];seen.update(m.visits);models.append(m)
  assert all(state(m)==state(models[0])for m in models);count+=1
 assert set(range(va,va+48,4))<=seen
 return dict(cases=count,executions=count*4,complete_original_wrapper_words=12,all_wrapper_words_executed=True,node_copy_and_return_poisons_verified=True)

def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom)
 q=dict(aligned_ROM_JALs=[i*4 for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF],aligned_ROM_Js=[i*4 for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF],aligned_ROM_pointer_literals=[i*4 for i,w in enumerate(words)if w==ENTRY])
 assert q==dict(aligned_ROM_JALs=[0xA6DC0],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22B474]);q.update(row=161,ABI='void(void)',callback_table='D_80086730');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')

def native():
 selected=source.SELECTED
 controls=[('unsigned-x',selected.replace('pathNode->x -','(u16)pathNode->x -')),('unsigned-z',selected.replace('pathNode->z -','(u16)pathNode->z -')),('wrong-node',selected.replace('D_800D1891 + 1','D_800D1891')),('wrong-radius',selected.replace('D_800D1893 << 3','D_800D1893 << 2')),('inclusive-inside',selected.replace('distance < deltaX','distance <= deltaX')),('inclusive-outside',selected.replace('deltaX < distance','deltaX <= distance')),('mode-one-only',selected.replace('D_800D1892 != 0','D_800D1892 == 1')),('missing-helper',selected.replace('        func_15075400(D_800D1890);',''))]
 assert all(text!=selected for _,text in controls)
 rows=[]
 for n in range(1024):
  c=Case(n&255,n>>8);s=symbols();m=fixture(c,s);take,arg=branch_info(m,s);node=m[s[NAMES[1]]];group=m[ACTOR+0x13F];p=read(m,TABLE+group*4)+(node+1)*8
  rows.append('{'+','.join(str(v)for v in(m[s[NAMES[0]]],node,m[s[NAMES[2]]],m[s[NAMES[3]]],half(read(m,p,2)),half(read(m,p+4,2))))+',0x%Xu,0x%Xu,%d}'%(read(m,ACTOR+0x14),read(m,ACTOR+0x1C),take))
 functions=selected+'\n'+'\n'.join(text.replace('func_150781F4','negative_'+str(i))for i,(_,text)in enumerate(controls))
 harness=r'''
struct C{u8 command,node,mode,radius;s16 x,z;u32 px,pz;u8 take;};static const struct C cases[]={ROWS};static const struct C*c;
static struct127 actor,other,expected;struct127*D_800D154C;u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;
static PathNode8 nodes[258];static PathNode8*table[1];s32*D_800D2104;static u32 calls,bad;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
f32 sqrtf(f32 v){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(v));return out;}
void func_15075400(s32 arg){calls++;if(arg!=c->command)bad=1;((u8*)&actor)[0x20]=0x12;D_800D154C=&other;D_800D1890=D_800D1891=D_800D1892=D_800D1893=0xA7;}
static void setup(void){u32 i;for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=((u8*)&other)[i]=0xA5;
for(i=0;i<258;i++){nodes[i].x=1234;nodes[i].z=-2345;nodes[i].pad2=nodes[i].pad6=(s16)0xA5A5;}
nodes[(u32)c->node+1].x=c->x;nodes[(u32)c->node+1].z=c->z;actor.unk13F=0;actor.x_position=real(c->px);actor.z_position=real(c->pz);
D_800D154C=&actor;table[0]=nodes;D_800D2104=(s32*)table;D_800D1890=c->command;D_800D1891=c->node;D_800D1892=c->mode;D_800D1893=c->radius;calls=bad=0;
for(i=0;i<sizeof(actor);i++)((u8*)&expected)[i]=((u8*)&actor)[i];if(c->take)((u8*)&expected)[0x20]=0x12;}
static int changed(void){u32 i;if(bad||calls!=c->take||D_800D154C!=(c->take?&other:&actor)||D_800D2104!=(s32*)table||table[0]!=nodes)return 1;
if(D_800D1890!=(c->take?0xA7:c->command)||D_800D1891!=(c->take?0xA7:c->node)||D_800D1892!=(c->take?0xA7:c->mode)||D_800D1893!=(c->take?0xA7:c->radius))return 1;
for(i=0;i<sizeof(actor);i++)if(((u8*)&actor)[i]!=((u8*)&expected)[i]||((u8*)&other)[i]!=0xA5)return 1;
for(i=0;i<258;i++)if(nodes[i].x!=(i==(u32)c->node+1?c->x:1234)||nodes[i].z!=(i==(u32)c->node+1?c->z:-2345)||nodes[i].pad2!=(s16)0xA5A5||nodes[i].pad6!=(s16)0xA5A5)return 1;return 0;}
static int run(void){u32 n,j,hits[8]={0};void(*f[8])(void)={FUNCTIONS};if(sizeof(void*)!=4||sizeof(PathNode8)!=8)return 20;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];setup();func_150781F4();if(changed())return 21;for(j=0;j<8;j++){setup();f[j]();hits[j]|=(u32)changed();}}
for(j=0;j<8;j++)if(!hits[j])return 30+(int)j;return 0;}
'''.replace('ROWS',',\n'.join(rows)).replace('FUNCTIONS',','.join('negative_'+str(i)for i in range(8)))
 result=[];code=source.HEADERS+functions+harness+START
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-mstackrealign','-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode);result.append(dict(profile=opt,cases=1024,UBSan=True,full_actor_and_path_canaries=True,all_eight_controls_effective=True,controls=[n for n,_ in controls],sqrt_instruction='SSE sqrtss',native_domain='finite coordinates',pointer_aliases_guest_only=True))
 return result

def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core;names=('original-func_150781F4.o','selected-final.o','qualified-padded.o','make-shadow/src/game_A28B0.c.o','before-conker_build_conker.us.elf','before-conker_conker.us.bin')
 fingerprint=source.sha(Path(__file__).read_bytes()+source.SELECTED.encode()+b''.join((o/n).read_bytes()for n in names));path=o/'runtime-qualification.json'
 if path.exists():
  q=json.loads(path.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census();g,p=guest();q=dict(fingerprint=fingerprint,guest=g,faults=faults(p),connected=connected(),callers=callers(),direct_wrapper=wrapper(),native=native())
 path.write_text(json.dumps(q,indent=2)+'\n');return q
