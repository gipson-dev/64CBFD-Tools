"""Position/alpha attenuation: actual callback ABI, live aliases, division guards and image gates."""
from pathlib import Path
from unittest.mock import patch
import csv,io,itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_position_byte_attenuation_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];ENTRY=source.ENTRY;F=source.FUNCTION;ARENA=0x22000;CELL=0x33000
COUNTERS=(-2147483648,-1,0,0x5FF,0x600,0x63F,0x640,0x7FF,0x800,0x1000,0x10000,0x7FFFFFFF)
COORDS=((0,0,0),(-32768,32767,-1),(32767,-32768,1),(1,1472,9),(1,1408,-17),(1,1310,7),(-10,4096,-23))
class GuestBreak(Exception):pass
class Oracle(RayOracle):
 def __init__(self,words,memory,args,entry=ENTRY,connected=None):
  TimingOracle.__init__(self,words,memory,entry=entry,arguments=args,connected=connected);self.trace=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def execute(self,word):
  if word>>26==0 and word&63==13:raise GuestBreak(word>>16&1023)
  if word>>26==0 and word&63==26 and self.r[word>>16&31]==0:
   # The following break7 is authoritative. Do not infer hardware HI/LO values on divide-by-zero.
   self.hi,self.lo=0xD1700007,0xD1700007;self.r[0]=0;return
  return super().execute(word)
 def record_call(self,target):
  assert target==ENTRY;args=self.arguments(4);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):raise AssertionError(('unowned helper',target))

def fixture(counter=0x800,coords=(17,-91,255),alpha=200,layout=0):
 memory={STACK+i:(i*17+0xA5)&255 for i in range(-768,512)};memory.update({ARENA+i:(i*13+0x59)&255 for i in range(-16,288)})
 inp,out,count,level=ARENA+0x40,ARENA+0x80,ARENA+0xD0,ARENA+0xE0
 if layout==1:out=inp
 elif layout==2:out=inp+2
 elif layout==3:out=inp-2
 elif layout==4:out=inp+4
 elif layout==5:out=count
 elif layout==6:count=inp
 elif layout==7:count=inp+4
 elif layout==8:count=out
 elif layout==9:count=out+4
 elif layout in(10,11,12,13):level=inp+(0,1,4,5)[layout-10]
 elif layout in(14,15):level=out+(0,4)[layout-14]
 elif layout in(16,17):level=count+(0,3)[layout-16]
 for i,value in enumerate(coords):put(memory,inp+i*2,value&65535,2)
 put(memory,count,counter&0xFFFFFFFF);memory[level]=alpha
 return memory,(inp,out,count,level)
def half(value):return((value&65535)^32768)-32768
def reference(initial,args):
 m=dict(initial);inp,out,count,alpha=args;current=signed(read(m,count))
 if current>=0x600:
  put(m,out+2,(half(read(m,inp+2,2))+(current>>6)-24)&65535,2)
  put(m,out,(half(read(m,inp,2))+(signed(read(m,count))>>8)-6)&65535,2)
  denominator=(signed(read(m,count))>>6)-23;original=read(m,alpha,1)
  if denominator==0:return m,7
  quotient=(original*128//abs(denominator))*(-1 if denominator<0 else 1);scaled=quotient>>4
  if scaled<original:put(m,alpha,scaled&255,1)
  put(m,count,0x600)
 else:
  put(m,out,read(m,inp,2),2);put(m,out+2,read(m,inp+2,2),2)
 put(m,out+4,read(m,inp+4,2),2);return m,None

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+512}

def controls():
 b=source.SELECTED
 return dict(exclusive_gate=b.replace('current >= 0x600','current > 0x600'),unsigned_gate=b.replace('current >= 0x600','(u32)current >= 0x600'),signed_alpha=b.replace('(*alpha << 7)','((s32)*(s8 *)alpha * 128)').replace('if (scaled < *alpha)','if (scaled < *(s8 *)alpha)'),wrong_denominator=b.replace('((*counter >> 6) - 23)','((*counter >> 5) - 23)'),wrong_clamp=b.replace('*counter = 0x600;','*counter = 0x5FF;'),always_alpha=b.replace('if (scaled < *alpha)','if (1)'),wrong_x_shift=b.replace('*counter >> 8','*counter >> 7'),wrong_numerator=b.replace('*alpha << 7','*alpha << 6'),early_z=b.replace('    output[2] = input[2];','').replace('    if (current >= 0x600)','    output[2] = input[2];\n    if (current >= 0x600)'),wrong_return=b.replace('return 0;','return 1;'))

