"""Byte phase offsets: actual mixed ABI, alias order, two checked guards and image."""
from dataclasses import replace
from pathlib import Path
import csv,io,itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_byte_phase_offset_match as source
from tools.tests import game_byte_phase_offset_oracle as oracle
from tools.tests.game_byte_phase_offset_oracle import Case,OffsetOracle,fixture,reference,public
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED;update='    phases[0] += rates[0] * (u32)D_800BE9E4;\n    phases[1] += rates[1] * (u32)D_800BE9E4;\n'
 return dict(missing_first=b.replace('    phases[0] += rates[0] * (u32)D_800BE9E4;\n',''),
  missing_second=b.replace('    phases[1] += rates[1] * (u32)D_800BE9E4;\n',''),
  wrong_rate=b.replace('rates[1]','rates[0]'),wrong_angle=b.replace('- 0x40','- 0x3F'),
  wrong_amplitude=b.replace('amplitudes[1]','amplitudes[0]'),missing_base=b.replace(' + base',' - base'),
  early_ticks=b.replace('    f32 sample;','    f32 sample;\n    u32 ticks = (u32)D_800BE9E4;').replace('* (u32)D_800BE9E4','* ticks'),
  early_amplitude=b.replace('    f32 sample;','    f32 sample;\n    f32 saved = amplitudes[0];').replace('sample * amplitudes[0]','sample * saved'),
  early_phase=b.replace('    sample = func_151423D8((u8)(phases[0]', '    saved = phases[1];\n    sample = func_151423D8((u8)(phases[0]').replace('    f32 sample;','    f32 sample;\n    u8 saved;').replace('(phases[1] - 0x40)','(saved - 0x40)'),
  late_advance=b.replace(update,'').replace('    *second = sample * amplitudes[1] + base;','    *second = sample * amplitudes[1] + base;\n'+update.rstrip()))

def native_harness(caller):
 t=source.HEADERS+source.SELECTED+'\n'+caller+'\n'
 for name,b in controls().items():t+=b.replace(source.FUNCTION,'negative_'+name)+'\n'
 t+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(f32)==4)?1:-1];
