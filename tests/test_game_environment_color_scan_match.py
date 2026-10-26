"""Color scan: command semantics, overlapping guest memory, ABI and strict image."""
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_environment_color_scan_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
COLORS,OFFSETS,COUNTER,INPUT=0x800BE530,0x800BE550,0x800BE564,0x30000
SYMBOLS={'D_800BE530':COLORS,'D_800BE550':OFFSETS,'D_800BE564':COUNTER}
def put(m,a,v,n=4):
 for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'big')):m[a+i]=b
def get(m,a,n=4):return int.from_bytes(bytes(m[a+i]for i in range(n)),'big')
def fixture(slot,opcodes=(0xFB,0xDF),pointer=INPUT,base=COLORS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 m.update({base+i:(i*13+0xA5)&255 for i in range(-16,800)})
 for i,op in enumerate(opcodes):put(m,pointer+8*i,(op<<24)|0x123456);put(m,pointer+8*i+4,(0x1234ABCD+i*0x172941)&0xFFFFFFFF)
 m[base+COUNTER-COLORS]=slot
 return m
class Boundary(Exception):pass
class Oracle(TimingOracle):
 def __init__(self,words,memory,pointer=INPUT,phase=0,fault=None,entry=source.ENTRY,connected=None,root_entry=None):
  super().__init__(words,memory,phase=phase,entry=entry,arguments=(pointer,0xABCD1234,0xA5A50080,0xDEAD8001),connected=connected)
  self.root_entry=entry if root_entry is None else root_entry;self.root_size=len(words)*4 if root_entry is None else source.SIZE
  self.root_fault,self.root_accesses=fault,0;self.target_calls=[]
 def get(self,a,n):
  self.access()
  if a%n or any(a+i not in self.memory for i in range(n)):raise Boundary(('read',a,n))
  v=get(self.memory,a,n);self.events.append(('R',a,n,v));return v
 def put(self,a,v,n):
  if self.recording:
   self.access()
   if a%n or any(a+i not in self.memory for i in range(n)):raise Boundary(('write',a,n))
   self.events.append(('W',a,n,v&((1<<(8*n))-1)))
  put(self.memory,a,v,n)
 def record_call(self,target):
  assert target==self.root_entry,hex(target)
  args=self.arguments(1);self.target_calls.append(args);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):raise AssertionError(('unexpected helper',target))
def run(model):
 try:model.run();return None
 except (Boundary,faults.AccessBoundary)as e:return type(e).__name__,e.args

def reference(initial,pointer=INPUT,base=COLORS):
 m=dict(initial);events=[];index=0
 def read(a,n):
  if a%n or any(a+i not in m for i in range(n)):raise Boundary(('read',a,n))
  v=get(m,a,n);events.append(('R',a,n,v));return v
 def write(a,v,n):
  if a%n or any(a+i not in m for i in range(n)):raise Boundary(('write',a,n))
  put(m,a,v,n);events.append(('W',a,n,v&((1<<(n*8))-1)))
 try:
  op=read(pointer,4)>>24
  while op!=0xDF:
   if op==0xFB:
    slot=read(base+COUNTER-COLORS,1);write(base+OFFSETS-COLORS+2*slot,index,2)
    write(base+3*slot,read(pointer+4,4)>>24,1)
    write(base+3*slot+1,read(pointer+4,4)>>16,1)
    blue=read(pointer+4,4);write(base+COUNTER-COLORS,slot+1,1);write(base+3*slot+2,blue>>8,1)
   op=read(pointer+8,4)>>24;index+=1;pointer+=8
  return m,events,index,None
 except Boundary as e:return m,events,None,('Boundary',e.args)

def native_harness(body):
 return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
EnvironmentColorBytes D_800BE530[256];s16 D_800BE550[256];u8 D_800BE564;
static EnvironmentColorBytes expectedColors[256];static s16 expectedOffsets[256];
static u32 commands[2*65539];static unsigned char expectedCount;
static void reset(int slot){int i;for(i=0;i<256;i++){
 D_800BE530[i].red=expectedColors[i].red=(u8)(i*3+1);
 D_800BE530[i].green=expectedColors[i].green=(u8)(i*5+2);
 D_800BE530[i].blue=expectedColors[i].blue=(u8)(i*7+3);
 D_800BE550[i]=expectedOffsets[i]=(s16)(i*11+123);}D_800BE564=expectedCount=(u8)slot;}
static int reference(void){unsigned int index=0,slot,word;while((commands[2*index]>>24)!=0xDF){
 if((commands[2*index]>>24)==0xFB){slot=expectedCount;word=commands[2*index+1];expectedOffsets[slot]=(s16)index;
 expectedColors[slot].red=(u8)(word>>24);expectedColors[slot].green=(u8)(word>>16);expectedColors[slot].blue=(u8)(word>>8);expectedCount=(u8)(slot+1);}index++;}return(int)index;}