def native_harness():
 code=source.HEADERS+r'''
typedef struct {u32 left[4];s16 vector[32];s32 counter;u8 alpha,pad[3];u32 right[4];}Storage;
typedef char ABI[(sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4&&__builtin_offsetof(Storage,counter)==80)?1:-1];
static Storage actual,expected;
static u8*alphaPointer(Storage*s,u32 mode,u32 ii,u32 oi){switch(mode){case 0:return&s->alpha;case 1:return(u8*)&s->counter;case 2:return(u8*)&s->counter+3;case 3:return(u8*)&s->vector[ii+2];case 4:return(u8*)&s->vector[ii+2]+1;case 5:return(u8*)&s->vector[oi];case 6:return(u8*)&s->vector[oi+2]+1;default:return(u8*)&s->vector[oi]+15;}}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():code+=body.replace(F,'test_'+name)+'\n'
 code+=r'''
typedef s32(*Update)(s16*,s16*,s32*,u8*);
static void expectedStep(Storage*s,u32 ii,u32 oi,u32 mode){s32 first,now,den,old,scaled;s64 value,quotient;u8*a=alphaPointer(s,mode,ii,oi);first=s->counter;
 if(first>=1536){value=(s64)s->vector[ii+1]+(first>>6)-24;s->vector[oi+1]=(s16)value;now=s->counter;value=(s64)s->vector[ii]+(now>>8)-6;s->vector[oi]=(s16)value;now=s->counter;den=(now>>6)-23;old=*a;quotient=old*128/den;scaled=(s32)quotient;scaled>>=4;if(scaled<old)*a=(u8)scaled;s->counter=1536;}
 else{s->vector[oi]=s->vector[ii];s->vector[oi+1]=s->vector[ii+1];}s->vector[oi+2]=s->vector[ii+2];}
