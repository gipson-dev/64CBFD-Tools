"""Paired sine fallback: live phases, clock reads, callback effects and original math."""
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
from tools.tests.test_game_trig_match import reference as sine_reference, GLOBALS
from tools.tests.test_game_sine_phase_update import wrap
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,SINE,WRAP,STATE,TABLE,SCRIPT=0x1511C548,0x15047D60,0x15144B68,0x30000,0x80088C90,0x70000
PHASES=(0.,-0.,.125,-.25,1.,-1.,6.283185,12.5,-15.75)
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0
 mode:int=0

def symbols(i=0,alias=0):
 s=dict(sinf=(SINE,0x17148000,0x17248000)[i],func_15144B68=(WRAP,0x17158000,0x17258000)[i],D_800A31EC=(0x800A31EC,0x3417FFC,0x2428000)[i],D_800A31F0=(0x800A31F0,0x3428000,0x2437FFC)[i],D_800BE9A4=(0x800BE9A4,0x3437FFC,0x2448000)[i])
 if alias==1:s['D_800BE9A4']=STATE+0x80
 elif alias==2:s['D_800A31F0']=STATE
 elif alias==3:s['D_800BE9A4']=STATE
 return s

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({STATE+i:0xA5 for i in range(-16,192)})
 put(m,s['D_800BE9A4'],bits((0.,-0.,.125,-.25,1.,-1.,4.,2.)[c.index%8]));put(m,s['D_800A31EC'],0x3D958106);put(m,s['D_800A31F0'],0x3D851EB8)
 for at,v in((0,bits(99.)),(8,bits(-99.)),(0x80,bits(PHASES[c.index%9])),(0x84,bits(PHASES[(c.index*3+1)%9]))):put(m,STATE+at,v)
 return m

def provider(c,ordinal):
 values=((0.,-0.,1.,-1.,.25,-.5,.75,2.),(0.,1.,-0.,-1.,0.,.5,-0.,.25),(1.5,-2.5,0.,-0.,1.,0.,-0.,2.),(0.,0.,1.,-0.,-0.,2.,0.,1.))
 return bits(values[ordinal][c.index%8])

def effect(m,c,s,ordinal):
 if ordinal==0 and c.mode&1:
  put(m,STATE+0x80,bits(3.));put(m,STATE+0x84,bits(-4.));put(m,s['D_800BE9A4'],bits(2.));put(m,s['D_800A31EC'],bits(-.125));put(m,s['D_800A31F0'],bits(.25))
 if ordinal==1 and c.mode&2:
  put(m,STATE+0x80,bits(-7.));put(m,STATE+0x84,bits(8.));put(m,s['D_800BE9A4'],bits(.5));put(m,s['D_800A31EC'],bits(.375));put(m,STATE,bits(-70.));put(m,STATE+8,bits(90.))
 if ordinal==2 and c.mode&1:
  put(m,STATE+0x84,bits(3.25));put(m,STATE+8,bits(1.));put(m,s['D_800BE9A4'],bits(-2.))
 if ordinal==3 and c.mode&2:
  put(m,STATE+8,bits((0.,-0.,1.)[c.index%3]));put(m,STATE+0x80,bits(-9.));put(m,STATE+0x84,bits(18.));put(m,STATE,bits(17.))

