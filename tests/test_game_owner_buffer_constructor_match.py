"""Owner payload-buffer construction: direct C, service ordering, native32 and image gates."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_owner_buffer_constructor_match as source
from tools.tests import game_owner_buffer_constructor_oracle as oracle
from tools.tests.game_owner_buffer_constructor_oracle import Case,BufferOracle,fixture,reference,public
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(identity=b.replace('[0x3B]','[0x3A]'),
  notify=b.replace('&notice, 14','&notice, 13'),
  size=b.replace('extraBytes + 0x300','extraBytes + 0x304'),
  priority=b.replace('1, priority, 1','1, 0, 1'),
  copy=b.replace('payload, 12','payload, 11'),
  cursor=b.replace('created + 0x30;','created + 0x34;'),
  zero=b.replace('0x2D0','0x2CC'),
  selector=b.replace('created[0x2C]','created[0x2D]'),
  result=b.replace('    return created;','    return NULL;'))

def native_harness():
 t=source.HEADERS+'\n'.join(b.replace(source.FUNCTION,'test_'+n)for n,b in dict(selected=source.SELECTED,**controls()).items())
 t+=r'''
typedef void *(*Fn)(struct185 *,s32,u8,s32);
static union {u32 align;u8 bytes[1024];} storage;
static struct185 payload;static u8 owner[128];
static int calls,bad,outcome,mutation;static s32 extra,context;static u8 priority,selector;
void func_15191B8C(s32 address,u8 code){
 OwnerBufferNotice1BA1D0 *p=(void*)address;
 if(calls++!=0||code!=14||p->owner!=owner||p->owner_id!=owner[59])bad=1;
 if(mutation){payload.unk8^=0x40;owner[59]^=0x55;}
}
void *func_15167A68(s32 kind,s32 ctx,s32 size,s32 direction,u8 prio,u8 flag){
 if(calls++!=1||kind!=32||ctx!=context||size!=extra+0x300||direction!=1||prio!=priority||flag!=1)bad=2;
 if(mutation)payload.unk9^=0x20;
 return outcome?storage.bytes:NULL;
}
void *memcpy(void *dst,const void *src,u32 n){
 u32 i;if(calls++!=2||dst!=storage.bytes+16||src!=&payload||n!=12)bad=3;
 if(n>16)return dst;for(i=0;i<n;i++)((u8*)dst)[i]=((const u8*)src)[i];return dst;
}
void bzero(void *dst,int n){
 int i;if(calls++!=3||dst!=storage.bytes+48||n!=720)bad=4;
 if(n<0||n>768)return;for(i=0;i<n;i++)((u8*)dst)[i]=0;
}
u8 func_151D8E20(void){if(calls++!=4)bad=5;return selector;}
static s32 sizes[]={-768,-1,0,1,2147482879};
static int check(Fn fn){int byte,j;u32 i;u8 *created;u8 *p=(u8*)&payload;
 if(sizeof(void*)!=4||sizeof(payload)!=12||sizeof(OwnerBufferNotice1BA1D0)!=12)return 90;
 for(byte=0;byte<256;byte++)for(j=0;j<5;j++)for(outcome=0;outcome<2;outcome++)for(mutation=0;mutation<2;mutation++){
  for(i=0;i<sizeof(owner);i++)owner[i]=0x5A;for(i=0;i<sizeof(storage.bytes);i++)storage.bytes[i]=0xA5;
  for(i=0;i<sizeof(payload);i++)p[i]=(u8)(i*17+byte);
  payload.unk0=(struct127*)owner;owner[59]=(u8)byte;extra=sizes[j];context=(byte&1)?-1:1;priority=(u8)byte;selector=(u8)(255-byte);calls=bad=0;
  created=fn(&payload,extra,priority,context);
  if(bad||calls!=(outcome?5:2)||created!=(outcome?storage.bytes:NULL))return 1;
  if(outcome){
   for(i=0;i<12;i++)if(storage.bytes[16+i]!=p[i])return 2;
   if(*(u32*)(storage.bytes+28)||*(u32*)(storage.bytes+32))return 3;
   if(*(u8**)(storage.bytes+36)!=storage.bytes+48||*(u8**)(storage.bytes+40)!=storage.bytes+768||storage.bytes[44]!=selector)return 4;
   for(i=48;i<768;i++)if(storage.bytes[i])return 5;
  }
  for(i=0;i<sizeof(storage.bytes);i++)if((!outcome||i<16||(i>=45&&i<48)||i>=768)&&storage.bytes[i]!=0xA5)return 6;
  for(i=0;i<sizeof(owner);i++)if(i!=59&&owner[i]!=0x5A)return 7;
 }return 0;
}
static int run(void){if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class OwnerBufferConstructorTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
  cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>52I',cls.rom,source.ROM));cls.words=cls.linked(cls.out/'qualified-padded.o',source.ENTRY,'qualified');cls.raw=cls.linked(cls.out/'selected.o',source.ENTRY,'selected')
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 @classmethod
 def linked(cls,obj,entry,label,s=None):
  defs=oracle.symbols()if s is None else s;text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION];assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,defs);assert not unknown;p=cls.fresh/label
  p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in defs.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
 def compare(self,c=Case(),images=None,entry=None,s=None,copy=False):
  initial=fixture(c);wanted=reference(initial,c,s);pair=[];connected={}
  if copy:connected.update(zip(range(oracle.COPY,oracle.COPY+44,4),struct.unpack_from('>11I',self.rom,0x22EC0)))
  for words in images or(self.truth,self.words,self.raw):
   m=BufferOracle(words,initial,c,entry=entry,s=s,connected=connected).run()
   self.assertEqual((public(m.memory),m.calls,m.r[2],m.notices,m.copies),(public(wanted[0]),wanted[1],wanted[2],[wanted[3]],[]if wanted[4]is None else[wanted[4]]),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(oracle.state(pair[0]),oracle.state(m))
  return pair[0]

 def test_01_owner_actual_Make_and_ABI(self):
  self.assertEqual(self.truth,self.words);self.assertEqual(self.truth,self.raw);self.assertEqual(self.raw[0],0x27BDFFC8)
  self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/'original-func_15190770.o'))
  for label in ('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),4);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),61)
  for a,b in (('before-owner.o','after-owner.o'),('before-padded.o','qualified-padded.o')):self.assertEqual(source.same_functions(self.out/a,self.out/b,(source.FUNCTION,)),60)
  self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual(source.check_owner_diagnostics((self.out/'actual-Make-diagnostics.txt').read_text()),4);self.assertFalse(source.NEW_GUARDS)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
  self.assertEqual([4*i for i,w in enumerate(ws)if w==jal],[0x3F64C,0x54C64,0x1BEE00,0x1D8DB8]);self.assertNotIn(source.ENTRY,ws)
  self.assertIn('func_15190770((struct185 *)payload, 0, record[0xC], record[1]);',(self.out/'proposed-owner.c').read_text())
  proof=json.loads((self.out/'caller-declaration-proof.json').read_text());self.assertTrue(proof['all_object_bytes_unchanged']);self.assertEqual(proof['same_compact_functions'],2);self.assertEqual(len(proof['actual_Make_commands']),3)
  self.assertEqual((ROOT/source.OTHER_OBJECT).read_bytes(),(self.out/'caller-make-shadow/src/game/done/game_3F560.c.o').read_bytes())
  self.assertEqual(source.recovered_caller(self.values[source.OTHER_SOURCE].decode()).encode(),(self.out/'proposed-caller.c').read_bytes())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=52,frame=56,bindings=5,guards=0,neighbors=60,Make_commands=3,inherited_warnings=4,new_warnings=0,callers=4,canonical_payload_type='struct185 *')

 def test_02_guest_ordered_constructor(self):
  cases=[Case(priority=i,identity=i,selector=i,seed=i)for i in range(256)]
  cases += [Case(extra=e,priority=p,context=x,outcome=a,mode=m,phase=phase)for e,p,x,a,m,phase in itertools.product((0,1,0x7FFFFD00,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,0x80000000,0xABCD00FF),(0,0xFFFFFFFF),range(2),(0,1,2,4,8,16,31),(0,8))]
  cases += [Case(payload=payload,mode=mode,outcome=result)for payload,mode,result in itertools.product((oracle.OUTPUT+4,oracle.OUTPUT+16,oracle.OUTPUT+20),(0,1,8),range(2))]
  seen=set()
  for c in cases:seen.update(self.compare(c).visits)
  self.assertEqual(len(seen),52);self.receipt['guest']=dict(cases=len(cases),covered_words=52,notification_before_allocation=True,homes_reload_after_providers=True,allocation_failure_short_circuit=True,copy_source_reloaded=True,all_priority_bytes=True,guest_wrap_and_overlap_only=True)

 def test_03_original_copy_and_callers(self):
  seen=set();count=0
  for outcome,mode,phase,priority in itertools.product(range(2),(0,1,2,4,8,16,31),(0,8),(0,1,255)):
   seen.update(self.compare(Case(outcome=outcome,mode=mode,phase=phase,priority=priority),copy=True).visits);count+=1
  self.assertTrue(set(range(oracle.COPY,oracle.COPY+44,4))<=seen)
  from tools.tests import game_actor_status_effect_oracle as status
  from tools.tests import game_linked_owner_effect_oracle as linked
  status_count=linked_count=0
  for outcome,mode,phase,byte in itertools.product(range(2),(0,1,2),(0,8),(0,128,255)):
   c=status.Case(kind=150,selector=255,allocated=bool(outcome),mode=mode,phase=phase,byte=byte);initial=status.fixture(c);wanted,calls,packets=status.reference(initial,c,real=True);pair=[]
   for target in (self.truth,self.words):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),target));body=struct.unpack_from('>51I',self.rom,0x1D8D04);m=status.StatusOracle(body,initial,c,connected=connected).run();self.assertEqual((status.public(m.memory),m.packets),(status.public(wanted),packets));pair.append(m)
   self.assertEqual((pair[0].memory,pair[0].calls,pair[0].trace),(pair[1].memory,pair[1].calls,pair[1].trace));status_count+=1
  for outcome,flags,phase,byte in itertools.product(range(2),range(2),(0,8),(0,128,255)):
   c=linked.Case(allocated=bool(outcome),flags=flags,phase=phase,byte=byte);initial=linked.fixture(c);pair=[]
   for target in (self.truth,self.words):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),target));body=struct.unpack_from('>49I',self.rom,0x1BED6C);m=linked.LinkedOracle(body,initial,c,connected=connected).run();pair.append(m)
    self.assertIn((source.ENTRY,(linked.RECORD+40,0,byte,(byte*17+3)&255)),m.calls)
   self.assertEqual((pair[0].memory,pair[0].calls,pair[0].trace),(pair[1].memory,pair[1].calls,pair[1].trace));linked_count+=1
  seen_parent=set();simple_count=script_count=0
  for outcome,mode,phase,identity,enabled in itertools.product(range(2),(0,1,8),(0,8),(0,128,255),range(2)):
   c=Case(outcome=outcome,mode=mode,phase=phase,identity=identity);initial=fixture(c);oracle.put(initial,0x800BE9F0,0 if enabled else 24);pair=[]
   for image in (self.truth,self.words):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),image));body=struct.unpack_from('>26I',self.rom,0x3F5FC)
    m=BufferOracle(body,initial,c,entry=0x1501214C,connected=connected,arguments=(oracle.OWNER,)).run();pair.append(m);seen_parent.update(m.visits)
    calls=[a for t,a in m.calls if t==source.ENTRY];self.assertEqual(len(calls),int(enabled))
    if enabled:self.assertEqual(calls[0],(oracle.STACK+phase-12,0,255,1))
   self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));simple_count+=1
  self.assertTrue(set(range(0x1501214C,0x150121B4,4))<=seen_parent)
  for outcome,phase,priority,mode in itertools.product(range(2),(0,8),(0,128,255),(0,1,8)):
   c=Case(outcome=outcome,phase=phase,priority=priority,mode=mode);initial=fixture(c);initial[oracle.STACK+phase+0x773]=priority;pair=[]
   for image in (self.truth,self.words):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),image));connected[0x150277BC]=0
    m=BufferOracle(struct.unpack_from('>3I',self.rom,0x54C60),initial,c,entry=0x150277B0,connected=connected,arguments=(oracle.PAYLOAD,0,0,0));m.code=oracle.WindowCode(m.code,m);m.code.ends=(0x150277BC,)
    with self.assertRaises(oracle.WindowBoundary):m.run()
    self.assertEqual(next(a for t,a in m.calls if t==source.ENTRY),(oracle.PAYLOAD,0,priority,1));pair.append(m)
   self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));script_count+=1
  self.receipt['integration']=dict(original_copy_cases=count,original_copy_words=11,complete_status_caller_words=51,status_caller_cases=status_count,complete_linked_caller_words=49,linked_caller_cases=linked_count,simple_C_caller_words=26,simple_C_caller_slot_words=29,simple_C_caller_padding_words=3,simple_C_caller_cases=simple_count,script_window_words=3,script_window_cases=script_count,script_prefix_preconditions=['a0 points to constructed payload','a1 is zero'],full_script_function_claimed=False,all_four_ROM_callers_accounted=True,providers_bounded=True)


 def test_04_native32_SDK_and_semantic_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());logs={}
  for opt in ('-O0','-O2','-O3'):
   exe=self.fresh/('native'+opt);built=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr);run=subprocess.run([str(exe)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stderr));logs[opt]=dict(exit=0,diagnostics=built.stderr)
  self.receipt['native']=dict(profiles=logs,cases_per_profile=256*5*2*2,controls=len(controls()),SDK=True,pointers32=True,trapping_UBSan=True,canaries=True,indeterminate_notice_padding_excluded=True,extra_arithmetic_representable=True)

 def test_05_guest_fault_prefixes(self):
  count=delay=0
  for c,copy in ((Case(outcome=0,mode=3),False),(Case(mode=31),False),(Case(),True)):
   code=dict(zip(range(oracle.COPY,oracle.COPY+44,4),struct.unpack_from('>11I',self.rom,0x22EC0)))if copy else{}
   full=BufferOracle(self.truth,fixture(c),c,connected=code).run()
   for cut in range(full.all_accesses):
    pair=[]
    for words in (self.truth,self.words):
     m=BufferOracle(words,fixture(c),c,connected=code);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(oracle.state(pair[0]),oracle.state(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].all_accesses),(pair[1].current_pc,pair[1].delay_of,cut));count+=1;delay+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=count,delay_slot_cuts=delay,complete_state_PC_trace=True,portable_C_fault_claimed=False)

 def test_06_rejections_padder_and_three_GNU_layouts(self):
  raw,rs=source.payload(self.out/'selected.o');rejects=0
  for at in range(0,len(raw),4):
   bad=bytearray(raw);bad[at+3]^=1
   with self.assertRaises(ValueError):source.checked_payload(bytes(bad),rs)
   rejects+=1
  for at in rs:
   bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):source.checked_payload(raw,bad)
   rejects+=1
  count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   defs=oracle.symbols()if j==0 else {n:entry+0x10000+i*0x1000 for i,n in enumerate(oracle.symbols())}
   paths=(self.out/'original-func_15190770.o',self.out/'make-shadow/src/game/generated_1BA1D0.c.o',self.out/'qualified-padded.o',self.out/'selected.o');images=[self.linked(p,entry,'rebase-%d-%d'%(j,k),defs)for k,p in enumerate(paths)]
   self.assertTrue(all(x==images[0]for x in images))
   for priority,outcome,mode in itertools.product((0,128,255),range(2),(0,1,31)):self.compare(Case(priority=priority,outcome=outcome,mode=mode),images,entry,defs);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_rejections=rejects,original_Make_padded_raw_equal=True,all_five_call_bindings=True)

 def test_07_compiled_semantic_negatives(self):
  evidence={}
  def view(m,calls,value,notices,copies):return public(m),[(t,a[1:])for t,a in calls],value,notices,copies
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.linked(obj,source.ENTRY,'negative-link-'+name)
   for c in (Case(identity=byte,priority=byte,outcome=outcome)for byte,outcome in itertools.product((0,128,255),range(2))):
    initial=fixture(c);m=BufferOracle(words,initial,c).run();wanted=reference(initial,c)
    # Guest controls use the correct service ABI but may intentionally change copy/zero sizes.
    want=(public(wanted[0]),[(t,a[1:])for t,a in wanted[1]],wanted[2],[wanted[3]],[]if wanted[4]is None else[wanted[4]])
    if view(m.memory,m.calls,m.r[2],m.notices,m.copies)!=want:evidence[name]=dict(identity=c.identity,outcome=c.outcome);break
   self.assertIn(name,evidence)
  self.receipt['compiled_controls']=dict(count=len(evidence),witnesses=evidence,all_terminated_without_incidental_fault=True)

 def test_08_strict_whole_image_and_inputs(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+208];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,208);named={n:(p,f,loc)for p,n,f,loc in source.symbol_rows(before)}
  positions=[20,at-4,at+208]+list(range(at,at+208))+list(range(named[source.FUNCTION][0],named[source.FUNCTION][0]+16))
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes())
  self.receipt['image']=dict(changed_bytes=sum(x!=y for x,y in zip(before,expected)),exclusions=0,corruptions=len(positions)+1,guard_CSV_unchanged=True,new_guards=0,focused_inputs=len(v))