static int check(void){int i;if(D_800BE564!=expectedCount)return 1;for(i=0;i<256;i++){
 if(D_800BE550[i]!=expectedOffsets[i]||D_800BE530[i].red!=expectedColors[i].red||D_800BE530[i].green!=expectedColors[i].green||D_800BE530[i].blue!=expectedColors[i].blue)return 2;}return 0;}
'''+body+r'''
static int run(void){unsigned int op,slot,i;int result,expected;
 if(sizeof(u32)!=4||sizeof(s16)!=2||sizeof(EnvironmentColorBytes)!=3||sizeof(void*)!=4)return 3;
 for(op=0;op<256;op++)for(slot=0;slot<256;slot++){
 reset(slot);commands[0]=(op<<24)|0x123456u;commands[1]=0x12AB34CDu;
 commands[2]=0xFB000000u;commands[3]=0xFE654380u;commands[4]=0xDF000000u;commands[5]=0x1234u;
 commands[6]=0xDE000000u;commands[7]=0;commands[8]=0xDF000000u;commands[9]=0;
 expected=reference();result=func_15012ED8(commands);if(result!=expected)return 4;if(check())return 5;}
 reset(255);for(i=0;i<65537;i++){commands[2*i]=0;commands[2*i+1]=0xABCDEF12u;}
 commands[2*65536]=0xFB000000u;commands[2*65537]=0xDF000000u;commands[2*65538]=0xDF000000u;
 expected=reference();if(func_15012ED8(commands)!=expected||check())return 6;return 0;}
