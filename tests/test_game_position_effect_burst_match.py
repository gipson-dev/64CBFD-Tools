"""Position effects: direct C, original RNGs, caller ABI and full image."""
from pathlib import Path
from dataclasses import replace
import csv,io,itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_position_effect_burst_match as source
from tools.tests import game_position_effect_burst_oracle as oracle
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
 return dict(missing_first=body.replace('    func_151D5514(position, kind, mode);\n',''),swapped_pair=body.replace('func_151D5514(position, kind, mode);\n    func_151D3FF4(position, kind, mode);','func_151D3FF4(position, kind, mode);\n    func_151D5514(position, kind, mode);'),signed_remainder=body.replace('u32 randomValue;','s32 randomValue;').replace('(u32)func_150ADA20()','func_150ADA20()').replace('% 56U','% 56').replace('+ 200U','+ 200'),wrong_width=body.replace('* 4.0f','* 5.0f'),rounded_coefficient=body.replace('1.6409999f','1.641f'),wrong_offset=body.replace('+ 200U','+ 201U'),nonzero_parameter=body.replace('0.0f, kind, mode','1.0f, kind, mode'),swapped_random=body.replace('randomScale = func_150ADA68();\n    randomValue = (u32)func_150ADA20();','randomValue = (u32)func_150ADA20();\n    randomScale = func_150ADA68();'))