def reference(initial,c,s,actual=False):
 m=dict(initial);calls=[]
 def call(name,arg):
  ordinal=len(calls);calls.append((s[name],(arg,)))
  answer=(sine_reference(arg)if name=='sinf'else wrap(arg))if actual else provider(c,ordinal)
  if not actual:effect(m,c,s,ordinal)
  return answer
 first=call('sinf',read(m,STATE+0x80));second=call('sinf',read(m,STATE+0x84))
 put(m,STATE,fp(first,bits(16.),'mul'));put(m,STATE+8,fp(second,bits(16.),'mul'))
 first=fp(read(m,STATE+0x80),fp(read(m,s['D_800A31EC']),read(m,s['D_800BE9A4']),'mul'),'add')
 put(m,STATE+0x80,first)
 second=fp(read(m,STATE+0x84),fp(read(m,s['D_800A31F0']),read(m,s['D_800BE9A4']),'mul'),'add')
 put(m,STATE+0x84,second)
 put(m,STATE+0x80,call('func_15144B68',read(m,STATE+0x80)))
 put(m,STATE+0x84,call('func_15144B68',read(m,STATE+0x84)))
 if floating(read(m,STATE+8))==0. and floating(read(m,STATE+0x84))==0.:
  put(m,STATE,bits(7.5));put(m,STATE+8,bits(8.))
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;self.ordinal=0;super().__init__(words,memory,c,entry=entry,s={},arguments=(STATE,),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(7,13):self.f[w>>6&31]=(self.f[w>>11&31]^0x80000000)if w&63==7 else trunc(self.f[w>>11&31])
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(1))
  else:assert t in(self.s['sinf'],self.s['func_15144B68']),hex(t);a=(self.f[12],)
  self.calls.append((t,a))
 def hook(self,t):
  assert t in(self.s['sinf'],self.s['func_15144B68']);answer=provider(self.c,self.ordinal);effect(self.memory,self.c,self.s,self.ordinal);self.ordinal+=1
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=answer
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>60I',sections(p.with_suffix('.elf'))['.text'][1][:240]))
def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17038000,0x1F00FFFC)[i];ps=[link(o/n,'paired-program-%d-%d-%d'%(i,alias,j),entry,s)for j,n in enumerate(('original-func_1511C548.o','qualified-padded.o','make-shadow/src/game/generated_142560.c.o','selected-final.o'))];raw=ps[-1][:]
 for at,a,b in source.NEW_GUARDS:assert ps[-1][at//4]==a;ps[-1][at//4]=b
 assert all(v==ps[0]for v in ps)
 return s,entry,ps+[raw]
def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p,code=None,initial=None):
 s,entry,ps=p;initial=fixture(c,s)if initial is None else initial;expected,calls=reference(initial,c,s,code is not None);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,code).run();assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls,[(hex(a),m.memory.get(a),expected[a])for a in expected if m.memory.get(a)!=expected[a]][:12]);models.append(m);assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
 assert all(state(v)==state(models[0])for v in models[:4])
 return models[0]
def guest():
 count=0;seen=set();p0=None
 for i in range(3):
  for alias in range(4):
   p=programs(i,alias)
   if not i and not alias:p0=p
   for index,phase,mode in itertools.product(range(256 if i==0 else 64),(0,8),(0,3)):
    m=compare(Case(index,alias,phase,mode),p);seen.update(m.visits);count+=1
 missing=set(range(ENTRY,ENTRY+240,4))-seen;assert not missing,[hex(v)for v in missing]
 return dict(cases=count,executions=count*5,rebases=3,all_60_words_executed=True,zero_and_nonzero_fallback_branches=True,global_alias_layouts=4,four_exact_programs_full_state_equal=True,unguarded_C_public_memory_and_preserved_ABI_equal=True),p0
def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(),Case(7,mode=3),Case(128,phase=8,mode=1),Case(255,mode=2)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps[:4]:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing paired sine fault prefix')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,exact_programs_full_state_equal=True,unguarded_C_fault_order_not_claimed=True)
def connected(p):
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();code={};seen=set();count=0
 for va,pos,n in((SINE,0x75210,104),(WRAP,0x172018,24)):
  words=struct.unpack_from('>%dI'%n,before,source.elf_slot_offset(before,va,n*4));assert words==struct.unpack_from('>%dI'%n,rom,pos);code.update(zip(range(va,va+n*4,4),words))
 constants=dict(GLOBALS);constants[0x800A56A4]=0x40C90FDB
 for a,v in constants.items():assert struct.unpack_from('>I',before,source.elf_slot_offset(before,a,4))[0]==v
 for alias in range(4):
  ps=programs(0,alias)
  for index,phase in itertools.product(range(128),(0,8)):
   c=Case(index,alias,phase);m=fixture(c,ps[0])
   for a,v in constants.items():put(m,a,v)
   result=compare(c,ps,code,m);seen.update(result.visits);count+=1
 return dict(cases=count,executions=count*5,original_sine_words=104,original_wrap_words=24,sine_words_executed=sum(SINE+j*4 in seen for j in range(104)),wrap_words_executed=sum(WRAP+j*4 in seen for j in range(24)),original_constants_pinned=True,independent_finite_sine_and_wrap_reference=True,full_FCSR_and_NaN_payloads_not_claimed=True)
