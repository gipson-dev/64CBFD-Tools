"""Owner sine scale: helper integration, return ABI, guards and full image."""
from pathlib import Path
from dataclasses import replace
import csv,io,itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_owner_sine_scale_match as source
from tools.tests import game_owner_sine_scale_oracle as oracle
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
 return dict(wrong_step=body.replace('D_800AA458 * D_800BE9A4','D_800AA458 + D_800BE9A4'),inclusive_wrap=body.replace('*state > period','*state >= period'),single_wrap=body.replace('while (*state > period)','if (*state > period)'),wrong_output=body.replace('(owner + 0x18)','(owner + 0x20)'),missing_base=body.replace('(result * (D_800AA45C * state[1])) + state[1]','(result * (D_800AA45C * state[1]))'),wrong_gain=body.replace('D_800AA45C * state[1]','1.0f * state[1]'),constant_result=body.replace('return func_15133894(owner);','func_15133894(owner);\n    return 1;'),early_base=body.replace('f32 result;','f32 result;\n    f32 savedBase;').replace('result = sinf(*state);','savedBase = state[1];\n    result = sinf(*state);').replace('(result * (D_800AA45C * state[1])) + state[1]','(result * (D_800AA45C * savedBase)) + savedBase'))

def link_object(obj,entry,label,fresh,symbols=None):
 defs=symbols or oracle.symbols();text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=fresh/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

class OwnerSineScaleTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM))
  cls.words=link_object(cls.out/'qualified-padded.o',source.ENTRY,'qualified',cls.fresh);cls.raw=link_object(cls.out/'selected.o',source.ENTRY,'selected',cls.fresh)
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def linked(self,obj,entry,label,symbols=None):return link_object(obj,entry,label,self.fresh,symbols)
 def test_01_owner_actual_Make_and_callback_ABI(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  assert truth==words and len(raw)==47 and len(truth)==48 and truth[0]==0x27BDFFD8
  assert rom[source.ROM+192:source.ROM+204]==bytes(12)
  assert source.normalized_payload(*source.payload(o/'selected.o'))==source.payload(o/'original-func_151B6254.o')
  for label in('before','after'):
   obj,diag=source.compile_owner(r,fresh,(o/(label+'-owner.c')).read_text(),'fresh-'+label);assert not diag;assert source.same_functions(obj,o/(label+'-owner.o'))==2
  assert source.same_functions(o/'before-owner.o',o/'after-owner.o',(source.FUNCTION,))==1
  assert source.normalized_pools(o/'before-owner.o')==source.normalized_pools(o/'after-owner.o')
  assert source.same_functions(o/'before-padded.o',o/'qualified-padded.o',(source.FUNCTION,))==1
  assert source.recovered_owner(self.values[source.SOURCE].decode()).encode()==(o/'proposed-owner.c').read_bytes()
  commands=json.loads((o/'Make-commands.json').read_text());assert len(commands)==3 and commands[0][0]=='../ido/ido5.3_recomp/cc'and '-O2'in commands[0]and '-g3'in commands[0]
  assert not(o/'actual-Make-diagnostics.txt').read_bytes()
  assert(o/'make-shadow/src/game/generated_1E34C0.c.o').read_bytes()==(o/'qualified-padded.o').read_bytes()
  ws=struct.unpack('>%dI'%(len(rom)//4),rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);assert jal not in ws
  assert[i*4 for i,w in enumerate(ws)if w==source.ENTRY]==[0x22E388]
  assert rom[0x24EF14:0x24EF20]==bytes.fromhex('40c90fdb3f0e56053d79db24')
  assert len(source.BINDINGS)==10 and source.BINDINGS[116]==[('R_MIPS_26','sinf')]and source.BINDINGS[164]==[('R_MIPS_26','func_15133894')]
  before=self.values['conker/build/conker.us.elf']
  for entry,pos,n in oracle.HELPERS:
   at=source.elf_slot_offset(before,entry,n*4);assert before[at:at+n*4]==rom[pos:pos+n*4]
  assert b'#pragma GLOBAL_ASM("asm/nonmatchings/generated_15F680/func_15133894.s")'in self.values['conker/src/game/generated_15F680.c']
  if self.installed:source.audit(r,o)
  self.receipt['owner']=dict(body_words=48,slot_words=51,alignment_words=3,compiler_words=47,frame=40,bindings=10,guards=5,neighbors=1,compact_functions=2,Make_commands=3,callback_slot=6,callback_table_bytes=100,forwarded_helper_return=True)

 def test_02_guest_phase_boundaries_and_post_call_reloads(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  angles=(0,0x80000000,0xBF800000,0xC1A00000,0x3F800000,0x40C90FDA,0x40C90FDB,0x40C90FDC,0x41490FDB,0x41C90FDB,0x7FC12345)
  cases=[oracle.Case(angle=a,tick=t,base=b,phase=p,mode=m,result=z)for a,t,b,p,m,z in itertools.product(angles,(0,0x3F800000,0x40800000),(0,0x40000000,0xC0300000),(0,8),(0,1,2,4),(0,0xFFFFFFFF))]
  visited=set()
  for c in cases:
   initial=oracle.fixture(c);expected,calls,result,observations=oracle.reference(initial,c);pair=[]
   for body in(truth,words):
    m=oracle.SineScaleOracle(body,initial,c).run();assert(oracle.public(m.memory),m.calls,m.r[2],m.snapshots)==(oracle.public(expected),calls,result,observations),c;pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1])
   m=oracle.SineScaleOracle(raw,initial,c).run();assert(oracle.public(m.memory),m.calls,m.r[2],m.snapshots)==(oracle.public(expected),calls,result,observations),c
  missing=set(range(source.ENTRY,source.ENTRY+192,4))-visited;assert not missing,list(map(hex,missing))
  print('GUEST',len(cases),len(visited),flush=True)
  self.receipt['guest']=dict(cases=len(cases),covered_words=len(visited),raw_public_equal=True,post_call_base_gain_and_owner_reloads=True,arbitrary_FCSR_hardware_or_NaN_payload_claimed=False)

 def test_03_original_callback_and_connected_helpers(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  caller_cases=0;caller_visited=set()
  for phase,selector,gate,result in itertools.product((0,8),(0,6),(0,5),(0,1,0xFFFFFFFF,0x80)):
   c=oracle.Case(phase=phase,result=result);pair=[]
   for body in(truth,words):
    m,initial=oracle.caller_machine(rom,body,c,selector,gate)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Caller window did not terminate at its declared end')
    expected,calls,value,observations=oracle.reference(initial,c)if selector else(initial,[],0,[])
    if selector:calls=[(source.ENTRY,(c.owner,))]+calls
    assert oracle.public(m.memory)==oracle.public(expected)and m.calls==calls and m.snapshots==observations
    assert m.r[5]==(1 if selector and result==0 else gate)
    pair.append(m);caller_visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1]);caller_cases+=1
  assert set(range(oracle.WINDOW,oracle.END,4))<=caller_visited
  print('CALLER',caller_cases,flush=True)
  visited=set();count=0;results=set();angles=(0,1,0x3F000000,0x3F800000,0x40C90FDB,0xC1A00000,0xE0AD78EC,0x7FC12345)
  for velocity,flags,selector,geometry,attachment,event,phase in itertools.product((0xC0000000,0,0x40000000),(0,1),(0,1),(0,1),(-1,0x40,0x60),(0,7,0x80),(0,8)):
   c=oracle.ConnectedCase(angle=angles[count%len(angles)],tick=0 if count%4==0 else 0x3F800000,velocity=velocity,flags=flags,selector=selector,geometry=geometry,attachment=attachment,event_result=event,phase=phase)
   initial=oracle.connected_fixture(c);expected,calls,result,snapshots,packets=oracle.connected_reference(initial,c)
   pair=[]
   for body in(truth,words):
    m=oracle.ConnectedOracle(body,initial,c,rom).run();assert(oracle.public(m.memory),m.calls,m.r[2],m.snapshots,m.geometry_packets)==(oracle.public(expected),calls,result,snapshots,packets),c;pair.append(m);visited.update(m.visits)
   assert oracle.full_state(pair[0])==oracle.full_state(pair[1])and pair[0].geometry_packets==pair[1].geometry_packets
   m=oracle.ConnectedOracle(raw,initial,c,rom).run();assert(oracle.public(m.memory),m.calls,m.r[2],m.snapshots,m.geometry_packets)==(oracle.public(expected),calls,result,snapshots,packets),c
   results.add(m.r[2]);count+=1
  for a,value in oracle.trig.GLOBALS.items():
   before=(o/'before-conker_build_conker.us.elf').read_bytes();at=source.elf_slot_offset(before,a,4);assert before[at:at+4]==struct.pack('>I',value),hex(a)
  report=dict(cases=count,helpers=[dict(entry=hex(entry),literal_words=n,covered_words=len(set(range(entry,entry+4*n,4))&visited))for entry,pos,n in oracle.HELPERS],return_values=sorted(results),geometry_and_event_boundary_hooks=True,full_gameplay_claimed=False)
  assert [h['covered_words']for h in report['helpers']]==[97,80,53]
  self.receipt['integration']=dict(caller_cases=caller_cases,caller_words=13,covered_caller_words=13,slot=6,connected_cases=count,helpers=report['helpers'],return_values=report['return_values'],geometry_and_event_boundary_hooks=True,complete_parent_or_gameplay_claimed=False)

 def test_04_native32_defined_inputs_and_controls(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  body=source.SELECTED
  controls=semantic_controls()
  text=source.HEADERS+body+'\n'
  for name,wrong in controls.items():assert wrong!=body;text+=wrong.replace(source.FUNCTION,'negative_'+name)+'\n'
  rows=[]
  for angle,tick,base,mode,sample,result in itertools.product((0,0x80000000,0xBF800000,0xC1A00000,0x3F800000,0x40C90FDA,0x40C90FDB,0x40C90FDC,0x41490FDB,0x41C90FDB),(0,0x40800000),(0,0x40000000,0xC0300000),(0,1,4,5),(0,0x3F800000,0xBF000000),(0,1,0xFFFFFFFF)):
   c=oracle.Case(angle=angle,tick=tick,base=base,mode=mode,sample=sample,result=result);initial=oracle.fixture(c);m,calls,answer,observations=oracle.reference(initial,c)
   values=[angle,tick,base,sample,result,mode,oracle.read(m,c.owner+0x170),oracle.read(m,c.owner+0x174),oracle.read(m,c.owner+0x18),oracle.read(m,c.owner+0x1C),oracle.read(m,oracle.symbols()['D_800AA45C']),oracle.read(m,oracle.symbols()['D_800BE9A4']),calls[0][1][0]]
   rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
  text+='static const u32 vectors[][13]={\n'+',\n'.join(rows)+'\n};\n'
  text+=r'''
  typedef struct {u8 prefix[0x18];f32 x,y;u8 gap[0x150];f32 angle,base;u8 suffix[0x88];} Owner;
  typedef char Layout[(sizeof(Owner)==0x200&&__builtin_offsetof(Owner,angle)==0x170&&__builtin_offsetof(Owner,base)==0x174)?1:-1];
  typedef s32(*Fn)(u8*);
  static Owner owner,want;static const u32 *v;static u32 number,error;
  f32 D_800AA454,D_800AA458,D_800AA45C,D_800BE9A4;
  static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
  static u32 word(const void*p){u32 b;copy(&b,p,4);return b;}
  static void set(f32*p,u32 b){copy(p,&b,4);}
  static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
  __attribute__((noinline,noclone)) f32 sinf(f32 angle){f32 result;
   if(number!=0||word(&angle)!=v[12])error=1;number++;
   if(v[5]&1){set(&owner.base,0xC0300000);set(&D_800AA45C,0x3E000001);}
   set(&result,v[3]);return result;
  }
  __attribute__((noinline,noclone)) s32 func_15133894(u8*p){
   if(number!=1||p!=(u8*)&owner||word(&owner.x)!=v[8]||word(&owner.y)!=v[9])error=2;number++;
   if(v[5]&4){set(&owner.angle,0xC0A00000);set(&D_800BE9A4,0x3F000000);}
   return (s32)v[4];
  }
  static int check(Fn fn){u32 n,i;for(n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){
   v=vectors[n];number=error=0;for(i=0;i<sizeof(owner);i++)((u8*)&owner)[i]=(u8)(i*13+0xA5);
   set(&owner.angle,v[0]);set(&owner.base,v[2]);set(&D_800BE9A4,v[1]);set(&D_800AA454,0x40C90FDB);set(&D_800AA458,0x3F0E5605);set(&D_800AA45C,0x3D79DB24);
   copy(&want,&owner,sizeof(owner));set(&want.angle,v[6]);set(&want.base,v[7]);set(&want.x,v[8]);set(&want.y,v[9]);
   if((u32)fn((u8*)&owner)!=v[4]||number!=2||error||!same(&owner,&want,sizeof(owner))||word(&D_800AA45C)!=v[10]||word(&D_800BE9A4)!=v[11]||word(&D_800AA454)!=0x40C90FDB||word(&D_800AA458)!=0x3F0E5605)return 1;
   }return 0;}
  static int run(void){if(check(func_151B6254))return 10;
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
  for parent,c in itertools.product((False,True),(oracle.Case(),oracle.Case(angle=0x41C90FDB,mode=3,result=0))):
   def machine(body):return oracle.caller_machine(rom,body,c)[0]if parent else oracle.SineScaleOracle(body,oracle.fixture(c),c)
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
  assert normalized[:4]==payload[:4]and normalized[4:12]==payload[8:16]and normalized[12:16]==payload[4:8]and normalized[16:164]==payload[16:164]
  assert normalized[164:168]==payload[168:172]and normalized[168:172]==payload[164:168]and normalized[172:176]==bytes(4)and normalized[176:]==payload[172:]
  assert bindings[4]==rs[8]and bindings[8]==rs[12]and bindings[168]==rs[164]
  for row in source.NEW_GUARDS:
   at=int(row['offset'],0)
   for variant in('word','binding'):
    altered=[dict(v)for v in source.NEW_GUARDS];item=next(v for v in altered if v['offset']==row['offset'])
    item['expected'if variant=='word'else'expected_relocations']=('0x%08X'%(int(item['expected'],0)^1))if variant=='word'else('-'if item['expected_relocations']!='-'else'R_MIPS_26:sinf')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,list(altered[0]),lineterminator='\n');writer.writeheader();writer.writerows(altered);manifest=fresh/('bad-%d-%s.csv'%(at,variant));manifest.write_text(stream.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=manifest)
  p=fresh/'padded.s';p.write_text(source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=o/'proposed-guards.csv'))
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
  assert p.with_suffix('.o').read_bytes()==(o/'qualified-padded.o').read_bytes();count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   defs=oracle.symbols()if j==0 else dict(D_800AA454=(0x800D8004,0x80107FFC)[j-1],D_800AA458=(0x800D7FFC,0x80108004)[j-1],D_800AA45C=(0x800E8004,0x80117FFC)[j-1],D_800BE9A4=(0x800F7FFC,0x80128004)[j-1],sinf=(entry&0xF0000000)+0x3030004,func_15133894=(entry&0xF0000000)+0x3048004)
   paths=(o/'original-func_151B6254.o',o/'make-shadow/src/game/generated_1E34C0.c.o',o/'qualified-padded.o');images=[linked(path,entry,'rebase-%d-%d'%(j,k),defs)for k,path in enumerate(paths)];assert images[0]==images[1]==images[2]
   unguarded=linked(o/'selected.o',entry,'rebase-raw-%d'%j,defs)
   for angle,phase,mode in itertools.product((0,0xBF800000,0x40C90FDB,0x41C90FDB),(0,8),(0,1)):
    c=oracle.Case(angle=angle,phase=phase,mode=mode);initial=oracle.fixture(c,defs);expected,calls,value,snapshots=oracle.reference(initial,c,defs);pair=[]
    for code in images:
     m=oracle.SineScaleOracle(code,initial,c,entry=entry,s=defs).run();assert(oracle.public(m.memory),m.calls,m.r[2],m.snapshots)==(oracle.public(expected),calls,value,snapshots);pair.append(m)
    assert all(oracle.full_state(m)==oracle.full_state(pair[0])for m in pair)
    m=oracle.SineScaleOracle(unguarded,initial,c,entry=entry,s=defs).run();assert(oracle.public(m.memory),m.calls,m.r[2],m.snapshots)==(oracle.public(expected),calls,value,snapshots);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,padder_guard_rejections=10,original_Make_and_padded_words_equal=True,raw_public_semantics_equal=True,guards=5,retail_nop_and_alignment_retained=True,signed_low_address_carries=True)

 def test_07_compiled_semantic_and_return_controls(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  evidence={};caller_proof=False
  for name,body in semantic_controls().items():
   assert body!=source.SELECTED;obj,diag=source.compile_owner(r,fresh,source.HEADERS+body,'negative-'+name);assert not diag;code=linked(obj,source.ENTRY,'negative-link-'+name)
   for angle,mode in itertools.product((0,0x40C90FDB,0x41C90FDB),(0,1)):
    c=oracle.Case(angle=angle,tick=0,mode=mode,result=0);initial=oracle.fixture(c);m=oracle.SineScaleOracle(code,initial,c).run();expected,calls,result,observations=oracle.reference(initial,c)
    if(oracle.public(m.memory),m.calls,m.r[2],m.snapshots)!=(oracle.public(expected),calls,result,observations):evidence[name]=dict(angle=hex(angle),mode=mode);break
   assert name in evidence,name
   if name=='constant_result':
    m,initial=oracle.caller_machine(rom,code,oracle.Case(result=0))
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Negative caller did not finish')
    assert m.r[5]==0 and 0x15132274 not in m.visits
    good,_=oracle.caller_machine(rom,words,oracle.Case(result=0))
    try:good.run()
    except oracle.WindowBoundary:pass
    assert good.r[5]==1 and 0x15132274 in good.visits;caller_proof=True
  assert caller_proof
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True,original_caller_observes_forwarded_failure=True)

 def test_08_strict_whole_image_and_guard_prefix(self):
  r=ROOT;o=self.out;fresh=self.fresh;rom=self.rom;truth=self.truth;words=self.words;raw=self.raw;linked=self.linked
  v=source.check_inputs(r,o,self.installed);source.verify_prepared(o);before=v['conker/build/conker.us.elf'];truth_bytes=rom[source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth_bytes)
  source.check_image(before,(o/'first-linked.elf').read_bytes(),truth_bytes);at=source.elf_slot_offset(before,source.ENTRY,204);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  assert sum(a!=b for a,b in zip(before,expected))==200
  assert sum(a!=b for a,b in zip(before[at:at+204],expected[at:at+204]))==150
  positions=[20,at,at+8,at+192,at+204,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,0x800AA454,12),source.elf_slot_offset(before,oracle.TABLE,100),source.elf_slot_offset(before,oracle.WINDOW,52)]
  positions+=list(range(2845476,2845508))+list(range(2961428,2961460))+list(range(3116991,3117023))+list(range(3212569,3212591))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth_bytes)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth_bytes)
  proposed=source.guard_manifest(v['conker/retail_word_patches.us.csv']);assert proposed==(o/'proposed-guards.csv').read_bytes()and proposed.startswith(v['conker/retail_word_patches.us.csv'])
  assert len(list(csv.DictReader(io.StringIO(proposed.decode()))))-len(list(csv.DictReader(io.StringIO(v['conker/retail_word_patches.us.csv'].decode()))))==5
  self.receipt['image']=dict(changed_bytes=200,code_bytes=150,extent_bytes=1,metadata_bytes=49,exclusions=0,corruptions=len(positions)+1,all_metadata_record_bytes_and_strings_guarded=True,inherited_guard_prefix_unchanged=True,new_guards=5,protected_Game_bytes=189088,focused_inputs=len(v))
