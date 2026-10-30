"""Direct state-9 C: exact words, callback lifetimes, aliases and full image."""
from pathlib import Path
import json,os,struct,subprocess,unittest
from tools.experiments import game_actor_state9_start_match as source
from tools.tests import game_actor_state9_start_oracle as oracle
ROOT=Path(__file__).resolve().parents[2]
class ActorState9StartTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def test_01_fresh_direct_C_and_installed_inputs(self):
  source.check_inputs(ROOT,self.out,self.installed);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED,'fresh-selected');self.assertFalse(diag);raw,rs=source.checked_payload(*source.payload(obj));self.assertEqual((raw,rs),source.payload(self.out/'original-func_15063404.o'))
  for at in range(224):
   bad=bytearray(raw);bad[at]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
  for data,bindings,kw in ((raw[:-4],rs,{}),(raw+b'\0'*4,rs,{}),(raw,{0:[('R_MIPS_LO16','foreign')]},{}),(raw,rs,dict(owner='foreign')),(raw,rs,dict(function='foreign'))):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings,**kw)
  self.receipt['fresh_C']=dict(words=56,bindings=5,guards=0,direct_C_exact=True,fingerprint_rejections=229)
 def test_02_guest_callers_provider_routes_and_compiled_controls(self):
  oracle.o=self.out
  for name,fn in (('guest',oracle.guest_suite),('helpers',oracle.helper_suite),('caller',oracle.caller_suite),('controls',oracle.compiled_controls)):
   value=fn();self.assertEqual(value,json.loads((self.out/('private-'+name+'-v11.json')).read_text()));self.receipt[name]=value
 def test_03_native32_UBSan_and_nineteen_controls(self):
  (self.fresh/'selected-semantic-input.c').write_bytes((self.out/'selected-semantic-input.c').read_bytes());oracle.o=self.fresh
  try:result=oracle.native_suite()
  finally:oracle.o=self.out
  self.assertEqual(result,json.loads((self.out/'private-native-v11.json').read_text()));self.receipt['native']=result
 def test_04_frame_and_actor_entry_lifetimes(self):
  raw,rs=source.payload(self.out/'selected-final.o');w=struct.unpack('>56I',raw);self.assertEqual((w[0],w[3],w[22],w[23],w[27],w[32],w[33]),(0x27BDFFD0,0xAFBF0024,0xAFA40030,0xAFA20028,0x8FA40030,0x8FA40030,0x8FA20028));self.assertEqual(w[-4:],(0x8FBF0024,0x27BD0030,0x03E00008,0));self.assertIn('void func_15063404(struct127 *actor)',source.SELECTED)
  old='    struct127 *entry = &D_800CC2D0[(u32)(((s32)actor -\n        (s32)D_800CC2D0) / (s32)sizeof(struct127))];';new='    s32 index = ((s32)actor - (s32)D_800CC2D0) / (s32)sizeof(struct127);\n    struct127 *entry = &D_800CC2D0[(u32)index];';self.assertIn(old,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.SELECTED.replace(old,new),'wrong-frame');self.assertFalse(diag)
  with self.assertRaises(ValueError):source.checked_payload(*source.payload(obj))
  self.receipt['frame']=dict(bytes=48,RA_offset=36,entry_home=40,incoming_actor_home=48,saved_S_registers=0,body_words=56,reachable_words=56,alignment_words=0,ABI='void(struct127 *)',wrong_frame_source_rejected=True)
 def test_05_zero_guards_and_inherited_manifest(self):
  self.assertEqual(source.NEW_GUARDS,[]);self.assertEqual(source.guard_manifest(self.values['conker/retail_word_patches.us.csv']),self.values['conker/retail_word_patches.us.csv']);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv']);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected-final.o')),source.payload(self.out/'selected-final.o'));self.receipt['guards']=dict(new_rows=0,inherited_CSV_bytes_unchanged=True,raw_compiler_words_exact=True)
 def test_06_complete_owner_and_actual_Make(self):
  obj,diag=source.compile_owner(ROOT,self.fresh,source.recovered_owner(self.values[source.SOURCE].decode()),'fresh-owner');source.check_owner_diagnostics(diag);self.assertEqual(source.checked_payload(*source.payload(obj)),source.payload(self.out/'selected-final.o'));self.assertEqual(source.same_functions(self.out/'before-owner.o',obj,(source.FUNCTION,)),18);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(obj));p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(obj,ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);self.assertEqual(p.with_suffix('.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5);self.assertEqual((self.out/'make-shadow/src/game/generated_90840.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.same_functions(obj,self.out/'make-shadow/src/game/generated_90840.c.o.compact'),19);self.receipt['owner']=dict(neighbors=18,actual_Make_commands=5,diagnostics=0,profile='O2/g3')
 def test_07_literal_image_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(x for x in source.symbol_rows(before)if x[1]==source.FUNCTION);offsets=set((0,4,52,len(actual)-1,*range(at,at+source.SIZE),*range(symbol[0],symbol[0]+16)))
  for offset in offsets:
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),179);self.receipt['image']=dict(strict=True,exclusions=0,controls=len(offsets),changed_bytes=179,code_bytes=178,extent_bytes=1,metadata_bytes=0)
 def test_08_installed_link_and_protected_data(self):
  source.check_inputs(ROOT,self.out,self.installed)
  if self.installed:source.audit(ROOT,self.out)
  else:
   report=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
  self.receipt['protected']=dict(Game_bytes=189088,owners=720,exact=True)
