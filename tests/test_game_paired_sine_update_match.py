"""Direct paired-sine C: original math, callback ABI, native32 and strict image."""
from pathlib import Path
from dataclasses import replace
import itertools,json,math,os,struct,subprocess,unittest
from tools.experiments import game_paired_sine_update_match as source
from tools.tests import game_paired_sine_update_oracle as oracle
from tools.tests.game_paired_sine_update_oracle import Case,bits,floating,fixture,reference,public,SineOracle,put,read,faults,WindowBoundary
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
def controls():
 b=source.SELECTED
 return dict(second_phase=b.replace('((PairedSineOwner *)state)->state.phaseY','((PairedSineOwner *)state)->state.phaseX'),wrong_amplitude=b.replace('state->amplitudeY * sines.y','state->amplitudeX * sines.y'),missing_base=b.replace('state->baseX + state->amplitudeX','0.0f + state->amplitudeX'),same_sine=b.replace('state->amplitudeY * sines.y','state->amplitudeY * sines.x'),wrong_phase_step=b.replace('state->rateY * D_800BE9A4','state->rateX * D_800BE9A4'),skip_wrap=b.replace('state->phaseY = func_15144B68(state->phaseY);','state->phaseY = state->phaseY;'),wrong_return=b.replace('return 1;','return 0;'),early_owner=b.replace('    sines.x = sinf(owner->state.phaseX);\n    state = (PairedSineState *)owner;','    state = (PairedSineState *)owner;\n    sines.x = sinf(((PairedSineOwner *)state)->state.phaseX);'),cached_clock=b.replace('    PairedSineState *state;','    PairedSineState *state;\n    f32 cachedClock;').replace('    state->valueX =','    cachedClock = D_800BE9A4;\n    state->valueX =',1).replace('* D_800BE9A4','* cachedClock'))
def native_cases():
 return[c for c in oracle.corpus()if c.alias is None and c.mode<8 and all(math.isfinite(floating(x))for x in c.fields)]
