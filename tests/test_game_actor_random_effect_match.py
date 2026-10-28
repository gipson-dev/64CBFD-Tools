"""Actor random effect: live provider state, float rounding, real dispatch and whole image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_actor_random_effect_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,OTHER=0x20000,0x22000
RANDOM=(0,0x80000000,0x3F000000,0x3F7FFFFF,0x3F800000,0x3DCCCCCD,1,0xBF000000)
PARAMS=(0,0x80000000,0x43AC8000,0xC0200000,0x7FC12345,0x7F800000)
@dataclass(frozen=True)
class Case:
 uid:int=37
 random:int=0x3F000000
 parameter:int=0x43AC8000
 mode:int=0
 layout:int=0
 phase:int=0
 argument:int=0x12345678
@dataclass(frozen=True)
class Globals:
 actor:int=source.ACTOR
 parameter:int=source.PARAMETER
 rng:int=source.RNG
 emitter:int=source.EMITTER

def entered(c):return STACK+c.phase
def fixture(c=Case(),g=Globals(),target_sp=None):
 sp=entered(c)if target_sp is None else target_sp;m={entered(c)+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base in(RECORD,OTHER):m.update({base+i:(i*13+0x59)&255 for i in range(-16,0x60)})
 record=(RECORD,sp-0x3B,sp-80-0x3B,g.parameter-0x3B,g.actor-0x3B,0)[c.layout]
 for base,size in((g.actor,4),(g.parameter,4),(source.SELECTOR,4)):
  m.update({(base+i)&0xFFFFFFFF:(i*7+0xA5)&255 for i in range(-8,size+8)})
 if record:m[record+0x3B]=c.uid
 m[OTHER+0x3B]=0xD3;put(m,g.parameter,c.parameter);put(m,g.actor,record);put(m,source.SELECTOR,32)
 return m

def valid(c):return not(c.layout==4 and c.mode&2)and not(c.layout==5 and not c.mode&1)
def provider_effect(m,c,g):
 if c.mode&1:put(m,g.actor,OTHER)
 if c.mode&2:m[read(m,g.actor)+0x3B]=0xE1
 if c.mode&4:put(m,g.parameter,0xC0200000)
def emitter_effect(m,c,g):
 if c.mode&8:put(m,g.actor,OTHER);put(m,g.parameter,0x3E800000)
def packet(m,c,g):
 actor=read(m,g.actor);uid=m[actor+0x3B];parameter=read(m,g.parameter);scaled=bits(floating(bits(floating(c.random)*10.0))+40.0)
 return(actor,uid,1,0xFFFFFFFF,0,0,parameter,0,0,bits(414.0),3,3,5,bits(20.0),scaled,1,bits(50.0))
def factory_packet(a):
 return(0,0,0,0,0,0,0,a[16],0,a[13],a[14],a[12],0x27,1,a[10],a[11],a[0],a[1],a[2],a[3],0,a[15],a[4],a[5],a[6],a[7],a[8],a[9])
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def reference(initial,c,g=Globals(),target_sp=None):
 sp=entered(c)if target_sp is None else target_sp;m=dict(initial);put(m,sp,c.argument&0xFFFFFFFF);provider_effect(m,c,g)
 for i in range(4):put(m,sp-80+4*i,0xB5000000+i)
 a=packet(m,c,g);emitter_effect(m,c,g);return m,[(g.rng,()),(g.emitter,a)]
class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),g=Globals(),entry=source.ENTRY,connected=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.argument,),connected=connected);self.case,self.globals=c,g;self.trace=[];self.target_entered=entered(c)
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  sizes={source.ENTRY:1,self.globals.rng:0,self.globals.emitter:17,source.FACTORY:28};assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==source.ENTRY:self.target_entered=self.r[29]
 def hook(self,target):
  c,g=self.case,self.globals
  if target==g.rng:provider_effect(self.memory,c,g);homes=4
  elif target in(g.emitter,source.FACTORY):emitter_effect(self.memory,c,g);homes=17 if target==g.emitter else 28
  else:raise AssertionError(('Unowned actor-effect provider',target))
  for i in range(homes):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEAD1234
  if target==g.rng:self.f[0]=c.random

def controls():
 b=source.SELECTED;head='void func_1506FD30(s32 arg0) {'
 actor=b.replace(head,head+'\n    struct127 *captured = D_800D154C;').replace('func_150E2EA4(D_800D154C, D_800D154C->unique_id','func_150E2EA4(captured, captured->unique_id')
 param=b.replace(head,head+'\n    f32 captured = D_80099EA0;').replace('zero, D_80099EA0,','zero, captured,')
 uid=b.replace(head,head+'\n    u8 captured = D_800D154C->unique_id;').replace('D_800D154C->unique_id,','captured,')
 return dict(wrong_scale=b.replace('random * 10.0f','random * 9.0f'),wrong_bias=b.replace('+ 40.0f','+ 41.0f'),double_scalar=b.replace('random * 10.0f + 40.0f','(f64)random * 10.0 + 40.0'),reassociated_scalar=b.replace('random * 10.0f + 40.0f','(random + 4.0f) * 10.0f'),signed_uid=b.replace('D_800D154C->unique_id,','(s8)D_800D154C->unique_id,'),cached_actor=actor,cached_parameter=param,cached_uid=uid,skip_random=b.replace('func_150ADA68()','0.5f'),wrong_flag=b.replace('unique_id, 1, -1,','unique_id, 2, -1,'),wrong_sentinel=b.replace('unique_id, 1, -1,','unique_id, 1, 0,'),wrong_limit=b.replace('3, 3, 5, 20.0f','3, 3, 4, 20.0f'),wrong_zero=b.replace('f32 zero = 0.0','f32 zero = 1.0'),wrong_parameter=b.replace('zero, D_80099EA0,','zero, 0.0f,'))

def native_harness():
 text=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&__builtin_offsetof(struct127,unique_id)==0x3B)?1:-1];
static struct{u32 pre[4];struct127 a,b;u32 post[4];}world,wanted;
struct127 *D_800D154C;f32 D_80099EA0;
static u32 mode,calls,bad,rngbits,wantedParameter,wantedId,got[17],want[17];static struct127*wantedActor;
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static void copy(void*d,const void*s,u32 n){u8*a=d;const u8*b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];}
static s32 same(const void*a,const void*b,u32 n){const u8*x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
f32 func_150ADA68(void){
 if(calls++!=0)bad=1;
 if(mode&1)D_800D154C=&world.b;
 if(mode&2)D_800D154C->unique_id=0xE1;
 if(mode&4)D_80099EA0=real(0xC0200000);
 return real(rngbits);
}
void func_150E2EA4(struct127*a,s32 id,s32 flag,s32 sentinel,f32 x,f32 y,f32 p,f32 u,f32 v,f32 radius,s32 n,s32 k,s32 limit,f32 low,f32 random,s32 enabled,f32 high){
 u32 values[17]={(u32)a,(u32)id,(u32)flag,(u32)sentinel,word(x),word(y),word(p),word(u),word(v),word(radius),(u32)n,(u32)k,(u32)limit,word(low),word(random),(u32)enabled,word(high)};u32 i;
 if(calls++!=1)bad=1;
 for(i=0;i<17;i++){got[i]=values[i];if(got[i]!=want[i])bad=1;}
 if(mode&8){D_800D154C=&world.b;D_80099EA0=0.25f;}
}
'''
 variants={'selected':source.SELECTED,**controls()}
 for name,body in variants.items():text+=body.replace(source.FUNCTION,source.FUNCTION+'_'+name)+'\n'
 text+=r'''
static s32 run(void(*fn)(s32),u32 random,u32 parameter,u32 id,u32 m){
 volatile f32 product;f32 scalar;struct127*finalActor;u32 finalParameter,i;
 mode=m;rngbits=random;calls=bad=0;world.a.unique_id=(u8)id;world.b.unique_id=0xD3;copy(&wanted,&world,sizeof(world));
 D_800D154C=&world.a;D_80099EA0=real(parameter);
 wantedActor=(m&1)?&world.b:&world.a;wantedId=(m&2)?0xE1:((m&1)?0xD3:id);
 if(m&2){if(m&1)wanted.b.unique_id=0xE1;else wanted.a.unique_id=0xE1;}
 wantedParameter=(m&4)?0xC0200000:parameter;product=real(random)*10.0f;scalar=product+40.0f;
 {u32 values[17]={(u32)wantedActor,wantedId,1,0xFFFFFFFF,0,0,wantedParameter,0,0,0x43CF0000,3,3,5,0x41A00000,word(scalar),1,0x42480000};for(i=0;i<17;i++){want[i]=values[i];got[i]=0xDEADBEEF;}}
 finalActor=(m&8)?&world.b:wantedActor;finalParameter=(m&8)?0x3E800000:wantedParameter;
 fn(32);
 return bad||calls!=2||D_800D154C!=finalActor||word(D_80099EA0)!=finalParameter||!same(&world,&wanted,sizeof(world));
}
int main(void){
 u32 i,j,k,n=0;u32 modes[4]={0,3,4,15};u32 params[4]={0x43AC8000,0x80000000,0x7FC12345,0xC0200000};u32 samples[8]={0,0x80000000,0x3F000000,0x3F7FFFFF,0x3F800000,0x3DCCCCCD,1,0xBF000000};
 u8*bytes=(u8*)&world;for(i=0;i<sizeof(world);i++)bytes[i]=(u8)(i*13+0x59);
 for(i=0;i<65536;i++){volatile f32 value=(f32)i*real(0x37800080);for(j=0;j<4;j++){if(run(func_1506FD30_selected,word(value),params[j],(i*13)&255,modes[j]))return 10;n++;}}
 for(i=0;i<256;i++)for(j=0;j<8;j++)for(k=0;k<4;k++){if(run(func_1506FD30_selected,samples[j],params[k],i,modes[k]))return 11;n++;}
 if(n!=270336)return 12;
'''
 for index,name in enumerate(controls()):
  text+=' {s32 fired=0;u32 uid,seed,m;for(uid=0;uid<256&&!fired;uid+=127)for(seed=0;seed<65536&&!fired;seed++)for(m=0;m<4&&!fired;m++){volatile f32 v=(f32)seed*real(0x37800080);fired=run(func_1506FD30_'+name+',word(v),0x43AC8000,uid,modes[m]);}if(!fired)return '+str(30+index)+';}\n'
 return text+'return 0;}\n'+START.replace('run()','main()')

class ActorRandomEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));raw,_=source.checked_payload(*source.payload(cls.out/'selected.o'));cls.installed=(ROOT/source.SOURCE).read_bytes()==(cls.out/'proposed-owner.c').read_bytes();cls.fresh=cls.out/('fresh-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=True);cls.receipt={};link_obj=cls.fresh/'selected-local.o';link_obj.write_bytes((cls.out/'selected.o').read_bytes());data,funcs=source.link_owner(ROOT,cls.fresh,link_obj,source.OWNER);f=funcs[source.FUNCTION];cls.words=list(struct.unpack_from('>48I',data,f['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,g=Globals()):
  initial=fixture(c,g);want,calls=reference(initial,c,g);runs=[Oracle(words,initial,c,g,entry).run()for words in(self.truth,self.words)if images is None]if images is None else[Oracle(words,initial,c,g,entry).run()for words in images]
  for m in runs:self.assertEqual((public(m.memory),m.calls),(public(want),calls));self.assertEqual(m.r[29],entered(c))
  self.assertEqual(complete(runs[0]),complete(runs[1]));self.assertEqual(runs[0].trace,runs[1].trace);return runs[1]
 def test_01_actual_owner_Make_callback_ABI_and_inherited_diagnostics(self):
  source.check_inputs(ROOT,self.out,self.installed);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/'original-func_1506FD30.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),327);self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),327);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game_981E0.c.o.compact'),328);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  before=self.values[source.SOURCE].decode();after=(self.out/'proposed-owner.c').read_text();self.assertEqual(after,source.recovered_owner(before));self.assertEqual(before.count('#pragma GLOBAL_ASM'),14);self.assertEqual(after.count('#pragma GLOBAL_ASM'),14);self.assertIn('void func_1506FD30(s32 arg0);',after);self.assertIn('extern void (*D_80086150[])(s32);',self.values['conker/include/variables.h'].decode());self.assertIn('/* 0x3B */  u8  unique_id;',self.values['conker/include/structs.h'].decode())
  diagnostics=[source.normalized_diagnostics((self.out/n).read_text())for n in('before-owner-diagnostics.txt','after-owner-diagnostics.txt','actual-Make-diagnostics.txt')];self.assertEqual(len(set(diagnostics)),1);self.assertFalse((self.out/'selected-diagnostics.txt').read_bytes());self.assertEqual(len(source.payload(self.out/'selected.o')[1]),6)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(source.ENTRY>>2&0x3FFFFFF);self.assertFalse(any(w in(jal,jump)for w in ws));self.assertEqual([i*4 for i,w in enumerate(ws)if w==source.ENTRY],[0x22AC90])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=80,bindings=6,guards=0,compact_functions=328,neighbors=327,GLOBAL_ASM=14,Make_commands=5,inherited_owner_diagnostics_equal=True,selected_diagnostics=0,canonical_unique_id_and_void_s32_callback=True)
 def test_02_guest_live_global_reads_provider_mutations_and_aliases(self):
  count=0;visits=set()
  for value,uid,mode,layout in itertools.product(RANDOM,(0,1,127,128,255),range(16),range(6)):
   c=Case(uid,value,PARAMS[(uid+layout)%len(PARAMS)],mode,layout,phase=(layout&1)*8)
   if not valid(c):continue
   m=self.compare(c);visits.update(m.visits);count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_body_words=len(visits),six_pointer_ID_parameter_and_stack_alias_layouts=True,provider_redirects_ID_parameter_and_post_emit_mutations=True,initial_null_allowed_when_provider_redirects=True,complete_private_trace_and_independent_public_call_reference=True,bounded_float32_model_not_full_FCSR=True)
 def test_03_native32_all_random_encodings_IDs_and_effective_controls(self):
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=270336,effective_controls=len(controls()),all65536_random_low_halfwords_and_all256_IDs=True,typed_canonical_actor_storage_and_whole_world_fences=True,trapping_UBSan=True,separate_float32_rounding=True,guest_aliases_not_portable_native_claim=True)
 def test_04_original_dispatcher_and_retained_emitter_wrapper_chain(self):
  for n,address,size in(('dispatcher',0x15071D38,64),('emitter_wrapper',source.EMITTER,236),('random_provider',source.RNG,100)):
   raw=(self.out/('original-'+n+'.bin')).read_bytes();rom_at=address-0x14FD2B50;elf_at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],address,size);self.assertEqual(raw,self.rom[rom_at:rom_at+size]);self.assertEqual(raw,self.values['conker/build/conker.us.elf'][elf_at:elf_at+size])
  parent=list(struct.unpack('>16I',(self.out/'original-dispatcher.bin').read_bytes()));wrapper=list(struct.unpack('>59I',(self.out/'original-emitter_wrapper.bin').read_bytes()));self.assertEqual(parent[0],0x27BDFFE8);self.assertEqual(wrapper[0],0x27BDFF88);self.assertEqual(self.rom[0x22AC90:0x22AC94],struct.pack('>I',source.ENTRY));data=self.values['conker/asm/data/22AC10.rodata.s'].decode();self.assertIn('22AC90 800861D0 1506FD30',data);count=0
  for value,uid,mode in itertools.product(RANDOM,(0,127,128,255),(0,3,4,15)):
   c=Case(uid,value,mode=mode,argument=32);sp=entered(c)-24;initial=fixture(c,target_sp=sp);put(initial,source.TABLE+32*4,source.ENTRY);want,calls=reference(initial,c,target_sp=sp);expected=[(source.ENTRY,(32,)),calls[0],calls[1],(source.FACTORY,factory_packet(calls[1][1]))];runs=[]
   for words in(self.truth,self.words):
    connected={**{source.ENTRY+i*4:w for i,w in enumerate(words)},**{source.EMITTER+i*4:w for i,w in enumerate(wrapper)}};m=Oracle(parent,initial,c,entry=0x15071D38,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(want),expected));self.assertEqual(m.r[29],entered(c));runs.append(m)
   self.assertEqual(complete(runs[0]),complete(runs[1]));self.assertEqual(runs[0].trace,runs[1].trace);count+=1
  c=Case(argument=2);initial=fixture(c);put(initial,source.SELECTOR,2);put(initial,source.TABLE+2*4,0);m=Oracle(parent,initial,c,entry=0x15071D38).run();self.assertEqual(m.calls,[])
  self.receipt['caller']=dict(original_dispatch_words=16,retained_wrapper_words=59,connected_cases=count,null_registration_suppresses_call=True,original_callback_argument32_and_void_return=True,outer17_inner28_arguments=True,frames=[24,80,120],deepest_frame=224,random_and_final_factory_bounded_no_full_provider_claim=True)
 def test_05_fired_access_prefixes_and_lazy_actor_mapping(self):
  cuts=0
  for value,mode,layout in itertools.product((0,0x3F7FFFFF),(0,3,4,15),range(6)):
   c=Case(random=value,mode=mode,layout=layout)
   if not valid(c):continue
   initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    runs=[]
    for words in(self.truth,self.words):
     m=Oracle(words,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);runs.append(m)
    self.assertEqual(complete(runs[0]),complete(runs[1]));self.assertEqual(runs[0].trace,runs[1].trace);cuts+=1
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_private_state_PC_delay_trace_equal=True,incoming_home_and_provider_outgoing_aliases=True,initial_null_not_dereferenced_before_provider=True,opaque_GPR_FPR_HI_LO_and_argument_home_clobbers=True)
 def test_06_actual_regular_padder_raw_controls_and_three_GNU_layouts(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[80]^=1
  for data,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,12:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(data,bindings)
  p=self.fresh/'padded.s';p.write_text(source.pad_c_object.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=ROOT/'conker/retail_word_patches.us.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,g)in enumerate(((source.ENTRY,Globals()),(0x17007FFC,Globals(0x800B7FFC,0x800A8004,0x17012340,0x17022340)),(0x2500FFFC,Globals(0x800B8004,0x800AFFFC,0x25123400,0x25234500)))):
   images=[]
   for k,obj in enumerate((self.out/'original-func_1506FD30.o',self.out/'selected.o')):
    script=self.fresh/('layout-%d-%d.ld'%(j,k));elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);symbols=dict(D_800D154C=g.actor,D_80099EA0=g.parameter,func_150ADA68=g.rng,func_150E2EA4=g.emitter);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);images.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
   self.assertEqual(*images)
   for uid,mode,layout in itertools.product((0,128,255),(0,3,4,15),(0,1,3)):
    self.compare(Case(uid,0x3F7FFFFF,mode=mode,layout=layout),images,entry,g);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,six_HI_LO_J26_bindings=True,signed_low_half_carries=True,raw_binding_controls=3,actual_regular_padder_equal=True,guards=0)
 def test_07_actual_IDO_cached_actor_parameter_and_rounding_controls(self):
  fired=[]
  for name,c in(('cached_actor',Case(mode=3)),('cached_parameter',Case(mode=4)),('reassociated_scalar',Case(random=1011712206))):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);data,functions=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=functions[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));initial=fixture(c);_,calls=reference(initial,c);m=Oracle(words,initial,c).run();self.assertNotEqual(m.calls,calls,name);fired.append(name)
  self.receipt['compiled_controls']=dict(actual_IDO_controls=len(fired),names=fired,all_fail_by_call_values_in_mapped_memory=True)
 def test_08_entire_image_closed_three_name_recipe_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+192];actual=(self.out/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION);metadata=next(p for p,n,_,_ in source.symbol_rows(before)if n=='D_80099EA0')
  for offset in(20,at,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol+8,metadata+4):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(len(actual),len(before));self.assertEqual(sum(x!=y for x,y in zip(before,actual)),199);self.assertEqual(sum(x!=y for x,y in zip(before[at:at+192],truth)),152);self.receipt['image']=dict(changed_bytes=199,code_bytes=152,size_bytes=1,closed_three_name_serialization_bytes=46,exclusions=0,effective_corruptions=6,all_named_definitions_checked=True,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088)
