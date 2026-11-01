"""Signed path coordinates, live lookup aliases and original script callback."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_animation_timeline_oracle import bits
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,ACTOR,OTHER,TABLE,ROW,SCRIPT,DISPATCH=0x15077DBC,0x30000,0x3F800000,0x40000,0x50000,0x60000,0x80086730
NAMES=('D_800D1890','D_800D1891','D_800D1892','D_800D1893')
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0

def symbols(i=0,alias=0):
 if not i:s=dict(D_800D154C=0x800D154C,D_800D2104=0x800D2104,**dict(zip(NAMES,range(0x800D1890,0x800D1894))))
 else:
  base=(0x2737FFC,0x3438000)[i-1];commands=(0x2747FFE,0x3447FFF)[i-1]
  s=dict(D_800D154C=base,D_800D2104=(0x2758000,0x3457FFC)[i-1],**dict(zip(NAMES,range(commands,commands+4))))
 if alias==4:s['D_800D2104']=ACTOR+0x14
 return s

def actor(c,s):return s['D_800D154C']-(0x14,0x18,0x1C)[c.alias-1]if c.alias in(1,2,3)else ACTOR
def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def fixture(c,s):
 a=actor(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 g=(c.index*3)&255;old=(c.index*17+251)&255;node=old if c.index==250 else c.index
 for base in(a,OTHER):
  m.update({base+i:0xA5 for i in range(-16,0x270)})
  m[base+0x13F]=g;m[base+0x21E]=old
 for table in((TABLE,OTHER)if c.alias==4 else(TABLE,)):
  for group in(g,):
   row=ROW+(0x4000 if table==OTHER else 0)
   put(m,table+group*4,row)
   for n in{node,old,min(node+1,256),max(node-1,0)}:
    p=row+(n+1)*8
    for off,value in zip((0,2,4),((-32768,-1,0,1,32767,257,-12345,12345)[(c.index+j)%8]for j in range(3))):put(m,p+off,value&65535,2)
    if table==OTHER:put(m,p+2,1234,2);put(m,p+4,(-2345)&65535,2)
 # Pointer/table aliases transition on an exactly representable float 1.0 store.
 if c.alias in(1,2,3,4,6):
  axis=c.alias-1 if c.alias in(1,2,3)else 0
  put(m,ROW+(node+1)*8+axis*2,1,2)
 if c.alias==5:
  put(m,TABLE+g*4,a+0x14-(node+1)*8)
  for off,value in((0,1),(2,-123),(4,32767)):put(m,a+0x14+off,value&65535,2)
 if c.alias==6:
  # The first output overwrites the selected table row pointer itself.
  put(m,s['D_800D2104'],a+0x14-g*4)
  put(m,a+0x14,ROW)
  for off,value in((2,(-222)&65535),(4,333)):put(m,OTHER+(node+1)*8+off,value,2)
 else:put(m,s['D_800D2104'],TABLE)
 for j,name in enumerate(NAMES):m[s[name]]=(c.index+j*37)&255
 put(m,s['D_800D154C'],a)
 return m

def reference(initial,c,s):
 m=dict(initial);command=m[s['D_800D1890']]
 if command!=250:m[read(m,s['D_800D154C'])+0x21E]=command
 for axis in range(3):
  a=read(m,s['D_800D154C']);group=m[a+0x13F];node=m[a+0x21E]
  row=read(m,read(m,s['D_800D2104'])+group*4)
  value=half(read(m,row+(node+1)*8+axis*2,2));put(m,a+0x14+axis*4,bits(float(value)))
 return public(m)

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},arguments=(),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):
  assert t==ENTRY,hex(t);self.calls.append((t,()))
 def hook(self,t):raise AssertionError('Unbounded path command provider')

def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 raw=sections(p.with_suffix('.elf'))['.text'][1]
 return list(struct.unpack('>%dI'%(len(raw)//4),raw))

def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17007FFC,0x1F007FFC)[i]
 paths=('original-func_15077DBC.o','qualified-padded.o','make-shadow/src/game_A28B0.c.o','selected-final.o')
 ps=[link(o/n,'path-program-%d-%d-%d'%(i,alias,j),entry,s)[:56]for j,n in enumerate(paths)]
 assert all(v==ps[0]for v in ps);return s,entry,ps

def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p):
 s,entry,ps=p;initial=fixture(c,s);expected=reference(initial,c,s);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry).run();assert public(m.memory)==expected,(c,[(hex(a),expected[a],m.memory.get(a))for a in expected if expected[a]!=m.memory.get(a)][:8])
  assert not m.calls and all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 assert all(state(v)==state(models[0])for v in models);return models[0]

def guest():
 count=0;seen=set();p0=None
 for i,alias in itertools.product(range(3),range(7)):
  p=programs(i,alias)
  if not i and not alias:p0=p
  for index,phase in itertools.product(range(256),(0,8)):
   m=compare(Case(index,alias,phase),p);seen.update(m.visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=seen
 return dict(cases=count,executions=count*4,rebases=3,alias_layouts=7,all_256_commands=True,all_56_words_executed=True,four_programs_full_state_equal=True),p0

def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(),Case(250),Case(255,phase=8)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing path access boundary')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,complete_states_equal=True)

class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1507BD68:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)

def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();before=(o/'before-conker_build_conker.us.elf').read_bytes();va=0x1507BD00
 body=struct.unpack_from('>29I',rom,va-0x15000000+0x2D4B0)
 assert body==struct.unpack_from('>29I',before,source.elf_slot_offset(before,va,116));count=0;seen=set()
 p=programs(0);s,entry,ps=p
 for index,opcode,poison,phase in itertools.product((0,1,127,250,255),(153,247,255),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
  c=Case(index,phase=phase);initial=fixture(c,s);a=actor(c,s);packet=[opcode,*[initial[s[n]]for n in NAMES]]
  for j,v in enumerate(packet):initial[SCRIPT+j]=v
  put(initial,a+0x218,SCRIPT);put(initial,DISPATCH+153*4,ENTRY);expected=dict(initial)
  if opcode==153:
   for name,v in zip(NAMES,packet[1:]):expected[s[name]]=v
   expected=reference(expected,c,s);put(expected,a+0x218,SCRIPT+5)
  else:put(expected,a+0x218,SCRIPT+1)
  for words in ps:
   code=dict(zip(range(entry,entry+224,4),words));m=Oracle(body,initial,c,s,va,code);m.r[16]=a
   for reg,name in zip((17,18,19,20),NAMES):m.r[reg]=s[name]
   m.r[21]=DISPATCH;m.before=m.r[:];m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=(0x1507BD74,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing script boundary')
   assert public(m.memory)==public(expected)and m.calls==([(ENTRY,())]if opcode==153 else[])and m.poison_hits==int(opcode==153)
   seen.update(m.visits)
  count+=1
 assert set(range(va,va+116,4))-seen=={va+0x20}
 return dict(cases=count,executions=count*4,original_window_words=29,reachable_words=28,return_poisons=4,packet_advance_5_or_1=True,void_return_ignored=True,full_dispatcher_emulation=False)

def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom)
 q=dict(aligned_ROM_JALs=[i*4 for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF],aligned_ROM_Js=[i*4 for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF],aligned_ROM_pointer_literals=[i*4 for i,w in enumerate(words)if w==ENTRY])
 assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22B454]);q.update(row=153,callback_table='D_80086730',ABI='void(void)');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')

def negative_aliases():
 b=source.SELECTED
 cached_actor=b.replace('void func_15077DBC(void) {','void func_15077DBC(void) {\n    struct127 *actor = D_800D154C;').replace('D_800D154C->','actor->')
 cached_table=b.replace('void func_15077DBC(void) {','void func_15077DBC(void) {\n    PathNode8 **table = (PathNode8 **)D_800D2104;').replace('((PathNode8 **)D_800D2104)','table')
 cached_node=source.OLD_BODY
 rows=[]
 for name,text,alias in(('cached-actor',cached_actor,1),('cached-table',cached_table,4),('cached-node',cached_node,4)):
  obj,diag=source.compile_owner(r,o,source.HEADERS+text,'negative-'+name);assert not diag
  s=symbols(0,alias);words=link(obj,'negative-linked-'+name,ENTRY,s);fired=False
  for index in(0,1,250,255):
   c=Case(index,alias);initial=fixture(c,s);m=Oracle(words,initial,c,s,ENTRY).run()
   fired|=public(m.memory)!=reference(initial,c,s)
  assert fired,name;rows.append(dict(control=name,effective=True))
 return rows

def native():
 b=source.SELECTED
 controls=[('wrong-sentinel',b.replace('!= 0xFA','!= 0xF9')),('unsigned-x',b.replace('].x;','].x;').replace('= ((PathNode8','= (u16)((PathNode8',1)),('unsigned-y',b.replace('->y_position = ','->y_position = (u16)')),('unsigned-z',b.replace('->z_position = ','->z_position = (u16)')),('swapped-x',b.replace('].x;','].z;')),('wrong-node',b.replace('unk21E + 1','unk21E')),('missing-z','\n'.join(v for v in b.splitlines()if '->z_position ='not in v)+'\n')]
 assert all(text!=b for _,text in controls)
 functions=b+'\n'+'\n'.join(text.replace('func_15077DBC','negative_'+str(i))for i,(_,text)in enumerate(controls))
 harness=r'''
static struct127 actor,expected;struct127 *D_800D154C;
u8 D_800D1890;static PathNode8 nodes[2][258];static PathNode8 *table[2];s32 *D_800D2104;
static unsigned char original[sizeof(nodes)];
static unsigned word(float f){union{float f;unsigned u;}v;v.f=f;return v.u;}
static void setup(unsigned n){unsigned i,j,k;unsigned char *a=(unsigned char*)&actor;
for(i=0;i<sizeof(actor);i++)a[i]=0xA5;
for(j=0;j<2;j++)for(k=0;k<258;k++){nodes[j][k].x=(s16)(k*257u+n*31u+j*7u);nodes[j][k].pad2=(s16)(0x8000u+k*193u+n*17u);nodes[j][k].z=(s16)(0x7FFFu-k*127u-n*19u);nodes[j][k].pad6=(s16)0xA5A5;}
actor.unk13F=(u8)(n&1);actor.unk21E=(u8)(n*17u+251u);D_800D1890=(u8)n;
table[0]=nodes[0];table[1]=nodes[1];D_800D2104=(s32*)table;D_800D154C=&actor;
for(i=0;i<sizeof(actor);i++)((unsigned char*)&expected)[i]=a[i];
if(D_800D1890!=250)expected.unk21E=D_800D1890;
j=expected.unk13F;k=(unsigned)expected.unk21E+1u;
expected.x_position=(float)nodes[j][k].x;expected.y_position=(float)nodes[j][k].pad2;expected.z_position=(float)nodes[j][k].z;
for(i=0;i<sizeof(nodes);i++)original[i]=((unsigned char*)nodes)[i];}
static int changed(void){unsigned i;for(i=0;i<sizeof(actor);i++)if(((unsigned char*)&actor)[i]!=((unsigned char*)&expected)[i])return 1;
for(i=0;i<sizeof(nodes);i++)if(original[i]!=((unsigned char*)nodes)[i])return 1;
return D_800D154C!=&actor||D_800D2104!=(s32*)table||table[0]!=nodes[0]||table[1]!=nodes[1];}
static int run(void){unsigned n,j,hits[7]={0};void(*f[7])(void)={FUNCTIONS};
if(sizeof(void*)!=4||sizeof(PathNode8)!=8||__builtin_offsetof(struct127,unk21E)!=0x21E||__builtin_offsetof(struct127,unk13F)!=0x13F)return 20;
for(n=0;n<2048;n++){setup(n);func_15077DBC();if(changed())return 21;for(j=0;j<7;j++){setup(n);f[j]();hits[j]|=(unsigned)changed();}}
for(j=0;j<7;j++)if(!hits[j])return 30+(int)j;return 0;}
'''.replace('FUNCTIONS',','.join('negative_'+str(i)for i in range(7)))
 # No fabricated integer-to-pointer aliases in portable native C; those are guest-qualified.
 code=source.HEADERS+'\n'+functions+harness+START;result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-mstackrealign','-fno-strict-aliasing','-Wno-unused-function',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  result.append(dict(profile=opt,cases=2048,UBSan=True,full_actor_canaries=True,path_data_unchanged=True,all_seven_controls_effective=True,pointer_aliases_guest_only=True,controls=[n for n,_ in controls]))
 return result

def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 artifact_names=('original-func_15077DBC.o','qualified-padded.o','make-shadow/src/game_A28B0.c.o','selected-final.o','before-conker_build_conker.us.elf','before-conker_conker.us.bin')
 fingerprint=source.sha(Path(__file__).read_bytes()+source.SELECTED.encode()+b''.join((o/n).read_bytes()for n in artifact_names))
 path=o/'runtime-qualification.json'
 if path.exists():
  result=json.loads(path.read_text())
  if result.get('fingerprint')==fingerprint:return result
 census();g,p=guest();result=dict(fingerprint=fingerprint,guest=g,faults=faults(p),callers=callers(),alias_negative_controls=negative_aliases(),native=native())
 path.write_text(json.dumps(result,indent=2)+'\n');return result
