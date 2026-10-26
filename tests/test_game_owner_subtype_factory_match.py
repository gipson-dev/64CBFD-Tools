"""Subtype callback: original guest states, late owner reads, caller ABI and direct C."""
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_owner_subtype_factory_match as source
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.check_game_data_layout import audit_layout

ROOT=Path(__file__).resolve().parents[2]
OWNER,OTHER,RECORD=0x30000,0x31000,0x32000
FACTORY,CLEANUP=0x151491F4,0x1516972C
FACTORY_ARGS=(100,2,0xFFFFFFFF,1,0,1,255,0)

def put(m,a,v,n=4):
 for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'big')):m[a+i]=b

def get(m,a,n=4):return int.from_bytes(bytes(m[a+i]for i in range(n)),'big')
def public(m):return {a:b for a,b in m.items()if not STACK-0x800<=a<STACK+0x300}
def fixture(mode,phase=0):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x300)}
 for base in(OWNER,OTHER,RECORD):
  for i in range(-16,256):m[base+i]=(i*13+mode*17)&255
 m[OWNER+0x72]=mode;m[OTHER+0x72]=mode^0xFD
 return m

class Oracle(TimingOracle):
 def __init__(self,words,memory,phase=0,returned=RECORD,pattern=0,owner=OWNER,fault=None,entry=source.ENTRY,connected=None,target_entry=source.ENTRY,factory=FACTORY,cleanup=CLEANUP):
  super().__init__(words,memory,phase=phase,entry=entry,arguments=(owner,0xABCD0080,0xA50000FF,0xDEAD8001),connected=connected)
  self.returned,self.provider_pattern,self.original_owner=returned,pattern,owner
  self.incoming_sp=STACK+phase;self.target_calls=[];self.factory,self.cleanup=factory,cleanup
  self.root_entry,self.root_size,self.root_fault,self.root_accesses=target_entry,source.BODY,fault,0
 def record_call(self,target):
  if target==self.root_entry:
   args=self.arguments(1);self.target_calls.append(args);self.incoming_sp=self.r[29]
  else:
   assert target in(self.factory,self.cleanup),hex(target)
   args=self.arguments(8 if target==self.factory else 1)
   if target==self.factory:assert args==FACTORY_ARGS,args
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(self.factory,self.cleanup)
  if target==self.factory:
   if self.provider_pattern==1:self.put(self.original_owner+0x72,(self.memory[self.original_owner+0x72]+17)&255,1)
   elif self.provider_pattern==2:self.put(self.incoming_sp,OTHER,4)
   value=self.returned
  else:
   assert self.calls[-1][1]==(self.returned,)
   if self.provider_pattern==3:self.put(self.original_owner+0x73,0x5A,1)
   value=0xD5000000+self.provider_pattern
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.lo,self.hi=0xA5000010,0xA5000011
  self.r[2]=value

def reference(initial,mode,returned,pattern):
 m=dict(initial);calls=[(FACTORY,FACTORY_ARGS)]
 if pattern==1:m[OWNER+0x72]=(mode+17)&255
 if returned:
  owner=OTHER if pattern==2 else OWNER;selector=m[owner+0x72]
  if selector in(251,252,253,254):m[returned+0x28]=(1,2,4,3)[selector-251]
  else:
   calls.append((CLEANUP,(returned,)))
   if pattern==3:m[OWNER+0x73]=0x5A
 return public(m),calls

class CallerBoundary(Exception):pass
class WindowCode(dict):
 def __init__(self,original,owner):super().__init__(original);self.owner=owner
 def __getitem__(self,pc):
  if pc in(0x1511C1C0,0x1511C3A0):raise CallerBoundary(pc)
  self.owner.current_pc=pc
  return super().__getitem__(pc)

class SubtypeFactoryTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;source.verify_prepared(cls.out);cls.values=source.snapshot(cls.out)
  cls.truth=list(struct.unpack_from('>46I',cls.values['conker/conker.us.bin'],source.ROM))
  data,functions=link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER);at=functions[source.FUNCTION]['value']
  cls.words=list(struct.unpack_from('>46I',data,at));assert cls.words==cls.truth
 def pair(self,initial,phase=0,returned=RECORD,pattern=0,owner=OWNER,fault=None):
  pair=[Oracle(w,initial,phase,returned,pattern,owner,fault)for w in(self.truth,self.words)]
  errors=[]
  for m in pair:
   try:m.run();errors.append(None)
   except faults.AccessBoundary:errors.append('fired')
   except AssertionError as e:errors.append(str(e))
  self.assertEqual(errors[0],errors[1]);self.assertEqual(complete(pair[0]),complete(pair[1]))
  return pair[0],errors[0]
 def test_01_direct_owner_Make_bindings_and_registration(self):
  q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['new_guards'],q['preserved_neighbors']),(46,40,0,11))
  source.checked_payload(*source.payload(self.out/'after-owner.o'))
  self.assertEqual(self.words,self.truth);self.assertEqual(q['Make']['compact_functions_equal'],12)
  self.assertTrue(q['Make']['complete_padded_object_equal'])
  source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
  rom=self.values['conker/conker.us.bin'];jal=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)
  direct=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal]
  literal=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==source.ENTRY]
  self.assertEqual(direct,[]);self.assertEqual(literal,[])
  caller=self.values['conker/asm/142560.s'].decode();self.assertEqual(caller.count('%hi(func_150DDED0)'),1)
  self.assertEqual(caller.count('%lo(func_150DDED0)'),1)
  self.assertIn('0040F809',caller);self.assertIn('02002025',caller)
  self.receipt['registration']=dict(no_direct_JAL=True,no_aligned_literal_registration=True,parent='func_1511BEBC',callback_load=0x1511C184,site=0x1511C1A8,void_owner_pointer_ABI=True)
 def test_02_guest_reference_aliases_late_home_and_complete_words(self):
  visits=set();cases=0
  for mode,phase,null,pattern,record in itertools.product(range(256),(0,8),(0,1),range(4),(RECORD,OWNER,OWNER+0x4A)):
   initial=fixture(mode,phase);returned=0 if null else record
   model,error=self.pair(initial,phase,returned,pattern);self.assertIsNone(error)
   expected,calls=reference(initial,mode,returned,pattern);self.assertEqual(public(model.memory),expected);self.assertEqual(model.calls,calls)
   self.assertEqual(model.r[29],STACK+phase);visits.update(model.visits);cases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
  for phase in(0,8):
   model,error=self.pair({a:b for a,b in fixture(0,phase).items()if STACK-0x800<=a<STACK+0x300},phase,0,0,0xDEADCAFE)
   self.assertIsNone(error);self.assertEqual(model.calls,[(FACTORY,FACTORY_ARGS)])
  self.receipt['guest']=dict(cases=cases,all_unsigned_selector_values=True,three_return_buffer_aliases=True,late_argument_home_mutation=True,complete_raw_original_states_equal=True,all_46_words_visited=True,NULL_return_does_not_read_owner=True,opaque_helpers=True)
 def test_03_frozen_SDK_native32_execution_and_eight_effective_controls(self):
  private=self.out/'reused-private';q=json.loads((private/'native-screen.json').read_text());raw=json.loads((private/'raw-screen.json').read_text())
  self.assertTrue(raw['linked_bytes_exact']);self.assertEqual(q['positive_cases_per_optimization'],3072)
  self.assertEqual((private/'candidate.c').read_text().split('/* Create a short-lived',1)[1],source.SELECTED.split('/* Create a short-lived',1)[1]+'\n')
  for row in q['positive']:
   path=private/row['name'];self.assertEqual(source.sha(path.read_bytes()),row['executable_SHA256'])
   path.chmod(0o755);p=subprocess.run([str(path)],capture_output=True,text=True);self.assertEqual(p.returncode,0,(row,p.stdout,p.stderr))
  self.assertEqual(len(q['effective_compiled_negatives']),8)
  for row in q['effective_compiled_negatives']:
   path=private/row['name'];self.assertEqual(source.sha(path.read_bytes()),row['executable_SHA256'])
   path.chmod(0o755);p=subprocess.run([str(path)],capture_output=True,text=True);self.assertEqual(p.returncode,row['exit']);self.assertNotEqual(p.returncode,0)
  self.receipt['native32']=dict(cases_per_optimization=3072,optimizations=['O0','O2','O3'],trap_UBSan=True,compiled_negatives=8,SDK_types=True,eight_factory_arguments=True,compiled_private_executions_reused_via_exact_source_profile_and_artifact_identity=True,all_binaries_freshly_executed=True)
 def test_04_original_indirect_caller_window_and_saved_temporaries(self):
  rom=self.values['conker/conker.us.bin'];start=0x1511C174;window=list(struct.unpack_from('>19I',rom,start-0x14FD2B50));cases=0;calls=0
  scenarios=itertools.product(range(256),(0,8),(0,1),(0,1),(RECORD,OWNER,STACK+0x48-0x28,STACK+0x72-0x28))
  for mode,phase,null,pattern,record in scenarios:
   if record>=STACK-0x100:record+=phase
   initial=fixture(mode,phase);returned=0 if null else record;models=[]
   for body in(self.truth,self.words):
    code={source.ENTRY+4*i:w for i,w in enumerate(body)}
    m=Oracle(window,initial,phase,returned,pattern,entry=start,connected=code)
    m.r[16]=OWNER;m.r[12]=0;m.r[9]=0;m.r[7]=0xABCD8001;m.code=WindowCode(m.code,m)
    with self.assertRaises(CallerBoundary):m.run()
    self.assertEqual(m.target_calls,[(OWNER,)]);self.assertEqual(m.r[29],STACK+phase)
    self.assertEqual(m.r[7],get(m.memory,STACK+phase+0x72,2)| (0xFFFF0000 if m.memory[STACK+phase+0x72]&128 else 0))
    self.assertEqual(m.r[8],get(m.memory,STACK+phase+0x48));self.assertEqual(m.r[9],get(m.memory,STACK+phase+0x3C));self.assertEqual(m.r[10],get(m.memory,STACK+phase+0x5C))
    models.append(m);calls+=len(m.target_calls)
   self.assertEqual(complete(models[0]),complete(models[1]));cases+=1
  for (gate12,gate9),phase in itertools.product(((1,0),(0,1),(0,0xFFFFFFFF),(1,1)),(0,8)):
   m=Oracle(window,fixture(251,phase),phase,entry=start);m.r[16]=OWNER;m.r[12]=gate12;m.r[9]=gate9;m.code=WindowCode(m.code,m)
   with self.assertRaises(CallerBoundary)as end:m.run()
   self.assertEqual(end.exception.args[0],0x1511C3A0 if gate12 else 0x1511C1C0)
   self.assertEqual(m.target_calls,[])
  self.receipt['caller']=dict(cases=cases,actual_target_calls=calls,site=0x1511C1A8,saved_halfword_and_three_temporaries=True,byte_aliases_to_saved_temporaries=True,independent_entry_gates=True,return_value_unused=True,whole_parent_acceptance=False)
 def test_05_fired_fault_prefixes_GNU_rebases_and_oversize_rejection(self):
  fired=0
  for mode,phase,null,pattern in itertools.product((0,251,252,253,254,255),(0,8),(0,1),range(4)):
   initial=fixture(mode,phase);returned=0 if null else OWNER+0x4A;model,error=self.pair(initial,phase,returned,pattern);self.assertIsNone(error)
   for fault in range(model.root_accesses):
    _,error=self.pair(initial,phase,returned,pattern,fault=fault);self.assertEqual(error,'fired');fired+=1
  for phase in(0,8):
   _,error=self.pair(fixture(251,phase),phase,RECORD,0,0xDEADCAFE);self.assertIn('unmapped read',error)
   initial=fixture(251,phase);_,error=self.pair(initial,phase,STACK+phase-4-0x28,0);self.assertIn('unowned jump',error)
  raw,bindings=source.payload(self.out/'selected.o')
  for i in range(46):
   wrong=bytearray(raw);wrong[4*i+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(wrong),bindings)
  for offset in bindings:
   wrong=dict(bindings);wrong[offset]=[('R_MIPS_26','func_150DDED0')]
   with self.assertRaises(ValueError):source.checked_payload(raw,wrong)
  with self.assertRaises(ValueError):source.checked_payload(raw[:-4],bindings)
  links=0
  for index,(entry,factory,cleanup)in enumerate(((source.ENTRY,FACTORY,CLEANUP),(0x12347FF0,0x12458000,0x12567FFC),(0x32348000,0x32447FFC,0x32548000))):
   bodies=[]
   for label,obj in(('original',self.out/'original-func_150DDED0.o'),('C',self.out/'selected.o')):
    script=self.out/('rebase-'+str(index)+'-'+label+'.ld');elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    p=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,'--defsym=func_151491F4=0x%X'%factory,'--defsym=func_1516972C=0x%X'%cleanup,'-o',str(elf),str(obj)],capture_output=True,text=True)
    self.assertEqual(p.returncode,0,p.stderr);bodies.append(sections(elf)['.text'][1][:source.BODY]);links+=1
   self.assertEqual(*bodies)
   pair=[Oracle(list(struct.unpack('>46I',b)),fixture(253),returned=OWNER,pattern=1,entry=entry,target_entry=entry,factory=factory,cleanup=cleanup).run()for b in bodies]
   self.assertEqual(complete(pair[0]),complete(pair[1]))
  data=bytearray((self.out/'after-owner.o').read_bytes());rows=[at for at,n,fields,_ in symbol_rows(bytes(data))if n==source.FUNCTION and fields[3]&15==2];self.assertEqual(len(rows),1);struct.pack_into('>I',data,rows[0]+8,4096)
  bad=self.out/'negative-oversized-owner.o';bad.write_bytes(data)
  with self.assertRaises((ValueError,AssertionError,RuntimeError)):
   source.emit_padded_assembly(bad,ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER)
  self.receipt['faults_and_links']=dict(fired_fault_prefix_pairs=fired,complete_states=True,unmapped_owner_and_saved_RA_aliases=True,GNU_links=links,three_J26_layouts=True,raw_word_controls=46,binding_controls=2,real_padder_oversize_negative=True,guest_faults_not_portable_C=True)
 def test_06_strict_image_every_function_and_protected_data(self):
  before=self.values['conker/build/conker.us.elf'];after=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
  source.check_image(before,after,truth)
  a,_,aa=source.load_elf_functions(str(self.out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=source.load_elf_functions(str(self.out/'first-linked.elf'),'mips-linux-gnu-objdump')
  self.assertEqual(aa,bb);self.assertEqual([n for n in a if a[n]!=b[n]],[source.FUNCTION]);self.assertEqual(len(a),6056)
  data=audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((data['exact'],data['owner_count'],data['bytes'],data['different_bytes']),(True,720,189088,0))
  slot=elf_slot_offset(before,source.ENTRY,source.SIZE);target_row=next(at for at,n,_,_ in symbol_rows(before)if n==source.FUNCTION)
  negatives=[]
  for offset in(slot+60,target_row+8,24,elf_slot_offset(before,0x150DB9E0,4),len(after)//2,len(after)-1):
   wrong=bytearray(after);wrong[offset]^=1;negatives.append(bytes(wrong))
  negatives.append(after+b'!')
  for wrong in negatives:
   with self.assertRaises(ValueError):source.check_image(before,wrong,truth)
  self.receipt['image']=dict(functions=len(a),other_bodies_preserved=6055,all_addresses_fixed=True,protected_data=data,complete_image_exclusions=0,effective_full_image_corruptions=7)
