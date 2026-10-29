"""Active record lookup: source profile, guard, ABI, guest/native and image gates."""
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_active_record_lookup_match as source
from tools.tests import game_active_record_lookup_oracle as oracle
from tools.tests.game_active_record_lookup_oracle import Case,fixture,reference,machine,state
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

class ActiveRecordLookupTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>52I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,source.TABLE,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,source.TABLE,'selected')
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,table,label):return oracle.linked(obj,entry,table,label,cls.fresh)
 def compare(self,images,table,entry,hit,flags,key,active,phase=0):
  initial=fixture(table,hit,flags,key,active);wanted=reference(initial,table,key);pair=[]
  for words in images:
   m=machine(words,initial,key,entry,phase).run();self.assertEqual(m.r[2],wanted,(hit,flags,key,active));self.assertEqual(m.memory,initial);self.assertFalse(m.calls);pair.append(m)
  for m in pair[1:]:self.assertEqual(state(pair[0]),state(m))
  return pair[0]

 def test_01_owner_actual_Make_and_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_1509CA98.o'))
  for label in ('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),19)
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.out/a,self.out/b,(source.FUNCTION,)),18)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertIn('-Wo,-loopunroll,0',commands[0]);self.assertFalse((self.out/'actual-Make-diagnostics.txt').read_bytes())
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x6D11C,0x6D130,0x6D168,0x6D41C]);self.assertNotIn(source.ENTRY,ws)
  self.assertIn(b's32 func_1503FB40() {\n    return 0;\n}',self.values['conker/src/game/generated_6CEA0.c'])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=52,frame=0,bindings=2,guards=2,neighbors=18,Make_commands=3,diagnostics=0,existing_no_unroll_profile=True,arguments=1,argument_type='u32',return_type='s32')

 def test_02_guest_search_and_boundaries(self):
  seen=set();cases=0
  for hit,flags,active in itertools.product(range(205),(0,7),(1,0x80000000)):
   seen.update(self.compare((self.truth,self.words,self.raw),source.TABLE,source.ENTRY,hit,flags,0x20000000,active).visits);cases+=1
  for key,flags,phase in itertools.product((0,1,34,0x1FFFFFFF,0x20000000,0x20000001,0xFFFFFFFF),range(8),(0,8)):
   self.compare((self.truth,self.words,self.raw),source.TABLE,source.ENTRY,203,flags,key,1,phase);cases+=1
  dead=set(range(source.ENTRY,source.ENTRY+208,4))-seen;self.assertEqual(dead,{source.ENTRY+i for i in (64,104,144,184)})
  self.receipt['guest']=dict(cases=cases,reachable_words=len(seen),dead_duplicate_offsets=[64,104,144,184],all204_positions=True,first_match_and_inactive_keys=True,full_state_and_access_trace=True,read_only_table=True)

 def test_03_original_caller_windows(self):
  windows=((0x1503FC64,0x6D114,4,0x1503FC74),(0x1503FC74,0x6D124,5,0x1503FC88),(0x1503FCB4,0x6D164,3,0x1503FCC0),(0x1503FF68,0x6D418,3,0x1503FF74));rows=[]
  for entry,offset,n,end in windows:
   count=0;visited=set()
   for byte,hit,phase,prior in itertools.product((0,1,127,255),(0,3,203,204),(0,8),(0,203,204)):
    key=(prior+1)&0xFFFFFFFF if entry==0x1503FF68 else byte+1;initial=fixture(source.TABLE,hit,7,key,1);initial[oracle.GLOBAL]=byte;wanted=reference(initial,source.TABLE,key);pair=[]
    for words in (self.truth,self.words,self.raw):
     connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),words));connected[end]=0;m=oracle.WindowOracle(struct.unpack_from('>%dI'%n,self.rom,offset),initial,Case(phase),entry=entry,s={},connected=connected,arguments=(0x80080000,));m.r[2]=prior;m.r[19]=prior;m.before=m.r[:];m.code=oracle.WindowCode(m.code,m);m.code.ends=(end,)
     with self.assertRaises(oracle.WindowBoundary):m.run()
     self.assertEqual(m.calls,[(source.ENTRY,(key,))]);self.assertEqual(m.r[2],wanted);self.assertEqual(m.memory,initial);pair.append(m);visited.update(m.visits)
    for m in pair[1:]:self.assertEqual(state(pair[0]),state(m))
    count+=1
   self.assertTrue(set(range(entry,entry+n*4,4))<=visited);rows.append(dict(entry=hex(entry),words=n,cases=count))
  self.receipt['integration']=dict(parent='func_1503FB40',windows=rows,total_cases=sum(x['cases']for x in rows),current_C_parent_stub=True,third_window_precondition='a0=0x80080000',fourth_window_precondition='s3=request minus one',full_parent_or_gameplay_claimed=False)

 def test_04_native32_and_controls(self):
  file=self.fresh/'native.c';file.write_text(oracle.native_harness());logs={}
  for opt in ('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);b=subprocess.run(native_command(opt)+[str(file),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(b.returncode,0,b.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=b.stderr)
  self.receipt['native']=dict(profiles=logs,cases_per_profile=6563,compiled_controls=7,SDK=True,pointers32=True,trapping_UBSan=True,whole_table_canaries=True)

 def test_05_fault_prefixes(self):
  cuts=delay=0
  for hit in (0,3,204):
   initial=fixture(source.TABLE,hit);full=machine(self.truth,initial,0x20000000).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in (self.truth,self.words,self.raw):
     m=machine(words,initial,0x20000000);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(state(pair[0]),state(m));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_groups=cuts,delay_slot_cuts=delay,original_raw_normalized_equal=True,portable_C_fault_claimed=False)

 def test_06_guard_proof_and_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/'original-func_1509CA98.o'));self.assertEqual(sorted(source.BINDINGS),[0,12]);self.assertEqual(sorted(source.NORMALIZED_BINDINGS),[0,16])
  reader=csv.DictReader(io.StringIO((self.out/'proposed-guards.csv').read_text()));fields=reader.fieldnames;rows=list(reader);rejects=0
  for n in range(2):
   for field,value in (('expected',hex(int(rows[-2+n]['expected'],0)^1)),('expected_relocations','R_MIPS_LO16:wrong')):
    bad=[dict(x)for x in rows];bad[-2+n][field]=value;s=io.StringIO(newline='');w=csv.DictWriter(s,fields);w.writeheader();w.writerows(bad);path=self.fresh/('bad-guard-%d-%s.csv'%(n,field));path.write_text(s.getvalue())
    with self.assertRaisesRegex(ValueError,'stale word patch|stale relocations'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=path)
    rejects+=1
  cases=0
  for j,(entry,table)in enumerate(((source.ENTRY,source.TABLE),(0x17007FFC,0x80417FFC),(0x2500FFFC,0x80528004))):
   images=[self.linked(obj,entry,table,'rebase-%d-%d'%(j,k))for k,obj in enumerate((self.out/'original-func_1509CA98.o',self.out/'qualified-padded.o',self.out/'selected.o',self.out/'make-shadow/src/game/generated_C9EC0.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[3])
   for hit,key in itertools.product((0,1,2,3,4,200,201,202,203,204),(1,0x20000000)):self.compare(images,table,entry,hit,7,key,1);cases+=1
  self.receipt['rebases']=dict(layouts=3,cases=cases,stale_guard_controls=rejects,only_two_independent_words_exchanged=True,low_relocation_moves_with_instruction=True)

 def test_07_IDO_compiled_semantic_controls(self):
  evidence={}
  for name,body in oracle.controls().items():
   self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,source.TABLE,'negative-link-'+name)
   for hit,flags,key in itertools.product((0,2,3,200,203,204),(0,7),(1,0x20000000)):
    initial=fixture(source.TABLE,hit,flags,key,1)
    if name=='third_key'and hit==2:oracle.put(initial,source.TABLE+3*20+4,77)
    wanted=reference(initial,source.TABLE,key);m=machine(words,initial,key).run()
    if m.r[2]!=wanted or m.memory!=initial:evidence[name]=dict(hit=hit,flags=flags,key=key);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)

 def test_08_strict_image_inputs_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];literal=self.rom[source.ROM:source.ROM+208];actual=(self.out/'first-linked.elf').read_bytes();source.check_image(before,actual,literal);at=source.elf_slot_offset(before,source.ENTRY,208);count=0
  for pos in (20,at-4,*range(at,at+208),at+208,next(x[0]for x in source.symbol_rows(before)if x[1]==source.FUNCTION)+8):
   bad=bytearray(actual);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),literal)
   count+=1
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for pos in range(0,len(raw),4):
   bad=bytearray(raw);bad[pos+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for pos in rs:
   bad=dict(rs);bad[pos]=[(rs[pos][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   rejects+=1
  old=v['conker/retail_word_patches.us.csv'];new=source.guard_manifest(old);self.assertTrue(new.startswith(old));self.assertEqual(new,(self.out/'proposed-guards.csv').read_bytes())
  self.receipt['image']=dict(changed_bytes=159,code_bytes=158,size_bytes=1,metadata_bytes=0,exclusions=0,image_corruptions=count,raw_binding_controls=rejects,inherited_guard_prefix_preserved=True,new_guards=2,focused_inputs=len(v))
