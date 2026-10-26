"""Sentinel wrapper: output ABI, live homes, original caller and strict image."""
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_sentinel_query_fallback_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
SCALAR,SCRATCH,OUT,DIST,ALT=0x800986EC,0x800C3FD0,0x30000,0x31000,0x32000
PRIMARY,FALLBACK=0x15037880,0x150380C0
SYMBOLS={'D_800986EC':SCALAR,'D_800C3FD0':SCRATCH,'func_15037880':PRIMARY,'func_150380C0':FALLBACK}
VALUES=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678,0xFFFF8000,0xFF)
FLOATS=(0xC7C34F80,0,0x80000000,0x3F800000,0x7F800000,0x7FC12345,0x7FA12345,0x7F7FFFFF)
def put(m,a,v,n=4):
 for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'big')):m[(a+i)&0xFFFFFFFF]=b
def get(m,a,n=4):return int.from_bytes(bytes(m[(a+i)&0xFFFFFFFF]for i in range(n)),'big')
def arguments(seed=0,output=OUT,distance=DIST):
 return(output,VALUES[seed%8],VALUES[(seed+1)%8],VALUES[(seed+2)%8],FLOATS[seed%8],VALUES[(seed+3)%8],distance,VALUES[(seed+4)%8],VALUES[(seed+5)%8],VALUES[(seed+6)%8],VALUES[(seed+7)%8])
def fixture(args,phase=0,symbols=None):
 s=symbols or SYMBOLS;m={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x300)}
 for base,n in((OUT-16,96),(DIST-16,48),(ALT-16,48),(s['D_800986EC']-16,64),(s['D_800C3FD0']-32,160)):
  m.update({base+i:(i*13+0x5A)&255 for i in range(n)})
 put(m,s['D_800986EC'],FLOATS[args[1]%8])
 for i,v in enumerate(args[4:]):put(m,STACK+phase+0x10+4*i,v)
 return m

def effect(m,kind,args,pattern,incoming,s):
 output=args[1]if kind=='primary'else args[0]
 if kind=='primary':
  if pattern&1:
   for i,v in enumerate((0x3F800000,0xC0000000,0x40400000)):put(m,output+4*i,v)
  if pattern&2:
   put(m,s['D_800986EC'],0x42F60000)
   for i in range(3):put(m,s['D_800C3FD0']+4*i,0x40800000+i*0x100000)
  if pattern&4:
   for i in range(1,11):put(m,incoming+4*i,ALT if i==6 else 0xA5000000+i*0x12345)
 else:
  for i,v in enumerate((0x41200000,0x41A00000,0x41F00000)):put(m,output+4*i,v)
  put(m,args[6],0x42200000)
 for i in range(4):put(m,incoming-64+4*i,0xB5000000+i)

def public(m,phase=0):return {a:b for a,b in m.items()if not STACK-0x800<=a<STACK+phase}

def reference(initial,args,returned,pattern,phase=0,symbols=None):
 s=symbols or SYMBOLS;m=dict(initial);sp=STACK+phase;output=args[0];sentinel=get(m,s['D_800986EC'])
 for i in range(1,4):put(m,sp+4*i,args[i])
 for base in(output,s['D_800C3FD0']):
  for i in range(3):put(m,base+4*i,sentinel)
 first=(get(m,sp+12),output);calls=[(s['func_15037880'],first)];effect(m,'primary',first,pattern,sp,s)
 if returned==0:
  forwarded=(output,*[get(m,sp+4*i)for i in range(1,11)]);calls.append((s['func_150380C0'],forwarded));effect(m,'fallback',forwarded,pattern,sp,s)
 return public(m,phase),calls

class Boundary(Exception):pass
class CallerBoundary(Exception):pass
class CallerCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==0x1503762C:raise CallerBoundary
  return super().__getitem__(pc)
