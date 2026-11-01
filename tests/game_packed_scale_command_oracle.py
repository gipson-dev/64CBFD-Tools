"""Packed signed scales, current-actor reloads and complete original scale helper."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,HELPER,NEST1,NEST2=0x15076D3C,0x15062BDC,0x15062AC4,0x15062B84
ACTOR,OTHER,MARK,DESCRIPTOR,TABLE,SCRIPT,DISPATCH=0x30000,0x3F800000,0x70000,0x50000,0x800D1C90,0x60000,0x80086730
NAMES=('D_800D1890','D_800D1891','D_800D1892','D_800D1893')
half=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0
 mode:int=0

def symbols(i=0,alias=0):
 if not i:s=dict(D_800D154C=0x800D154C,D_8009A144=0x8009A144,func_15062BDC=HELPER,**dict(zip(NAMES,range(0x800D1890,0x800D1894))))
 else:
  base=(0x2737FFC,0x3438000)[i-1];bytes_base=(0x2747FFE,0x3447FFF)[i-1]
  s=dict(D_800D154C=base,D_8009A144=(0x2758000,0x3457FFC)[i-1],func_15062BDC=(0x17048000,0x1F01FFFC)[i-1],**dict(zip(NAMES,range(bytes_base,bytes_base+4))))
 if alias==5:s['D_8009A144']=ACTOR+0x14C
 if alias==6:s.update(zip(NAMES,range(ACTOR+0x14C,ACTOR+0x150)))
 return s

def actor(c,s):return s['D_800D154C']-(0x14C,0x150,0x154,0x158)[c.alias-1]if c.alias in(1,2,3,4)else ACTOR
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def fixture(c,s):
 a=actor(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base in(a,OTHER):
  m.update({base+i:0xA5 for i in range(-16,0x340)})
  m[base+4]=255 if c.index&1 else 0
  for at,v in((0x14C,bits(2.5)),(0x150,bits(-3.5))):put(m,base+at,v)
 put(m,MARK,0)
 for ident in range(2):
  p=DESCRIPTOR+ident*64;put(m,TABLE+ident*4,p)
  for off,value in((0x1A,-31),(0x1C,17),(0x1E,63),(0x20,100),(0x22,-200),(0x24,300)):put(m,p+off,value&65535,2)
 if c.alias in(1,2,3,4):x=y=1;scale=bits(1.)
 else:
  x=(c.index&255)|(((c.index*17+3)&255)<<8);y=((c.index*37+1)&255)|(((c.index*63+128)&255)<<8)
  scale=(0x3C23D70A,bits(-0.),bits(.5),bits(-.25),bits(1.),bits(-1.),bits(2.),bits(3.))[c.index%8]
 for name,value in zip(NAMES,(x&255,x>>8,y&255,y>>8)):m[s[name]]=value
 put(m,s['D_8009A144'],scale);put(m,s['D_800D154C'],a)
 return m

def nested_effect(m,a,ordinal):put(m,MARK,read(m,MARK)+ordinal);put(m,a+0x24,0x70000000+ordinal)
def effect(m,c,args):
 if c.mode:
  a=args[0];put(m,a+0x20,0x12345678);put(m,a+0x14C,bits(-70.));put(m,a+0x150,bits(90.))

def helper_reference(m,args,c,calls):
 a,x,y=args;put(m,a+0x14C,x);put(m,a+0x150,y)
 if m[a+4]!=255:
  desc=read(m,TABLE+m[a+4]*4)
  # The original helper snapshots both scales before its dimension stores.
  for src,dst,v in((0x20,0xD2,x),(0x22,0xD4,y),(0x24,0xD6,y),(0x1A,0xE4,x),(0x1C,0xE6,y),(0x1E,0xE8,y)):
   value=trunc(fp(bits(float(half(read(m,desc+src,2)))),v,'mul'));put(m,a+dst,value&65535,2)
  calls.append((NEST1,(a,)));nested_effect(m,a,1);calls.append((NEST2,(a,)));nested_effect(m,a,2)

def reference(initial,c,s,actual=False):
 m=dict(initial);scale=read(m,s['D_8009A144']);x=half(m[s[NAMES[0]]]|m[s[NAMES[1]]]<<8);y=half(m[s[NAMES[2]]]|m[s[NAMES[3]]]<<8)
 a=read(m,s['D_800D154C']);put(m,a+0x14C,fp(bits(float(x)),scale,'mul'))
 a=read(m,s['D_800D154C']);put(m,a+0x150,fp(bits(float(y)),scale,'mul'))
 a=read(m,s['D_800D154C']);put(m,a+0x154,read(m,a+0x14C))
 a=read(m,s['D_800D154C']);put(m,a+0x158,read(m,a+0x150))
 a=read(m,s['D_800D154C']);args=(a,read(m,a+0x14C),read(m,a+0x150));calls=[(s['func_15062BDC'],args)]
 if actual:helper_reference(m,args,c,calls)
 else:effect(m,c,args)
 return public(m),calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},arguments=(),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:self.f[w>>6&31]=trunc(self.f[w>>11&31])
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:n=0
  elif t==self.s['func_15062BDC']:n=3
  else:assert t in(NEST1,NEST2),hex(t);n=1
  self.calls.append((t,tuple(self.arguments(n))))
 def hook(self,t):
  args=self.calls[-1][1]
  if t==self.s['func_15062BDC']:effect(self.memory,self.c,args)
  else:assert t in(NEST1,NEST2);nested_effect(self.memory,args[0],1 if t==NEST1 else 2)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def link(obj,label,entry,s,normalize=False):
 text,fs,relocs=parse_object(obj);info=fs[source.FUNCTION]
 if normalize:
  raw,bindings=source.payload(obj);text=source.normalized_payload(raw,bindings);relocs=source.normalized_bindings(bindings);info=dict(info,value=0,size=184)
 assembly,unknown=emit_function(text,info,relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>46I',sections(p.with_suffix('.elf'))['.text'][1][:184]))

def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17007FFC,0x1F007FFC)[i]
 paths=('original-func_15076D3C.o','qualified-padded.o','make-shadow/src/game_A28B0.c.o','selected-final.o','selected-final.o')
 ps=[link(o/n,'scale-program-%d-%d-%d'%(i,alias,j),entry,s,j==3)for j,n in enumerate(paths)]
 assert all(v==ps[0]for v in ps[:4]);return s,entry,ps

def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p,code=None,initial=None):
 s,entry,ps=p;initial=fixture(c,s)if initial is None else initial;expected,calls=reference(initial,c,s,code is not None);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,code).run()
  assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls,[(hex(a),m.memory.get(a),expected[a])for a in expected if m.memory.get(a)!=expected[a]][:10])
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 assert all(state(v)==state(models[0])for v in models[:4]);return models[0]

def guest():
 count=0;seen=set();p0=None
 for i in range(3):
  for alias in range(7):
   p=programs(i,alias)
   if not i and not alias:p0=p
   for index,phase,mode in itertools.product(range(256 if i==0 else 64),(0,8),(0,1)):
    m=compare(Case(index,alias,phase,mode),p);seen.update(m.visits);count+=1
 assert set(range(ENTRY,ENTRY+184,4))<=seen
 return dict(cases=count,executions=count*5,rebases=3,all_46_words_executed=True,global_alias_layouts=7,all_256_values_in_each_packed_byte=True,four_exact_programs_full_state_equal=True,unguarded_C_public_memory_and_preserved_ABI_equal=True),p0

def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(),Case(128,mode=1),Case(255,phase=8)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps[:4]:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing scale access boundary')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,exact_programs_full_state_equal=True,unguarded_C_fault_order_not_claimed=True)

def connected():
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>77I',before,source.elf_slot_offset(before,HELPER,308));assert words==struct.unpack_from('>77I',rom,0x9008C)
 assert struct.unpack_from('>I',before,source.elf_slot_offset(before,0x8009A144,4))[0]==0x3C23D70A
 code=dict(zip(range(HELPER,HELPER+308,4),words));count=0;seen=set();nested=0
 for alias in(0,1,5,6):
  p=programs(0,alias)
  for index,phase in itertools.product(range(128),(0,8)):
   m=compare(Case(index,alias,phase),p,code);seen.update(m.visits);nested+=len(m.calls)==3;count+=1
 assert all(HELPER+j*4 in seen for j in range(77))
 return dict(cases=count,executions=count*5,complete_original_scale_helper_words=77,all_77_helper_words_executed=True,nested_paths=nested,original_factor_pinned=True,independent_dimension_reference=True,two_nested_helpers_are_providers=True)

class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1507BD68:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)

def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();va=0x1507BD00;n=29;body=struct.unpack_from('>29I',rom,va-0x15000000+0x2D4B0);count=0;seen=set()
 for alias in(0,1,5,6):
  s,entry,ps=programs(0,alias)
  for index,opcode,poison,phase in itertools.product((0,1,127,128,255),(86,247,255),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
   c=Case(index,alias,phase,1);initial=fixture(c,s);a=actor(c,s);packet=[opcode,*[initial[s[name]]for name in NAMES]]
   for j,v in enumerate(packet):initial[SCRIPT+j]=v
   put(initial,a+0x218,SCRIPT);put(initial,DISPATCH+86*4,ENTRY);expected=dict(initial)
   if opcode==86:
    for name,v in zip(NAMES,packet[1:]):expected[s[name]]=v
    expected,calls=reference(expected,c,s);put(expected,a+0x218,SCRIPT+5)
   else:calls=[];put(expected,a+0x218,SCRIPT+1)
   for words in ps:
    code=dict(zip(range(entry,entry+184,4),words));m=Oracle(body,initial,c,s,va,code);m.r[16]=a
    for reg,name in zip((17,18,19,20),NAMES):m.r[reg]=s[name]
    m.r[21]=DISPATCH;m.before=m.r[:];m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=(0x1507BD74,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing script packet window boundary')
    assert public(m.memory)==public(expected)and m.calls==([(ENTRY,())]+calls if opcode==86 else[])and m.poison_hits==int(opcode==86)
    seen.update(m.visits)
   count+=1
 missing=set(va+j*4 for j in range(n))-seen
 assert missing=={va+0x20},[hex(v)for v in missing]
 return dict(cases=count,executions=count*5,original_window_words=29,all_28_reachable_window_words_executed=True,unreachable_duplicate_load='0x20',original_JALR_executed=True,return_poisons=4,void_result_ignored=True,packet_bytes_and_advance_5_or_1_verified=True,opcodes=[86,247,255],larger_dispatcher_not_fully_emulated=True)

def trampolines():
 before=(o/'before-conker_build_conker.us.elf').read_bytes();after=(o/'first-linked.elf').read_bytes();names=('func_150781F4','func_150A7D00');old={n:f for _,n,f,_ in source.symbol_rows(before)};new={n:f for _,n,f,_ in source.symbol_rows(after)};count=0
 for name in names:
  va=old[name][1];bodies=[struct.unpack_from('>2I',data,source.elf_slot_offset(data,va,8))for data in(before,after)];dest=[((v[0]&0x3FFFFFF)<<2)|(va&0xF0000000)for v in bodies]
  assert dest[1]==dest[0]-192 and bodies[0][1]==bodies[1][1]==0
  for phase,return_pc in itertools.product((0,8),(0x12345678,0xFFFFFFFF,0x80000000,0)):
   c=Case(phase=phase);s=symbols();initial=fixture(c,s);models=[]
   for words,end in zip(bodies,dest):
    m=Oracle(words,initial,c,s,va);m.r[31]=return_pc;m.before=m.r[:];m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing retargeted private-entry boundary')
    assert m.r==m.before and m.memory==initial and not m.calls;models.append(m)
   assert models[0].f==models[1].f;count+=1
 return dict(cases=count,executions=count*2,retargeted_entries=2,original_trampoline_words=2,all_registers_and_memory_unchanged=True,private_bodies_proved_identical_by_full_image_closure=True)

def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom)
 q=dict(aligned_ROM_JALs=[4*i for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_Js=[4*i for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_pointer_literals=[4*i for i,w in enumerate(words)if w==ENTRY])
 assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22B348])
 q.update(callback_table='D_80086730',row=86,ABI='void(void)');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')

def native():
 selected=source.SELECTED
 controls=(('unsigned-x',selected.replace('x = (s16)','x = (u16)')),('unsigned-y',selected.replace('y = (s16)','y = (u16)')),('wrong-x-endian',selected.replace('D_800D1890 | (D_800D1891 << 8)','D_800D1891 | (D_800D1890 << 8)')),('wrong-y-endian',selected.replace('D_800D1892 | (D_800D1893 << 8)','D_800D1893 | (D_800D1892 << 8)')),('lost-factor-capture',selected.replace('(f32)y * scale','(f32)y * D_8009A144')),('wrong-x-mirror',selected.replace('unk154 = D_800D154C->xz_scale','unk154 = D_800D154C->y_scale')),('wrong-y-mirror',selected.replace('unk158 = D_800D154C->y_scale','unk158 = D_800D154C->xz_scale')),('missing-helper',selected.replace('    func_15062BDC(D_800D154C, D_800D154C->xz_scale, D_800D154C->y_scale);\n','')))
 assert all(v!=selected for _,v in controls)
 array=lambda v:'{'+','.join('0x%Xu'%x for x in v)+'}'
 def image(m):
  v=bytearray(m[ACTOR+j]for j in range(352))
  for at in(0x20,0x14C,0x150,0x154,0x158):v[at:at+4]=v[at:at+4][::-1]
  return v
 rows=[]
 for index,alias,mode in itertools.product(range(512),(0,5),(0,1)):
  c=Case(index,alias,mode=mode);s=symbols(0,alias);m=fixture(c,s);expected,calls=reference(m,c,s)
  rows.append('{%d,%d,%s,0x%Xu,%s,%s,%s}'%(alias,mode,array([m[s[n]]for n in NAMES]),read(m,s['D_8009A144']),array(calls[0][1][1:]),array(image(m)),array(image(expected))))
 code=source.HEADERS+r'''
typedef struct{u32 alias,mode;u8 bytes[4];u32 factor,args[2];u8 input[352],expected[352];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[211];u8 bytes[844];}Record;
static Record record;static u8 *state;static Case *current;static u32 calls,error;
struct127 *D_800D154C;u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;
static f32 factor,*scaleAddress;
#define D_8009A144 (*scaleAddress)
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
void func_15062BDC(struct127 *a,f32 x,f32 y){if(calls++||a!=(struct127*)state||bits(x)!=current->args[0]||bits(y)!=current->args[1])error=1;
 if(current->mode){*(u32*)(state+0x20)=0x12345678u;*(f32*)(state+0x14C)=-70.f;*(f32*)(state+0x150)=90.f;}}
'''
 for j,(_,body)in enumerate((('valid',selected),)+controls):code+=body.replace('func_15076D3C(','candidate_%d('%j)+'\n'
 code+='static void (*candidates[])(void)={'+','.join('candidate_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;state=record.bytes+16;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  current=&cases[n];calls=error=0;D_800D154C=(struct127*)state;factor=floating(current->factor);scaleAddress=current->alias?(f32*)(state+0x14C):&factor;
  D_800D1890=current->bytes[0];D_800D1891=current->bytes[1];D_800D1892=current->bytes[2];D_800D1893=current->bytes[3];
  for(k=0;k<844;k++)record.bytes[k]=0xA5;for(k=0;k<352;k++)state[k]=current->input[k];candidates[j]();failed=error||calls!=1;
  for(k=0;k<844;k++)if(record.bytes[k]!=(k>=16&&k<368?current->expected[k-16]:0xA5))failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==255u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode);result.append(dict(profile=opt,cases=len(rows),UBSan=True,canaries=True,all_eight_controls_effective=True,controls=[n for n,_ in controls],factor_alias_native_qualified=True,current_actor_pointer_aliases_guest_only=True))
 return result

def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core;code=Path(__file__).read_bytes()
 artifacts=b''.join((o/n).read_bytes()for n in('qualified-padded.o','selected-final.o','first-linked.elf'))
 fingerprint=source.sha(artifacts+code+source.SELECTED.encode());saved=o/'runtime-qualification.json'
 if saved.exists():
  q=json.loads(saved.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census()
 model_fingerprint=source.sha(artifacts+code.split(b'def trampolines():')[0]+source.SELECTED.encode()+source.SNAPSHOT_SHA.encode()+repr(source.normalized_bindings(source.BINDINGS)).encode())
 progress=o/'runtime-stage-progress.json';stages={}
 if progress.exists():
  prior=json.loads(progress.read_text())
  if prior.get('model_fingerprint')==model_fingerprint:stages=prior['stages']
 def save():progress.write_text(json.dumps(dict(model_fingerprint=model_fingerprint,stages=stages),indent=2)+'\n')
 if 'guest'not in stages:
  stages['guest'],p=guest();save();print('guest qualified',stages['guest']['cases'],flush=True)
 else:p=programs(0,0)
 for name,fn in(('faults',lambda:faults(p)),('connected',connected),('callers',callers)):
  if name not in stages:stages[name]=fn();save();print(name,'qualified',flush=True)
 q=dict(fingerprint=fingerprint,model_fingerprint=model_fingerprint,**stages,retargeted_trampolines=trampolines(),native=native())
 saved.write_text(json.dumps(q,indent=2)+'\n');return q
