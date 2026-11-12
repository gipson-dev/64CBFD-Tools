"""Guarded match and bounded semantics for the resource motion callback."""
import csv,io,itertools,struct,subprocess,unittest
from tools.experiments import game_resource_motion_15157aa8_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.tests import game_resource_motion_15157aa8_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put

class ResourceMotionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_guarded_words_and_bindings(self):
  self.assertEqual(len(self.state['raw_words']),184);self.assertEqual(len(match.MANIFEST['guard_rows']),16)
  self.assertEqual(len(match.payload(self.state['after'])[1]),10)
  self.assertEqual(self.state['retail_words'],struct.unpack_from('>184I',self.state['rom'],0x184f58))
 def test_02_guest_reference(self):
  seen=set();count=0
  for args in itertools.product(range(16),range(13),(g.bits(0.),g.bits(.5),g.bits(1.)),
                                (g.bits(0.),g.bits(1.),g.bits(2.)),range(2),(0,8)):
   c=g.Case(*args);expected=g.reference(c)
   for words in (self.state['raw_words'],self.state['retail_words']):
    machine=g.Oracle(words,c);machine.run();self.assertEqual((g.public(machine.memory),machine.r[2]),(expected,1),c)
    if words is self.state['retail_words']:seen.update(machine.visits)
   count+=1
  self.assertEqual(count,7488);self.assertEqual(sum(g.ENTRY+4*i in seen for i in range(184)),184)
 def test_03_native_and_controls(self):
  from tools.tests import game_resource_motion_15157aa8_native as native
  self.assertEqual(set(native.profiles),{'-O0','-O2','-O3'})
  for v in native.profiles.values():self.assertEqual((v['cases'],v['negative_controls'],v['UBSan']),(1728,5,True))
 def test_04_padders_guards_and_rebases(self):
  one,two=match.pad_both(self.state);self.assertEqual(same_functions(one,two),26)
  fields=None
  with self.state['guards'].open(newline='') as f:
   reader=csv.DictReader(f);fields=reader.fieldnames;allrows=list(reader)
  target=[i for i,r in enumerate(allrows) if r['function']==match.NAME];self.assertEqual(len(target),16)
  for index in target:
   rows=[dict(r) for r in allrows];rows[index]['expected']=hex(int(rows[index]['expected'],0)^1)
   out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
   bad=match.OUT/'bad-guard.csv';bad.write_text(out.getvalue())
   with self.assertRaises(ValueError):match.pad_generated_object.emit_padded_assembly(self.state['after'],match.ROOT/match.MANIFEST['assembly'],filename=match.OWNER,word_patches_path=bad)
   with self.assertRaises(ValueError):match.pad_c_object.emit_padded_assembly(self.state['after'],match.ROOT/'conker/retail_layout.us.txt',match.OWNER,word_patches_path=bad)
  data,refs=match.payload(one)
  source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+'\n.type '+match.NAME+',@function\n'+match.NAME+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
   for typ,symbol in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+symbol+'\n'
   source+='.word 0x%08X\n'%word
  isolated=match.assemble(source+'.size '+match.NAME+',.-'+match.NAME+'\n','isolated')
  self.assertEqual(match.payload(isolated),(data,refs));names=sorted({n for rows in refs.values() for _,n in rows})
  for low in (0,0x7ffc,0x8000,0xfffc):
   symbols={n:0x80010000+i*0x10000+low for i,n in enumerate(names)}
   expected=bound_blob(data,refs,symbols);script=match.OUT/('rebase-%04x.ld'%low);script.write_text('SECTIONS { .text 0x15157AA8 : SUBALIGN(4) { *(.text) } }\n')
   elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   cmd=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(isolated)]
   z=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr)
   subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True)
   self.assertEqual(list(struct.unpack_from('>184I',binary.read_bytes())),expected)
 def test_05_connected_resource_dispatch(self):
  parent,first,update,link=0x151572D0,0x8008AD90,0x1503F4B0,0x32000
  retail=struct.unpack_from('>84I',self.state['rom'],0x184780)
  live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');self.assertEqual(tuple(live['func_151572D0']),retail)
  connected=dict(zip(range(g.ENTRY,g.ENTRY+736,4),self.state['retail_words']))
  class Model(FactoryOracle):
   def __init__(self,c,m):super().__init__(retail,m,c,entry=parent,arguments=(g.OBJ,),connected=connected);self.recorded=[]
   def record_call(self,t):assert t in (g.ENTRY,update),hex(t);self.recorded.append((t,(self.r[4],)))
   def hook(self,t):
    assert t==update
    for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
    for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
    self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
  count=0
  for flags,ticks,time,inv,phase in itertools.product((0,1,3,15),(0,1,4,8),(g.bits(0.),g.bits(.5)),(g.bits(0.),g.bits(1.)),(0,8)):
   c=g.Case(flags,ticks,time,inv,0,phase);memory=g.fixture(c);memory[g.OBJ+0x10]=0;memory[g.OBJ+0x11]=0;memory[g.OBJ+0x12]=255
   put(memory,g.OBJ+0x68,link);memory.update({first+i:0 for i in range(16)});put(memory,first,g.ENTRY)
   expected=g.reference(c)
   for a,v in g.public(memory).items():
    if a not in expected:expected[a]=v
   expected[g.OBJ+0x10]=0;expected[g.OBJ+0x11]=0;expected[g.OBJ+0x12]=255;put(expected,g.OBJ+0x68,link)
   machine=Model(c,memory);machine.run();self.assertEqual(g.public(machine.memory),expected)
   self.assertEqual(machine.recorded,[(g.ENTRY,(g.OBJ,)),(update,(link,))]);count+=1
  self.assertEqual(count,128)
 def test_06_bounded_external_access_cuts(self):
  class Stop(Exception):pass
  class Cut(g.Oracle):
   def __init__(self,words,c,cut):super().__init__(words,c);self.limit=cut;self.ext=0
   def check(self,a):
    if self.own_instruction and not g.STACK-2048<=a<g.STACK+512:
     if self.ext==self.limit:raise Stop()
     self.ext+=1
   def get(self,a,n):self.check(a);return super().get(a,n)
   def put(self,a,v,n):
    if self.recording:self.check(a)
    return super().put(a,v,n)
  padded,_=match.pad_both(self.state)
  data,refs=match.payload(padded)
  names={name for rows in refs.values() for _,name in rows}
  normalized=tuple(bound_blob(data,refs,{name:self.state['symbols'][name] for name in names}))
  self.assertEqual(normalized,self.state['retail_words'])
  c=g.Case(7,3,g.bits(.5),g.bits(2.),0,0)
  direct=Cut(self.state['raw_words'],c,None);direct.run()
  retail=Cut(self.state['retail_words'],c,None);retail.run()
  self.assertEqual(g.public(direct.memory),g.public(retail.memory))
  self.assertNotEqual(direct.trace,retail.trace)
  total=0
  for flags,ticks in ((0,0),(1,0),(7,3),(15,8)):
   c=g.Case(flags,ticks,g.bits(.5),g.bits(2.),0,0);full=Cut(self.state['retail_words'],c,None);full.run()
   for cut in range(full.ext+1):
    states=[]
    for words in (self.state['retail_words'],normalized):
     machine=Cut(words,c,cut)
     try:machine.run();stopped=False
     except Stop:stopped=True
     trace=[x for x in machine.trace if not g.STACK-2048<=x[1]<g.STACK+512]
     states.append((stopped,g.public(machine.memory),trace))
    self.assertEqual(states[0],states[1],(c,cut));total+=1
  self.assertGreater(total,20)