class Oracle(TimingOracle):
 def __init__(self,words,memory,args,returned=0,pattern=0,phase=0,fault=None,entry=source.ENTRY,connected=None,symbols=None,root_entry=None):
  super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
  self.incoming,self.phase,self.returned,self.pattern=STACK+phase,phase,returned,pattern;self.symbols=symbols or SYMBOLS
  self.root_entry=entry if root_entry is None else root_entry;self.root_size=source.BODY;self.root_fault,self.root_accesses=fault,0;self.target_calls=[];self.observations=[]
 def get(self,a,n):
  self.access()
  if a%n or any((a+i)&0xFFFFFFFF not in self.memory for i in range(n)):raise Boundary(('read',a,n))
  value=get(self.memory,a,n);self.events.append(('R',a,n,value));return value
 def put(self,a,v,n):
  if self.recording:
   self.access()
   if a%n or any((a+i)&0xFFFFFFFF not in self.memory for i in range(n)):raise Boundary(('write',a,n))
   self.events.append(('W',a,n,v&((1<<(n*8))-1)))
  put(self.memory,a,v,n)
 def call_args(self,n):return tuple(self.r[4:4+min(n,4)])+tuple(get(self.memory,self.r[29]+16+4*i)for i in range(max(0,n-4)))
 def record_call(self,target):
  if target==self.root_entry:args=self.call_args(11);self.target_calls.append(args);self.incoming=self.r[29]
  else:
   assert target in(self.symbols['func_15037880'],self.symbols['func_150380C0']),hex(target)
   args=self.call_args(2 if target==self.symbols['func_15037880']else 11)
   if target==self.symbols['func_15037880']:self.observations.append(tuple(get(self.memory,base+4*i)for base in(args[1],self.symbols['D_800C3FD0'])for i in range(3)))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  kind='primary'if target==self.symbols['func_15037880']else'fallback';args=self.calls[-1][1];effect(self.memory,kind,args,self.pattern,self.incoming,self.symbols)
  for register in(1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
  self.r[2]=self.returned if kind=='primary'else 0xD5000080

def run(model):
 try:model.run();return None
 except (Boundary,faults.AccessBoundary,AssertionError)as e:return type(e).__name__,e.args

def native_harness(body):
 return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
f32 D_800986EC;f32 D_800C3FD0[16];static f32 output[16],distance[4],expectedOutput[16],expectedScratch[16];
static u32 expected[11],calls,errors,primaryResult,mode;static f32*selected;
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static f32 real(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
static void primaryEffect(f32*out){int i;if(mode&1){out[0]=1;out[1]=-2;out[2]=3;}if(mode&2){D_800986EC=123;for(i=0;i<3;i++)D_800C3FD0[i]=real(0x40800000u+i*0x100000u);}}
s32 func_15037880(s32 playerIndex,f32*out){int i;if(calls++||playerIndex!=(s32)expected[3]||out!=selected)errors=1;for(i=0;i<3;i++)if(word(out[i])!=word(D_800986EC)||word(D_800C3FD0[i])!=word(D_800986EC))errors=2;primaryEffect(out);return(s32)primaryResult;}
s32 func_150380C0(f32*out,s32 a1,s32 a2,s32 a3,f32 a4,s32 a5,f32*a6,s32 a7,s32 a8,s32 a9,s32 a10){
 u32 actual[11]={(u32)out,(u32)a1,(u32)a2,(u32)a3,word(a4),(u32)a5,(u32)a6,(u32)a7,(u32)a8,(u32)a9,(u32)a10};int i;
 if(calls++!=1||primaryResult)errors=3;for(i=0;i<11;i++)if(actual[i]!=expected[i])errors=4;
 out[0]=10;out[1]=20;out[2]=30;*a6=40;return-127;}
'''+body+r'''
static const u32 values[8]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0x12345678u,0xFFFF8000u,255};
static const u32 floats[8]={0xC7C34F80u,0,0x80000000u,0x3F800000u,0xBF800000u,0x7F7FFFFFu,0xFF7FFFFFu,0x3E800000u};
static int run(void){unsigned int seed,which,ret,pattern,alias;int i;f32*expectSelected;
 if(sizeof(void*)!=4||sizeof(f32)!=4||sizeof(s32)!=4)return 1;
 for(seed=0;seed<256;seed++)for(which=0;which<4;which++)for(pattern=0;pattern<4;pattern++)for(alias=0;alias<3;alias++){
  for(i=0;i<16;i++){output[i]=expectedOutput[i]=(f32)i;D_800C3FD0[i]=expectedScratch[i]=(f32)(i+20);}for(i=0;i<4;i++)distance[i]=(f32)(i+90);
  selected=alias==0?output+4:alias==1?D_800C3FD0:D_800C3FD0+4;expectSelected=alias==0?expectedOutput+4:alias==1?expectedScratch:expectedScratch+4;
  D_800986EC=real(floats[seed%8]);mode=pattern;primaryResult=which==0?0:which==1?1:which==2?0xFFFFFFFFu:0x80000000u;ret=primaryResult;
  for(i=0;i<11;i++)expected[i]=values[(seed+i)%8];expected[0]=(u32)selected;expected[4]=floats[(seed+1)%8];expected[6]=(u32)distance;
  for(i=0;i<3;i++){expectSelected[i]=D_800986EC;expectedScratch[i]=D_800986EC;}
  if(mode&1){expectSelected[0]=1;expectSelected[1]=-2;expectSelected[2]=3;}if(mode&2)for(i=0;i<3;i++)expectedScratch[i]=real(0x40800000u+i*0x100000u);
  if(ret==0){expectSelected[0]=10;expectSelected[1]=20;expectSelected[2]=30;}
  calls=errors=0;func_1503B708(selected,(s32)expected[1],(s32)expected[2],(s32)expected[3],real(expected[4]),(s32)expected[5],distance,(s32)expected[7],(s32)expected[8],(s32)expected[9],(s32)expected[10]);
  if(errors||calls!=(ret==0?2u:1u))return 2;for(i=0;i<16;i++)if(word(output[i])!=word(expectedOutput[i])||word(D_800C3FD0[i])!=word(expectedScratch[i]))return 3;
  if(word(distance[0])!=(ret==0?0x42200000u:0x42B40000u)||distance[1]!=91||distance[2]!=92||distance[3]!=93)return 4;
 }
 return 0;}
'''+START.replace('void _start(void)', 'void __attribute__((force_align_arg_pointer)) _start(void)')

class SentinelQueryTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;source.verify_prepared(cls.out);cls.values=source.snapshot(cls.out);rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>45I',rom,source.ROM));cls.raw_bytes,cls.raw_bindings=source.payload(cls.out/'selected.o')
  cls.words=cls.link(cls.out/'qualified-padded.o','fitted-retail',source.ENTRY,SYMBOLS,full=True);cls.raw=cls.link(cls.out/'selected.o','raw-retail',source.ENTRY,SYMBOLS);assert cls.words==cls.truth
 @classmethod
 def link(cls,obj,name,entry,symbols,full=False):
  from tools.experiments.game_remaining_donor_candidates import link_owner
  if full:
   data,fn=link_owner(ROOT,cls.out,obj,source.OWNER);at=fn[source.FUNCTION]['value'];return list(struct.unpack_from('>45I',data,at))
  script=cls.out/(name+'.ld');elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  p=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%row for row in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert p.returncode==0,p.stderr;return list(struct.unpack_from('>%dI'%(len(source.payload(obj)[0])//4),sections(elf)['.text'][1]))
 def pair(self,initial,args,returned=0,pattern=0,phase=0,fault=None,words=None,symbols=None,entry=source.ENTRY,reference_check=True):
  body=words or(self.truth,self.words,self.raw);models=[Oracle(w,initial,args,returned,pattern,phase,fault,entry=entry,symbols=symbols)for w in body];errors=[run(m)for m in models]
  self.assertEqual(errors[0],errors[1]);self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].root_accesses,models[0].current_pc,models[0].delay_of),(models[1].root_accesses,models[1].current_pc,models[1].delay_of))
  if reference_check:
   self.assertEqual(errors,[None]*len(models));expected,calls=reference(initial,args,returned,pattern,phase,symbols)
   for m in models:self.assertEqual(public(m.memory,phase),expected);self.assertEqual(m.calls,calls);self.assertEqual(m.r[29],STACK+phase)
  return models[0],errors[0]
 def test_01_owner_Make_bindings_real_census_and_inherited_diagnostic(self):
  q=json.loads((self.out/'qualification.json').read_text());source.checked_payload(self.raw_bytes,self.raw_bindings)
  self.assertEqual((q['body_words'],q['alignment_words'],q['frame'],q['guards'],q['preserved_neighbors']),(45,1,64,26,18));self.assertEqual(q['Make']['compact_functions_equal'],19)
  self.assertTrue(q['Make']['complete_padded_object_equal']);self.assertEqual(q['omitted_words'],4);source.normalized_diagnostics((self.out/'before-owner-diagnostics.txt').read_text());source.normalized_diagnostics((self.out/'after-view-owner-diagnostics.txt').read_text())
  source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE]);rom=self.values['conker/conker.us.bin'];jal=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)
  self.assertEqual([i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal],[0x64A94]);self.assertFalse(any(int.from_bytes(rom[i:i+4],'big')==source.ENTRY for i in range(0,len(rom)-3,4)))
  self.receipt['shape']=dict(body_words=45,alignment_words=1,frame=64,guards=26,raw_words=49,raw_bindings=8,bindings=6,neighbors=18,whole_owner_functions=19,unchanged_warning_712=True,typed_call_views_and_fixed_call_folds_preserve_provider_stub_bodies=True,sole_JAL_ROM=0x64A94)
 def test_02_independent_guest_reference_aliases_live_homes_and_lazy_arguments(self):
  cases=0;visits=set()
  for phase,seed,returned,pattern,alias in itertools.product((0,8),range(8),(0,1,0xFFFFFFFF,0x80000000),range(8),range(10)):
   output=(OUT,SCRATCH,SCRATCH+4,SCRATCH-4,SCALAR,STACK+phase+4,STACK+phase+8,STACK+phase+12,STACK+phase+16,STACK+phase+32)[alias];distance=(DIST,output+4,SCRATCH)[seed%3];args=arguments(seed,output,distance);initial=fixture(args,phase)
   model,error=self.pair(initial,args,returned,pattern,phase);self.assertIsNone(error);visits.update(model.visits);cases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+source.BODY,4)))
  lazy=0
  for returned,phase in itertools.product((1,0xFFFFFFFF,0x80000000),(0,8)):
   args=arguments(3);models=[Oracle(w,fixture(args,phase),args,returned,0,phase)for w in(self.truth,self.words)]
   for m in models:
    for a in range(STACK+phase+16,STACK+phase+44):m.memory.pop(a,None)
    for a in range(DIST-16,DIST+32):m.memory.pop(a,None)
    self.assertIsNone(run(m));self.assertEqual(m.calls,[(PRIMARY,(args[3],OUT))])
   self.assertEqual(complete(models[0]),complete(models[1]));lazy+=1
  self.receipt['guest']=dict(cases=cases,all_32_bit_value_classes=True,eight_provider_patterns=True,ten_output_aliases=True,live_homes_and_distance_aliases=True,raw_public_memory_and_calls_equal=True,fitted_complete_original_states_equal=True,all_45_body_words_visited=True,lazy_stack_and_distance_cases=lazy,provider_contracts_not_full_provider_execution=True)
 def test_03_SDK_native32_and_effective_compiled_semantic_controls(self):
  b=source.SELECTED;controls={'wrong-gate':b.replace('== 0','!= 0'),'missing-output':b.replace('    output[1] = sentinel;\n',''),'missing-scratch':b.replace('    D_800C3FD0[2] = sentinel;\n',''),'zero-sentinel':b.replace('f32 sentinel = D_800986EC','f32 sentinel = 0'),'wrong-player':b.replace('(playerIndex, output)','(arg1, output)'),'wrong-primary-output':b.replace('(playerIndex, output)','(playerIndex, D_800C3FD0)'),'wrong-float':b.replace('playerIndex, arg4, arg5','playerIndex, 0.0f, arg5'),'wrong-last':b.replace('arg8, arg9, arg10);','arg8, arg9, 0);')};rows=[]
  for label,opt,body in[(o[1:],o,b)for o in('-O0','-O2','-O3')]+[(n,'-O2',s)for n,s in controls.items()]:
   src=self.out/('native-'+label+'.c');exe=src.with_suffix('');src.write_text(native_harness(body));p=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=30)
   if label in controls:self.assertNotEqual(p.returncode,0,label)
   else:self.assertEqual(p.returncode,0,(label,p.stdout,p.stderr))
   rows.append(dict(name=exe.name,exit=p.returncode,SHA256=source.sha(exe.read_bytes()),negative=label in controls))
  self.receipt['native32']=dict(cases_per_optimization=12288,optimizations=['O0','O2','O3'],trap_UBSan=True,aligned_freestanding_entry=True,all_eleven_arguments=True,three_in_bounds_output_aliases=True,compiled_negatives=8,executions=rows,signaling_NaN_bit_transport_guest_only=True)
 def test_04_original_caller_window_argument_delay_and_unused_result(self):
  rom=self.values['conker/conker.us.bin'];start=0x15037594;end=0x1503762C;window=list(struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x14FD2B50));cases=0
  self.assertEqual(window[(0x150375E4-start)//4],0x0D40EDC2);self.assertEqual(window[(0x150375E8-start)//4],0xAFB80014);self.assertEqual(window[(0x15037600-start)//4],0x3C02800C)
  for seed,returned,pattern,phase in itertools.product(range(8),(0,1,0xFFFFFFFF),range(4),(0,8)):
   initial=fixture(arguments(seed),phase);sp=STACK+phase
   for off,val in((0x54,seed),(0x78,256),(0x84,0x47C35000)):put(initial,sp+off,val)
   initial[0x800C3E78]=(seed+1)&255
   for a in range(SCRATCH-32,SCRATCH+128):initial[a]=0
   models=[]
   for body in(self.truth,self.words):
    connected={source.ENTRY+4*i:w for i,w in enumerate(body)};m=Oracle(window,initial,(0,0,0,0),returned,pattern,phase,entry=start,connected=connected,root_entry=source.ENTRY)
    m.r[16],m.r[17],m.r[31]=12,1,3;m.r[8],m.r[9],m.r[10],m.r[11],m.r[12],m.r[13]=17,19,23,29,31,37;m.f[6],m.f[8],m.f[2]=0x3F800000,0x40000000,0x3F000000;m.code=CallerCode(m.code,m)
    with self.assertRaises(CallerBoundary):m.run()
    self.assertEqual(m.target_calls,[(SCRATCH+24,12,1,seed,0x40400000,256,sp+0x84,31,23,3,37)]);self.assertEqual((m.r[16],m.r[17],m.r[29]),(12,1,sp));self.assertEqual(m.r[2],get(m.memory,0x800C3FFA,1))
    models.append(m)
   self.assertEqual(complete(models[0]),complete(models[1]));cases+=1
  self.receipt['caller']=dict(cases=cases,real_38_word_window=True,eleven_argument_slots=True,arg5_in_JAL_delay_slot=True,output_read_after_call=True,V0_overwritten_before_use=True,parent_full_execution_not_claimed=True)
 def test_05_fired_faults_GNU_carries_and_expected_word_controls(self):
  fired=0
  for seed,returned,pattern in itertools.product((0,3,7),(0,1,0xFFFFFFFF),(0,3,4,7)):
   args=arguments(seed);initial=fixture(args);base,error=self.pair(initial,args,returned,pattern)
   for fault in range(base.root_accesses):
    m,error=self.pair(initial,args,returned,pattern,fault=fault,words=(self.truth,self.words),reference_check=False);self.assertEqual(error[0],'AccessBoundary');fired+=1
  for output in(0xDEADCAFE,OUT+1,STACK-8,STACK-4):
   args=arguments(1,output);self.pair(fixture(args),args,0,0,words=(self.truth,self.words),reference_check=False)
  for i in range(len(self.raw_bytes)//4):
   bad=bytearray(self.raw_bytes);bad[4*i+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),self.raw_bindings)
  for at in self.raw_bindings:
   bad=dict(self.raw_bindings);bad[at]=[('R_MIPS_LO16','wrong')]
   with self.assertRaises(ValueError):source.checked_payload(self.raw_bytes,bad)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));mine=[i for i,r in enumerate(rows)if r['function']==source.FUNCTION];rejections=0
  for i in mine:
   for field in('expected','expected_relocations'):
    bad=[dict(r)for r in rows];bad[i][field]='0x00000000'if field=='expected'else'R_MIPS_LO16:wrong';stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(bad[0]));writer.writeheader();writer.writerows(bad);path=self.out/'negative-guards.csv';path.write_text(stream.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-view-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
    rejections+=1
  fixed,bindings,_=source.normalized(self.raw_bytes,self.raw_bindings);text,missing=emit_function(fixed,dict(value=0,size=source.BODY),bindings,source.FUNCTION,SYMBOLS);self.assertFalse(missing);asm=self.out/'isolated-fitted.s';obj=asm.with_suffix('.o');asm.write_text(text);p=subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);links=0
  for i,(entry,scalar,scratch,primary,fallback)in enumerate(((source.ENTRY,SCALAR,SCRATCH,PRIMARY,FALLBACK),(0x12347FF0,0x70007FFC,0x71008004,0x12437880,0x125380C0),(0x32348000,0x90008004,0x91007FFC,0x32437880,0x325380C0))):
   symbols=dict(D_800986EC=scalar,D_800C3FD0=scratch,func_15037880=primary,func_150380C0=fallback);original=self.link(self.out/'original-func_1503B708.o','original-carry%d'%i,entry,symbols);fitted=self.link(obj,'fitted-carry%d'%i,entry,symbols);raw=self.link(self.out/'selected.o','raw-carry%d'%i,entry,symbols);self.assertEqual(original,fitted)
   for returned,pattern in itertools.product((0,1),(0,3,4)):
    args=arguments(5);self.pair(fixture(args,symbols=symbols),args,returned,pattern,words=(original,fitted,raw),symbols=symbols,entry=entry)
   links+=3
  self.receipt['faults']=dict(fired_prefixes=fired,complete_fitted_original_states=True,misaligned_unmapped_and_saved_register_aliases=True,raw_word_controls=49,binding_controls=8,actual_padder_stale_rejections=rejections,GNU_links=links,HI_LO_and_J26_carries=True,raw_fault_states_not_claimed=True,emitted_guest_faults_not_portable_C=True)
 def test_06_strict_image_every_function_data_and_padding(self):
  before=self.values['conker/build/conker.us.elf'];after=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,after,truth)
  a,_,aa=source.load_elf_functions(str(self.out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=source.load_elf_functions(str(self.out/'first-linked.elf'),'mips-linux-gnu-objdump');self.assertEqual(aa,bb);self.assertEqual(list(n for n in a if a[n]!=b[n]),[source.FUNCTION]);self.assertEqual(len(a),6056)
  data=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0));slot=source.elf_slot_offset(before,source.ENTRY,source.SIZE);self.assertEqual(after[slot+source.BODY:slot+source.SIZE],b'\0'*4)
  row=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION);bad=[]
  for offset in(slot+60,slot+source.BODY,row+8,24,len(after)//2,len(after)-1):
   wrong=bytearray(after);wrong[offset]^=1;bad.append(bytes(wrong))
  bad.append(after+b'!')
  for wrong in bad:
   with self.assertRaises(ValueError):source.check_image(before,wrong,truth)
  self.receipt['image']=dict(functions=6056,other_bodies_fixed=6055,all_addresses_fixed=True,protected_data=data,alignment_word_zero=True,exclusions=0,effective_corruptions=7)