typedef void(*Fn)(u8*,s8*,f32,f32*,f32*,f32*);
typedef struct {u32 prefix;u8 phase[2];s8 rate[2];f32 amp[2],out[2];u32 suffix;} State;
static State actual,expected;static s32 expectedTicks; s32 D_800BE9E4;
static u32 calls,error,mode;static u8 wanted[2];static u8 *livePhase;static f32 *liveAmp;
static f32 value(u8 angle){return ((s32)angle-128)*0.03125f;}
static void effect(u32 ordinal,u8*p,f32*a){if(ordinal==0&&(mode&1)){a[0]=-7.5f;p[1]=0x91;}if(ordinal==1&&(mode&2))a[1]=11.5f;}
f32 func_151423D8(u8 angle){if(calls>=2||angle!=wanted[calls])error=1;effect(calls,livePhase,liveAmp);calls++;return value(angle);}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 ticks[]={0,1,7,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
static int check(Fn fn){u32 seed,j,alias,i;f32 base,sample;u8 *p,*q;f32 *first,*efirst;
 for(seed=0;seed<256;seed++)for(j=0;j<6;j++)for(mode=0;mode<4;mode++)for(alias=0;alias<3;alias++){
  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=(u8)(seed+i*13);
  actual.phase[0]=(u8)seed;actual.phase[1]=(u8)(seed*17+3);actual.rate[0]=(s8)(seed*7+1);actual.rate[1]=(s8)(seed*11+3);
  actual.amp[0]=((s32)seed-127)*0.25f;actual.amp[1]=((s32)seed-111)*-0.125f;actual.out[0]=actual.out[1]=0.0f;
  copy(&expected,&actual,sizeof(actual));D_800BE9E4=expectedTicks=(s32)ticks[j];base=((s32)seed-128)*0.125f;
  p=alias==1?(u8*)&D_800BE9E4:actual.phase;q=alias==1?(u8*)&expectedTicks:expected.phase;
  first=alias==2?actual.amp+1:actual.out;efirst=alias==2?expected.amp+1:expected.out;
  q[0]=(u8)(q[0]+expected.rate[0]*(u32)expectedTicks);q[1]=(u8)(q[1]+expected.rate[1]*(u32)expectedTicks);
  wanted[0]=(u8)(q[0]-64);sample=value(wanted[0]);effect(0,q,expected.amp);*efirst=sample*expected.amp[0]+base;
  wanted[1]=(u8)(q[1]-64);sample=value(wanted[1]);effect(1,q,expected.amp);expected.out[1]=sample*expected.amp[1]+base;
  calls=error=0;livePhase=p;liveAmp=actual.amp;fn(p,actual.rate,base,actual.amp,first,actual.out+1);
  if(error||calls!=2||!same(&actual,&expected,sizeof(actual))||D_800BE9E4!=expectedTicks)return 1;
 }return 0;
}
typedef struct {u8 prefix[0x38];f32 first,second;u8 gap[0x68];f32 base;u8 phases[2];s8 rates[2];f32 amplitudes[2];u8 tail[64];} Owner;
typedef char Layout[(__builtin_offsetof(Owner,base)==0xA8&&__builtin_offsetof(Owner,phases)==0xAC&&__builtin_offsetof(Owner,amplitudes)==0xB0)?1:-1];
static Owner owner,want;
static int caller_check(void){u32 seed,i;f32 sample;
 for(seed=0;seed<256;seed++){
  for(i=0;i<sizeof(owner);i++)((u8*)&owner)[i]=(u8)(seed+i*13);
  owner.base=((s32)seed-128)*0.25f;owner.phases[0]=(u8)seed;owner.phases[1]=(u8)(seed*17+3);
  owner.rates[0]=(s8)(seed*7+1);owner.rates[1]=(s8)(seed*11+3);owner.amplitudes[0]=3.25f;owner.amplitudes[1]=-1.75f;
  copy(&want,&owner,sizeof(owner));D_800BE9E4=3;mode=0;
  want.phases[0]=(u8)(want.phases[0]+want.rates[0]*3u);want.phases[1]=(u8)(want.phases[1]+want.rates[1]*3u);
  wanted[0]=(u8)(want.phases[0]-64);sample=value(wanted[0]);want.first=sample*want.amplitudes[0]+want.base;
  wanted[1]=(u8)(want.phases[1]-64);sample=value(wanted[1]);want.second=sample*want.amplitudes[1]+want.base;
  calls=error=0;livePhase=owner.phases;liveAmp=owner.amplitudes;
  if(func_15192308((u8*)&owner,0x12345678)!=1||error||calls!=2||!same(&owner,&want,sizeof(owner)))return 1;
 }return 0;
}
static int run(void){if(check(func_15131C84)||caller_check())return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(negative_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class BytePhaseOffsetTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>50I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
  elf=cls.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,oracle.TRIG_TABLE,260);cls.table=elf[at:at+260]
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,label,s=None,function=None):
  defs=oracle.symbols()if s is None else s;function=function or source.FUNCTION;text,functions,bindings=parse_object(obj);f=functions[function];assembly,unknown=emit_function(text,f,bindings,function,defs);assert not unknown;p=cls.fresh/label
  p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=False):
  initial=fixture(c,s,self.table if connected else None);wanted=reference(initial,c,s,connected);pair=[];code=oracle.helpers(self.rom)if connected else None
  for words in images or(self.truth,self.words):
   m=OffsetOracle(words,initial,c,entry=entry,s=s,connected=code).run();self.assertEqual((public(m.memory),m.calls,m.snapshots),(public(wanted[0]),wanted[1],wanted[2]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0]
 def test_01_owner_actual_Make_and_corrected_caller_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(sum(a!=b for a,b in zip(self.truth,self.raw)),2)
  self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_15131C84.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),31)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),30);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  for label in('before','after'):
   text=(self.out/('caller-'+label+'.c')).read_text();obj,diag=source.compile_owner(ROOT,self.fresh,text,'fresh-caller-'+label)
   old=(self.out/('caller-'+label+'-diagnostics.txt')).read_text();normalize=lambda d:re.sub(r'(cfe: Warning 712: ).*?(, line 29:)',r'\1<file>\2',d)
   self.assertEqual(normalize(diag),normalize(old));self.assertEqual(diag.count('Warning 712:'),1);self.assertIn('s32 call_result = func_15192308(arg0, arg1);',diag);self.assertEqual(source.same_functions(obj,self.out/('caller-'+label+'.o')),8)
  self.assertEqual(source.same_functions(self.out/'caller-before.o',self.out/'caller-after.o'),8);self.assertEqual((self.out/'caller-qualified-padded.o').read_bytes(),self.values[source.CALLER_OBJECT])
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes());self.assertEqual(source.recovered_caller(self.values[source.CALLER_SOURCE].decode()).encode(),(self.out/'proposed-caller.c').read_bytes())
  self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual(len(json.loads((self.out/'caller-Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(ws)if w==jal],[0x15F27C,0x1BF7E8]);self.assertNotIn(source.ENTRY,ws)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(body_words=50,frame=24,bindings=4,guards=2,neighbors=30,compact_functions=31,Make_commands=5,caller_owner_functions=8,caller_Make_commands=3,caller_object_bytes_unchanged=True,caller_inherited_warning712=1,mixed_float_argument_in_a2=True,void_return=True)
 def test_02_guest_byte_lanes_aliases_and_late_reads(self):
  vectors=[]
  for byte,field in itertools.product(range(256),range(4)):
   vectors.append(Case(angles=(byte,201)if field==0 else(17,byte)if field==1 else(17,201),rates=(byte,241)if field==2 else(3,byte)if field==3 else(3,241)))
  vectors.extend(Case(angles=(a,a^255),rates=(128,255),ticks=t,mode=m,phase=p)for a,t,m,p in itertools.product((0,63,64,127,128,191,192,255),(0,1,7,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,4,8,15),(0,8)))
  aliases=[Case(phases=p,ticks=0x12345678)for p in(oracle.RATE-1,oracle.RATE,oracle.RATE+1,*[oracle.TICKS+i for i in range(4)])]
  aliases.extend(Case(first=p)for p in(oracle.PHASE,oracle.AMP,oracle.AMP+4,oracle.SECOND,oracle.TICKS))
  aliases.extend(Case(phases=oracle.STACK+p+at,phase=p)for p,at in itertools.product((0,8),(-24,-16,32,40)))
  aliases.extend(Case(base=b,amplitudes=(a,0xBEAAAAAB))for a,b in itertools.product((0,0x80000000,0x3F800001,0x4B000001,0x00800000),(0,0x80000000,0xBF800001,0x4B000000)))
  vectors+=aliases;visited=set()
  for c in vectors:visited.update(self.compare(c).visits)
  self.assertEqual(len(visited),50);self.compare(Case(),images=(self.truth,self.raw))
  self.receipt['guest']=dict(cases=len(vectors),covered_words=50,alias_and_rounding_vectors=len(aliases),all_phase_and_signed_rate_lanes=True,live_tick_reload=True,first_output_before_second_phase_read=True,private_home_mutation_scope='guest only',NaN_payload_FCSR_or_hardware_claimed=False)
 def test_03_original_trig_and_complete_callers(self):
  before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,oracle.TRIG,108);self.assertEqual(before[at:at+108],self.rom[0x16F888:0x16F8F4]);visited=set()
  for byte,phase in itertools.product(range(256),(0,8)):visited.update(self.compare(Case(angles=(byte,byte^255),phase=phase),connected=True).visits)
  self.assertEqual(sum(p in visited for p in range(oracle.TRIG,oracle.TRIG+108,4)),27)
  linked=self.linked(self.out/'caller-make-shadow/src/game/generated_1BF090.c.o',0x15192308,'corrected-caller',s={source.FUNCTION:source.ENTRY},function='func_15192308');self.assertEqual(linked,list(struct.unpack_from('>20I',self.rom,0x1BF7B8)))
  count=0;covered=[set(),set()]
  for index,connected,phase,mode in itertools.product(range(2),range(2),(0,8),(0,1,15)):
   if connected and mode:continue
   c=Case(phase=phase,mode=mode);pair=[]
   for words in(self.truth,self.words):
    m,initial,adjusted=oracle.caller_machine(self.rom,words,c,index,bool(connected),self.table if connected else None,linked if index else None);m.run();wanted=reference(initial,adjusted,connected=bool(connected),home=oracle.STACK+phase-40)
    self.assertEqual((public(m.memory),m.calls,m.snapshots,m.r[2]),(public(wanted[0]),[(source.ENTRY,oracle.args(adjusted))]+wanted[1],wanted[2],1));self.assertEqual(m.target_entries,[oracle.args(adjusted)]);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));covered[index].update(pair[0].visits);count+=1
  self.assertEqual([sum(p in v for p in range(row[0],row[0]+80,4))for row,v in zip(oracle.CALLERS,covered)],[20,20])
  self.receipt['integration']=dict(connected_cases=512,trig_words=27,trig_covered_words=27,table_bytes=260,caller_cases=count,caller_words=[20,20],both_returns_one=True,corrected_C_caller_linked=True,original_GLOBAL_ASM_caller_unchanged=True,gameplay_claimed=False)
 def test_04_native32_SDK_corrected_C_caller_and_controls(self):
  text=(self.out/'proposed-caller.c').read_text();m=re.search(r's32 func_15192308\([^{}]*\) \{[^{}]*\}',text);self.assertIsNotNone(m)
  p=self.fresh/'native.c';p.write_text(native_harness(m[0]));logs={}
  for opt in('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(optimizations=logs,cases_per_profile=256*6*4*3,caller_cases_per_profile=256,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,native_representation_alias=True,valid_backing_and_canaries=True)
 def test_05_direct_and_caller_fault_prefixes(self):
  count=delay=0
  for connected,parent,mode in itertools.product(range(2),range(3),(0,15)):
   if connected and mode:continue
   c=Case(mode=mode)
   def machine(words):return oracle.caller_machine(self.rom,words,c,parent-1,bool(connected),self.table if connected else None)[0]if parent else OffsetOracle(words,fixture(c,table=self.table if connected else None),c,connected=oracle.helpers(self.rom)if connected else None)
   full=machine(self.truth).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=machine(words);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=count,delay_slot_cuts=delay,complete_state_PC_trace=True,portable_C_fault_claimed=False)
 def test_06_guard_rejections_padder_and_three_GNU_layouts(self):
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for at in range(0,len(raw),4):
   bad=bytearray(raw);bad[at+3]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.normalized_payload(raw,bad)
   rejects+=1
  for row in source.NEW_GUARDS:
   at=int(row['offset'],0);a,b=int(row['expected'],0),int(row['replacement'],0);self.assertFalse(rs.get(at));self.assertEqual(a&~((31<<11)|(31<<16)),b&~((31<<11)|(31<<16)));self.assertEqual((a>>11&31,a>>16&31),(b>>16&31,b>>11&31))
   for variant in('word','binding'):
    altered=[dict(v)for v in source.NEW_GUARDS];target=next(v for v in altered if v['offset']==row['offset']);target['expected'if variant=='word'else'expected_relocations']='0x00000000'if variant=='word'else'R_MIPS_26:func_151423D8'
    out=io.StringIO(newline='');writer=csv.DictWriter(out,list(altered[0]),lineterminator='\n');writer.writeheader();writer.writerows(altered);manifest=self.fresh/('bad-%d-%s.csv'%(at,variant));manifest.write_text(out.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=manifest,filename=source.OWNER)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   s=oracle.symbols()if not j else dict(func_151423D8=entry+0x10004,D_800BE9E4=0x800D8004 if j==1 else 0x80107FFC)
   paths=(self.out/'original-func_15131C84.o',self.out/'make-shadow/src/game/generated_15D730.c.o',self.out/'qualified-padded.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),s)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for mode,phase in itertools.product((0,1,2,4,8,15),(0,8)):self.compare(Case(mode=mode,phase=phase),images,entry,s);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,padder_guard_rejections=4,all_three_objects_linked=True,guards=2,signed_low_address_carries=True)
 def test_07_compiled_semantic_and_signed_load_controls(self):
  evidence={}
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(Case(mode=1),Case(phases=oracle.TICKS+3,ticks=0x12345678),Case(first=oracle.PHASE),Case(first=oracle.AMP+4)):
    initial=fixture(c);m=OffsetOracle(words,initial,c).run();wanted=reference(initial,c)
    if(public(m.memory),m.calls,m.snapshots)!=(public(wanted[0]),wanted[1],wanted[2]):evidence[name]=dict(mode=c.mode,phases=c.phases,first=c.first);break
   self.assertIn(name,evidence)
  body=source.SELECTED.replace('s8 *rates','u8 *rates');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'unsigned-load-control');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  words=self.linked(obj,source.ENTRY,'unsigned-load-link');self.assertNotEqual(words,self.raw)
  # Modulo-256 output alone cannot distinguish signed/unsigned rate loads.
  c=Case(rates=(128,255));initial=fixture(c);pair=[OffsetOracle(w,initial,c).run()for w in(self.truth,words)]
  self.assertEqual((public(pair[0].memory),pair[0].calls,pair[0].snapshots),(public(pair[1].memory),pair[1].calls,pair[1].snapshots))
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,unsigned_rate_instruction_gate=True,unsigned_rate_public_modulo_equivalence=True)
 def test_08_strict_whole_image_and_guard_prefix(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+200];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,200);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at,at+128,at+176,at+200,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.TRIG,108),source.elf_slot_offset(before,oracle.TRIG_TABLE,260),source.elf_slot_offset(before,0x15192308,80)]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  proposed=source.guard_manifest(v['conker/retail_word_patches.us.csv']);self.assertEqual(proposed,(self.out/'proposed-guards.csv').read_bytes());self.assertTrue(proposed.startswith(v['conker/retail_word_patches.us.csv']));self.assertEqual(len(list(csv.DictReader(io.StringIO(proposed.decode()))))-len(list(csv.DictReader(io.StringIO(v['conker/retail_word_patches.us.csv'].decode())))),2)
  self.assertEqual(sum(x!=y for x,y in zip(before,expected)),155)
  self.receipt['image']=dict(changed_bytes=155,code_bytes=154,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=len(positions)+1,inherited_guard_prefix_unchanged=True,new_guards=2,protected_Game_bytes=189088,focused_inputs=len(v),caller_owner_object_bytes_unchanged=True)
