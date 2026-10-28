"""Threshold effect: semantic C, closed guards, actual Make and original callback routes."""
from dataclasses import replace
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_threshold_effect_update_match as source
from tools.tests import game_threshold_effect_update_oracle as oracle
from tools.tests.game_threshold_effect_update_oracle import Case,fixture,reference,base,public,parent_reference,ThresholdOracle,RECORD,CONTEXT,TICKS,PARENT,NEXT,FREE,EXIT,TABLE,EXIT_TABLE,TIME,STACK,put,read,half,faults,bits
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(inclusive_first=b.replace('counter < parameters[2]','counter <= parameters[2]'),inclusive_float=b.replace('counter < parameters[4]','counter <= parameters[4]'),inclusive_final=b.replace('counter < parameters[0]','counter <= parameters[0]'),unsigned_counter=b.replace('counter = record->counter','counter = (u16)record->counter'),unsigned_increment=b.replace('increment = (s32)','increment = (u32)'),wrong_second_float=b.replace('secondValue += increment','secondValue -= increment'),wrong_callback=b.replace('updateSelector = 1','updateSelector = 2'),wrong_mode=b.replace('firstMode = 2','firstMode = 3'),wrong_state=b.replace('0x5203','0x5202'),wrong_first_scale=b.replace('counter * parameters[3]','counter * parameters[1]'),wrong_final_scale=b.replace('counter * parameters[1]','counter * parameters[3]'),wrong_return=b.replace('return 1;','return 0;'))

def native_harness():
 head,body=source.SELECTED.split('s32 '+source.FUNCTION,1);unit=source.HEADERS+'s32 D_800BE9E4;\n'+head
 unit+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(ThresholdEffectRecord1D0840)==180&&__builtin_offsetof(ThresholdEffectRecord1D0840,counter)==26&&__builtin_offsetof(ThresholdEffectRecord1D0840,firstOutput)==43&&__builtin_offsetof(ThresholdEffectRecord1D0840,firstValue)==56&&__builtin_offsetof(ThresholdEffectRecord1D0840,firstMode)==112&&__builtin_offsetof(ThresholdEffectRecord1D0840,updateSelector)==114&&__builtin_offsetof(ThresholdEffectRecord1D0840,parameters)==168)?1:-1];
static struct{u32 left[4];ThresholdEffectRecord1D0840 record;u32 right[4];}actual,expected;
static u32 context[8];
typedef union{u32 u;f32 f;} FloatBits;
'''
 for name,value in dict(selected=source.SELECTED,**controls()).items():unit+=value[value.index('s32 '+source.FUNCTION):].replace(source.FUNCTION,'test_'+name)+'\n'
 unit+=r'''
