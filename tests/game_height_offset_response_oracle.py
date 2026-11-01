"""Height-offset response, private frames, live query effects and original helper."""
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
ENTRY,QUERY,STATE,TABLE,SCRIPT=0x1511617C,0x1510F648,0x30000,0x80088C90,0x70000
QSYMS=dict(func_1510F800=0x1510F800,func_150A64C8=0x150A64C8,func_150A44F0=0x150A44F0,func_150A43E0=0x150A43E0,D_800D3830=0x800D3830,D_800D3300=0x800D3300,D_800A2D98=0x800A2D98)
GAPS=(-201.,-200.,-199.,-0.,0.,0.25,199.,200.,201.,32768.,1e20,-1e20)
OFFSETS=(-2147483648,-5000,-40,-20,-1,0,1,20,40,5000,2147483647)
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0
 mode:int=0
 verdict:int=0
def symbols(i=0,alias=0):
 s=dict(D_800CC354=(0x800CC354,0x3407FFE,0x2428000)[i],D_800A2FA8=(0x800A2FA8,0x3418000,0x2427FFC)[i],D_800A2FAC=(0x800A2FAC,0x3427FFC,0x2438000)[i],func_1510F648=(QUERY,0x17148000,0x17248000)[i])
 if alias==1:s['D_800A2FA8']=STATE+0x7C
 elif alias==2:s['D_800A2FAC']=STATE+0x7C
 elif alias==3:s['D_800CC354']=STATE+0x12
 return s
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def fixture(c,s,finite=False):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({STATE+i:0xA5 for i in range(-16,192)})
 put(m,s['D_800CC354'],(0,75,0x804B,65535)[(c.index//3)%4],2);put(m,s['D_800A2FA8'],0x3E4CCCCD);put(m,s['D_800A2FAC'],0x3E99999A)
 for at,val in((0x10,(-32768,-1,0,32767)[c.index%4]),(0x12,(-32768,-1,0,75,32767)[c.index%5]),(0x14,(32767,-32768,1,0)[(c.index//4)%4])):put(m,STATE+at,val&65535,2)
 put(m,STATE+0x3C,((-5000,-40,-20,-1,0,1,20,40,5000)if finite else OFFSETS)[c.index%(9 if finite else len(OFFSETS))]&0xFFFFFFFF)
 m[STATE+0x4F]=(0,1,4,5,128,132,251,255)[c.index%8]
 for a,v in((QSYMS['D_800D3300'],query_height(c)),(QSYMS['D_800A2D98'],height(c,m,finite))):put(m,a,v)
 m.update({QSYMS['D_800D3830']+j:(j*13+0x33)&255 for j in range(128)})
 return m
def query_height(c):return(-8388608,-256,0,19200,8388352,0x7FFFFFFF)[c.index%6]&0xFFFFFFFF
def height(c,m,finite=False):return bits(float(half(read(m,STATE+0x12,2)))+GAPS[c.index%(10 if finite else len(GAPS))])
def effect(m,c,s):
 if c.mode&1:
  put(m,STATE+0x12,(75 if c.index&1 else-12345)&65535,2);put(m,STATE+0x3C,(-33 if c.index&1 else 125)&0xFFFFFFFF);m[STATE+0x4F]^=4
  put(m,s['D_800CC354'],75,2);put(m,s['D_800A2FA8'],bits(0.5));put(m,s['D_800A2FAC'],bits(0.25))
 if c.mode&2:
  m[STATE+0x4F]^=128;put(m,STATE+0x7C,0xDEADBEEF);put(m,s['D_800CC354'],0x804B,2);put(m,s['D_800A2FA8'],0);put(m,s['D_800A2FAC'],bits(-0.125))
def reference(initial,c,s,connected=False,finite=False):
 m=dict(initial);oldY=half(read(m,STATE+0x12,2));args=tuple(bits(float(half(read(m,STATE+at,2))))for at in(0x10,0x12,0x14));result=height(c,m,finite);calls=[(s['func_1510F648'],args)]
 if connected:
  out=STACK+c.phase-48;token=0x12345678^c.index
  calls.extend(((QSYMS['func_1510F800'],(2,)),(QSYMS['func_150A64C8'],(trunc(args[0]),trunc(args[2]),out,trunc(args[1]))),(QSYMS['func_150A44F0'],(token,QSYMS['D_800D3830'],0)),(QSYMS['func_150A43E0'],(trunc(args[0]),trunc(args[2]),token,QSYMS['D_800D3830']))))
  put(m,QSYMS['D_800D3830'],token^0x13579BDF);put(m,QSYMS['D_800D3300'],query_height(c)^0x100);put(m,QSYMS['D_800A2D98'],result)
 effect(m,c,s)
 if connected:result=fp(bits(float(signed(read(m,QSYMS['D_800D3300'])))),bits(1./256),'mul')if c.verdict else read(m,QSYMS['D_800A2D98'])
 put(m,STATE+0x7C,result)
 distance=fp(result,bits(float(half(read(m,STATE+0x12,2)))),'sub')&0x7FFFFFFF
 if floating(distance)>200.:put(m,STATE+0x3C,0)
 velocity=read(m,STATE+0x3C)
 if not m[STATE+0x4F]&4:delta=(-velocity)&0xFFFFFFFF;factor=read(m,s['D_800A2FA8'])
 else:delta=((-40 if read(m,s['D_800CC354'],2)==75 else-20)-velocity)&0xFFFFFFFF;factor=read(m,s['D_800A2FAC'])
 offset=trunc(fp(bits(float(signed(velocity))),fp(bits(float(signed(delta))),factor,'mul'),'add'));put(m,STATE+0x3C,offset)
 y=trunc(fp(read(m,STATE+0x7C),bits(float(signed(offset))),'add'));put(m,STATE+0x12,y&65535,2);put(m,STATE+0x5C,(half(y)-oldY)&65535,2)
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;self.height_result=height(c,memory);self.query_out=None;self.raw=False
  super().__init__(words,memory,c,entry=entry,s={},arguments=(STATE,),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(5,13):self.f[w>>6&31]=(self.f[w>>11&31]&0x7FFFFFFF)if w&63==5 else trunc(self.f[w>>11&31])
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(1))
  elif t==self.s['func_1510F648']:a=(self.f[12],self.f[14],self.r[6])
  else:
   counts={QSYMS['func_1510F800']:1,QSYMS['func_150A64C8']:4,QSYMS['func_150A44F0']:3,QSYMS['func_150A43E0']:4};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]))
   if t==QSYMS['func_150A64C8']:
    self.query_out=a[2]
    if self.raw:a=(*a[:2],a[2]-8,a[3])
  self.calls.append((t,a))
 def hook(self,t):
  c,s=self.c,self.s;value=0xDEADBEEF;answer=None
  if t==s['func_1510F648']:effect(self.memory,c,s);answer=self.height_result
  elif t==QSYMS['func_1510F800']:pass
  elif t==QSYMS['func_150A64C8']:put(self.memory,self.query_out,0x12345678^c.index)
  elif t==QSYMS['func_150A44F0']:put(self.memory,QSYMS['D_800D3830'],(0x12345678^c.index)^0x13579BDF)
  elif t==QSYMS['func_150A43E0']:
   put(self.memory,QSYMS['D_800D3300'],query_height(c)^0x100);put(self.memory,QSYMS['D_800A2D98'],self.height_result);effect(self.memory,c,s);value=c.verdict
  else:raise AssertionError(('Unexpected height helper',hex(t)))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
  if answer is not None:self.f[0]=answer
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>86I',sections(p.with_suffix('.elf'))['.text'][1][:344]))
def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17038000,0x1F00FFFC)[i]
 ps=[link(o/n,'height-program-%d-%d-%d'%(i,alias,j),entry,s)for j,n in enumerate(('original-func_1511617C.o','qualified-padded.o','make-shadow/src/game/generated_142560.c.o','selected-final.o'))];raw=ps[-1][:]
 for at,a,b in source.NEW_GUARDS:
  word=ps[-1][at//4];mask=0xFFFF0000 if at in source.BINDINGS else 0xFFFFFFFF;assert word&mask==a;ps[-1][at//4]=(word&~mask)|b
 assert all(v==ps[0]for v in ps)
 return s,entry,ps+[raw]
def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p,code=None):
 s,entry,ps=p;initial=fixture(c,s);expected,calls=reference(initial,c,s,code is not None);models=[]
 for j,words in enumerate(ps):
  m=Oracle(words,initial,c,s,entry,code);m.raw=j==4;m.run();assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls,[(hex(a),m.memory.get(a),expected[a])for a in expected if m.memory.get(a)!=expected[a]][:12]);models.append(m)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
 assert all(state(v)==state(models[0])for v in models[:4])
 return models[0]
def guest():
 count=0;seen=set();p0=None
 for i in range(3):
  for alias in range(4):
   p=programs(i,alias)
   if not i and not alias:p0=p
   for index,phase,mode in itertools.product(range(64 if i==0 else 32),(0,8),range(4)if i==0 else(0,3)):
    m=compare(Case(index,alias,phase,mode),p);seen.update(m.visits);count+=1
 assert seen>=set(range(ENTRY,ENTRY+344,4))
 return dict(cases=count,executions=count*5,rebases=3,all_86_words_executed=True,global_alias_layouts=4,four_exact_programs_full_state_equal=True,unguarded_C_public_memory_and_preserved_ABI_equal=True,private_frames_32_and_40=True,float_invalid_guest_model_only=True),p0
def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(),Case(7,mode=3),Case(21,phase=8,mode=1),Case(43,mode=2)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps[:4]:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing height fault prefix')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,exact_programs_full_state_equal=True,unguarded_C_fault_order_not_claimed=True)
def connected(p):
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>54I',before,source.elf_slot_offset(before,QUERY,216));assert words==struct.unpack_from('>54I',rom,0x13CAF8);code=dict(zip(range(QUERY,QUERY+216,4),words));count=0;seen=set()
 for index,verdict,mode in itertools.product(range(128),(0,1),range(4)):
  m=compare(Case(index,mode=mode,verdict=verdict),p,code);seen.update(m.visits);count+=1
 assert all(QUERY+j*4 in seen for j in range(54))
 return dict(cases=count,executions=count*5,original_helper_words=54,all_54_words_executed=True,four_query_subservices_are_providers=True,actual_FP_o32_packet=True)
class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==self.owner.return_pc:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
def callers(p):
 rom=(r/'conker/conker.us.bin').read_bytes();s,entry,ps=p;count=0;seen=set()
 windows=((0x15113EE0,0x141390,7,(0x15113EB4,0x15113EFC),0x15113EF0),(0x15113FB8,0x141468,9,(0x15113FDC,),0x15113FC8))
 for va,off,n,ends,return_pc in windows:
  body=struct.unpack_from('>%dI'%n,rom,off)
  for index,poison,loop in itertools.product((0,1,7,21,43,63),(0,1,0x80000000,0xFFFFFFFF),(0,1)):
   c=Case(index,mode=index%4);initial=fixture(c,s);put(initial,STATE+0x38,ENTRY);put(initial,0x800D23C0,0x60000);put(initial,0x60002,0x1234,2);expected,calls=reference(initial,c,s)
   for j,words in enumerate(ps):
    code=dict(zip(range(entry,entry+344,4),words));m=Oracle(body,initial,c,s,va,code);m.raw=j==4;m.r[16]=STATE;m.r[17]=0x60000;m.r[18]=loop;m.r[23]=0;m.r[30]=0;m.before=m.r[:];m.return_pc=return_pc;m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing height caller boundary')
    assert public(m.memory)==expected and m.calls==[(ENTRY,(STATE,))]+calls and m.poison_hits==1 and m.r[2]==poison
    if va==windows[0][0]:assert m.r[30]==1 and m.r[17]==0x600A0
    else:assert m.r[4]==0x1234 and m.r[5]==0x60000 and m.r[6]==2
    seen.update(m.visits)
   count+=1
  assert all(va+4*j in seen for j in range(n))
 return dict(cases=count,executions=count*5,original_window_words=[7,9],both_original_JALR_sites_executed=True,return_poisons=4,void_result_ignored=True,larger_dispatcher_not_fully_emulated=True)
def installer():
 rom=(r/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>22I',rom,0xCC06C);va=0x1509EBBC;c=Case();s=symbols();m=fixture(c,s);m.update({SCRIPT+i:0xA5 for i in range(32)})
 for j in range(3):put(m,TABLE+51*12+j*4,struct.unpack_from('>I',rom,0x22D9B4+j*4)[0])
 put(m,SCRIPT+8,51);expected=dict(m);put(expected,STATE+0x38,ENTRY);put(expected,STATE+0x78,0);expected[STATE+0x92]=0;instance=Oracle(body,m,c,s,va);instance.r[16]=SCRIPT;instance.r[2]=STATE;instance.before=instance.r[:];instance.code=WindowCode(instance.code,instance);instance.code.ends=(0x1509ED5C,)
 try:instance.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing height installer boundary')
 assert public(instance.memory)==public(expected)and all(va+j*4 in instance.visits for j in range(22))
 return dict(original_words=22,table_row=51,callback_field='0x38',all_words_executed=True)
def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom);q=dict(aligned_ROM_JALs=[4*i for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_Js=[4*i for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_pointer_literals=[4*i for i,w in enumerate(words)if w==ENTRY]);assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22D9B4]),q;q.update(callback_table='D_80088C90',row=51,callback_field='0x38',ABI='void(u8 *state)');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')
def native():
 selected=source.SELECTED;controls=(('cached-live-y',selected.replace('(f32)*(s16 *)(state + 0x12)) > 200.0f','(f32)oldY) > 200.0f')),('inclusive-gap',selected.replace('> 200.0f','>= 200.0f')),('wrong-damping',selected.replace('* D_800A2FA8','* D_800A2FAC')),('wrong-target-type',selected.replace('== 0x4B','== 0x804B')),('wrong-flag',selected.replace('state[0x4F] & 4','state[0x4F] & 1')),('wrong-target-speed',selected.replace('target = -40','target = -20')),('wrong-feedback-snapshot',selected.replace('- oldY;','- *(s16 *)(state + 0x12);').replace('    s16 oldY = *(s16 *)(state + 0x12);\n','')),('wrong-helper-z',selected.replace('(f32)*(s16 *)(state + 0x14));','(f32)*(s16 *)(state + 0x10));')))
 assert all(v!=selected for _,v in controls)
 def array(v):return'{'+','.join('0x%Xu'%x for x in v)+'}'
 def image(m):
  v=bytearray(m[STATE+j]for j in range(160))
  for at,n in((0x10,2),(0x12,2),(0x14,2),(0x3C,4),(0x5C,2),(0x7C,4)):v[at:at+n]=v[at:at+n][::-1]
  return v
 rows=[]
 for index,mode in itertools.product(range(512),range(4)):
  c=Case(index,mode=mode);s=symbols();m=fixture(c,s,True);expected,calls=reference(m,c,s,finite=True);rows.append('{%d,%d,0x%Xu,0x%Xu,%s,%s,%s}'%(index,mode,read(m,s['D_800CC354'],2),height(c,m,True),array(calls[0][1]),array(image(m)),array(image(expected))))
 code=source.HEADERS+r'''
typedef struct{u32 index,mode,type,result,args[3];u8 input[160],expected[160];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[48];u8 bytes[192];}Record;
static Record record;static u8 *state;static Case *current;static u32 callCount,error;
u16 D_800CC354;f32 D_800A2FA8,D_800A2FAC;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
f32 fabsf(f32 x){return floating(bits(x)&0x7FFFFFFFu);}
f32 func_1510F648(f32 x,f32 y,f32 z){u32 mode=current->mode;callCount++;if(callCount!=1||bits(x)!=current->args[0]||bits(y)!=current->args[1]||bits(z)!=current->args[2])error=1;
 if(mode&1){*(s16*)(state+0x12)=current->index&1?75:-12345;*(s32*)(state+0x3C)=current->index&1?-33:125;state[0x4F]^=4;D_800CC354=75;D_800A2FA8=0.5f;D_800A2FAC=0.25f;}
 if(mode&2){state[0x4F]^=128;*(u32*)(state+0x7C)=0xDEADBEEFu;D_800CC354=0x804B;D_800A2FA8=0.0f;D_800A2FAC=-0.125f;}
 return floating(current->result);
}
'''
 for j,(_,body)in enumerate((('valid',selected),)+controls):code+=body.replace('func_1511617C(','candidate_%d('%j)+'\n'
 code+='static void (*candidates[])(u8*)={'+','.join('candidate_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;state=record.bytes+16;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  current=&cases[n];callCount=error=0;D_800CC354=(u16)current->type;D_800A2FA8=floating(0x3E4CCCCDu);D_800A2FAC=floating(0x3E99999Au);
  for(k=0;k<192;k++)record.bytes[k]=0xA5;for(k=0;k<160;k++)state[k]=current->input[k];candidates[j](state);failed=error||callCount!=1;
  for(k=0;k<192;k++)if(record.bytes[k]!=(k>=16&&k<176?current->expected[k-16]:0xA5))failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==255u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode);result.append(dict(profile=opt,cases=len(rows),UBSan=True,canaries=True,all_eight_controls_effective=True,controls=[n for n,_ in controls],native_casts_in_range=True))
 return result
def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core;fingerprint=source.sha(b''.join((o/n).read_bytes()for n in('qualified-padded.o','selected-final.o','first-linked.elf'))+Path(__file__).read_bytes()+source.SELECTED.encode());saved=o/'runtime-qualification.json'
 if saved.exists():
  q=json.loads(saved.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census();g,p=guest();q=dict(fingerprint=fingerprint,guest=g,faults=faults(p),connected=connected(p),callers=callers(p),installer=installer(),native=native());saved.write_text(json.dumps(q,indent=2)+'\n');return q
