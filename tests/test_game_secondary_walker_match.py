"""Bounded checks for the secondary registered-callback walker."""
import csv
import io
import itertools
import struct
import subprocess
import unittest
from tools.experiments import game_secondary_walker_match as match
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests import game_type64_walker_oracle as guest
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

class SecondaryWalkerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=match.prepare()
 def test_01_retail_guest(self):
  seen=set()
  for case in guest.cases():
   expected,calls=guest.reference(case)
   for words in (self.state['retail_words'],self.state['raw_words']):
    m=guest.Oracle(words,case);m.run();self.assertEqual((guest.public(m.memory),[x[:3] for x in m.observed]),(expected,calls),case)
    self.assertEqual(m.r[16:24],m.before[16:24]);self.assertEqual(m.r[28:],m.before[28:]);self.assertEqual(m.f[20:],m.before_f[20:])
    if words==self.state['retail_words']:seen.update(m.visits)
  self.assertEqual(sum(guest.ENTRY+4*i in seen for i in range(74)),74)
 def test_02_native(self):
  from tools.tests import game_secondary_walker_native
  result=game_secondary_walker_native.main();self.assertEqual(set(result['profiles']),{'-O0','-O2','-O3'});self.assertTrue(all(x['cases']==96 and x['negative_controls']==5 and x['UBSan'] for x in result['profiles'].values()))
 def test_03_frame_loop_window(self):
  start,end=0x150192ec,0x150192f4;rom=(match.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>2I',rom,start-0x15000000+0x2d4b0);self.assertEqual(window,(0x0d459c7a,0))
  class Caller(guest.Oracle):
   def record_call(self,target):
    if target==guest.ENTRY:self.entered=True
    else:super().record_call(target)
  count=0
  for pattern in range(4):
   for mutation in range(4):
    for depth in (0,2):
     case=guest.Case(pattern,mutation,depth,0);expected,calls=guest.reference(case)
     for words in (self.state['retail_words'],self.state['raw_words']):
      m=Caller(words,case);m.entered=False;m.r[29]=guest.STACK-0x180;code=dict(zip(range(guest.ENTRY,guest.ENTRY+4*len(words),4),words));code.update(zip(range(start,end,4),window));code[end]=0;m.code=WindowCode(code,m);m.code.ends=(end,);m.entry=start
      with self.assertRaises(WindowBoundary):m.run()
      self.assertTrue(m.entered);self.assertEqual(m.r[29],guest.STACK-0x180);self.assertEqual(m.r[31],end);self.assertEqual((guest.public(m.memory),[x[:3]for x in m.observed]),(expected,calls))
     count+=1
  self.assertEqual(count,32)
 def test_04_padders_and_corruption_controls(self):
  a,b=match.pad_both(self.state);self.assertEqual(match.payload(a),match.payload(b));rows=match.MANIFEST['guard_rows'];self.assertEqual(len(rows),35)
  fields=list(rows[0]);counts=[0,0]
  for i,row in enumerate(rows):
   altered=[dict(x)for x in rows];altered[i]['expected']=hex(int(row['expected'],0)^1);out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(altered);path=match.OUT/'bad-guards.csv';path.write_text(out.getvalue())
   with self.assertRaises(ValueError):match.pad_c_object.emit_padded_assembly(self.state['raw_obj'],self.state['layout'],match.OWNER,word_patches_path=path)
   counts[0]+=1
   with self.assertRaises(ValueError):match.pad_generated_object.emit_padded_assembly(self.state['raw_obj'],self.state['target'],filename=match.OWNER,word_patches_path=path)
   counts[1]+=1
  self.assertEqual(counts,[35,35])
 def test_05_rebases_and_access_cuts(self):
  objects=(*match.pad_both(self.state),self.state['retail_obj']);programs=[];links=0
  for index,obj in enumerate(objects):
   raw,refs=match.payload(obj);symbols=sorted({n for es in refs.values()for _,n in es});actual={'D_8008B4A8':guest.TABLE,'D_800DCE50':guest.LISTS,'D_800DD190':guest.DEPTH,'D_800DD198':guest.SLOTS};programs.append(match.bound_blob(raw,refs,actual))
   for low in (0,0x7ffc,0x8000,0xfffc):
    syms={n:0x80010000+i*0x10000+low for i,n in enumerate(symbols)};expected=match.bound_blob(raw,refs,syms);script=match.OUT/('rebase-%d-%04x.ld'%(index,low));script.write_text('SECTIONS { .text 0x151671E8 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');z=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%x for x in syms.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);self.assertEqual(z.returncode,0,z.stderr);binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);self.assertEqual(list(struct.unpack_from('>74I',binary.read_bytes())),expected);links+=1
  self.assertEqual(links,12)
  case=guest.Case(3,3,2,8);full=guest.Oracle(programs[0],case);full.run();count=0
  def state(m):return m.memory,m.r,m.f,m.calls,m.observed,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition
  for cut in range(full.all_accesses):
   models=[]
   for words in programs:
    m=guest.Oracle(words,case);m.cut=cut
    with self.assertRaises(AccessBoundary):m.run()
    models.append(m)
   self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[1]),state(models[2]));count+=1
  self.assertEqual(count,270)
 def test_06_caller_and_placeholder_interface(self):
  source=(match.ROOT/match.MANIFEST['caller']).read_text();correct=source.replace('s32 func_151671E8(void);','void func_151671E8(void);')
  a,ad=match.compile_owner(match.ROOT,match.OUT,source,'caller-before');b,bd=match.compile_owner(match.ROOT,match.OUT,correct,'caller-after');self.assertEqual(match.same_functions(a,b),16);self.assertEqual(diagnostic_rows(ad),diagnostic_rows(bd));self.assertEqual({k:v for k,v in sections(a).items() if k!='.mdebug'},{k:v for k,v in sections(b).items() if k!='.mdebug'})
  source=(match.ROOT/match.MANIFEST['placeholder']).read_text();correct=source.replace(match.body(source,'func_151AD174'),'void func_151AD174(u8 *record) {\n}',1);a,ad=match.compile_owner(match.ROOT,match.OUT,source,'stub-before');b,bd=match.compile_owner(match.ROOT,match.OUT,correct,'stub-after');self.assertEqual(match.same_functions(a,b,('func_151AD174',)),32);self.assertEqual(diagnostic_rows(ad),diagnostic_rows(bd))
  guard_path=match.ROOT/'conker/retail_word_patches.us.csv'
  with guard_path.open(newline='')as f:rd=csv.DictReader(f);fields=rd.fieldnames;rows=[r for r in rd if r['function']!='func_151AD174']
  rows.append(match.MANIFEST['placeholder_guard']);out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);full=match.OUT/'placeholder-guards.csv';full.write_text(out.getvalue());asm=match.pad_generated_object.emit_padded_assembly(b,match.ROOT/'conker/asm/1D92F0.s',filename='generated_1D92F0',word_patches_path=full);obj=match.assemble(asm,'placeholder-padded');old=match.ROOT/'conker/build/src/game/generated_1D92F0.c.o';self.assertEqual(match.same_functions(old,obj),33);self.assertEqual(match.parse_object(old),match.parse_object(obj));self.assertEqual({k:v for k,v in sections(old).items() if k!='.mdebug'},{k:v for k,v in sections(obj).items() if k!='.mdebug'})
  for n in ('func_151041E4','func_151ACB60'):
   f='conker/src/game/generated_131620.c' if n=='func_151041E4' else match.MANIFEST['placeholder'];text=(match.ROOT/f).read_text();self.assertIn('void '+n+'(u8 *',match.body(text,n))

 def test_07_connected_timer_callback(self):
     from tools.tests import game_type64_walker_oracle as walker
     from tools.tests import game_type64_timer_oracle as oracle
     from tools.match_progress import load_elf_functions
     rom=(match.ROOT/'conker/conker.us.bin').read_bytes()
     walker_words=self.state['raw_words']
     retail_child=struct.unpack_from('>170I',rom,0x131694)
     live,_,_=load_elf_functions(str(match.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
     live_child=tuple(live['func_151041E4']);self.assertEqual(live_child,retail_child)
     child=oracle.ENTRY
     class Combined(walker.Oracle):
         def __init__(self,child_words,wcase,tcase,memory):
             super().__init__(walker_words,wcase);self.tcase=tcase;self.memory.update(memory)
             self.code.update(dict(zip(range(child,child+len(child_words)*4,4),child_words)));self.events2=[]
         def record_call(self,target):
             assert target==child or target in oracle.SIGNATURE,hex(target)
             args=tuple(self.arguments(1 if target==child else oracle.SIGNATURE[target]))
             self.events2.append((target,args));self.calls.append((target,args))
         def hook(self,target):
             assert target in oracle.SIGNATURE
             if self.tcase.mutation and target==oracle.START:
                 walker.put(self.memory,oracle.REC+0x10,oracle.ALT);walker.put(self.memory,oracle.REC+0x14,oracle.ALT)
             if self.tcase.mutation and target==oracle.ADJUST:walker.put(self.memory,oracle.OWNER+0x318,oracle.ALT_ACTOR)
             for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
             for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
             self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
     cases=[]
     for selector,height,mutation,row,phase in itertools.product((0,1,2),(0x4197ffff,0x41980000),(0,1),(0,1),(0,8)):
         cases.append((oracle.Case(0,selector,15,0,1,20,height,mutation,phase),row))
     for state,timer,fade,ticks,mutation,row in itertools.product((1,2,3,4),(0,180),(0,11,255),(0,1),(0,1),(0,1)):
         cases.append((oracle.Case(state,0,timer,fade,ticks,1,0x41980000,mutation,0),row))
     self.assertEqual(len(cases),240)
     for case,row in cases:
         wc=walker.Case(0,0,0,case.phase);memory=walker.fixture(wc);memory.update(oracle.fixture(case))
         memory.update({walker.TABLE+i:b for i,b in enumerate(rom[0x22FF68:0x22FF68+101*52])})
         walker.put(memory,oracle.REC+8,0);walker.put(memory,walker.LISTS+row*0x1a0+100*4,oracle.REC)
         self.assertEqual(walker.read(memory,walker.TABLE+100*52+4),child)
         expected,events=oracle.reference(case);want=walker.public(dict(memory));want.update(expected)
         walker.put(want,oracle.REC+8,0);walker.put(want,walker.SLOTS+4,0)
         for child_words in (retail_child,live_child):
             model=Combined(child_words,wc,case,memory);model.run()
             self.assertEqual((walker.public(model.memory),model.events2),(want,[(child,(oracle.REC,))]+events),case)
             self.assertEqual(model.r[16:24],model.before[16:24]);self.assertEqual(model.r[28:],model.before[28:])


 def test_08_wrong_replacements_are_detected(self):
  rows=match.MANIFEST['guard_rows'];fields=list(rows[0]);indices=(0,len(rows)//2,len(rows)-1)
  for index in indices:
   changed=[dict(r)for r in rows];changed[index]['replacement']=hex(int(changed[index]['replacement'],0)^1);out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(changed);path=match.OUT/'wrong-replacement.csv';path.write_text(out.getvalue());assembly=match.pad_c_object.emit_padded_assembly(self.state['raw_obj'],self.state['layout'],match.OWNER,word_patches_path=path);obj=match.assemble(assembly,'wrong-replacement');raw,refs=match.payload(obj);words=match.bound_blob(raw,refs,{nm:self.state['symbols'][nm] for group in refs.values()for _,nm in group});self.assertNotEqual(tuple(words),self.state['retail_words'])
  row=dict(match.MANIFEST['placeholder_guard']);row['expected']=hex(int(row['expected'],0)^1)
  with (match.ROOT/'conker/retail_word_patches.us.csv').open(newline='')as f:rd=csv.DictReader(f);fields=rd.fieldnames;full=[r for r in rd if r['function']!='func_151AD174']
  full.append(row);out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(full);path=match.OUT/'wrong-placeholder.csv';path.write_text(out.getvalue())
  source=(match.ROOT/match.MANIFEST['placeholder']).read_text();source=source.replace(match.body(source,'func_151AD174'),'void func_151AD174(u8 *record) {\n}',1);obj,_=match.compile_owner(match.ROOT,match.OUT,source,'stub-control')
  with self.assertRaises(ValueError):match.pad_generated_object.emit_padded_assembly(obj,match.ROOT/'conker/asm/1D92F0.s',filename='generated_1D92F0',word_patches_path=path)

 def test_09_sdk_structure_layout(self):
  from tools.tests.test_game_projected_packet_draw import native_command
  source='''#include <ultra64.h>
#include <stddef.h>
#include "build/game-secondary-walker-tests/overlay/structs.h"
typedef char size_check[(sizeof(struct115)==0x34)?1:-1];
typedef char p0_check[(offsetof(struct115,unk0)==0)?1:-1];
typedef char p4_check[(offsetof(struct115,unk4)==4)?1:-1];
typedef char p18_check[(offsetof(struct115,unk18)==0x18)?1:-1];
typedef char p1c_check[(offsetof(struct115,unk1C)==0x1c)?1:-1];
void sizes_probe(void) {}
'''
  _,diag=match.compile_owner(match.ROOT,match.OUT,source,'layout-ido');self.assertFalse(diag)
  wrong=source.replace('offsetof(struct115,unk4)==4','offsetof(struct115,unk4)==8');self.assertNotEqual(wrong,source)
  _,bad_diag=match.compile_owner(match.ROOT,match.OUT,wrong,'layout-ido-negative');self.assertIn('Warning 654',bad_diag)
  for label,text,expect in (('layout-native',source,True),('layout-native-negative',wrong,False)):
   path=match.OUT/(label+'.c');path.write_text(text.replace('offsetof(struct115,','__builtin_offsetof(struct115,'));z=subprocess.run(native_command('-O2')+['-I','conker','-fsyntax-only',str(path)],cwd=match.ROOT,capture_output=True,text=True)
   self.assertEqual(z.returncode==0,expect,z.stderr[-2000:])

if __name__=='__main__':unittest.main()
