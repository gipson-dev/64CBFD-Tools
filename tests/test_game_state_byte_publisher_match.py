"""Publisher C, mixed-profile owner, caller/provider ABI and whole-image gates."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_state_byte_publisher_match as source
from tools.tests import game_state_byte_publisher_oracle as oracle
from tools.tests.game_state_byte_publisher_oracle import Case,PublisherOracle,fixture,reference,symbols,public,state
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
class StateBytePublisherTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>52I',cls.rom,source.ROM));cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,symbols(),'selected');cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,symbols(),'qualified')
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,s,label):return oracle.linked(obj,entry,s,label,cls.fresh)
 def compare(self,c,s=None,entry=None,images=None):
  s=s or symbols();entry=source.ENTRY if entry is None else entry;initial=fixture(c,s);want,calls=reference(initial,c,s);pair=[]
  for words in images or(self.truth,self.raw,self.words):
   m=PublisherOracle(words,initial,c,entry,s).run();self.assertEqual((public(m.memory),m.calls),(public(want),calls));pair.append(m)
  for m in pair[1:]:self.assertEqual(state(pair[0]),state(m))
  return pair[0]

 def test_01_owner_mixed_Make_and_caller_ABI(self):
  self.assertEqual(self.truth,self.raw);self.assertEqual(self.raw,self.words);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in ('before','after'):
   text=(self.out/(label+'-owner.c')).read_text()
   for suffix,flags in (('',('-O2','-g3')),('-nodebug',('-O2',))):
    obj,diag=source.compile_owner(ROOT,self.fresh,text,'fresh-'+label+suffix,flags);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner'+suffix+'.o')),5)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),4);self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),4)
  commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),4);self.assertIn('-g3',commands[0]);self.assertNotIn('-g3',commands[1]);self.assertIn('--function-object',commands[2]);self.assertFalse((self.out/'actual-Make-diagnostics.txt').read_bytes())
  proof=json.loads((self.out/'caller-declaration-proof.json').read_text());self.assertTrue(proof['all_object_bytes_unchanged']);self.assertEqual(proof['same_compact_functions'],16);self.assertEqual((ROOT/source.OTHER_OBJECT).read_bytes(),(self.out/'caller-make-shadow/src/game_45B80.c.o').read_bytes());self.assertEqual(source.recovered_caller(self.values[source.OTHER_SOURCE].decode()).encode(),(self.out/'proposed-caller.c').read_bytes())
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0D45CE31],[0x467D4]);self.assertNotIn(source.ENTRY,ws)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=52,frame=32,bindings=14,guards=0,neighbors=4,Make_commands=4,mixed_profile_identity_helper='func_151733D8',caller_functions=16,caller_padded_object_identical=True,helper_C_placeholder_unchanged=True)

 def test_02_guest_provider_order_and_aliases(self):
  cases=[Case(status=i,seed=i)for i in range(256)];cases +=[Case(flags=f,context=x,mode=m,phase=p,seed=m)for f,x,m,p in itertools.product((0,1,2,0xFFFFFFFF),(0,0x80000000,0xFFFFFFFF),range(16),(0,8))];seen=set()
  for c in cases:seen.update(self.compare(c).visits)
  self.assertEqual(set(range(source.ENTRY,source.ENTRY+208,4))-seen,{0x15173944});s=symbols();count=0
  for dst,flags,mode in itertools.product((s['D_800DD2E4'],s['D_800DD2E4']+1,s['D_800DD2E4']-1,oracle.STATE+6,oracle.ALT+6),(0,1),(0,1,2,3)):
   defs=dict(s,D_800DBEA8=dst);images=[self.linked(obj,source.ENTRY,defs,'alias-%d-%d'%(count,k))for k,obj in enumerate((self.out/'original-func_151738C4.o',self.out/'selected.o',self.out/'qualified-padded.o'))];self.compare(Case(flags=flags,mode=mode),defs,images=images);count+=1
  self.receipt['guest']=dict(cases=len(cases),alias_cases=count,covered_words=len(seen),dead_duplicate='0x15173944',positive_snapshot_and_negative_interleaving=True,provider_bounded=True,portable_partial_global_aliases_claimed=False)

 def test_03_original_caller_and_provider_prefix(self):
  s=symbols();count=0
  self.assertEqual(struct.unpack_from('>2I',self.rom,0x46754),(0x3C10800C,0x2610E9F0))
  for status,flags,context,mode,phase in itertools.product((0,128,255),(0,1),(0,1,0x80000000,0xFFFFFFFF),(0,3),(0,8)):
   c=Case(status=status,flags=flags,context=context,mode=mode,phase=phase);initial=fixture(c,s);oracle.put(initial,0x800BE9F0,context);want,calls=reference(initial,c,s);pair=[]
   for target in (self.truth,self.raw):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),target));connected[0x1501932C]=0;m=oracle.CallerOracle(struct.unpack_from('>2I',self.rom,0x467D4),initial,c,entry=0x15019324,s=s,connected=connected);m.r[16]=0x800BE9F0;m.r[4]=0xDEADBEEF;m.before=m.r[:];m.code=oracle.WindowCode(m.code,m);m.code.ends=(0x1501932C,)
    with self.assertRaises(oracle.WindowBoundary):m.run()
    self.assertEqual(m.calls,[(source.ENTRY,(context,))]+calls);self.assertEqual(public(m.memory),public(want));pair.append(m)
   self.assertEqual(state(pair[0]),state(pair[1]));count+=1
  seen=set();prefixcases=0
  for flags,context,phase in itertools.product((0,1),(0,1,0x80000000,0xFFFFFFFF),(0,8)):
   c=Case(flags=flags,context=context,phase=phase);initial=fixture(c,s);oracle.put(initial,0x800DD2F0,0xABCD,2);pair=[]
   for target in (self.truth,self.raw):
    connected=dict(zip(range(source.PROVIDER,0x15173438,4),struct.unpack_from('>21I',self.rom,0x1A0894)));connected[0x15173438]=0;m=PublisherOracle(target,initial,c,s=s,connected=connected);m.code=oracle.WindowCode(m.code,m);m.code.ends=(0x15173438,)
    with self.assertRaises(oracle.WindowBoundary):m.run()
    self.assertEqual((m.r[16],m.r[19],m.r[18]),(0xFFFFFFFF,0,0));self.assertEqual([oracle.read(m.memory,oracle.STACK+phase-32+4*i)for i in range(3)],[6 if flags else 0,6 if flags else 0,context]);self.assertEqual(oracle.read(m.memory,0x800DD2F0,2),0);pair.append(m);seen.update(m.visits)
   self.assertEqual(state(pair[0]),state(pair[1]));prefixcases+=1
  self.assertTrue(set(range(source.PROVIDER,0x15173438,4))<=seen);self.receipt['integration']=dict(caller='func_15019130',caller_words=2,caller_cases=count,caller_precondition='s0=&D_800BE9F0',result_ignored=True,provider_prefix_words=21,provider_prefix_cases=prefixcases,five_word_ABI_verified=True,complete_parent_or_provider_claimed=False)

 def test_04_native32_and_controls(self):
  file=self.fresh/'native.c';file.write_text(oracle.native_harness());logs={}
  for opt in ('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);b=subprocess.run(native_command(opt)+[str(file),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(b.returncode,0,b.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=b.stderr)
  self.receipt['native']=dict(profiles=logs,cases_per_profile=65536,controls=8,SDK=True,pointers32=True,trapping_UBSan=True,partial_global_aliases_excluded=True)

 def test_05_fault_prefixes_and_sparse_skip(self):
  s=symbols();cuts=delay=0
  for c in (Case(status=0),Case(flags=0,mode=1),Case(flags=1,mode=3)):
   initial=fixture(c,s);full=PublisherOracle(self.truth,initial,c).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in (self.truth,self.raw):
     m=PublisherOracle(words,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(state(pair[0]),state(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delay+=pair[0].delay_of is not None
  for status in range(255):
   c=Case(status=status);initial=fixture(c,s)
   for p in (s['D_800DBFF0'],s['D_800DD2E4'],s['D_800DBEA8']):
    for i in range(4):initial.pop(p+i,None)
   m=PublisherOracle(self.raw,initial,c,s=s).run();self.assertFalse(m.calls);self.assertEqual(public(m.memory),public(initial))
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delay,sparse_skip_cases=255,portable_C_fault_claimed=False)

 def test_06_real_mixed_padder_and_rebases(self):
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,function_objects={'func_151733D8':self.out/'after-owner-nodebug.o'},word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   defs=symbols()if j==0 else{name:0x80417FFC+0x1000*i for i,name in enumerate(symbols())};defs['func_151733E4']=source.PROVIDER if j==0 else entry+0x10000;images=[self.linked(obj,entry,defs,'rebase-%d-%d'%(j,k))for k,obj in enumerate((self.out/'original-func_151738C4.o',self.out/'selected.o',self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_1A0790.c.o'))];self.assertTrue(all(x==images[0]for x in images))
   for status,flags,mode in itertools.product((0,255),(0,1),(0,3)):self.compare(Case(status=status,flags=flags,mode=mode),defs,entry,images);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,all14_bindings_preserved=True,mixed_profile_identity_override_preserved=True)

 def test_07_IDO_semantic_controls(self):
  evidence={};s=symbols()
  for name,body in oracle.controls().items():
   self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,s,'negative-link-'+name)
   for status,flags,context in itertools.product((0,255),(0,1,2),(1,0x80000000)):
    c=Case(status=status,flags=flags,context=context);initial=fixture(c,s);want,calls=reference(initial,c,s);m=PublisherOracle(words,initial,c).run()
    if(public(m.memory),m.calls)!=(public(want),calls):evidence[name]=dict(status=status,flags=flags,context=context);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)

 def test_08_strict_image_inputs_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];literal=self.rom[source.ROM:source.ROM+208];actual=(self.out/'first-linked.elf').read_bytes();source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,208);count=0
  for p in (20,at-4,*range(at,at+208),at+208,next(x[0]for x in source.symbol_rows(before)if x[1]==source.FUNCTION)+8):
   bad=bytearray(actual);bad[p]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
   count+=1
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for p in range(0,len(raw),4):
   bad=bytearray(raw);bad[p+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for p in rs:
   bad=dict(rs);bad[p]=[(rs[p][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   rejects+=1
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),v['conker/retail_word_patches.us.csv']);self.receipt['image']=dict(changed_bytes=165,code_bytes=164,size_bytes=1,metadata_bytes=0,exclusions=0,image_corruptions=count,raw_binding_controls=rejects,guards=0,focused_inputs=len(v))