class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==self.owner.return_pc:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
def callers(p):
 rom=(r/'conker/conker.us.bin').read_bytes();s,entry,ps=p;count=0;seen=set();windows=((0x15113EE0,0x141390,7,(0x15113EB4,0x15113EFC),0x15113EF0),(0x15113FB8,0x141468,9,(0x15113FDC,),0x15113FC8))
 for va,off,n,ends,return_pc in windows:
  body=struct.unpack_from('>%dI'%n,rom,off)
  for index,poison,loop in itertools.product((0,1,7,63,128,255),(0,1,0x80000000,0xFFFFFFFF),(0,1)):
   c=Case(index,mode=3);initial=fixture(c,s);put(initial,STATE+0x38,ENTRY);put(initial,0x800D23C0,0x60000);put(initial,0x60002,0x1234,2);expected,calls=reference(initial,c,s)
   for words in ps:
    code=dict(zip(range(entry,entry+240,4),words));m=Oracle(body,initial,c,s,va,code);m.r[16]=STATE;m.r[17]=0x60000;m.r[18]=loop;m.r[23]=0;m.r[30]=0;m.before=m.r[:];m.return_pc=return_pc;m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing paired sine callback boundary')
    assert public(m.memory)==expected and m.calls==[(ENTRY,(STATE,))]+calls and m.poison_hits==1 and m.r[2]==poison
    if va==windows[0][0]:assert m.r[30]==1 and m.r[17]==0x600A0
    else:assert m.r[4]==0x1234 and m.r[5]==0x60000 and m.r[6]==2
    seen.update(m.visits)
   count+=1
  assert all(va+j*4 in seen for j in range(n))
 return dict(cases=count,executions=count*5,original_window_words=[7,9],both_original_JALR_sites_executed=True,return_poisons=4,void_result_ignored=True,larger_dispatcher_not_fully_emulated=True)
