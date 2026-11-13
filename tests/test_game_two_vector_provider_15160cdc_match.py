"""Two-vector provider: exact owner, guest model, native source and callers."""
import itertools,struct,unittest
from tools.experiments import game_two_vector_provider_15160cdc_match as packet
from tools.tests import game_two_vector_provider_15160cdc_guest as guest
from tools.tests import game_two_vector_provider_15160cdc_native as native
from tools.tests import game_two_vector_provider_15160cdc_rebase as rebase
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class TwoVectorProviderMatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.prepared=packet.prepare()
 def test_guest_model(self):guest.run()
 def test_native_controls(self):native.run()
 def test_relocations(self):rebase.run()
 def test_fault_prefixes(self):
  programs=[guest.bound_blob(*guest.payload(self.prepared[x],'func_15160CDC'),guest.SYMS) for x in ('retail','after','generic','generated')]
  cases=(guest.Case(owner=0),guest.Case(allocated=False),guest.Case(alias_output=True,mode=1))
  for c in cases:
   initial=guest.fixture(c);args=(c.owner,255,guest.src.VEC_A,guest.src.VEC_B,0x80000000,255,0xffff8000,1,2,3,4,1,0xa5,1,255,0xffffffff)
   for i,v in enumerate(args[4:],4):guest.put(initial,guest.STACK+i*4,v)
   complete=guest.EffectOracle(programs[0],initial.copy(),c,entry=guest.src.EFFECT,arguments=args[:4]).run()
   for cut in range(complete.all_accesses):
    states=[]
    for p in programs:
     m=guest.EffectOracle(p,initial.copy(),c,entry=guest.src.EFFECT,arguments=args[:4]);m.cut=cut
     with self.assertRaises(AccessBoundary):m.run()
     states.append((m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of))
    self.assertTrue(all(s==states[0] for s in states),(c,cut))
 def test_vector_stack_aliases(self):
  programs=[guest.bound_blob(*guest.payload(self.prepared[x],'func_15160CDC'),guest.SYMS) for x in ('retail','after','generic','generated')]
  for delta,allocated,alias in itertools.product((-128,-112,-80,-48,-16,0,16,32),(False,True),(False,True)):
   c=guest.Case(allocated=allocated,alias_output=alias);initial=guest.fixture(c);first=guest.STACK+delta;second=guest.STACK+delta+12
   for i in range(6):guest.put(initial,first+4*i,0x3f000000+i)
   args=(c.owner,255,first,second,0x80000000,255,0xffff8000,1,2,3,4,1,0xa5,1,255,0xffffffff)
   for i,v in enumerate(args[4:],4):guest.put(initial,guest.STACK+i*4,v)
   states=[]
   for p in programs:
    m=guest.EffectOracle(p,initial.copy(),c,entry=guest.src.EFFECT,arguments=args[:4]);m.run()
    states.append((m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of))
   self.assertTrue(all(s==states[0] for s in states),(delta,allocated,alias))
 def test_original_caller_window(self):
  rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();start=0x151bc074
  window=struct.unpack_from('>36I',rom,0x1e9524)
  programs=[guest.bound_blob(*guest.payload(self.prepared[x],'func_15160CDC'),guest.SYMS) for x in ('retail','after','generic','generated')]
  vec1,vec2,scale=0x800aa760,0x800aa76c,0x800aa82c
  for allocated,mode,alias in itertools.product((False,True),(0,1),(False,True)):
   c=guest.Case(owner=guest.OWNER,allocated=allocated,mode=mode,alias_output=alias);initial=guest.fixture(c)
   for addr,value in ((vec1,0x3f800000),(vec1+4,0x40000000),(vec1+8,0x40400000),(vec2,0x40800000),(vec2+4,0x40a00000),(vec2+8,0x40c00000),(scale,0x3f000000)):guest.put(initial,addr,value)
   args=(c.owner,1,vec1,vec2,0x3f000000,2,300,255,255,255,255,1,0,0,255,1)
   expected,calls,observations,result=guest.provider_reference(initial,args,c,guest.STACK-72)
   for p in programs:
    connected=dict(zip(range(guest.src.EFFECT,guest.src.EFFECT+len(p)*4,4),p))
    m=guest.EffectOracle(window,initial.copy(),c,entry=start,arguments=(c.owner,),connected=connected).run()
    self.assertEqual((guest.public(m.memory),m.calls,m.factory_observations,m.r[2]),(guest.public(expected),[(guest.src.EFFECT,args)]+calls,observations,result))
if __name__=='__main__':unittest.main(verbosity=2)