def link_object(obj,entry,label,fresh,symbols=None):
 defs=symbols or oracle.symbols();text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=fresh/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class PositionEffectBurstTests(unittest.TestCase):
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
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  assert truth==words==raw and len(raw)==51 and truth[0]==0x27BDFFD0 and source.NEW_GUARDS==[]
  assert source.payload(o/'selected.o')==source.payload(o/'original-func_151D5648.o')
  for label in('before','after'):
   obj,diag=source.compile_owner(r,fresh,(o/(label+'-owner.c')).read_text(),'fresh-'+label);assert not diag;assert source.same_functions(obj,o/(label+'-owner.o'))==28
  assert source.same_functions(o/'before-owner.o',o/'after-owner.o',(source.FUNCTION,))==27
  assert source.normalized_pools(o/'before-owner.o')==source.normalized_pools(o/'after-owner.o')
  assert source.same_functions(o/'before-padded.o',o/'qualified-padded.o',(source.FUNCTION,))==27
  assert source.recovered_owner(self.values[source.SOURCE].decode()).encode()==(o/'proposed-owner.c').read_bytes()
  commands=json.loads((o/'Make-commands.json').read_text());assert len(commands)==5 and commands[1][0]=='../ido/ido5.3_recomp/cc'and '-O2'in commands[1]and '-g3'in commands[1]
  assert not(o/'actual-Make-diagnostics.txt').read_bytes()
  assert(o/'make-shadow/src/game/generated_200930.c.o').read_bytes()==(o/'qualified-padded.o').read_bytes()
  ws=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
  assert[i*4 for i,w in enumerate(ws)if w==jal]==[0x55F50]and source.ENTRY not in ws
  assert source.BINDINGS=={28:[('R_MIPS_26','func_151D5514')],44:[('R_MIPS_26','func_151D3FF4')],52:[('R_MIPS_26','func_150ADA68')],60:[('R_MIPS_26','func_150ADA20')],180:[('R_MIPS_26','func_151541B8')]}
  assert b's32 func_150265CC() {\n    return 0;\n}'in self.values['conker/src/game/generated_50D80.c']
  before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,oracle.SCALE,4);assert before[at:at+4]==bytes.fromhex('37800080')
  for entry,pos,n in oracle.HELPERS:
   at=source.elf_slot_offset(before,entry,n*4);assert before[at:at+n*4]==rom[pos:pos+n*4]
  for name,owner in [('func_151D5514','game/generated_200930'),('func_151D3FF4','game/generated_200930'),('func_150ADA68','game_DAE50'),('func_150ADA20','game_DAE50'),('func_151541B8','game/generated_17CAF0')]:
   assert ('#pragma GLOBAL_ASM("asm/nonmatchings/'+owner.removeprefix('game/')+'/'+name+'.s")').encode()in self.values['conker/src/'+owner+'.c']
  if self.installed:source.audit(r,o)
  self.receipt['owner']=dict(body_words=51,slot_words=51,alignment_words=0,compiler_words=51,frame=48,bindings=5,guards=0,neighbors=27,compact_functions=28,Make_commands=5,original_direct_caller=True,void_result_discarded=True)

 def test_02_guest_unsigned_boundaries_and_argument_reloads(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  cases=[]
  for kind in range(256):cases.append(oracle.Case(kind=0xABCD0000|kind,random=(kind*0x01010101)&0xFFFFFFFF,sample=oracle.bits((kind%65)/64),mutation=kind%8,phase=(kind&1)*8,result=kind&1))
  for sample,random,mutation,phase in itertools.product((0,0x80000000,1,0x3E800000,0x3F000000,0x3F7FFFFF,0x3F800000,0xBF800000,0xC0400000),(0,55,56,57,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,4,7),(0,8)):cases.append(oracle.Case(sample=sample,random=random,mutation=mutation,phase=phase))
  visited=set()
  for c in cases:
   initial=oracle.fixture(c);expected,calls,snapshots=oracle.reference(initial,c);pair=[]
   for body in(truth,words):
    m=oracle.BurstOracle(body,initial,c).run();assert(oracle.public(m.memory),m.calls,m.snapshots)==(oracle.public(expected),calls,snapshots),c;pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1])
  missing=set(range(source.ENTRY,source.ENTRY+204,4))-visited;assert missing==set(range(0x151D56D4,0x151D56E4,4)),list(map(hex,missing))
  print('GUEST',len(cases),len(visited),flush=True)
  self.receipt['guest']=dict(cases=len(cases),covered_words=len(visited),unreachable_original_words=list(map(hex,sorted(missing))),raw_words_equal_retail=True,live_argument_homes_reloaded=True,hardware_or_arbitrary_FCSR_claimed=False)

 def test_03_original_caller_and_connected_RNGs(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  caller_count=0;caller_visited=set()
  for phase,kind,mutation,result in itertools.product((0,8),(0,127,128,255),(0,1,2,4),(0,0xFFFFFFFF)):
   c=oracle.Case(phase=phase,kind=kind,mutation=mutation,result=result);pair=[]
   for body in(truth,words):
    m,(expected,calls,snapshots)=oracle.caller_machine(rom,body,c)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Missing original caller boundary')
    assert(oracle.public(m.memory),m.calls,m.snapshots,m.r[2])==(oracle.public(expected),calls,snapshots,1),c
    pair.append(m);caller_visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1]);caller_count+=1
  assert set(range(oracle.WINDOW,oracle.WINDOW+52,4))<=caller_visited

  visited=set();count=0
  for seed,phase,mutation,result in itertools.product(oracle.SEEDS,(0,8),(0,1),(0,0xFFFFFFFF)):
   c=oracle.Case(seed=seed,phase=phase,mutation=mutation,result=result);initial=oracle.connected_fixture(c);expected,calls,snapshots=oracle.connected_reference(initial,c);pair=[]
   for body in(truth,words,raw):
    m=oracle.ConnectedOracle(body,initial,c,rom).run();assert(oracle.public(m.memory),m.calls,m.snapshots)==(oracle.public(expected),calls,snapshots),c;pair.append(m);visited.update(m.visits)
   assert all(oracle.full_state(m)==oracle.full_state(pair[0])for m in pair);count+=1
  helpers=[dict(entry=hex(entry),literal_words=n,covered_words=len(set(range(entry,entry+4*n,4))&visited))for entry,pos,n in oracle.HELPERS];assert [x['covered_words']for x in helpers]==[25,18]
  self.receipt['integration']=dict(caller_cases=caller_count,caller_words=13,covered_caller_words=13,result_discarded=True,connected_cases=count,helpers=helpers,three_effect_helpers_are_ABI_hooks=True,seed_state_and_call_order_checked=True,complete_parent_or_gameplay_claimed=False)

 def test_04_native32_defined_inputs_and_controls(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  body=source.SELECTED
  controls=semantic_controls()
  text=source.HEADERS+body+'\n'
  for name,wrong in controls.items():assert wrong!=body;text+=wrong.replace(source.FUNCTION,'negative_'+name)+'\n'
  rows=[]
  for sample,random,kind,mode,mutation in itertools.product((0,0x80000000,1,0x3E800000,0x3F000000,0x3F7FFFFF,0x3F800000,0xBF800000,0xC0400000),(0,55,56,57,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,127,128,255),(0,1,0x80000000,0xFFFFFFFF),(0,1)):
   c=oracle.Case(sample=sample,random=random,kind=kind,mode=mode,mutation=mutation);m,calls,snapshots=oracle.reference(oracle.fixture(c),c)
   values=[sample,random,kind,mode,mutation,0,calls[-1][1][1],calls[-1][1][3],oracle.read(m,oracle.MARK),*snapshots[0][0],*snapshots[1][0],*snapshots[-1][0],*[z[1]for z in snapshots]];assert len(values)==23
   rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
  text+='static const u32 vectors[][23]={\n'+',\n'.join(rows)+'\n};\n'
  text+=r'''
  typedef struct {u8 prefix[16];f32 xyz[3];u8 suffix[16];} Point;
  typedef void(*Fn)(f32*,u8,s32);
  static Point point,want;static const u32*v;static u32 number,error,marker;
  static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
  static u32 word(const void*p){u32 b;copy(&b,p,4);return b;}
  static void set(f32*p,u32 b){copy(p,&b,4);}
  static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
  static void stage(u32 expected,f32*p){u32 i,offset=0;
   if(number!=expected||marker!=v[18+expected])error=1;
   if(p){offset=expected==0?9:expected==1?12:15;
    if(p!=point.xyz)error=2;
    for(i=0;i<3;i++)if(word(p+i)!=v[offset+i])error=3;
   }
   marker=(marker*33)^expected^0x1234;number++;
  }
  __attribute__((noinline,noclone)) void func_151D5514(f32*p,u8 kind,s32 mode){
   if(kind!=v[2]||(u32)mode!=v[3])error=4;stage(0,p);if(v[4])set(p,0xC1200000);
  }
  __attribute__((noinline,noclone)) void func_151D3FF4(f32*p,u8 kind,s32 mode){
   if(kind!=v[2]||(u32)mode!=v[3])error=5;stage(1,p);if(v[4])set(p+1,0x41180000);
  }
  __attribute__((noinline,noclone)) f32 func_150ADA68(void){f32 sample;stage(2,0);set(&sample,v[0]);return sample;}
  __attribute__((noinline,noclone)) s32 func_150ADA20(void){stage(3,0);return(s32)v[1];}
  __attribute__((noinline,noclone)) u8*func_151541B8(f32*p,f32 width,f32 coefficient,f32 amount,f32 zero,u8 kind,s32 mode){
   if(word(&width)!=v[6]||word(&coefficient)!=0x3FD20C49||word(&amount)!=v[7]||word(&zero)!=0||kind!=v[2]||(u32)mode!=v[3])error=6;
   stage(4,p);return(u8*)&point;
  }
  static int check(Fn fn){u32 n,i;for(n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){
   v=vectors[n];number=error=0;marker=0xA5B2BFCC;
   for(i=0;i<sizeof(point);i++)((u8*)&point)[i]=(u8)((i-16)*13+0xA5);
   set(point.xyz,0x3FC00000);set(point.xyz+1,0xC0300000);set(point.xyz+2,0x47000001);copy(&want,&point,sizeof(point));
   for(i=0;i<3;i++)set(want.xyz+i,v[15+i]);
   fn(point.xyz,(u8)v[2],(s32)v[3]);
   if(number!=5||error||marker!=v[8]||!same(&point,&want,sizeof(point)))return 1;
   }return 0;}
  static int run(void){if(check(func_151D5648))return 10;
  '''
  for i,name in enumerate(controls):text+='if(!check(negative_'+name+'))return '+str(20+i)+';\n'
  text+='return 0;}\n'+START;(fresh/'native.c').write_text(text);reports={}
  for opt in('-O0','-O2','-O3'):
   binary=fresh/('native'+opt);p=subprocess.run(native_command(opt)+[str(fresh/'native.c'),'-o',str(binary)],cwd=r,capture_output=True,text=True);assert p.returncode==0 and not(p.stdout+p.stderr),(opt,p.returncode,p.stdout,p.stderr)
   run=subprocess.run([str(binary)],capture_output=True,text=True);reports[opt]=dict(exit=run.returncode,diagnostics=run.stdout+run.stderr);assert run.returncode==0 and not(run.stdout+run.stderr),(opt,reports[opt])
  self.receipt['native']=dict(cases_per_profile=len(rows),optimizations=reports,controls=len(controls),SDK=True,pointers32=True,trapping_UBSan=True,precomputed_expected_bytes=True,valid_backing_and_canaries=True,guest_home_mutations_excluded=True)

 def test_05_direct_and_caller_fault_prefixes(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  count=delay=0
  for parent,c in itertools.product((False,True),(oracle.Case(),oracle.Case(mutation=7,random=0xFFFFFFFF))):
   def machine(body):return oracle.caller_machine(rom,body,c)[0]if parent else oracle.BurstOracle(body,oracle.fixture(c),c)
   m=machine(truth)
   try:m.run()
   except oracle.WindowBoundary:pass
   for cut in range(m.all_accesses):
    pair=[]
    for body in(truth,words):
     model=machine(body);model.cut=cut
     try:model.run()
     except faults.AccessBoundary:pass
     else:raise AssertionError(('Unfired access cut',cut))
     pair.append(model)
    assert oracle.full_state(pair[0])==oracle.full_state(pair[1])and(pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses)==(pair[1].current_pc,pair[1].delay_of,cut)
    count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=count,delay_slot_cuts=delay,complete_RAM_registers_trace_PC_and_delay=True,portable_C_fault_claimed=False)

 def test_06_raw_rejections_padder_and_three_GNU_layouts(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  payload,rs=source.payload(o/'selected.o');rejects=0
  for at in range(0,len(payload),4):
   bad=bytearray(payload);bad[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(payload,bad)
   rejects+=1
  assert source.normalized_payload(payload,rs)==(payload,rs)and source.NEW_GUARDS==[]
  p=fresh/'padded.s';p.write_text(source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=o/'proposed-guards.csv'))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
  assert p.with_suffix('.o').read_bytes()==(o/'qualified-padded.o').read_bytes();count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   defs=oracle.symbols()if j==0 else {name:(entry&0xF0000000)+0x3007FFC+index*0x10004 for index,name in enumerate(oracle.symbols())}
   paths=(o/'original-func_151D5648.o',o/'make-shadow/src/game/generated_200930.c.o',o/'qualified-padded.o',o/'selected.o');images=[linked(path,entry,'rebase-%d-%d'%(j,k),defs)for k,path in enumerate(paths)];assert images[0]==images[1]==images[2]==images[3]
   for random,kind,phase,mutation in itertools.product((0,0x80000000,0xFFFFFFFF),(0,255),(0,8),(0,7)):
    c=oracle.Case(random=random,kind=kind,phase=phase,mutation=mutation);initial=oracle.fixture(c);expected,calls,snapshots=oracle.reference(initial,c,defs);pair=[]
    for code in images:
     m=oracle.BurstOracle(code,initial,c,entry=entry,s=defs).run();assert(oracle.public(m.memory),m.calls,m.snapshots)==(oracle.public(expected),calls,snapshots);pair.append(m)
    assert all(oracle.full_state(m)==oracle.full_state(pair[0])for m in pair);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,original_Make_padded_and_raw_words_equal=True,guards=0,all_five_call_bindings_rebased=True)

 def test_07_compiled_semantic_controls(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  evidence={}
  for name,body in semantic_controls().items():
   assert body!=source.SELECTED;obj,diag=source.compile_owner(r,fresh,source.HEADERS+body,'negative-'+name);assert not diag;code=linked(obj,source.ENTRY,'negative-link-'+name)
   for sample,random,mutation in itertools.product((0,0x3F000000),(0,55,56,0xFFFFFFFF),(0,1)):
    c=oracle.Case(sample=sample,random=random,mutation=mutation);initial=oracle.fixture(c);m=oracle.BurstOracle(code,initial,c);m.strict_calls=False;m.run();expected,calls,snapshots=oracle.reference(initial,c)
    if(oracle.public(m.memory),m.calls,m.snapshots)!=(oracle.public(expected),calls,snapshots):evidence[name]=dict(sample=hex(sample),random=hex(random),mutation=mutation);break
   assert name in evidence,name
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,call_order_and_argument_bits_observed=True)

 def test_08_strict_whole_image_and_unchanged_guards(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  v=source.check_inputs(r,o,self.installed);source.verify_prepared(o);before=v['conker/build/conker.us.elf'];truth_bytes=rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth_bytes)
  source.check_image(before,(o/'first-linked.elf').read_bytes(),truth_bytes);at=source.elf_slot_offset(before,source.ENTRY,204);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  assert sum(a!=b for a,b in zip(before,expected))==157
  assert sum(a!=b for a,b in zip(before[at:at+204],expected[at:at+204]))==156
  positions=[20,at-4,at+204,source.elf_slot_offset(before,oracle.SEED,8),source.elf_slot_offset(before,oracle.SCALE,4),source.elf_slot_offset(before,oracle.WINDOW,52)]
  positions+=list(range(at,at+204))+list(range(named[source.FUNCTION][0],named[source.FUNCTION][0]+16))
  for entry,pos,n in oracle.HELPERS:positions.append(source.elf_slot_offset(before,entry,4))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth_bytes)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth_bytes)
  manifest=v['conker/retail_word_patches.us.csv'];assert source.guard_manifest(manifest)==manifest==(o/'proposed-guards.csv').read_bytes()
  with self.assertRaises(ValueError):source.guard_manifest(manifest+b'\n')
  assert not[row for row in csv.DictReader(io.StringIO(manifest.decode()))if row['function']==source.FUNCTION]
  self.receipt['image']=dict(changed_bytes=157,code_bytes=156,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=len(positions)+1,all_target_bytes_and_symbol_record_guarded=True,guard_manifest_unchanged=True,new_guards=0,protected_Game_bytes=189088,focused_inputs=len(v))