'''+START

class ColorScanTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;source.verify_prepared(cls.out);cls.values=source.snapshot(cls.out)
  cls.truth=list(struct.unpack_from('>46I',cls.values['conker/conker.us.bin'],source.ROM))
  cls.raw_bytes,cls.raw_bindings=source.payload(cls.out/'after-retail.o')
  cls.raw=cls.link(cls.out/'after-retail.o','raw-retail',source.ENTRY,SYMBOLS)
  cls.words=cls.link(cls.out/'qualified-padded.o','fitted-retail',source.ENTRY,SYMBOLS,full_owner=True)
  assert cls.words==cls.truth
 @classmethod
 def link(cls,obj,name,entry,symbols,full_owner=False):
  script=cls.out/(name+'.ld');elf=script.with_suffix('.elf');first=0x150127B0 if full_owner else entry
  script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%first)
  anchors=dict(symbols)
  _,funcs,rel=source.parse_object(obj)
  for row in rel.values():
   for _,n in row:
    if n not in anchors and n.startswith('D_'):anchors[n]=int(n[2:],16)
  args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%row for row in anchors.items()],'-o',str(elf),str(obj)]
  p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stderr
  data=sections(elf)['.text'][1];text,funcs,_=source.parse_object(obj);at=funcs[source.FUNCTION]['value'];n=funcs[source.FUNCTION]['size']//4
  return list(struct.unpack_from('>%dI'%n,data,at))
 def compare(self,initial,pointer=INPUT,phase=0,words=None,base=COLORS,entry=source.ENTRY):
  original,fitted,raw=words or(self.truth,self.words,self.raw);models=[Oracle(w,initial,pointer,phase,entry=entry)for w in(original,fitted,raw)]
  errors=[run(m)for m in models];self.assertEqual(errors[0],errors[1]);self.assertEqual(complete(models[0]),complete(models[1]))
  expected,events,count,error=reference(initial,pointer,base)
  self.assertEqual(errors,[error]*3)
  for m in models:
   self.assertEqual(m.memory,expected);self.assertEqual(m.events,events)
   if error is None:self.assertEqual(m.r[2],count);self.assertEqual(m.r[29],STACK+phase)
  return models[0]
 def test_01_owner_profile_guards_census_and_inputs(self):
  q=json.loads((self.out/'qualification.json').read_text());source.checked_payload(self.raw_bytes,self.raw_bindings)
  self.assertEqual(q['Make']['compact_functions_equal'],4);self.assertTrue(q['Make']['complete_padded_object_equal']);self.assertEqual(q['preserved_neighbors'],3)
  source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
  rom=self.values['conker/conker.us.bin'];jal=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)
  self.assertEqual([i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal],[0x400FC])
  self.assertNotIn(struct.pack('>I',source.ENTRY),[rom[i:i+4]for i in range(0,len(rom)-3,4)])
  self.receipt['shape']=dict(words=46,frame=0,return_count=True,compiler_profile=['-O2'],guards=q['guards'],omitted_words=q.get('omitted_return_copies',0),six_relocations=True,three_neighbors_preserved=True,direct_call_ROM=0x400FC)
 def test_02_guest_reference_all_opcodes_slots_aliases_and_word_coverage(self):
  visits=set();cases=0;alias_faults=0
  for opcode,slot,phase in itertools.product(range(256),(0,9,10,17,127,255),(0,8)):
   m=self.compare(fixture(slot,(opcode,0xFB,0xDF)),phase=phase);visits.update(m.visits);cases+=1
  for slot in range(256):self.compare(fixture(slot));cases+=1
  for slot,pointer in itertools.product(range(256),range(COLORS-8,COLORS+64,4)):
   m=self.compare(fixture(slot,(0xFB,0xFB,0xDF),pointer),pointer);alias_faults+=run(Oracle(self.truth,fixture(slot,(0xFB,0xFB,0xDF),pointer),pointer))is not None;cases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
  self.receipt['guest']=dict(cases=cases,all_opcode_and_unsigned_slot_values=True,input_global_output_aliases=True,actual_fixed_global_overlap=True,alias_missing_end_faults=alias_faults,raw_memory_return_access_order_equal=True,fitted_complete_original_states_equal=True,all_46_words=True)
 def test_03_native32_SDK_and_effective_compiled_controls(self):
  positives=[];negatives=[]
  controls={'wrong-match':source.SELECTED.replace('opcode == -5','opcode == -6'),'wrong-stop':source.SELECTED.replace('opcode != -33','opcode != -34'),'wrong-red':source.SELECTED.replace('cursor[1] >> 24','cursor[1] >> 16'),'wrong-green':source.SELECTED.replace('cursor[1] >> 16','cursor[1] >> 8'),'wrong-blue':source.SELECTED.replace('payload >> 8','payload >> 0'),'wrong-index':source.SELECTED.replace('= index;','= index + 1;'),'wrong-count':source.SELECTED.replace('slot + 1','slot + 2'),'false-return':source.SELECTED.replace('return index;','return 0;')}
  for label,opt,body in [(opt[1:],opt,source.SELECTED)for opt in('-O0','-O2','-O3')]+[(n,'-O2',b)for n,b in controls.items()]:
   fixture_path=self.out/('native-'+label+'.c');exe=fixture_path.with_suffix('');fixture_path.write_text(native_harness(body))
   p=subprocess.run(native_command(opt)+[str(fixture_path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
   p=subprocess.run([str(exe)],capture_output=True,timeout=30);row=dict(name=exe.name,exit=p.returncode,SHA256=source.sha(exe.read_bytes()))
   if label in controls:self.assertNotEqual(p.returncode,0,label);negatives.append(row)
   else:self.assertEqual(p.returncode,0,row);positives.append(row)
  self.receipt['native32']=dict(positive=positives,compiled_negatives=negatives,cases_per_optimization=65537,SDK_types=True,trap_UBSan=True,index_halfword_truncation=True,logical_arrays_only_guest_overlap_separate=True)
 def test_04_actual_parent_tail_and_upstream_return_lifetime(self):
  rom=self.values['conker/conker.us.bin'];start=0x15012C48;window=list(struct.unpack_from('>15I',rom,start-0x14FD2B50));cases=0
  self.assertEqual(window[:3],[0x3C04800B,0x0D404BB6,0x8C840E00])
  upstream=struct.unpack_from('>4I',rom,0x1500E514-0x14FD2B50);self.assertEqual(upstream,(0x0D4049EC,0,0x0D46560B,0))
  for slot,phase in itertools.product((0,9,10,17,127,255),(0,8)):
   initial=fixture(slot,(0,0xFB,0xFB,0xDF));put(initial,0x800B0E00,INPUT)
   models=[]
   for body in(self.truth,self.words):
    code={source.ENTRY+4*i:w for i,w in enumerate(body)};m=Oracle(window,initial,phase=phase,entry=start,connected=code,root_entry=source.ENTRY)
    frame=STACK+phase-64;m.r[29]=frame
    for reg,offset in list(zip(range(16,24),range(0x18,0x38,4)))+[(30,0x38),(31,0x3C)]:put(m.memory,frame+offset,m.before[reg])
    self.assertIsNone(run(m));self.assertEqual(m.target_calls,[(INPUT,)]);self.assertEqual(m.r[2],3);self.assertEqual(m.r[29],STACK+phase);models.append(m)
   self.assertEqual(complete(models[0]),complete(models[1]));cases+=1
  self.receipt['caller']=dict(cases=cases,real_15_word_tail=True,JAL_delay_slot_global_pointer=True,parent_forwards_V0=True,saved_registers_and_SP=True,upstream_result_unused_before_next_JAL=True,full_parent_not_claimed=True)
 def test_05_fault_prefixes_and_raw_guard_negatives(self):
  fired=0
  for slot,pointer in itertools.product((0,9,10,17,127,255),(INPUT,COLORS,COLORS+16,COLORS+48)):
   initial=fixture(slot,(0xFB,0xFB,0xDF),pointer);base=Oracle(self.truth,initial,pointer);run(base)
   for fault in range(base.root_accesses):
    models=[Oracle(w,initial,pointer,fault=fault)for w in(self.truth,self.words,self.raw)];errors=[run(m)for m in models]
    self.assertTrue(all(e and e[0]=='AccessBoundary'for e in errors));self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].memory,models[2].memory);self.assertEqual(models[0].events,models[2].events);fired+=1
  for pointer in(INPUT+1,INPUT+2,0xDEADCAFE):self.compare(fixture(0),pointer)
  for i in range(len(self.raw_bytes)//4):
   wrong=bytearray(self.raw_bytes);wrong[4*i+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(wrong),self.raw_bindings)
  for offset in self.raw_bindings:
   wrong=dict(self.raw_bindings);wrong[offset]=[('R_MIPS_LO16','wrong_symbol')]
   with self.assertRaises(ValueError):source.checked_payload(self.raw_bytes,wrong)
  text=(self.out/'qualified-guards.csv').read_text();rows=list(csv.DictReader(io.StringIO(text)));our=[i for i,row in enumerate(rows)if row['function']==source.FUNCTION];rejections=0
  for i in our:
   for field in('expected','expected_relocations'):
    bad=[dict(row)for row in rows];bad[i][field]='0x00000000'if field=='expected'else'R_MIPS_LO16:wrong_symbol'
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(bad[0]));writer.writeheader();writer.writerows(bad);path=self.out/'negative-stale-guards.csv';path.write_text(stream.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-retail.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
    rejections+=1
  links=0
  for number,(entry,base)in enumerate(((source.ENTRY,COLORS),(0x12347FF0,0x23457FE0),(0x32348000,0x55348004))):
   symbols={n:base+v-COLORS for n,v in SYMBOLS.items()};original=self.link(self.out/'original-func_15012ED8.o','original-carry%d'%number,entry,symbols)
   # Isolate just this body with the actual guarded emitter, retaining all six bindings.
   from tools.experiments.alternative_source_draft_word_screen import emit_function
   asm=self.out/('isolated-fit%d.s'%number);obj=asm.with_suffix('.o');fixed,bindings,_=source.normalized(self.raw_bytes,self.raw_bindings)
   # GNU receives relocatable instructions from the same actual whole-owner padded object.
   full=self.out/'qualified-padded.o';text,funcs,rels=source.parse_object(full);f=funcs[source.FUNCTION];words=list(struct.unpack_from('>46I',text,f['value']));relative={at-f['value']:r for at,r in rels.items()if f['value']<=at<f['value']+source.SIZE}
   assembly,unresolved=emit_function(fixed,dict(value=0,size=184),bindings,source.FUNCTION,symbols);self.assertFalse(unresolved);asm.write_text(assembly);p=subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
   fitted=self.link(obj,'fitted-carry%d'%number,entry,symbols);raw=self.link(self.out/'after-retail.o','raw-carry%d'%number,entry,symbols)
   self.assertEqual(original,fitted);self.compare(fixture(17,base=base),words=(original,fitted,raw),base=base,entry=entry);links+=3
  self.receipt['faults']=dict(fired_fault_prefixes=fired,raw_access_prefixes_equal=True,fitted_complete_states=True,alignment_unmapped_reads=True,raw_word_negatives=len(self.raw_bytes)//4,binding_negatives=6,real_padder_stale_rejections=rejections,GNU_links=links,three_HI_LO_carry_layouts=True,guest_fault_semantics_only=True)
 def test_06_strict_image_all_functions_protected_data_and_corruption_controls(self):
  before=self.values['conker/build/conker.us.elf'];after=(self.out/'first-linked.elf').read_bytes();truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];source.check_image(before,after,truth)
  a,_,aa=source.load_elf_functions(str(self.out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=source.load_elf_functions(str(self.out/'first-linked.elf'),'mips-linux-gnu-objdump');self.assertEqual(aa,bb);self.assertEqual(list(n for n in a if a[n]!=b[n]),[source.FUNCTION]);self.assertEqual(len(a),6056)
  data=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
  at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);row=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
  wrongs=[]
  for offset in(at+60,row+8,24,source.elf_slot_offset(before,0x150127B0,4),len(after)//2,len(after)-1):
   bad=bytearray(after);bad[offset]^=1;wrongs.append(bytes(bad))
  wrongs.append(after+b'!')
  for bad in wrongs:
   with self.assertRaises(ValueError):source.check_image(before,bad,truth)
  self.receipt['image']=dict(functions=6056,other_bodies_fixed=6055,all_addresses_fixed=True,protected_data=data,exclusions=0,effective_corruptions=7)