def native_harness(body,cases):
 rows=[]
 for c in cases:
  initial=fixture(c);expected,calls,_=reference(initial,c)
  arrays=[','.join('0x%Xu'%read(m,oracle.OWNER+off)for off in oracle.OFFSETS)for m in(initial,expected)]
  rows.append('{{%s},{%s},{%s},{%s},0x%Xu,0x%Xu,%d}'%(*arrays,','.join('0x%Xu'%v for _,v in calls),','.join('0x%Xu'%v for v in c.results),c.clock,read(expected,source.CLOCK),c.mode))
 return source.HEADERS+r'''
typedef char Pointer32[sizeof(void*)==4?1:-1];
typedef char StateSize[sizeof(PairedSineState)==40?1:-1];
typedef char StateOffset[__builtin_offsetof(PairedSineOwner,state)==0xA8?1:-1];
typedef char OwnerSize[sizeof(PairedSineOwner)==0xD0?1:-1];
typedef struct {u32 initial[10],expected[10],args[4],results[4],clock,afterClock,mode;} TestCase;
static const TestCase cases[]={'''+',\n'.join(rows)+r'''};
static struct {u32 left[4];PairedSineOwner owner;u32 right[4];} storage;
static u8 contextMemory[64];static const TestCase *item;static u32 ordinal,error;
f32 D_800BE9A4;
static u32 word(f32 x){union{f32 f;u32 w;}v;v.f=x;return v.w;}
static f32 number(u32 x){union{f32 f;u32 w;}v;v.w=x;return v.f;}
static f32 helper(f32 arg,u32 sine){u32 n=ordinal++;PairedSineState*s=&storage.owner.state;
 if(n>=4){error=1;return 0;}if(word(arg)!=item->args[n]||sine!=(n<2))error=1;
 if(n==0&&(item->mode&1)){s->phaseY=2;s->amplitudeX=7;s->baseX=-4;D_800BE9A4=2;}
 if(n==1&&(item->mode&2)){s->baseY=11;s->amplitudeY=-5;s->rateX=.5f;s->rateY=-.25f;D_800BE9A4=.5f;}
 if(n==2&&(item->mode&4)){s->phaseY=3.25f;s->valueX=17;D_800BE9A4=-2;}
 return number(item->results[n]);}
__attribute__((noinline,noclone)) f32 sinf(f32 x){return helper(x,1);}
__attribute__((noinline,noclone)) f32 func_15144B68(f32 x){return helper(x,0);}
'''+body+r'''
static s32(*volatile callback)(PairedSineOwner*,void*)=func_151025F4;
static int run(void){u32 n,i,j,context;u8*p=(u8*)&storage.owner;void*arg;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(context=0;context<3;context++){
  item=&cases[n];ordinal=error=0;for(i=0;i<sizeof(storage);i++)((u8*)&storage)[i]=0xA5;
  for(i=0;i<sizeof(contextMemory);i++)contextMemory[i]=(u8)(i*17+0x57);
  for(i=0;i<10;i++)for(j=0;j<4;j++)p[0xA8+4*i+j]=(u8)(item->initial[i]>>(8*j));
  D_800BE9A4=number(item->clock);arg=context==0?0:context==1?(void*)contextMemory:(void*)(contextMemory+64);
  if(callback(&storage.owner,arg)!=1||ordinal!=4||error||word(D_800BE9A4)!=item->afterClock)return 1;
  for(i=0;i<10;i++)for(j=0;j<4;j++)if(p[0xA8+4*i+j]!=(u8)(item->expected[i]>>(8*j)))return 2;
  for(i=0;i<0xA8;i++)if(p[i]!=0xA5)return 3;
  for(i=0;i<4;i++)if(storage.left[i]!=0xA5A5A5A5||storage.right[i]!=0xA5A5A5A5)return 4;
  for(i=0;i<sizeof(contextMemory);i++)if(contextMemory[i]!=(u8)(i*17+0x57))return 5;
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
class PairedSineUpdateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,label,s=None):
  defs=oracle.symbols()if s is None else s;text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label
  p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=False,real=False):
  initial=fixture(c,s);wanted=reference(initial,c,s,real);pair=[];code=oracle.helper_code(self.rom)if connected else None
  for words in images or(self.truth,self.words,self.raw):
   m=SineOracle(words,initial,c,entry=entry,s=s,connected=code,real=real).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(wanted[0]),wanted[1],1),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_Make_and_original_call_contract(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_151025F4.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),23)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),22);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertFalse(source.NEW_GUARDS)
  words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(words)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[]);self.assertEqual([4*i for i,w in enumerate(words)if w==source.ENTRY],[0x22E24C]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22E220+11*4)[0],source.ENTRY)
  self.assertIn('s32 func_151303EC() {\n    return 0;\n}',self.values['conker/src/game/generated_15D730.c'].decode())
  for at,value in {**oracle.trig.GLOBALS,oracle.BOUND:0x40C90FDB}.items():self.assertEqual(struct.unpack_from('>I',self.values['conker/build/conker.us.elf'],source.elf_slot_offset(self.values['conker/build/conker.us.elf'],at,4))[0],value)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=48,bindings=6,guards=0,neighbors=22,compact_functions=23,Make_commands=3,new_diagnostics=0,original_direct_calls=0,table_slot=11,signature_arguments=2,second_argument='unused context pointer',local_frame_layout_not_historical_source_proof=True)
 def test_02_guest_float_order_aliases_and_owner_reload(self):
  visited=set();cases=list(oracle.corpus());aliases=0
  for c in cases:
   m=self.compare(c);visited.update(m.visits);aliases+=c.alias is not None
  self.assertEqual(len(visited),50);self.receipt['guest']=dict(cases=len(cases),covered_words=50,clock_alias_cases=aliases,late_phase_and_clock_reads=True,incoming_home_mutation_guest_only=True,caller_saved_clobbers=True,FCSR_or_hardware_parity=False)
 def test_03_original_math_and_slot11_callback(self):
  visited=set();count=caller_count=0
  phases=(-90.,-7.,-0.,0.,.00000001,.25,1.5,7.,90.,floating(0x7FC12345))
  for angle,clock,phase in itertools.product(phases,(0.,1.,-1.,4.),(0,8)):
   fields=list(Case().fields);fields[6]=bits(angle);fields[7]=bits(-angle);c=Case(fields=tuple(fields),clock=bits(clock),phase=phase);m=self.compare(c,connected=True,real=True);visited.update(m.visits);count+=1
  for word in(0x4F000000,0xCF000000,0x7F800000,0xFF800000):
   fields=list(Case().fields);fields[6]=word;fields[7]=word;fields[8]=word^0x80000000;fields[9]=word^0x80000000;m=self.compare(Case(fields=tuple(fields)),connected=True,real=True);visited.update(m.visits);count+=1
  coverage=[sum(pc in visited for pc in range(entry,entry+4*n,4))for entry,_,n in oracle.HELPERS];self.assertEqual(coverage[1],24)
  for index,gate,mode,phase in itertools.product((11,-1),(0,1,128,255),(0,7,8,15),(0,8)):
   pair=[]
   for words in(self.truth,self.words,self.raw):
    m,wanted=oracle.caller_machine(self.rom,words,Case(mode=mode,phase=phase),index,gate)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls,m.r[7],m.r[4]),wanted);pair.append(m)
   for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
   caller_count+=1
  self.receipt['integration']=dict(connected_cases=count,caller_cases=caller_count,caller_windows=1,caller_words=17,helper_words=128,helper_coverage=coverage,all_wrap_words=True,complete_literal_helpers=True,parent_current_C_placeholder=True,unused_context_untouched=True,signed_selector_and_return_gate=True,full_parent_or_gameplay=False,infinite_or_huge_wrap_completion_not_claimed=True,FCSR_or_hardware_parity=False)
 def test_04_native32_SDK_and_effective_controls(self):
  cases=native_cases();logs={}
  def run(body,label,opt):
   path=self.fresh/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body,cases));built=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);return subprocess.run([str(exe)],capture_output=True).returncode,built.stderr
  for opt in('-O0','-O2','-O3'):
   code,diag=run(source.SELECTED,'native',opt);self.assertEqual(code,0,opt);logs[opt]=dict(exit=code,diagnostics=diag)
  controls_run=0
  for label,body in controls().items():
   if label in('early_owner','cached_clock'):continue
   code,_=run(body,'negative-'+label,'-O2');self.assertGreater(code,0,(label,code));controls_run+=1
  self.receipt['native']=dict(optimizations=logs,cases_per_optimization=len(cases)*3,input_cases=len(cases),contexts=3,controls=controls_run,SDK=True,pointers32=True,trapping_UBSan=True,valid_owner_backing=True,context_and_fences_unchanged=True,scripted_math=True,guest_home_and_global_alias_not_portable_C_claim=True)
 def test_05_complete_guest_fault_prefixes(self):
  count=caller_count=delay=0
  for c,connected in((Case(),False),(Case(mode=15),False),(Case(alias=0xC0,mode=7),False),(Case(),True)):
   initial=fixture(c);code=oracle.helper_code(self.rom)if connected else None;full=SineOracle(self.truth,initial,c,connected=code,real=connected).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=SineOracle(words,initial,c,connected=code,real=connected);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(m.current_pc,m.delay_of,cut))
    count+=1;delay+=pair[0].delay_of is not None
  c=Case(mode=7);full,_=oracle.caller_machine(self.rom,self.truth,c)
  with self.assertRaises(WindowBoundary):full.run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(self.truth,self.words):
    m,_=oracle.caller_machine(self.rom,words,c);m.cut=cut
    with self.assertRaises(faults.AccessBoundary):m.run()
    pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));caller_count+=1
  self.receipt['faults']=dict(direct_and_connected_prefixes=count,caller_prefixes=caller_count,delay_slot_cuts=delay,complete_state_PC_and_trace=True,portable_C_fault_claimed=False)
 def test_06_raw_rejections_and_GNU_rebases(self):
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for at in range(0,len(raw),4):
   bad=bytearray(raw);bad[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   rejects+=1
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   s=oracle.symbols()if j==0 else dict(sinf=entry+0x10000,func_15144B68=entry+0x20000,D_800BE9A4=(0x80417FFC,0x80528004)[j-1]);paths=(self.out/'original-func_151025F4.o',self.out/'make-shadow/src/game/generated_12DAB0.c.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for mode,phase in itertools.product(range(16),(0,8)):self.compare(Case(mode=mode,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,bindings=6,all_three_objects_linked=True,no_guards=True,padded_object_reproduced=True)
 def test_07_compiled_semantic_controls(self):
  evidence={}
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(mode=mode,alias=alias)for mode,alias in itertools.product((0,7,8,15),(None,0xC0,0xA8))):
    initial=fixture(c);m=SineOracle(words,initial,c).run();wanted=reference(initial,c)
    if(public(m.memory),m.calls,m.r[2])!=(public(wanted[0]),wanted[1],wanted[2]):evidence[name]=dict(mode=c.mode,alias=c.alias);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,private_stack_addresses_excluded_from_semantic_decision=True,guest_only_controls=['early_owner','cached_clock'])
 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)}
  positions=[20,at,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.WINDOW,68),source.elf_slot_offset(before,oracle.TABLE+44,4),0x2D4E84,0x2FBC30]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),155)
  self.receipt['image']=dict(changed_bytes=155,code_bytes=154,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=9,guard_CSV_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v),caller_helpers_and_other_bodies_unchanged=True)
