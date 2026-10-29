"""Owner byte scale: original callback, conversion bounds, guards and full image."""
from pathlib import Path
from dataclasses import replace
import csv,io,itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_owner_byte_scale_match as source
from tools.tests import game_owner_byte_scale_oracle as oracle
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.game_animation_timeline_oracle import bits,floating
ROOT=Path(__file__).resolve().parents[2]

def semantic_controls():
 body=source.SELECTED
 return dict(wrong_source=body.replace('[0x2F]','[0x2E]'),wrong_output=body.replace('[0x70]','[0x71]'),integer_scale=body.replace('value * D_800A04C0','value * (u32)D_800A04C0'),add_scale=body.replace('value * D_800A04C0','value + D_800A04C0'),failed_result=body.replace('return 1;','return 0;'),clamped=body.replace('owner[0x70] = (u32)(value * D_800A04C0);','owner[0x70] = value * D_800A04C0 > 255.0f ? 255 : (u32)(value * D_800A04C0);'))

def link_object(obj,entry,label,fresh,symbols=None):
 defs=symbols or dict(D_800A04C0=oracle.SCALE);text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=fresh/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class OwnerByteScaleTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM))
  cls.words=link_object(cls.out/'qualified-padded.o',source.ENTRY,'qualified',cls.fresh);cls.raw=link_object(cls.out/'selected.o',source.ENTRY,'selected',cls.fresh)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def linked(self,obj,entry,label,symbols=None):return link_object(obj,entry,label,self.fresh,symbols)
 def test_01_owner_actual_Make_and_callback_ABI(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  assert truth==words and len(raw)==50 and len(truth)==51
  assert source.normalized_payload(*source.payload(o/'selected.o'))==source.payload(o/'original-func_150C7670.o')
  for label in('before','after'):
   obj,diag=source.compile_owner(r,fresh,(o/(label+'-owner.c')).read_text(),'fresh-'+label);assert not diag;assert source.same_functions(obj,o/(label+'-owner.o'))==2
  assert source.same_functions(o/'before-owner.o',o/'after-owner.o',(source.FUNCTION,))==1
  assert source.normalized_pools(o/'before-owner.o')==source.normalized_pools(o/'after-owner.o')
  assert source.same_functions(o/'before-padded.o',o/'qualified-padded.o',(source.FUNCTION,))==1
  assert source.recovered_owner(self.values[source.SOURCE].decode()).encode()==(o/'proposed-owner.c').read_bytes()
  commands=json.loads((o/'Make-commands.json').read_text());assert len(commands)==3 and commands[0][0]=='../ido/ido5.3_recomp/cc'and '-O2'in commands[0]and '-g3'in commands[0]
  assert not(o/'actual-Make-diagnostics.txt').read_bytes()
  assert(o/'make-shadow/src/game/generated_F4B20.c.o').read_bytes()==(o/'qualified-padded.o').read_bytes()
  ws=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);assert jal not in ws
  assert[i*4 for i,w in enumerate(ws)if w==source.ENTRY]==[0x22E3EC]
  assert rom[0x22E3EC:0x22E3F0]==struct.pack('>I',source.ENTRY)
  assert rom[0x244F80:0x244F84]==bytes.fromhex('4013020d')
  assert source.BINDINGS=={40:[('R_MIPS_HI16','D_800A04C0')],44:[('R_MIPS_LO16','D_800A04C0')]}
  if self.installed:source.audit(r,o)
  self.receipt['owner']=dict(body_words=51,compiler_words=50,frame=0,bindings=2,guards=2,neighbors=1,compact_functions=2,Make_commands=3,callback_slot=6,callback_table_bytes=32,public_return_one=True)

 def test_02_guest_byte_lanes_aliases_and_conversion_bounds(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  visited=set();cases=[]
  for byte,phase,fcsr in itertools.product(range(256),(0,8),(0,0x800004,0xA5A50000)):cases.append(oracle.Case(byte=byte,phase=phase,fcsr=fcsr,seed=byte))
  scales=(0,0x80000000,0x3E800000,0x3F800001,0x4B800000,0x4F000000,0x4F7FFFFF,0x4F800000,0xBF800000,0x7F800000,0x7FC12345)
  cases.extend(oracle.Case(byte=b,scale=s)for b,s in itertools.product((0,1,2,127,128,254,255),scales))
  cases.extend((oracle.Case(data=oracle.OWNER+0x41),oracle.Case(link=oracle.OWNER+0x5C),oracle.Case(data=oracle.SCALE-0x2F)))
  for c in cases:
   initial=oracle.fixture(c);expected=oracle.reference(initial,c);pair=[]
   for body in(truth,words):
    m=oracle.ScaleOracle(body,initial,c).run();assert(m.memory,m.r[2])==expected,c;pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1])
   # Unnormalized C has the same public operation, with a different instruction schedule.
   m=oracle.ScaleOracle(raw,initial,c).run();assert(m.memory,m.r[2])==expected
  missing=sorted(set(range(source.ENTRY,source.ENTRY+204,4))-visited)
  assert missing==[source.ENTRY+n for n in(32,36,40,168)],list(map(hex,missing))
  self.receipt['guest']=dict(cases=len(cases),covered_words=len(visited),unreachable_original_words=list(map(hex,missing)),all_byte_lanes=True,aliases=3,raw_public_equal=True,FCSR_scope='bounded conversions and control-state restoration',hardware_or_arbitrary_rounding_claimed=False)

 def test_03_original_callback_table_and_return_gate(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  caller_cases=0;caller_visited=set()
  for byte,phase,selector,gate in itertools.product((0,1,127,128,255),(0,8),(0,6),(0,1,255)):
   c=oracle.Case(byte=byte,phase=phase);pair=[]
   for body in(truth,words):
    m,initial=oracle.caller_machine(rom,body,c,selector,gate)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Caller window did not reach its declared end')
    expected=oracle.reference(initial,c)[0]if selector and not gate else initial
    public=lambda state:{p:v for p,v in state.items()if not oracle.STACK-1024<=p<oracle.STACK+1024}
    assert public(m.memory)==public(expected) and m.r[5]==gate and m.fcsr==c.fcsr
    assert len(m.calls)==int(bool(selector)and not gate)
    if m.calls:assert m.calls==[(source.ENTRY,(c.owner,))]
    pair.append(m);caller_visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1]);caller_cases+=1
  assert set(range(oracle.WINDOW,oracle.END,4))-{oracle.WINDOW+56}<=caller_visited
  self.receipt['integration']=dict(caller_cases=caller_cases,caller_words=16,covered_caller_words=len(caller_visited&set(range(oracle.WINDOW,oracle.END,4))),slot=6,skipped_selector_or_gate=True,result_zero_arm_unreachable=True,complete_parent_or_gameplay_claimed=False)

 def test_04_native32_defined_inputs_and_controls(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  scale_words=(0,0x3E800000,0x3F800000,0x4013020D,0x47800000,0x4B7FFFFF)
  expected=[[oracle.converted(floating(bits(byte*floating(s))))for byte in range(256)]for s in scale_words]
  body=source.SELECTED
  controls=semantic_controls()
  text=source.HEADERS+body+'\n'
  for name,wrong in controls.items():assert wrong!=body;text+=wrong.replace(source.FUNCTION,'negative_'+name)+'\n'
  text+='static u8 expected[6][256]='+str(expected).replace('[','{').replace(']','}')+';\n'
  text+='static u32 scales[6]={'+','.join(hex(x)+'u'for x in scale_words)+'};\n'
  text+=r'''
  typedef s32(*Fn)(u8*);
  typedef struct {u8 prefix[0x170];u8 *link;u8 suffix[32];} Owner;
  typedef struct {u8 prefix[0x14];u8 *data;u8 suffix[32];} Link;
  typedef char Layout[(sizeof(void*)==4&&__builtin_offsetof(Owner,link)==0x170&&__builtin_offsetof(Link,data)==0x14)?1:-1];
  static Owner owner,want;static Link link;static u8 data[128];f32 D_800A04C0;
  static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
  static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
  static int check(Fn fn){u32 byte,scale,alias,i;u8 saved[sizeof(Link)],savedData[128];
   for(byte=0;byte<256;byte++)for(scale=0;scale<6;scale++)for(alias=0;alias<2;alias++){
    for(i=0;i<sizeof(owner);i++)((u8*)&owner)[i]=(u8)(i*13+byte+0xA5);
    for(i=0;i<sizeof(link);i++)((u8*)&link)[i]=(u8)(i*17+byte+0xB5);
    for(i=0;i<sizeof(data);i++)data[i]=(u8)(i*19+byte+0xC5);
    owner.link=(u8*)&link;link.data=alias?owner.prefix+0x41:data;link.data[0x2F]=(u8)byte;
    copy(&want,&owner,sizeof(owner));copy(saved,&link,sizeof(link));copy(savedData,data,sizeof(data));copy(&D_800A04C0,scales+scale,4);want.prefix[0x70]=expected[scale][byte];
    if(fn((u8*)&owner)!=1||!same(&owner,&want,sizeof(owner))||!same(&link,saved,sizeof(link))||!same(data,savedData,sizeof(data)))return 1;
   }return 0;
  }
  static int run(void){if(check(func_150C7670))return 10;
  '''
  for i,name in enumerate(controls):text+='if(!check(negative_'+name+'))return '+str(20+i)+';\n'
  text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');native=fresh/'native.c';native.write_text(text);profiles={}
  for opt in('-O0','-O2','-O3'):
   exe=fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(native),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0,build.stderr
   run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);profiles[opt]=dict(exit=0,diagnostics=build.stderr)
  self.receipt['native']=dict(cases_per_profile=3072,optimizations=profiles,controls=len(controls),SDK=True,pointers32=True,trapping_UBSan=True,precomputed_expected_bytes=True,valid_backing_and_canaries=True,guest_invalid_conversions_excluded=True)

 def test_05_direct_and_caller_fault_prefixes(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  fault_count=delay=0
  for parent,scale in itertools.product((False,True),(0x4013020D,0x4F7FFFFF,0xBF800000)):
   c=oracle.Case(scale=scale)
   def machine(body):return oracle.caller_machine(rom,body,c)[0]if parent else oracle.ScaleOracle(body,oracle.fixture(c),c)
   m=machine(truth)
   try:m.run()
   except oracle.WindowBoundary:pass
   for cut in range(m.all_accesses):
    pair=[]
    for body in(truth,words):
     model=machine(body);model.cut=cut
     try:model.run()
     except faults.AccessBoundary:pass
     else:raise AssertionError(('unfired access cut',cut))
     pair.append(model)
    assert oracle.full_state(pair[0])==oracle.full_state(pair[1])
    assert(pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses)==(pair[1].current_pc,pair[1].delay_of,cut)
    fault_count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=fault_count,delay_slot_cuts=delay,complete_RAM_registers_trace_PC_delay_and_FCSR=True,portable_C_fault_claimed=False)

 def test_06_guard_rejections_padder_and_three_GNU_layouts(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  payload,rs=source.payload(o/'selected.o');rejects=0
  for at in range(0,len(payload),4):
   bad=bytearray(payload);bad[at+3]^=1
   with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.normalized_payload(payload,bad)
   rejects+=1
  normalized,bindings=source.normalized_payload(payload,rs)
  assert normalized[:8]==payload[:8]and normalized[8:12]==payload[188:192]and normalized[12:192]==payload[8:188]and normalized[192:196]==bytes(4)and normalized[196:]==payload[192:]
  assert bindings=={at+4:v for at,v in rs.items()}
  for row in source.NEW_GUARDS:
   at=int(row['offset'],0);assert not rs.get(at)
   for variant in('word','binding'):
    altered=[dict(v)for v in source.NEW_GUARDS];item=next(v for v in altered if v['offset']==row['offset']);item['expected'if variant=='word'else'expected_relocations']='0x00000000'if variant=='word'else'R_MIPS_HI16:D_800A04C0'
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,list(altered[0]),lineterminator='\n');writer.writeheader();writer.writerows(altered);manifest=fresh/('bad-%d-%s.csv'%(at,variant));manifest.write_text(stream.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=manifest)
  p=fresh/'padded.s';p.write_text(source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=o/'proposed-guards.csv'))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
  assert p.with_suffix('.o').read_bytes()==(o/'qualified-padded.o').read_bytes();count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   defs=dict(D_800A04C0=(oracle.SCALE,0x800D8004,0x80107FFC)[j])
   paths=(o/'original-func_150C7670.o',o/'make-shadow/src/game/generated_F4B20.c.o',o/'qualified-padded.o');images=[linked(path,entry,'rebase-%d-%d'%(j,k),defs)for k,path in enumerate(paths)];assert images[0]==images[1]==images[2]
   unguarded=linked(o/'selected.o',entry,'rebase-raw-%d'%j,defs)
   for byte,phase in itertools.product((0,1,63,127,128,173,254,255),(0,8)):
    c=oracle.Case(byte=byte,phase=phase);initial=oracle.fixture(c,defs);expected=oracle.reference(initial,c,defs);pair=[]
    for code in images:
     m=oracle.ScaleOracle(code,initial,c,entry=entry,symbols=defs).run();assert(m.memory,m.r[2])==expected;pair.append(m)
    assert all(oracle.full_state(m)==oracle.full_state(pair[0])for m in pair)
    m=oracle.ScaleOracle(unguarded,initial,c,entry=entry,symbols=defs).run();assert(m.memory,m.r[2])==expected;count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,padder_guard_rejections=4,original_Make_and_padded_words_equal=True,raw_public_semantics_equal=True,guards=2,existing_result_move=True,retail_nop_retained=True,signed_low_address_carries=True)

 def test_07_compiled_semantic_and_return_controls(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  evidence={};false_caller=None
  for name,body in semantic_controls().items():
   assert body!=source.SELECTED;obj,diag=source.compile_owner(r,fresh,source.HEADERS+body,'negative-'+name);assert not diag;code=linked(obj,source.ENTRY,'negative-link-'+name)
   for byte in(0,1,127,173,255):
    c=oracle.Case(byte=byte);initial=oracle.fixture(c);m=oracle.ScaleOracle(code,initial,c).run();expected=oracle.reference(initial,c)
    if(m.memory,m.r[2])!=expected:evidence[name]=byte;break
   assert name in evidence,name
   if name=='failed_result':
    m,initial=oracle.caller_machine(rom,code)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Negative caller did not finish the window')
    assert m.r[5]==1 and 0x151322B0 in m.visits and m.calls==[(source.ENTRY,(oracle.OWNER,))];false_caller=True
  assert false_caller
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,original_caller_rejects_false_result=True,previously_unreachable_caller_arm_exercised=True)

 def test_08_strict_whole_image_and_guard_prefix(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  v=source.check_inputs(r,o,self.installed);source.verify_prepared(o);before=v['conker/build/conker.us.elf'];truth_bytes=rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth_bytes)
  source.check_image(before,(o/'first-linked.elf').read_bytes(),truth_bytes);at=source.elf_slot_offset(before,source.ENTRY,204);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  assert sum(a!=b for a,b in zip(before,expected))==146
  assert sum(a!=b for a,b in zip(before[at:at+204],expected[at:at+204]))==127
  positions=[20,at,at+8,at+192,at+204,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,oracle.SCALE,4),source.elf_slot_offset(before,oracle.TABLE,32),source.elf_slot_offset(before,oracle.WINDOW,64)]
  positions+=list(range(2820580,2820612))+list(range(3096928,3096950))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth_bytes)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth_bytes)
  proposed=source.guard_manifest(v['conker/retail_word_patches.us.csv']);assert proposed==(o/'proposed-guards.csv').read_bytes()and proposed.startswith(v['conker/retail_word_patches.us.csv'])
  assert len(list(csv.DictReader(io.StringIO(proposed.decode()))))-len(list(csv.DictReader(io.StringIO(v['conker/retail_word_patches.us.csv'].decode()))))==2
  self.receipt['image']=dict(changed_bytes=146,code_bytes=127,extent_bytes=1,metadata_bytes=18,exclusions=0,corruptions=len(positions)+1,all_metadata_record_bytes_and_strings_guarded=True,inherited_guard_prefix_unchanged=True,new_guards=2,protected_Game_bytes=189088,focused_inputs=len(v))
