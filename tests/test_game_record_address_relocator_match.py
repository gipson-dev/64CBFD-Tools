"""Direct record relocation, pointer-cell declarations and strict image scope."""
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_address_relocator_match as source
from tools.tests import game_record_address_relocator_oracle as oracle
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2]

def semantic_controls():
 b=source.SELECTED
 return dict(missing_count_clear=b.replace('    D_800B0E34[index] = 0;\n',''),early_null=b.replace('    D_800B0E30[index] = records;','    if (!records) return;\n    D_800B0E30[index] = records;'),missing_first=b.replace('            D_800B0E30[index][count * 3] += offset;\n',''),missing_second=b.replace('            D_800B0E30[index][count * 3 + 1] += offset;\n',''),wrong_field=b.replace('count * 3 + 1','count * 3 + 2'),wrong_count=b.replace('D_800B0E34[index] = count;','D_800B0E34[index] = count + 1;'))

def link_object(obj,entry,label,fresh,symbols=None):
 defs=symbols or oracle.symbols();text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=fresh/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class RecordAddressRelocatorTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM))
  cls.words=link_object(cls.out/'qualified-padded.o',source.ENTRY,'qualified',cls.fresh);cls.raw=link_object(cls.out/'selected.o',source.ENTRY,'selected',cls.fresh)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def linked(self,obj,entry,label,symbols=None):return link_object(obj,entry,label,self.fresh,symbols)
 def test_01_owner_actual_Make_and_caller_ABI(self):
  o=self.out;v=self.values
  assert self.truth==self.words==self.raw and len(self.raw)==51 and source.NEW_GUARDS==[]
  assert source.payload(o/'selected.o')==source.payload(o/'original-func_15003120.o')
  for label in('before','after'):
   header=v[source.HEADER]if label=='before'else source.recovered_header(v[source.HEADER].decode()).encode()
   obj,diag=source.compile_frozen_owner(ROOT,self.fresh,(o/(label+'-owner.c')).read_text(),header,'fresh-'+label)
   assert not diag and source.same_functions(obj,o/(label+'-owner.o'))==9
  assert source.same_functions(o/'before-owner.o',o/'after-owner.o',(source.FUNCTION,))==8
  assert source.normalized_pools(o/'before-owner.o')==source.normalized_pools(o/'after-owner.o')
  assert source.same_functions(o/'before-padded.o',o/'qualified-padded.o',(source.FUNCTION,))==8
  assert source.recovered_owner(v[source.SOURCE].decode()).encode()==(o/'proposed-owner.c').read_bytes()
  assert source.recovered_header(v[source.HEADER].decode()).encode()==(o/'proposed-variables.h').read_bytes()
  commands=json.loads((o/'Make-commands.json').read_text());assert len(commands)==3 and commands[0][0]=='../ido/ido5.3_recomp/cc'and '-O2'in commands[0]and '-g3'in commands[0]
  assert not(o/'actual-Make-diagnostics.txt').read_bytes()
  assert(o/'make-shadow/src/game_305D0.c.o').read_bytes()==(o/'qualified-padded.o').read_bytes()
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
  assert[i*4 for i,w in enumerate(ws)if w==jal]==[0x30804]and source.ENTRY not in ws
  assert b's32 func_150031EC() {\n    return 0;\n}'in v[source.SOURCE]
  for name,row in source.HEADER_DEPENDENTS.items():
   a=o/('header-before-shadow/'+name.removeprefix('conker/build/'));b=o/row['shadow']
   assert parse_object(a)==parse_object(b)and source.normalized_pools(a)==source.normalized_pools(b)
  assert(o/'header-linked.elf').read_bytes()==(o/'first-linked.elf').read_bytes()
  debug_controls=0
  for name,row in source.HEADER_DEPENDENTS.items():
   a=(o/row['shadow']).read_bytes();b=(o/'production-diagnostic'/name).read_bytes();assert source.check_dependent(a,b)
   positions=[source.dependent_sections(b)[sec][0][4]for sec in('.text','.strtab','.symtab','.reginfo')]
   sh,raw=source.dependent_sections(b)['.mdebug'];h=struct.unpack_from('>HH23I',raw);positions.extend((h[14],h[10]+4,h[20]+16,h[16]+10))
   for at in positions:
    bad=bytearray(b);bad[at]^=1
    with self.assertRaises((ValueError,AssertionError,UnicodeError,struct.error)):source.check_dependent(a,bytes(bad))
    debug_controls+=1
  assert debug_controls==56
  if self.installed:source.audit(ROOT,o)
  self.receipt['owner']=dict(body_words=51,slot_words=51,alignment_words=0,compiler_words=51,frame=0,bindings=4,guards=0,neighbors=8,compact_functions=9,Make_commands=3,original_direct_caller=True,pointer_cell_header_types=True)

 def test_02_guest_unsigned_boundaries_and_alias_reloads(self):
  cases=[oracle.Case(index=i,offset=b,count=n,null=z,seed=seed)for i,b,n,z,seed in itertools.product((0,3,0xFFFFFFFF,0x7FFFFFFF),(0,4,64,0x80000000,0xFFFFFFFC),(0,1,2,255,256,257),(0,1),(0,7))]
  cases.extend(oracle.Case(alias=a,seed=seed)for a,seed in itertools.product(range(1,5),(0,7)))
  visited=set()
  for c in cases:
   initial,args=oracle.fixture(c);expected=oracle.reference(initial,args);pair=[]
   for body in(self.truth,self.words):
    m=oracle.RelocatorOracle(body,initial,args,c).run();assert m.memory==expected,c;assert m.calls==[];pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1])
  assert set(range(source.ENTRY,source.ENTRY+204,4))<=visited
  self.receipt['guest']=dict(cases=len(cases),covered_words=51,full_RAM_registers_and_trace=True,count_modulo_256=True,full_word_sparse_indices=True,guest_only_alias_classes=4,stack_untouched=True)

 def test_03_original_caller_window(self):
  count=0;visited=set()
  for index,n,null,phase,seed in itertools.product((0,3,4),(0,2),(0,1),(0,8),(0,1)):
   c=oracle.Case(index=index,count=n,null=null,phase=phase,seed=seed);pair=[]
   for body in(self.truth,self.words):
    m,expected,args=oracle.caller_machine(self.rom,body,c)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    assert m.memory==expected and m.calls==[(source.ENTRY,args)]
    assert m.r[5]==0 and m.r[2]==4*index
    pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1]);count+=1
  for phase,seed in itertools.product((0,8),(0,1)):
   c=oracle.Case(phase=phase,seed=seed);pair=[]
   for body in(self.truth,self.words):
    m,expected,args=oracle.caller_machine(self.rom,body,c,reject=True)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Missing rejected caller boundary')
    assert m.memory==expected and m.calls==[] and m.r[2]==oracle.read(expected,oracle.STACK+phase+0x64)
    pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1]);count+=1
  own=set(range(oracle.WINDOW,oracle.END,4));assert own<=visited
  self.receipt['integration']=dict(caller_cases=count,caller_words=23,covered_caller_words=23,return_value_discarded=True,three_header_relocations_qualified=True,complete_parent_or_gameplay_claimed=False)

 def test_04_native32_defined_inputs_and_controls(self):
  controls=semantic_controls();text=source.HEADERS+source.SELECTED+'\n'
  for name,body in controls.items():assert body!=source.SELECTED;text+=body.replace(source.FUNCTION,'negative_'+name)+'\n'
  vectors=list(itertools.product((0,3),(0,4,64,0x80000000,0xFFFFFFFC),(0,1,2,255,256,257),(0,1),(0,7)))
  text+='static const u32 cases[][5]={'+','.join('{'+','.join('0x%Xu'%v for v in row)+'}'for row in vectors)+'};\n'
  text+=r'''
  static u32 record[3*258+8],expected[3*258+8];static u32 *table[8],*want[8];static u8 counts[8],wanted[8];
  u32 **D_800B0E30;u8 *D_800B0E34;
  typedef void(*Fn)(s32,u32,u32*);
  static int check(Fn fn){u32 c,i,j,index,offset,n,z,seed;u32*input;
   for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++){
    index=cases[c][0];offset=cases[c][1];n=cases[c][2];z=cases[c][3];seed=cases[c][4];
    for(i=0;i<sizeof(record)/sizeof(record[0]);i++)record[i]=expected[i]=0xA5A5A5A5u+i;
    for(i=0;i<n;i++){
     record[4+3*i]=(0xFFFFFFF0u-i*17-seed)|1u;record[4+3*i+1]=0x7FFFFFFFu+i*23+seed;
     expected[4+3*i]=record[4+3*i]+(z?0:offset);expected[4+3*i+1]=record[4+3*i+1]+(z?0:offset);
    }
    record[4+3*n]=expected[4+3*n]=0;
    for(j=0;j<8;j++){table[j]=want[j]=record;counts[j]=wanted[j]=0xA5;}
    D_800B0E30=table;D_800B0E34=counts;input=z?0:(u32*)((u32)(record+4)-offset);
    want[index]=z?0:record+4;wanted[index]=z?0:(u8)n;fn((s32)index,offset,input);
    if(D_800B0E30!=table||D_800B0E34!=counts)return 1;
    for(i=0;i<sizeof(record)/sizeof(record[0]);i++)if(record[i]!=expected[i])return 1;
    for(i=0;i<8;i++)if(table[i]!=want[i]||counts[i]!=wanted[i])return 1;
   }return 0;
  }
  static int run(void){if(check(func_15003120))return 10;
  '''
  for i,name in enumerate(controls):text+='if(!check(negative_'+name+'))return '+str(20+i)+';\n'
  text+='return 0;}\n'+START;(self.fresh/'native.c').write_text(text);reports={}
  for opt in('-O0','-O2','-O3'):
   binary=self.fresh/('native'+opt);p=subprocess.run(native_command(opt)+[str(self.fresh/'native.c'),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);assert p.returncode==0 and not(p.stdout+p.stderr),(opt,p.returncode,p.stdout,p.stderr)
   p=subprocess.run([str(binary)],capture_output=True,text=True);reports[opt]=dict(exit=p.returncode,diagnostics=p.stdout+p.stderr);assert p.returncode==0 and not(p.stdout+p.stderr),(opt,reports[opt])
  self.receipt['native']=dict(cases_per_profile=len(vectors),optimizations=reports,controls=len(controls),SDK=True,pointers32=True,trapping_UBSan=True,typed_backing_and_canaries=True,guest_aliases_and_sparse_indices_excluded=True)

 def test_05_direct_and_caller_fault_prefixes(self):
  count=delay=0
  cases=[(False,oracle.Case(null=1)),(False,oracle.Case(count=0)),(False,oracle.Case()),(False,oracle.Case(alias=2)),(False,oracle.Case(alias=3)),(True,oracle.Case(index=3))]
  for parent,c in cases:
   def machine(body):
    if parent:return oracle.caller_machine(self.rom,body,c)[0]
    m,args=oracle.fixture(c);return oracle.RelocatorOracle(body,m,args,c)
   m=machine(self.truth)
   try:m.run()
   except oracle.WindowBoundary:pass
   for cut in range(m.all_accesses):
    pair=[]
    for body in(self.truth,self.words):
     model=machine(body);model.cut=cut
     try:model.run()
     except faults.AccessBoundary:pass
     else:raise AssertionError(('Unfired access cut',cut))
     pair.append(model)
    assert oracle.full_state(pair[0])==oracle.full_state(pair[1])and(pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses)==(pair[1].current_pc,pair[1].delay_of,cut)
    count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=count,delay_slot_cuts=delay,complete_RAM_registers_trace_PC_and_delay=True,portable_C_fault_claimed=False)

 def test_06_raw_rejections_padder_and_three_GNU_layouts(self):
  o=self.out;payload,rs=source.payload(o/'selected.o');rejects=0
  for at in range(0,len(payload),4):
   bad=bytearray(payload);bad[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(payload,bad)
   rejects+=1
  assert source.normalized_payload(payload,rs)==(payload,rs)and source.NEW_GUARDS==[]
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(o/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=o/'proposed-guards.csv'))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
  assert p.with_suffix('.o').read_bytes()==(o/'qualified-padded.o').read_bytes();count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   defs=oracle.symbols()if j==0 else dict(D_800B0E30=0x80007FFC+j*0x10000,D_800B0E34=0x80018004+j*0x20000)
   paths=(o/'original-func_15003120.o',o/'make-shadow/src/game_305D0.c.o',o/'qualified-padded.o',o/'selected.o');images=[self.linked(path,entry,'rebase-%d-%d'%(j,k),defs)for k,path in enumerate(paths)];assert images[0]==images[1]==images[2]==images[3]
   for c in(oracle.Case(),oracle.Case(null=1),oracle.Case(count=0),oracle.Case(index=0xFFFFFFFF),oracle.Case(count=256),oracle.Case(alias=1),oracle.Case(alias=2),oracle.Case(alias=3),oracle.Case(alias=4)):
    initial,args=oracle.fixture(c,defs);expected=oracle.reference(initial,args,defs);pair=[]
    for code in images:
     m=oracle.RelocatorOracle(code,initial,args,c,entry=entry,s=defs).run();assert m.memory==expected;pair.append(m)
    assert all(oracle.full_state(m)==oracle.full_state(pair[0])for m in pair);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,original_Make_padded_and_raw_words_equal=True,guards=0,all_four_bindings_rebased=True,HI_LO_carry_boundaries=True)

 def test_07_compiled_semantic_controls(self):
  controls=semantic_controls();controls['cached_record_pointer']=source.SELECTED.replace('    s32 count;','    s32 count;\n    u32 *cached;').replace('        for (count','        cached = D_800B0E30[index];\n        for (count').replace('D_800B0E30[index][count * 3','cached[count * 3')
  evidence={}
  for name,body in controls.items():
   assert body!=source.SELECTED;obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);assert not diag;code=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in(oracle.Case(null=1),oracle.Case(count=0),oracle.Case(),oracle.Case(alias=2)):
    initial,args=oracle.fixture(c);m=oracle.RelocatorOracle(code,initial,args,c).run();expected=oracle.reference(initial,args)
    if m.memory!=expected:evidence[name]=dict(null=c.null,count=c.count,alias=c.alias);break
   assert name in evidence,name
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,cached_pointer_rejected=True)

 def test_08_strict_whole_image_and_unchanged_guards(self):
  o=self.out;v=source.check_inputs(ROOT,o,self.installed);source.verify_prepared(o);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth)
  source.check_image(before,(o/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  assert sum(a!=b for a,b in zip(before,expected))==147
  assert sum(a!=b for a,b in zip(before[at:at+204],expected[at:at+204]))==146
  positions=[20,at-4,at+204,source.elf_slot_offset(before,oracle.WINDOW,92)]
  positions+=list(range(at,at+204))+list(range(named[source.FUNCTION][0],named[source.FUNCTION][0]+16))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  manifest=v['conker/retail_word_patches.us.csv'];assert source.guard_manifest(manifest)==manifest==(o/'proposed-guards.csv').read_bytes()
  with self.assertRaises(ValueError):source.guard_manifest(manifest+b'\n')
  assert not[row for row in csv.DictReader(io.StringIO(manifest.decode()))if row['function']==source.FUNCTION]
  self.receipt['image']=dict(changed_bytes=147,code_bytes=146,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=len(positions)+1,all_target_bytes_and_symbol_record_guarded=True,guard_manifest_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
