"""Record opacity envelope: direct compiler match and original callback integration."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_record_opacity_envelope_match as source
from tools.tests import game_record_opacity_envelope_oracle as oracle
from tools.tests.game_record_opacity_envelope_oracle import Case,fixture,reference,public,EnvelopeOracle,GuestBreak,RECORD,DESCRIPTOR,PARENTS,STACK,put,read,half,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(unsigned_lifetime=b.replace('*(s16 *)(record + 0x24)','*(u16 *)(record + 0x24)'),inclusive_fade=b.replace('boundary < remaining','boundary <= remaining'),inclusive_hold=b.replace('boundary - hold < remaining','boundary - hold <= remaining'),wrong_scale=b.replace('* 255','* 254'),wrong_out=b.replace('/ fadeOut','/ (fadeOut * 2)'),wrong_hold=b.replace('boundary - hold','boundary + hold'),wrong_output=b.replace('record[0x45]','record[0x44]'),unsigned_phases=b.replace('*(s32 *)(record + 0x18) >> 16','*(u32 *)(record + 0x18) >> 16').replace('*(s32 *)(record + 0x1C) >> 16','*(u32 *)(record + 0x1C) >> 16'))

def native_harness():
 t=source.HEADERS+r'''
typedef struct{u8 pad0[24];s32 phases,durations;u8 pad20[4];s16 remaining;u8 pad26[31];u8 opacity;u8 tail[10];}Record;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record)==80&&__builtin_offsetof(Record,phases)==24&&__builtin_offsetof(Record,durations)==28&&__builtin_offsetof(Record,remaining)==36&&__builtin_offsetof(Record,opacity)==69)?1:-1];
static struct{u32 left[4];Record record;u32 right[4];}actual,expected;
'''
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,'test_'+n)+'\n'
 t+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){static const s32 ins[]={20,-1,32767,-32768};static const s32 outs[]={40,7,-1,32767};u32 n,k,i;u8*p=(u8*)&actual,*q=(u8*)&expected;s32 duration,fadeIn,hold,fadeOut,remaining,boundary,num,den;
 for(n=0;n<65536;n++)for(k=0;k<4;k++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n+k*17);
  duration=k==0?100:k==1?0:k==2?65535:32767;fadeIn=ins[k];hold=k==0?30:k==1?65535:k==2?0:32767;fadeOut=outs[k];remaining=(s16)n;
  actual.record.phases=(s32)(((u32)fadeIn<<16)|(u32)hold);actual.record.durations=(s32)(((u32)fadeOut<<16)|(u32)duration);actual.record.remaining=(s16)n;
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];boundary=duration-fadeIn;
  if(remaining>boundary){num=(duration-remaining)*255;den=fadeIn;expected.record.opacity=(u8)(num/den);}
  else if(remaining>boundary-hold)expected.record.opacity=255;
  else{num=remaining*255;den=fadeOut;expected.record.opacity=(u8)(num/den);}
  fn((u8*)&actual.record);for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 # Inclusive fade is equivalent for nonzero fadeIn: both branches emit 255 at that boundary.
 # Its zero-divisor difference is qualified separately with actual guest break7, not native UB.
 for i,n in enumerate(n for n in controls()if n!='inclusive_fade'):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class RecordOpacityEnvelopeTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.raw=list(struct.unpack('>49I',source.checked_payload(*source.payload(cls.out/'selected.o'))[0]));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>49I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY):
  initial=fixture(c);wanted,trap=reference(initial,c.record);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=EnvelopeOracle(words,initial,c,entry)
   if trap:
    with self.assertRaises(GuestBreak)as caught:m.run()
    self.assertEqual(caught.exception.args,(7,));self.assertIn(m.current_pc,(entry+72,entry+160))
   else:m.run()
   self.assertEqual(m.memory,wanted);self.assertFalse(m.calls);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  return pair[0],trap
 def rebased(self,obj,entry,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,{});self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);body=sections(p.with_suffix('.elf'))['.text'][1];return list(struct.unpack('>%dI'%(len(body)//4),body))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.raw,self.truth)
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),10);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),24)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),23);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertIn('void func_150F55C8(u8 *record);',proposed);self.assertNotIn('#pragma GLOBAL_ASM',proposed);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x231508]);self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x122A60])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=49,frame=0,bindings=0,guards=0,neighbors=23,compact_functions=24,Make_commands=3,selected_diagnostics=0,inherited_owner_warnings=10,arguments=1,void_return=True,direct_caller='func_150F5590',callback_table='D_8008CA20',callback_slot=10)
 def test_02_guest_phase_boundaries_signed_halves_and_traps(self):
  count=traps=0;visits=set()
  for duration,fade_in,hold,fade_out in itertools.product((0,100,65535),(-32768,-1,0,20,32767),(0,30,65535),(-32768,-1,0,50,32767)):
   boundary=duration-fade_in
   for left in set((-32768,-1,0,1,32767,boundary-1,boundary,boundary+1,boundary-hold-1,boundary-hold,boundary-hold+1)):
    if -32768<=left<=32767:
     m,t=self.compare(Case(duration,fade_in,hold,fade_out,left));visits.update(m.visits);count+=1;traps+=t is not None
  for location,phase in itertools.product((RECORD,STACK-128,STACK+16),(0,8)):
   for remaining in(0,50,80,90):self.compare(Case(remaining=remaining,record=location,phase=phase));count+=1
  self.assertEqual(len(visits),47);self.assertGreater(traps,0);self.assertNotIn(source.ENTRY+96,visits);self.assertNotIn(source.ENTRY+184,visits)
  self.receipt['guest']=dict(cases=count,divide_by_zero_cases=traps,visited_words=len(visits),signed_packed_high_halves_and_remaining=True,unsigned_low_duration_and_hold=True,three_phase_boundaries=True,raw_padded_original_complete_state_equal=True,all_memory_and_access_order_equal=True,unreachable_INT_MIN_overflow_breaks_retained=True,divide_zero_store_sentinel_not_hardware_claim=True,guest_stack_record_locations=True)
 def test_03_original_direct_and_all_four_table_dispatch_routes(self):
  table=self.rom[0x2314E0:0x23150C];self.assertEqual(len(table),44);self.assertEqual(struct.unpack_from('>2I',table,36),(source.WRAPPER,source.ENTRY));elf=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,source.TABLE,44);self.assertEqual(elf[at:at+44],table)
  wrapper=list(struct.unpack_from('>14I',self.rom,0x122A40));at=source.elf_slot_offset(elf,source.WRAPPER,56);self.assertEqual(elf[at:at+56],self.rom[0x122A40:0x122A78]);direct=0
  for remaining in(-32768,-1,0,50,80,90,32767):
   c=Case(remaining=remaining);initial=fixture(c);wanted,calls=oracle.callback_reference(dict(initial),9);calls=calls[1:];pair=[]
   for w in(self.truth,self.words):
    m=EnvelopeOracle(wrapper,initial,c,source.WRAPPER,{source.ENTRY+i*4:v for i,v in enumerate(w)}).run();self.assertEqual(public(m.memory),public(wanted));self.assertEqual(m.calls,calls);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));direct+=1
  reports={}
  for entry,length in PARENTS.items():
   parent=list(struct.unpack_from('>%dI'%length,self.rom,entry-0x14FD2B50));retained=elf[source.elf_slot_offset(elf,entry,length*4):][:length*4]==struct.pack('>%dI'%length,*parent);seen=set();count=0
   for selector,variant,phase in itertools.product((9,10,(-1 if entry==0x15167E0C else 0)),range(8),(0,8)):
    c=Case(duration=10000,fade_in=3000,hold=2000,fade_out=5000,remaining=(0,50,80,90,-1,-32768,32767,1)[variant],phase=phase);initial=fixture(c);initial.update({source.TABLE+i:b for i,b in enumerate(table)});put(initial,source.TICKS,(-1,0,1,2,7,32767,0x7FFFFFFF,3)[variant]&0xFFFFFFFF);put(initial,RECORD+0x10,DESCRIPTOR);initial[DESCRIPTOR+4]=(1,3,127,255)[variant%4]
    put(initial,RECORD+0x26,(-32768,-1,0,32767)[variant%4]&65535,2);put(initial,RECORD+0x28,(-32768,-1,1,32767)[variant%4]&65535,2);initial[RECORD+0x41]=(0,1,3,255)[variant%4]
    if entry==0x15168BAC:initial[RECORD+0xE4]=selector
    elif entry==0x15169988:initial[RECORD+0x40]=selector
    elif entry==0x15167B44:
     initial[RECORD+0x24]=selector;initial[RECORD+0x22]=(-128,-1,0,1,2,127,-3,3)[variant]&255;initial[RECORD+0x23]=(0,1,127,255)[variant%4];put(initial,RECORD+0x14,(-32768,-1,0,256,512,32767,1000,32760)[variant]&65535,2);put(initial,RECORD+0x16,(-32768,-256,-1,0,1,256,32767,8)[variant]&65535,2)
    else:initial[RECORD+0x48]=selector&255;put(initial,RECORD+0x38,variant,2);put(initial,source.TICKS,variant+1);initial[RECORD+0x3A]=0;initial[RECORD+0x2F]=255
    wanted,calls=oracle.caller_reference(initial,entry,selector);pair=[]
    for w in(self.truth,self.words):
     connected={source.ENTRY+i*4:v for i,v in enumerate(w)}|{source.WRAPPER+i*4:v for i,v in enumerate(wrapper)};m=EnvelopeOracle(parent,initial,c,entry,connected).run();self.assertEqual(public(m.memory),public(wanted),(hex(entry),selector,variant));self.assertEqual(m.calls,calls);seen.update(m.visits);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
   reports[hex(entry)]=dict(cases=count,original_words=length,visited_original_words=len(seen&set(range(entry,entry+length*4,4))),current_body_exact=retained,entry_to_return=True)
  self.receipt['caller']=dict(direct_wrapper_cases=direct,table_words=11,table_preserved=True,dispatchers=reports,slot9_wrapper_and_slot10_direct_and_disabled_routes=True,release_provider_bounded=True,large_parent_lifetime_expiry_routes_only=True,no_whole_parent_or_gameplay_acceptance=True)
 def test_04_native32_canonical_record_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=262144,effective_controls=7,all65536_remaining_encodings=True,canonical_record_fields_and_void_pointer_ABI=True,whole_record_fences=True,trapping_UBSan=True,nonzero_selected_divisors_only=True,signed_right_shift_is_GCC_IDO_target_behavior=True)
 def test_05_fired_access_prefixes_and_zero_divisor_store_order(self):
  cuts=0
  for phase,remaining,fade_out in itertools.product((0,8),(-32768,0,50,80,90,32767),(0,50)):
   c=Case(remaining=remaining,fade_out=fade_out,phase=phase);good,trap=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=EnvelopeOracle(words,fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    cuts+=1
  c=Case(duration=0,fade_in=0,remaining=1);m,trap=self.compare(c);self.assertEqual(trap,7);self.assertEqual(m.current_pc,source.ENTRY+72);self.assertEqual([e[1]for e in m.trace if e[0]=='W'],[RECORD+0x45]);c=Case(fade_out=0,remaining=80);m,trap=self.compare(c);self.assertIsNone(trap);self.assertEqual(m.memory[RECORD+0x45],255)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,store_before_original_break7=True,inactive_zero_denominator_safe_on_plateau=True,zero_divide_HI_LO_sentinel_not_hardware_claim=True)
 def test_06_real_padder_controls_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{0:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   images=[self.rebased(p,entry,'rebase-%d-%d'%(j,k))[:49]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o',self.out/'make-shadow/src/game/generated_1228D0.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for left in(-32768,-1,0,50,80,90,32767):self.compare(Case(remaining=left),images,entry);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=0,original_compiler_and_actual_Make=True,raw_binding_controls=3,guards=0)
 def test_07_actually_compiled_semantic_controls(self):
  tests={'unsigned_lifetime':Case(remaining=-1),'wrong_scale':Case(remaining=81),'wrong_out':Case(remaining=25),'wrong_hold':Case(remaining=80),'wrong_output':Case(),'unsigned_phases':Case(duration=0,fade_in=-1,fade_out=-1,remaining=-1),'inclusive_hold':Case(remaining=50,fade_out=20),'inclusive_fade':Case(duration=0,fade_in=0,hold=1,remaining=0)}
  for name,c in tests.items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+controls()[name],'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,'negative-link-'+name);wanted,trap=reference(fixture(c));m=EnvelopeOracle(words,fixture(c),c)
   try:m.run();observed=None
   except GuestBreak as e:observed=e.args[0]
   self.assertNotEqual((m.memory,observed),(wanted,trap),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=len(tests),semantic_value_or_original_guard_failures=True,inclusive_fade_guest_zero_division_control=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,source.TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(count,q['changed_bytes']);self.receipt['image']=dict(changed_bytes=count,code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_parents_and_guards_unchanged=True)