def installer():
 rom=(r/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>22I',rom,0xCC06C);va=0x1509EBBC;c=Case();s=symbols();m=fixture(c,s);m.update({SCRIPT+i:0xA5 for i in range(32)})
 for j in range(3):put(m,TABLE+14*12+j*4,struct.unpack_from('>I',rom,0x22D7F8+j*4)[0])
 put(m,SCRIPT+8,14);expected=dict(m);put(expected,STATE+0x38,ENTRY);put(expected,STATE+0x78,0);expected[STATE+0x92]=0;instance=Oracle(body,m,c,s,va);instance.r[16]=SCRIPT;instance.r[2]=STATE;instance.before=instance.r[:];instance.code=WindowCode(instance.code,instance);instance.code.ends=(0x1509ED5C,)
 try:instance.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing paired sine installer boundary')
 assert public(instance.memory)==public(expected)and all(va+j*4 in instance.visits for j in range(22))
 return dict(original_words=22,table_row=14,callback_field='0x38',all_words_executed=True)
def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom);q=dict(aligned_ROM_JALs=[4*i for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_Js=[4*i for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_pointer_literals=[4*i for i,w in enumerate(words)if w==ENTRY]);assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22D7F8]),q;q.update(callback_table='D_80088C90',row=14,callback_field='0x38',ABI='void(u8 *state)');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')
def native():
 selected=source.SELECTED
 lost=selected.replace('first * 16.0f','second * 16.0f').replace('    f32 first;\n','').replace('    first = sinf','    sinf')
 cached=selected.replace('    f32 first;','    f32 first;\n    f32 savedClock = D_800BE9A4;').replace(' * D_800BE9A4',' * savedClock')
 controls=(('wrong-first-phase',selected.replace('first = sinf(*(f32 *)(state + 0x80))','first = sinf(*(f32 *)(state + 0x84))')),('lost-first-result',lost),('wrong-output-amplitude',selected.replace('16.0f','8.0f')),('cached-entry-clock',cached),('wrong-first-coefficient',selected.replace('D_800A31EC','D_800A31F0')),('missing-second-wrap',selected.replace('    *(f32 *)(state + 0x84) = func_15144B68(*(f32 *)(state + 0x84));\n','')),('incorrect-fallback-or',selected.replace(' && ',' || ')),('incorrect-fallback-seven',selected.replace('7.5f','7.0f')))
 assert all(v!=selected for _,v in controls)
 def array(v):return'{'+','.join('0x%Xu'%x for x in v)+'}'
 def image(m):
  v=bytearray(m[STATE+j]for j in range(160))
  for at in(0,8,0x80,0x84):v[at:at+4]=v[at:at+4][::-1]
  return v
 rows=[]
 for index,mode in itertools.product(range(512),range(4)):
  c=Case(index,mode=mode);sy=symbols();m=fixture(c,sy);expected,calls=reference(m,c,sy)
  rows.append('{%d,%d,0x%Xu,%s,%s,%s,%s}'%(index,mode,read(m,sy['D_800BE9A4']),array([a[1][0]for a in calls]),array([provider(c,j)for j in range(4)]),array(image(m)),array(image(expected))))
 code=source.HEADERS+r'''
typedef struct{u32 index,mode,clock,args[4],returns[4];u8 input[160],expected[160];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[48];u8 bytes[192];}Record;
static Record record;static u8 *state;static Case *current;static u32 calls,error;
f32 D_800BE9A4,D_800A31EC,D_800A31F0;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
static f32 helper(f32 x,u32 kind){u32 ordinal=calls++,mode=current->mode;if(ordinal>=4){error=1;return 0;}if(bits(x)!=current->args[ordinal]||kind!=(ordinal>=2))error=1;
 if(ordinal==0&&(mode&1)){*(f32*)(state+0x80)=3.f;*(f32*)(state+0x84)=-4.f;D_800BE9A4=2.f;D_800A31EC=-.125f;D_800A31F0=.25f;}
 if(ordinal==1&&(mode&2)){*(f32*)(state+0x80)=-7.f;*(f32*)(state+0x84)=8.f;D_800BE9A4=.5f;D_800A31EC=.375f;*(f32*)state=-70.f;*(f32*)(state+8)=90.f;}
 if(ordinal==2&&(mode&1)){*(f32*)(state+0x84)=3.25f;*(f32*)(state+8)=1.f;D_800BE9A4=-2.f;}
 if(ordinal==3&&(mode&2)){static f32 z[]={0.f,-0.f,1.f};*(f32*)(state+8)=z[current->index%3];*(f32*)(state+0x80)=-9.f;*(f32*)(state+0x84)=18.f;*(f32*)state=17.f;}
 return floating(current->returns[ordinal]);
}
f32 sinf(f32 x){return helper(x,0);}f32 func_15144B68(f32 x){return helper(x,1);}
'''
 for j,(_,body)in enumerate((('valid',selected),)+controls):code+=body.replace('func_1511C548(','candidate_%d('%j)+'\n'
 code+='static void (*candidates[])(u8*)={'+','.join('candidate_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;state=record.bytes+16;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  current=&cases[n];calls=error=0;D_800BE9A4=floating(current->clock);D_800A31EC=floating(0x3D958106u);D_800A31F0=floating(0x3D851EB8u);
  for(k=0;k<192;k++)record.bytes[k]=0xA5;for(k=0;k<160;k++)state[k]=current->input[k];candidates[j](state);failed=error||calls!=4;
  for(k=0;k<192;k++)if(record.bytes[k]!=(k>=16&&k<176?current->expected[k-16]:0xA5))failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==255u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode);result.append(dict(profile=opt,cases=len(rows),UBSan=True,canaries=True,all_eight_controls_effective=True,controls=[n for n,_ in controls]))
 return result

def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core;fingerprint=source.sha(b''.join((o/n).read_bytes()for n in('qualified-padded.o','selected-final.o','first-linked.elf'))+Path(__file__).read_bytes()+source.SELECTED.encode());saved=o/'runtime-qualification.json'
 if saved.exists():
  q=json.loads(saved.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census();g,p=guest();q=dict(fingerprint=fingerprint,guest=g,faults=faults(p),connected=connected(p),callers=callers(p),installer=installer(),native=native());saved.write_text(json.dumps(q,indent=2)+'\n');return q