static int check(Update fn){static const s32 counters[]={(-2147483647-1),-1,0,1535,1536,1599,1600,2047,2048,4096,65536,2147483647};u32 n,i,ii,oi,mode,layout,alpha;u8*p=(u8*)&actual,*q=(u8*)&expected;s32 counter,result;
 for(n=0;n<68608;n++){
  ii=12;layout=(n>>8)&3;oi=layout==0?20:layout==1?12:layout==2?13:11;mode=(n>>10)&7;
  counter=n<65536?counters[n%12]:counters[(n-65536)>>8];alpha=n&255;
  for(i=0;i<sizeof(Storage);i++)p[i]=(u8)(i*13+n*7);
  for(i=0;i<32;i++)actual.vector[i]=(s16)(n+i*17u);
  actual.vector[ii]=(s16)n;actual.vector[ii+1]=(s16)(n*29u);actual.vector[ii+2]=(s16)~n;actual.counter=counter;*alphaPointer(&actual,mode,ii,oi)=(u8)alpha;
  for(i=0;i<sizeof(Storage);i++)q[i]=p[i];expectedStep(&expected,ii,oi,mode);
  result=fn(actual.vector+ii,actual.vector+oi,&actual.counter,alphaPointer(&actual,mode,ii,oi));if(result!=0)return 1;
  for(i=0;i<sizeof(Storage);i++)if(p[i]!=q[i])return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return code+'return 0;}\n'+START

class WindowEnd(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc in(self.owner.ends):raise WindowEnd(pc)
  return super().__getitem__(pc)

class PositionByteAttenuationTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM))
  for name,attribute in(('selected.o','raw'),('qualified-padded.o','words')):
   p=cls.fresh/name;p.write_bytes((cls.out/name).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,p,source.OWNER);f=functions[F];setattr(cls,attribute,list(struct.unpack_from('>48I',data,f['value'])))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,initial,args,images=None,entry=ENTRY):
  want,trap=reference(initial,args);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=Oracle(words,initial,args,entry)
   if trap:
    with self.assertRaises(GuestBreak)as caught:m.run()
    self.assertEqual(caught.exception.args,(trap,));self.assertEqual(m.current_pc,entry+96)
   else:m.run();self.assertEqual(m.r[2],0)
   self.assertEqual(public(m.memory),public(want));self.assertEqual(m.r[29],STACK);self.assertFalse(m.calls);pair.append(m)
  for m in pair[1:]:self.assertEqual(pair[0].trace,m.trace)
  self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0],trap
 def test_01_owner_Make_registry_and_canonical_four_pointer_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+F+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),14)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(F,)),13);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1A89B0.c.o.compact'),14)
  self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',(self.out/'proposed-owner.c').read_text());self.assertIn('s32 func_1517B6E8(s16 *input, s16 *output, s32 *counter, u8 *alpha)',source.SELECTED)
  words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(words)if w==ENTRY],[0x231994]);self.assertFalse(any(w in(0x0C000000|(ENTRY>>2&0x3FFFFFF),0x08000000|(ENTRY>>2&0x3FFFFFF))for w in words));self.assertEqual(source.REGISTRY+2*12,0x8008CED4)
  data=self.values['conker/asm/data/231970.rodata.s'].decode().split('dlabel D_8008CEBC',1)[1].split('enddlabel D_8008CEBC',1)[0];self.assertEqual(len(re.findall(r'/\*',data)),17);self.assertEqual(struct.unpack_from('>3I',self.rom,0x231994),(ENTRY,0,0x1500BAB8))
  for n in('conker/asm/data/231970.rodata.s','conker/build/asm/data/231970.rodata.s.o'):self.assertEqual((ROOT/n).read_bytes(),self.values[n])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=0,bindings=0,guards=2,neighbors=13,compact_functions=14,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,registry_slot=2,registry_stride=12,retail_table_words=17,s32_result_and_four_pointer_ABI=True)
 def test_02_raw_C_and_literal_guest_boundaries_live_aliases_and_traps(self):
  count=traps=0;visits=set()
  for counter,coords,alpha,layout in itertools.product(COUNTERS,COORDS,(0,1,127,128,255),range(18)):
   m,t=self.compare(*fixture(counter,coords,alpha,layout));visits.update(m.visits);traps+=t is not None;count+=1
  for alpha in range(256):self.compare(*fixture(0x1000,(-32768,32767,-1),alpha));count+=1
  self.assertEqual(visits,set(range(ENTRY,ENTRY+192,4))-{ENTRY+120,ENTRY+156});self.assertGreater(traps,0)
  self.receipt['guest']=dict(cases=count,divide_by_zero_cases=traps,visited_words=len(visits),unreachable_overflow_break_and_redundant_load_retained=True,all256_alpha_bytes=True,signed_counter_coordinate_and_quotient_boundaries=True,raw_C_public_memory_return_and_access_trace_equal=True,all18_input_output_counter_alpha_alias_layouts=True,normalized_complete_private_state_equal=True,divide_zero_HI_LO_is_bounded_model_not_hardware_claim=True)
 def test_03_original_registry_dispatch_and_vertex_alpha_replication(self):
  entry,end=0x1517C6D8,0x1517C780;window=list(struct.unpack_from('>42I',self.rom,entry-0x14FD2B50));asm=self.values[source.ASM].decode();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};self.assertEqual(window,[literal[entry+i*4]for i in range(42)]);self.assertEqual(literal[0x1517C65C],0x02202825);self.assertEqual(literal[0x1517C660],0x27A600BC);self.assertEqual(literal[0x1517C670],0x2627000F);count=0
  for counter,alpha,coords in itertools.product(COUNTERS,(0,1,127,128,255),COORDS[:3]):
   initial,args=fixture(counter,coords,alpha);inp,out,_,_=args;args=(inp,out,STACK+0xBC,out+15);put(initial,STACK+0xBC,counter&0xFFFFFFFF);initial[out+15]=alpha;initial[inp+6]=0x20;put(initial,CELL,inp);put(initial,source.REGISTRY+24,struct.unpack_from('>I',self.rom,0x231994)[0]);put(initial,STACK+0xD4,0x12345678)
   expected=dict(initial);put(expected,STACK+0xD4,0xDEADCAFE);expected,trap=reference(expected,args);self.assertIsNone(trap);color=expected[inp+6]|0x9F;opacity=expected[out+15]
   for vertex in range(4):
    for channel in(12,13,14):put(expected,out+vertex*16+channel,color,1)
    put(expected,out+vertex*16+15,opacity,1)
   pair=[]
   for words in(self.truth,self.words):
    m=Oracle(window,initial,args,entry,{ENTRY+i*4:w for i,w in enumerate(words)});m.r[2]=0x80090000;m.r[24]=24;m.r[16]=inp;m.r[17]=out;m.r[19]=0;m.r[23]=CELL;m.r[13]=0xDEADCAFE;m.ends=(end,0x1517C864);m.code=WindowCode(dict(m.code),m)
    with self.assertRaises(WindowEnd)as caught:m.run()
    self.assertEqual(caught.exception.args,(end,));self.assertEqual(m.memory,expected);self.assertEqual(m.calls,[(ENTRY,args)]);self.assertEqual(m.r[2],opacity);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
  self.assertIn('s32 func_1517BBAC() {\n    return 0;\n}',self.values[source.SOURCE].decode());self.receipt['caller']=dict(original_dispatch_words=42,connected_cases=count,registry_slot2_and_four_pointer_arguments=True,counter_in_parent_stack_plusBC_and_alpha_in_vertex_plusF=True,zero_result_continues_RGB_and_alpha_replication_to_four_vertices=True,current_parent_stub_unchanged=True,no_full_parent_or_gameplay_acceptance=True)
 def test_04_native32_valid_overlaps_and_effective_controls(self):
  self.assertTrue(all(b!=source.SELECTED for b in controls().values()))
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=68608,effective_controls=len(controls()),all65536_coordinate_encodings_and_all256_alpha_bytes=True,valid_shared_s16_array_and_unsigned_char_aliases=True,whole_storage_fences=True,trapping_UBSan=True,nonzero_signed_division_domain=True,counter_halfword_aliases_and_zero_division_separate_guest_probes=True)
 def test_05_fired_access_prefixes_lazy_alpha_and_guarded_division(self):
  cuts=0
  for counter,coords,layout in itertools.product((0,0x600,0x7FFFFFFF),((17,-91,255),(1,1472,9)),range(18)):
   initial,args=fixture(counter,coords,200,layout);good,_=self.compare(initial,args)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     m=Oracle(words,initial,args);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(public(pair[0].memory),public(pair[2].memory));self.assertEqual(pair[0].trace,pair[2].trace);cuts+=1
  initial,args=fixture(0)
  initial.pop(args[3]);m,_=self.compare(initial,args);self.assertFalse(any(e[1]==args[3]for e in m.trace))
  initial,args=fixture(0x600,(1,1472,9),200,5);m,trap=self.compare(initial,args);self.assertEqual(trap,7);self.assertEqual(read(m.memory,args[2]),1472);self.assertEqual([e[1]for e in m.trace if e[0]=='W'],[args[1]+2,args[1]])
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,normalized_complete_state_PC_delay_equal=True,raw_public_prefix_and_trace_equal=True,inactive_alpha_unmapped=True,zero_divisor_reaches_original_break7_after_two_coordinate_stores=True,unreachable_break6_retained=True,no_hardware_zero_divide_HI_LO_claim=True)
 def test_06_closed_two_register_exchange_padder_guards_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertFalse(rs);self.assertEqual(len(source.NEW_GUARDS),2);words=list(struct.unpack('>48I',raw));self.assertEqual(words[4:7],[0x848E0002,0x00027983,0x01CFC021]);self.assertEqual(self.truth[4:7],[0x848F0002,0x00027183,0x01CFC021])
  # The shared addu sums the same two values; neither old temporary is read before being overwritten.
  pending={14,15}
  for word in words[7:21]:
   op,rsn,rtn,rdn,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word&63;reads=set();writes=set()
   if op in(33,35,36):reads={rsn};writes={rtn}
   elif op in(41,43):reads={rsn,rtn}
   elif op==9:reads={rsn};writes={rtn}
   elif op==0:
    if fn in(0,3):reads={rtn};writes={rdn}
    elif fn==33:reads={rsn,rtn};writes={rdn}
    else:self.fail(('unexpected induction instruction',hex(word)))
   else:self.fail(('unexpected induction opcode',hex(word)))
   self.assertFalse(pending&reads);pending-=writes
  self.assertFalse(pending)
  for i in range(2):
   rows=[dict(x)for x in source.NEW_GUARDS];rows[i]['expected']='0xDEADBEEF'
   with patch.object(source,'NEW_GUARDS',rows):
    with self.assertRaises(ValueError):source.normalized_payload(raw,{})
  for data,bindings in((raw[:-4],{}),(raw[:-1]+bytes([raw[-1]^1]),{}),(raw,{16:[('R_MIPS_26','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(data,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'proposed-word-patches.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  before=self.values['conker/retail_word_patches.us.csv'];proposal=(self.out/'proposed-word-patches.csv').read_bytes();self.assertEqual(proposal,source.guard_manifest(before));self.assertTrue(proposal.startswith(before));reader=csv.DictReader(io.StringIO(proposal.decode()));fields=reader.fieldnames;rows=list(reader);next(x for x in rows if x['function']==F)['expected']='0x00000000';bad_csv=self.fresh/'bad.csv'
  with bad_csv.open('w',newline='')as stream:writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
  with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad_csv,filename=source.OWNER)
  normalized,bindings=source.normalized_payload(raw,{});asm,unresolved=emit_function(normalized,dict(value=0,size=192),bindings,F,{});self.assertFalse(unresolved);p=self.fresh/'normalized.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(p)],capture_output=True,check=True);cases=0
  for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
   pair=[]
   for k,artifact in enumerate((self.out/('original-'+F+'.o'),obj)):
    p=self.fresh/('layout-%d-%d.ld'%(j,k));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',F,'-o',str(elf),str(artifact)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
   self.assertEqual(*pair)
   for counter,layout in itertools.product((0,0x600,0x7FFFFFFF),(0,2,5)):
    self.compare(*fixture(counter,(1,1472,9),200,layout),images=pair,entry=entry);cases+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=cases,no_external_bindings=True,closed_t6_t7_value_exchange_and_commutative_add=True,no_read_before_each_temporary_overwrite=True,effective_raw_guard_binding_controls=5,actual_padder_bad_expected_rejected=True,guards=2)
 def test_07_actually_compiled_cached_counter_and_rounding_controls(self):
  bodies={'cached':source.SELECTED.replace('((*counter >> 6) - 23)','((current >> 6) - 23)'),'truncated':source.SELECTED.replace('/ ((*counter >> 6) - 23)) >> 4','/ ((*counter >> 6) - 23)) / 16')};cases={'cached':(fixture(0x600,(-10,4096,-23),200,5),(39,200)),'truncated':(fixture(0x600,(1,1310,7),1,5),(253,254))}
  for name,body in bodies.items():
   self.assertNotEqual(body,source.SELECTED);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);data,funcs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=funcs[F];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));(initial,args),wanted=cases[name];expected,trap=reference(initial,args);self.assertIsNone(trap);m=Oracle(words,initial,args).run();self.assertEqual((read(expected,args[3],1),read(m.memory,args[3],1)),wanted);self.assertNotEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],0)
  self.receipt['compiled_controls']=dict(actual_IDO_controls=2,live_post_store_counter_rejected_by_alpha_39_vs200=True,arithmetic_shift_of_negative_quotient_rejected_by_alpha253_vs254=True,both_fail_by_value_in_mapped_guest_memory=True)
 def test_08_strict_entire_image_size_and_effective_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==F)+8
  for offset in(20,at,at+156,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  q=json.loads((self.out/'preparation.json').read_text());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),q['changed_bytes']);self.assertEqual(q['metadata_bytes'],1);self.receipt['image']=dict(changed_bytes=q['changed_bytes'],code_bytes=q['code_bytes'],size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,inherited_guards_headers_registry_and_current_parent_unchanged=True)