typedef s32(*Update)(ThresholdEffectRecord1D0840*,void*);
static int check(Update fn){u32 n,k,i,clock;u8*a=(u8*)&actual,*e=(u8*)&expected;FloatBits f;f32 increment;ThresholdEffectRecord1D0840*r=&actual.record,*wanted=&expected.record;
 const u32 patterns[]={0,0x80000000,1,0x80000001,0x3FA00000,0xC1280000,0x7F7FFFFF,0xFF7FFFFF};
 for(n=0;n<65536;n++)for(k=0;k<4;k++){
  for(i=0;i<sizeof(actual);i++)a[i]=(u8)(i*13+n*7+k);for(i=0;i<8;i++)context[i]=0x12340000u+i;
  r->counter=(s16)n;r->parameters[0]=(s16)(n+(k&1));r->parameters[2]=(s16)(n+((k>>1)&1));r->parameters[4]=(s16)(n+((k^(k>>1))&1));
  r->parameters[1]=(s16)(n*7u+3);r->parameters[3]=(s16)(n*13u-3);r->parameters[5]=(s16)(n^0x55AAu);clock=0x76543211u*n+0x80000001u*k;D_800BE9E4=(s32)clock;
  f.u=patterns[(n+k)&7];r->firstValue=f.f;f.u=patterns[(n+k+3)&7];r->secondValue=f.f;for(i=0;i<sizeof(actual);i++)e[i]=a[i];
  if(wanted->counter<wanted->parameters[2])wanted->firstOutput=(u8)(wanted->counter*wanted->parameters[3]);
  if(wanted->counter<wanted->parameters[4]){increment=(f32)(s32)((u32)wanted->parameters[5]*clock);wanted->firstValue=(f32)(wanted->firstValue+increment);wanted->secondValue=(f32)(wanted->secondValue+increment);}
  if(wanted->counter<wanted->parameters[0]){wanted->updateSelector=1;wanted->firstMode=wanted->secondMode=2;wanted->secondOutput=(u8)(wanted->counter*wanted->parameters[1]);wanted->state=0x5203;}
  if(fn(r,(n&1)?(void*)context:(void*)0)!=1||(u32)D_800BE9E4!=clock)return 1;
  for(i=0;i<sizeof(actual);i++)if(a[i]!=e[i])return 1;for(i=0;i<8;i++)if(context[i]!=0x12340000u+i)return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):unit+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return unit+'return 0;}\n'+START

class ThresholdEffectUpdateTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',data,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,initial=None):
  initial=fixture(c)if initial is None else initial;wanted=reference(initial,c);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=ThresholdOracle(words,initial,c,entry).run();self.assertEqual(m.memory,wanted,c);self.assertEqual(m.r[2],1);self.assertFalse(m.calls);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,clock,label):
  symbols={'D_800BE9E4':clock};text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'--defsym=D_800BE9E4=0x%X'%clock,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);size=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(size//4),sections(p.with_suffix('.elf'))['.text'][1][:size]))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),23)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),22);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertIn('s32 func_151A483C(ThresholdEffectRecord1D0840 *record, void *unusedContext)',proposed);self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),1);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22E220]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(raw_words=49,body_words=49,frame=0,bindings=2,guards=11,neighbors=22,compact_functions=23,GLOBAL_ASM_preserved=1,Make_commands=5,selected_diagnostics=0,owner_diagnostics=0,arguments=2,second_argument_ignored_pointer=True,result=1,callback_table='D_80089760',callback_slot=0)
 def test_02_guest_signed_thresholds_wrap_float_and_argument_homes(self):
  count=0;visits=set()
  for limits,counter,ticks,scales,phase in itertools.product(itertools.product((-1,10),repeat=3),(-32768,-1,0,1,10,32767),(0,2,0x7FFFFFFF,0x80000000),((7,3,2),(-32768,32767,-3),(0,0,-32768)),(0,8)):
   m=self.compare(Case(counter,limits,scales,ticks,phase=phase));visits.update(m.visits);count+=1
  for pattern,ticks,phase in itertools.product((0,0x80000000,1,0x80000001,0x7FFFFF,0x800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345),(0,1,0x80000001),(0,8)):self.compare(Case(floats=(pattern,pattern),ticks=ticks,phase=phase));count+=1
  for value in range(256):self.compare(Case(counter=value-128,scales=(value-128,255-value,value),argument=value*0x01010101));count+=1
  for home,argument,phase in itertools.product((0,0x18,0x28,0x2C,0x38,0x3C,0x70,0xA8,0xAC,0xB0),(0,0x26000,0xDEADBEEF),(0,8)):self.compare(Case(home=home,argument=argument,phase=phase));count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+196,4)));self.receipt['guest']=dict(cases=count,visited_words=len(visits),signed_thresholds_and_scale_wrap=True,default_float32_model=True,all_byte_arguments=True,argument_home_alias_offsets=10,raw_C_complete_memory_and_result_equal=True,normalized_complete_state_trace_equal=True,raw_fault_prefixes_not_equated=True,no_hardware_FCSR_claim=True)
 def parent_case(self,c,flags,selector,exit_selector,images=None,initial=None):
  m=fixture(c)if initial is None else dict(initial);put(m,RECORD+0x68,flags);put(m,RECORD+0x20,0);m[RECORD+0x72]=selector;m[RECORD+0x73]=exit_selector;put(m,TIME,bits(.5))
  for i,at in enumerate((0x40,0x44,0x48,0x58,0x5C,0x60,0x64)):put(m,RECORD+at,bits(float(i)-2.25))
  table=list(struct.unpack_from('>40I',self.rom,0x22E220))
  for i,v in enumerate(table):put(m,TABLE+4*i,v)
  put(m,EXIT_TABLE,EXIT);parent=list(struct.unpack_from('>428I',self.rom,0x15D89C));neighbor=list(struct.unpack_from('>39I',self.rom,0x1D1DB0));expected,calls=parent_reference(m,c,flags,selector,exit_selector);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   code={source.ENTRY+4*i:w for i,w in enumerate(words)};code.update({NEXT+4*i:w for i,w in enumerate(neighbor)});model=ThresholdOracle(parent,m,c,PARENT,connected=code,arguments=(RECORD,)).run();self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls);pair.append(model)
  if len(pair)>1:self.assertEqual(complete(pair[0]),complete(pair[1]))
  return pair[0]
 def test_03_original_parent_return_consumption_and_next_callback(self):
  elf=self.values['conker/build/conker.us.elf']
  for address,length,rom_at in((TABLE,160,0x22E220),(EXIT_TABLE,4,0x22E2C0),(NEXT,156,0x1D1DB0)):
   at=source.elf_slot_offset(elf,address,length);self.assertEqual(elf[at:at+length],self.rom[rom_at:rom_at+length])
  self.assertIn('s32 func_151303EC() {\n    return 0;\n}',self.values['conker/src/game/generated_15D730.c'].decode());count=0;visits=set()
  for flags,selector,life,ticks,phase,exit_selector in itertools.product(range(8),(0,255),(-1,0,1,32767),(0,1,3),(0,8),(0,255)):
   m=self.parent_case(Case(counter=life,ticks=ticks,phase=phase),flags,selector,exit_selector);visits.update(m.visits);count+=1
  chains=0;next_calls=0;neighbor_visits=set()
  for counter,flags,ticks,phase in itertools.product((1,5,9),(0,1),(0,1),(0,8)):
   c=Case(counter=counter,ticks=ticks,phase=phase);first=self.parent_case(c,flags,0,255);self.assertEqual(first.memory[RECORD+0x72],1);second=self.parent_case(c,flags,1,255,initial=first.memory);called=any(t==NEXT for t,a in second.calls);self.assertEqual(called,not(flags&1 and half(read(first.memory,RECORD+0x1A,2)-ticks)<0));next_calls+=called;neighbor_visits.update(second.visits);chains+=1
  self.assertIn(0x15130A38,visits);self.assertIn(0x15130A44,visits);self.assertIn(0x15130A84,visits)
  self.receipt['caller']=dict(original_parent_words=428,selected_parent_cases=count,parent_words_visited=len(visits&set(range(PARENT,PARENT+1712,4))),scope='entry-to-return low flags 0..7, zero animation rate, callback/expiry/disabled routes',complete_parent_recovery_claim=False,parent_placeholder_unchanged=True,actual_two_pointer_interface=True,actual_result_consumed=True,table_entries=40,slot0_to_slot1_chains=chains,next_callback_invocations=next_calls,second_tick_expiry_cases=chains-next_calls,retained_neighbor_words=39,neighbor_words_visited=len(neighbor_visits&set(range(NEXT,NEXT+156,4))),current_neighbor_exact=True,release_and_exit_bounded=True)
 def test_04_native32_canonical_record_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=262144,effective_controls=12,all65536_counter_encodings=True,canonical_record_and_two_pointer_ABI=True,whole_record_and_context_fences=True,trapping_UBSan=True,guest_private_aliases_and_nonfinite_cases_not_claimed_native=True)
 def test_05_fired_access_prefixes_and_lazy_scale(self):
  count=0
  for limits,counter,phase in itertools.product(itertools.product((-1,10),repeat=3),(-1,1,10),(0,8)):
   c=Case(limits=limits,counter=counter,phase=phase);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=ThresholdOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));count+=1
  c=Case(counter=10);initial=fixture(c)
  for address in(TICKS,*range(RECORD+0xAE,RECORD+0xB0),*range(RECORD+0xB2,RECORD+0xB4),*range(RECORD+0xAA,RECORD+0xAC)):
   if address==TICKS:
    for i in range(4):initial.pop(address+i)
   else:initial.pop(address)
  self.compare(c,initial=initial);self.receipt['faults']=dict(fired_prefix_pairs=count,retail_and_normalized_complete_state_trace_PC_delay=True,disabled_thresholds_skip_scalars_and_clock=True,raw_reordered_prefixes_not_equated=True)
 def test_06_closed_guards_real_padder_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));normalized,rels=source.normalized_payload(raw,rs);self.assertEqual(rs,rels);a=struct.unpack('>49I',raw);b=struct.unpack('>49I',normalized)
  for at in(36,168):
   x,y=a[at//4],b[at//4];self.assertEqual(x&0xFC00FFFF,25);self.assertEqual(y&0xFC00FFFF,25);self.assertEqual((x>>21&31,x>>16&31),(y>>16&31,y>>21&31))
  self.assertEqual(a[23],0x8483001A);self.assertEqual(b[23:32],a[24:32]+a[23:24]);self.assertFalse(set(range(26,28))&set(range(56,64)));self.assertFalse(set(rs)&set(range(92,128,4)))
  for damaged,bindings in((raw[:-4],rs),(bytes([raw[0]^1])+raw[1:],rs),(raw,{**rs,92:[('R_MIPS_HI16','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  manifest=self.fresh/'guards.csv';manifest.write_bytes(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=manifest,filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  for ordinal,row in enumerate(source.NEW_GUARDS):
   altered=dict(row,expected='0x%08X'%(int(row['expected'],0)^1));rows=[altered if i==ordinal else v for i,v in enumerate(source.NEW_GUARDS)];out=io.StringIO(newline='');csv.DictWriter(out,list(row),lineterminator=chr(13)+chr(10)).writerows(rows);bad=self.fresh/('bad-guard-%d.csv'%ordinal);bad.write_bytes(self.values['conker/retail_word_patches.us.csv']+out.getvalue().encode())
   with self.assertRaisesRegex(ValueError,'stale word patch'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
  count=0;layouts=((source.ENTRY,TICKS),(0x17007FFC,0x81117FFC),(0x2500FFFC,0x81218004),*((0x17007FFC,RECORD+off)for off in(0x18,0x28,0x38,0xA8)))
  for j,(entry,clock)in enumerate(layouts):
   images=[self.rebased(p,entry,clock,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_1D0840.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1])
   for limits,ticks,phase in itertools.product(itertools.product((-1,10),repeat=3),(0,0x80000001),(0,8)):self.compare(Case(limits=limits,ticks=ticks,phase=phase,clock=clock),images,entry);count+=1
  self.receipt['rebases']=dict(layouts=len(layouts),guest_cases=count,clock_alias_layouts=4,bindings=2,HI16_LO16_carries=True,original_raw_and_actual_Make=True,raw_binding_controls=3,real_padder_stale_guard_controls=11,guards=11,no_omissions_or_insertions=True,two_multu_commutations_and_one_closed_reload_rotation=True)
 def test_07_actually_compiled_semantic_controls(self):
  return_control=None
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,TICKS,'negative-link-'+name);c=Case(counter=10 if name.startswith('inclusive')else -1 if name=='unsigned_counter'else 1,ticks=0x80000000 if name=='unsigned_increment'else 2,scales=(7,3,3));wanted=reference(fixture(c),c);m=ThresholdOracle(words,fixture(c),c).run();self.assertNotEqual((m.memory,m.r[2]),(wanted,1),name)
   if name=='wrong_return':return_control=words
  with self.assertRaises(AssertionError):self.parent_case(Case(),0,0,255,images=(return_control,))
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=12,semantic_value_store_and_return_failures=True,actual_parent_rejects_zero_return=True)
 def test_08_strict_entire_image_extent_guards_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  manifest=source.guard_manifest(v['conker/retail_word_patches.us.csv']);self.assertTrue(manifest.startswith(v['conker/retail_word_patches.us.csv']));self.assertEqual(manifest,(self.out/'proposed-guards.csv').read_bytes());count=sum(x!=y for x,y in zip(before,expected));q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(count,q['changed_bytes']);self.receipt['image']=dict(changed_bytes=count,code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,inherited_guard_manifest_bytes_preserved=True,shared_headers_helpers_parent_and_next_callback_unchanged=True)
