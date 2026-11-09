"""Camera dispatch: strict image, original caller, native layout and semantics."""
import json,struct,subprocess,unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.experiments import game_camera_transition_dispatch_15128540_match as match
from tools.tests import game_camera_transition_dispatch_15128540_oracle as guest
from tools.tests import game_camera_transition_dispatch_15128540_caller as caller
from tools.tests import game_camera_transition_dispatch_15128540_native as native
from tools.tests import test_game_attachment_effect_150eee00_match as linking
ROOT=match.ROOT
class CameraDispatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.prepared=match.prepare();cls.out=ROOT/match.BUILD
  cls.truth=list(struct.unpack('>80I',(ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE]))
 def receipt(self,name,v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def test_01_entire_owner_Make_and_strict_image_guards(self):
  report=self.prepared['report'];self.assertEqual((report['words'],report['frame'],report['raw_neighbors'],report['padded_neighbors'],report['strict_changed_bytes'],report['exclusions']),(80,32,44,44,248,0))
  self.assertEqual(report['inherited_diagnostics'],5);self.assertEqual(report['isolated_diagnostics'],0)
  blob,refs=match.payload(self.out/'qualified-owner.o');match.checked(blob,refs)
  for i in range(len(blob)):
   bad=bytearray(blob);bad[i]^=1
   with self.assertRaises(ValueError):match.checked(bytes(bad),refs)
  for at in refs:
   bad=dict(refs);bad[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.checked(blob,bad)
  before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=struct.pack('>80I',*self.truth)
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,match.SIZE)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
  bad=bytearray(truth);bad[0]^=1
  with self.assertRaises(ValueError):match.strict_image(before,after,bytes(bad))
 def test_02_predicates_priority_copy_live_effects_and_faults(self):
  v=guest.guest_checks();self.assertEqual((v['cases_per_body'],v['visited_words'],v['unreachable_words']),(2456,78,[16,74]));self.receipt('guest-contract',v)
 def test_03_complete_original_caller_target_connection(self):
  v=caller.caller_checks();self.assertEqual((v['cases_per_body'],v['caller_words'],v['target_words_visited']),(512,261,78));self.receipt('caller-contract',v)
 def test_04_GNU_rebases_and_compiled_semantic_controls(self):
  rows={};rebases=0
  with patch.object(linking,'match',match):
   for j in range(6):
    entry=match.ENTRY+j*0x10000;syms={k:v+j*0x20000 for k,v in guest.SYMS.items()}
    ws,_=linking.linked(self.out/'qualified-owner.o',entry,syms,'rebase-'+str(j),self.out)
    for c in(guest.Case(),guest.Case(first=0x80000000),guest.Case(busy=1),guest.Case(fallback=0xFFFFFFFF),guest.Case(flags=1<<19,mutation=127),guest.Case(flags=1<<20),guest.Case(flags=1<<21),guest.Case(flags=1<<22)):
     initial=guest.fixture(c);m=guest.Oracle(ws,initial,c,entry=entry,syms=syms).run();guest.check(m,initial,c);rebases+=1
   cases=list(guest.cases())
   for name,b in native.controls().items():
    obj,diag=match.shared.compile_owner(ROOT,self.out,match.HEADER+b,'negative-'+name);self.assertFalse(diag)
    ws,pools=linking.linked(obj,match.ENTRY,guest.SYMS,'negative-link-'+name,self.out,True);witness=None
    for c in cases:
     initial=guest.fixture(c);initial.update(pools);m=guest.Oracle(ws,initial,c).run()
     try:guest.check(m,initial,c)
     except AssertionError:witness=c;break
    self.assertIsNotNone(witness,name);rows[name]=dict(compiled=True,counterexample=vars(witness),literal_words=len(ws))
  self.assertEqual(rebases,48);self.assertEqual(len(rows),12);self.receipt('rebases-controls',dict(GNU_links=6,rebased_cases=rebases,controls=rows))
 def test_05_native32_camera_layout_aliasing_and_effective_controls(self):
  source=(match.HEADER+match.SELECTED).replace('__attribute__((__may_alias__))','')
  obj,diag=match.shared.compile_owner(ROOT,self.out,source,'no-alias-IDO-control');self.assertFalse(diag);match.checked(*match.payload(obj))
  v=native.native_checks();self.assertEqual((v['cases_per_profile'],v['semantic_controls']),(896,12));self.receipt('native-summary',v)

if __name__=='__main__':unittest.main()
