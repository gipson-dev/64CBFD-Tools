"""Heap/state initializer: literal objects, full image, caller and native32."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_audio_state_initialize_15016170_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner,body as source_body
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_audio_state_initialize_15016170_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def cases():
 for byte,mutation,phase in itertools.product(range(256),(0,15),(0,8)):
  yield guest.Case(left=(byte*257)&65535,right=((255-byte)*251)&65535,pattern=byte,mutation=mutation,phase=phase,results=(0 if byte&1 else 0x81234560,byte*0x01010101,(~byte)&0xFFFFFFFF))
 for real,limit,current,alias in itertools.product((0,1),(0,79,80,95,96,1167,1168,1183,1184,4096),(0,16,31),(0,1)):
  yield guest.Case(real_heap=real,limit=limit,current=current,buffer_alias=alias,left=32768,right=32767)
 for h in(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF):yield guest.Case(heap=h,mutation=15)

def controls():
 b=match.SELECTED
 rows={n:b.replace(a,z)for n,a,z in(('clear_size','sizeof(D_800E0D80)','sizeof(D_800E0D80)-1'),('first_size',', 1, 80)',', 1, 81)'),('second_size',', 1, 1088)',', 1, 1089)'),('third_size',', 1, 8)',', 1, 17)'),('wrong_heap','(ALHeap *)heapAddress','(ALHeap *)0'),('wrong_count',', 1, 80)',', 2, 80)'),('wrong_pan','unkC = 64','unkC = 63'),('wrong_aux','unk96 = 64','unk96 = 63'),('wrong_gain','unkE = 0x7FFF','unkE = 0x7FFE'),('wrong_reverse','D_8002BC10 + 127','D_8002BC10 + 126'),('left_shift','>> 15','>> 14'),('wrong_state','unk24 = 1','unk24 = 0'),('missing_callback','func_151F3C34((s32)func_151F3C4C);','(void)heapAddress;'))}

 rows['unsigned_sample']=b.replace('*(s16 *)((u8 *)&D_8002BC10 + index)','*(u16 *)((u8 *)&D_8002BC10 + index)')
 rows['wrong_pointer_slot']=b.replace('unk74 = (s32)alHeapDBAlloc','unk5C = (s32)alHeapDBAlloc')
 rows['rollback']=b.replace('    D_800E0D80.unkC = 64;','    if (D_800E0D80.unk8 == 0) return;\n    D_800E0D80.unkC = 64;')
 assert all(v!=b for v in rows.values());return rows

def linked(obj,entry,label,out,defs=None):
 defs=guest.symbols()if defs is None else defs;t,fs,rs=parse_object(obj);f=fs[match.FUNCTION];assembly,unknown=emit_function(t,f,rs,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

class AudioInitTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>77I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.truth==cls.fitted
 def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def check(self,c,images=None,entry=match.ENTRY,s=None,connected=None):
  s=guest.symbols()if s is None else s
  if c.table_alias:s=dict(s,D_8002BC10=s['D_800E0D80']-110)
  initial=guest.fixture(c,s);expected,calls,snaps=guest.reference(initial,c,s);pair=[]
  for w in(self.truth,self.raw,self.fitted)if images is None else images:
   m=guest.Oracle(w,initial,c,entry,s,connected).run();self.assertEqual((guest.public(m.memory),m.calls,m.snapshots),(guest.public(expected),calls,snaps),c);pair.append(m)
  self.assertTrue(all(guest.observable(m)==guest.observable(pair[0])for m in pair))
  if images is None:self.assertEqual(guest.state(pair[0]),guest.state(pair[-1]))
  return pair
 def test_01_whole_owners_Make_guards_and_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(77,40,19,0,0,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['exclusions']),(3,1,233,0));self.assertEqual((q['caller']['functions'],q['caller']['diagnostics'],q['caller']['actual_Make']['commands']),(7,1,3));self.assertTrue(q['caller']['padded_object_unchanged'])
  for at in range(308):
   b=bytearray(self.blob);b[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(b),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),19)
  for index in indices:
   altered=[dict(r)for r in rows];altered[index]['expected']='0x%08X'%(int(altered[index]['expected'],16)^1);p=self.out/'rejected-guard.csv'
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(altered)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/nonmatchings/game_43620/func_15016170.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes();slot=self.rom[match.ROM:match.ROM+320]
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,320)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),slot)
  self.assertEqual(slot[-12:],bytes(12))
 def test_02_state_bytes_failure_and_live_heap_protocol(self):
  n=0;seen=set()
  for c in cases():seen.update(self.check(c)[0].visits);n+=1
  self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+308,4)));self.receipt('guest-contract',dict(cases_per_body=n,visited_body_words=77,slot_padding_words=3,all160_state_bytes_and_provider_snapshots=True,allocation_failures_and_return_bits=True,three_live_heap_homes=True,signed_samples_and_arithmetic_shift=True,raw_memory_call_access_saved_and_HI_LO_equal=True,raw_caller_temporaries_excluded=True))
 def test_03_aliases_address_equation_and_fault_prefixes(self):
  aliases=0
  for buffer,table,mutation in itertools.product((0,1),(0,1),(0,4,15)):
   c=guest.Case(buffer_alias=buffer,table_alias=table,mutation=mutation,real_heap=1,limit=160 if buffer else 4096)
   if table:
    s=dict(guest.symbols(),D_8002BC10=guest.STATE-110);images=[linked(p,match.ENTRY,'overlap-%d-%d-%d'%(buffer,mutation,i),self.out,s)for i,p in enumerate((self.out/'qualified-owner.o',self.prepared['qualified_object']))];self.check(c,images,s=s)
   else:self.check(c)
   aliases+=1
  equations=0
  for base,index in itertools.product((0x80027F02,0x81007F10,0x8200FFF0,0xFFFFFF00),(0,2,126,128,254,0xFFFFFFFE)):
   end=guest.u32(base+254);hi=(end+32768)&0xFFFF0000;lo=guest.half(end);raw=guest.u32(end-index);fitted=guest.u32(hi+guest.u32(-index)+lo);self.assertEqual(raw,fitted);equations+=1
  cuts=delay=0
  for c in(guest.Case(),guest.Case(mutation=15),guest.Case(real_heap=1,limit=96,left=32768,right=65535)):
   initial=guest.fixture(c);done=guest.Oracle(self.truth,initial,c).run()
   for cut in range(done.all_accesses):
    pair=[]
    for w in(self.truth,self.raw,self.fitted):
     m=guest.Oracle(w,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(guest.observable(pair[0]),guest.observable(pair[1],raw_fault=True));self.assertEqual(guest.state(pair[0]),guest.state(pair[2]));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_cases_per_body=aliases,modular_reverse_address_equations=equations,fired_prefix_triples=cuts,delay_slot_cuts=delay,raw_fault_PC_mapping={'38':39},raw_temporaries_excluded=True,fitted_literal_full_state_equal=True,portable_C_global_aliases_claimed=False))
 def test_04_complete_original_Init_caller(self):
  words=list(struct.unpack_from('>17I',self.rom,0x12588));n=0
  for real,limit,mutation,phase in itertools.product((0,1),(0,96,1184),(0,15),(0,8)):
   c=guest.Case(real_heap=real,limit=limit,mutation=mutation,phase=phase);initial=guest.fixture(c);pair=[]
   for w in(self.truth,self.raw,self.fitted):
    m=guest.Oracle(words,initial,c,entry=0x10012588,connected=dict(zip(range(match.ENTRY,match.ENTRY+308,4),w))).run();self.assertEqual(m.calls[0],(match.ENTRY,(c.heap,)));self.assertEqual(m.calls[-2:],[(guest.QUEUE,(0x800427A0,0x800427B0,64)),(guest.HOOK,(0x10012560,))]);pair.append(m)
   self.assertTrue(all(guest.observable(m)==guest.observable(pair[0])for m in pair));self.assertEqual(guest.state(pair[0]),guest.state(pair[2]));n+=1
  self.receipt('callers',dict(cases_per_body=n,complete_original_words=17,Init_owner_functions_unchanged=7,explicit_void_s32_prototype=True,return_ignored=True,trailing_queue_and_callback_setup=True))
 def test_05_original_heap_clear_and_setter(self):
  before=self.prepared['predecessor_elf'].read_bytes();n=0;seen=set()
  for limit,current,left,right in itertools.product((0,79,80,95,96,1167,1168,1183,1184,4096),(0,16),(0,32768),(32767,65535)):
   c=guest.Case(real_heap=1,limit=limit,current=current,left=left,right=right);pair=self.check(c,connected=guest.helpers(self.rom));seen.update(pair[0].visits);n+=1
  for e,p,words in((guest.ZERO,0x226F0,40),(guest.ALLOC,0x12844,35),(guest.SET,0x2210E4,6),(0x10012588,0x12588,17)):
   at=match.elf_slot_offset(before,e,words*4);self.assertEqual(before[at:at+words*4],self.rom[p:p+words*4])
  at=match.elf_slot_offset(before,guest.TABLE,256);self.assertEqual(before[at:at+256],self.rom[0x2BC10:0x2BD10]);self.receipt('connections',dict(cases_per_body=n,allocator_words=35,bzero_slot_words=40,setter_slot_words=6,all_helper_and_caller_baselines_exact=True,pan_data_exact=True,parent_entries=127,separate_terminal=1,allocator_words_visited=len(seen&set(range(guest.ALLOC,guest.ALLOC+140,4))),heap_rounding_and_exhaustion=True))
 def test_06_independent_GNU_rebases(self):
  n=0
  for j,entry in enumerate((0x15007FF0,0x16008010,0x1700FFF0)):
   s=dict(D_800E0D80=0x81007FF0+j*0x10000,D_8002BC10=0x82007F10+j*0x8000,bzero=entry+0x10004,alHeapDBAlloc=entry+0x20008,func_151F3C34=entry+0x3000C,func_151F3C4C=0x8300FFF0+j*0x10000);images=[linked(p,entry,'rebase-%d-%d'%(j,i),self.out,s)for i,p in enumerate((self.out/'qualified-owner.o',self.prepared['qualified_object']))]
   for c in list(cases())[::127]:self.check(c,images,entry,s);n+=1
  self.receipt('rebases',dict(independent_GNU_links=6,cases_per_body=n,table_end_addend_and_HI_LO_carry=True,state_and_callback_pairs=True,five_R26_calls=True))
 def test_07_compiled_semantic_negatives(self):
  rows={};quick=[guest.Case(),guest.Case(results=(0,0,0),left=32768,right=65535,mutation=4),guest.Case(pattern=255,left=0x1234,right=0x7654)]
  for name,fragment in controls().items():
   obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+fragment,'negative-'+name);self.assertFalse(diag);ws=linked(obj,match.ENTRY,'negative-link-'+name,self.out);killed=False
   for c in quick:
    initial=guest.fixture(c);expected,calls,snaps=guest.reference(initial,c)
    try:m=guest.Oracle(ws,initial,c).run();killed=(guest.public(m.memory),m.calls,m.snapshots)!=(guest.public(expected),calls,snaps)
    except(AssertionError,KeyError):killed=True
    if killed:break
   self.assertTrue(killed,name);rows[name]=dict(compiled=True,public_counterexample=True)
  self.receipt('compiled-controls',rows)
 def test_08_native32_SDK_heap_and_state(self):
  text,n=native_program();p=self.out/'native.c';p.write_text(text)
  for opt in('-O0','-O2','-O3'):
   binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
  self.receipt('native-contract',dict(cases_per_profile=n,profiles=['O0','O2','O3'],compiled_controls=len(controls()),all_controls_effective=True,SDK_struct160_and_ALHeap16=True,actual_C_SDK_allocator=True,all_state_bytes_and_heap_fields=True,UBSan_traps=True,guest_home_and_table_alias_cases_excluded=True))

def native_program():
 import re
 chosen=[guest.Case(),guest.Case(results=(0,0,0),left=32768,right=65535,mutation=4),guest.Case(pattern=255,left=0x1234,right=0x7654)]
 chosen+= [replace(c,phase=0,mutation=c.mutation&12)for c in cases()if c.heap==guest.HEAPS[0]and not c.buffer_alias and not c.table_alias]
 chosen=list(dict.fromkeys(chosen));rows=[]
 arr=lambda v:'{'+','.join('0x%Xu'%x for x in v)+'}'
 for c in chosen:
  expected,calls,snaps=guest.reference(guest.fixture(c),c);h=[guest.read(expected,p+o)for p in guest.HEAPS for o in(0,4,8,12)]
  rows.append('{'+','.join((str(c.real_heap),str(c.limit),str(c.current),str(c.pattern),str(c.mutation),str(c.left),str(c.right),arr(c.results),arr(guest.data(expected,guest.STATE,160)),arr([b for snapshot in snaps for b in snapshot]),arr(h)))+'}')
 allocator=source_body((ROOT/'conker/src/libultra/audio/heap.c').read_text(),'alHeapDBAlloc').replace('alHeapDBAlloc','sdkHeapAlloc',1)
 alignment=int(re.search(r'^#define\s+AL_CACHE_ALIGN\s+(\d+)',(ROOT/'conker/src/libultra/audio/synthInternals.h').read_text(),re.M)[1]);assert alignment==15
 text=match.ISOLATED_HEADER+'\n#define AL_CACHE_ALIGN '+str(alignment)+r'''
typedef char state_size[sizeof(struct186)==160?1:-1];typedef char heap_size[sizeof(ALHeap)==16?1:-1];typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef char pointer_offset[__builtin_offsetof(struct186,unk74)==0x74?1:-1];
typedef struct {u32 real,limit,current,pattern,mutation,left,right,results[3];u8 expected[160],snapshots[800];u32 heaps[8];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
struct186 D_800E0D80;s16 D_8002BC10[127];
static u8 buffers[2][4096];static ALHeap heaps[2];static const Row *current;static u32 calls,bad,registered;
void func_151F3C4C(void){}
static u32 value(const u8 *p,u32 n){u32 r=0,i;for(i=0;i<n;i++)r=(r<<8)|p[i];return r;}
static u32 mapped(u32 a){if(a>=0x50000&&a<=0x51000)return(u32)(buffers[0]+(a-0x50000));if(a>=0x60000&&a<=0x61000)return(u32)(buffers[1]+(a-0x60000));return a;}
static int field(u32 i,u32 *start){static const u8 offsets[]={8,12,14,16,18,20,22,36,48,50,92,116,124,132,136,148,150};static const u8 sizes[]={4,2,2,2,2,2,2,2,2,2,4,4,4,4,4,2,2};u32 j;for(j=0;j<17;j++)if(offsets[j]<=i&&i<offsets[j]+sizes[j]){*start=offsets[j];return sizes[j];}return 0;}
static void initialize(const u8 *expected){u32 i,j,start,n,v;u8 *d=(u8*)&D_800E0D80;for(i=0;i<160;){n=field(i,&start);if(n){v=value(expected+i,n);for(j=0;j<n;j++)d[i+j]=(u8)(v>>(8*j));i+=n;}else{d[i]=expected[i];i++;}}}
static int compare(const u8 *expected){u32 i,j,start=0,n,v,w;u8 *d=(u8*)&D_800E0D80;for(i=0;i<160;i++){n=field(i,&start);if(n){v=0;for(j=0;j<n;j++)v|=(u32)d[start+j]<<(8*j);w=value(expected+start,n);if(current->real&&(start==8||start==92||start==116))w=mapped(w);if(start==124&&w==0x151F3C4Cu)w=(u32)func_151F3C4C;if(v!=w)return 0;}else if(d[i]!=expected[i])return 0;}return 1;}
static void effect(u32 stage){u32 i;static const u8 offsets[]={0,4,24,52,152,159};if(current->mutation&4)for(i=0;i<6;i++)((u8*)&D_800E0D80)[offsets[i]]=(u8)(current->pattern*17+stage*31+offsets[i]);if((current->mutation&8)&&stage==3){D_8002BC10[64]=(s16)(current->left^65535);D_8002BC10[63]=(s16)(current->right^65535);}}
void bzero(void *p,int n){u32 i;if(calls!=0||p!=&D_800E0D80||n!=160||!compare(current->snapshots))bad=1;calls++;if(p==&D_800E0D80&&n>=0&&n<=160)for(i=0;i<(u32)n;i++)((u8*)p)[i]=0;effect(0);}
'''+allocator+r'''
void *alHeapDBAlloc(u8 *file,s32 line,ALHeap *hp,s32 number,s32 size){u32 stage=calls;void *p=0;static const u32 sizes[]={80,1088,8};if(stage<1||stage>3){bad=1;return 0;}if(!compare(current->snapshots+stage*160)||file!=0||line!=0||hp!=heaps||number!=1||(u32)size!=sizes[stage-1]){bad=1;}else p=current->real?sdkHeapAlloc(file,line,hp,number,size):(void*)current->results[stage-1];calls++;effect(stage);return p;}
void func_151F3C34(s32 address){u32 i;if(calls!=4||!compare(current->snapshots+640)||(u32)address!=(u32)func_151F3C4C)bad=1;calls++;registered=address;for(i=0;i<4;i++)((u8*)&D_800E0D80)[124+i]=((u8*)&registered)[i];}
'''
 names=['selected',*controls()]
 for name,fragment in dict(selected=match.SELECTED,**controls()).items():text+=fragment.replace(match.FUNCTION,name,1)+'\n'
 text+=r'''
static int check(void(*fn)(s32),const Row *r){u32 i,h,words[4];current=r;bad=calls=registered=0;initialize(r->snapshots);for(i=0;i<127;i++)D_8002BC10[i]=(s16)((i*251+r->pattern*17)&32767);D_8002BC10[64]=(s16)r->left;D_8002BC10[63]=(s16)r->right;
 for(i=0;i<2;i++){heaps[i].base=buffers[i];heaps[i].cur=buffers[i]+r->current;heaps[i].len=r->limit;heaps[i].count=0x12345678;}
 fn((s32)heaps);if(calls!=5||registered!=(u32)func_151F3C4C||!compare(r->expected))bad=1;
 for(h=0;h<2;h++){words[0]=(u32)heaps[h].base;words[1]=(u32)heaps[h].cur;words[2]=heaps[h].len;words[3]=heaps[h].count;for(i=0;i<4;i++)if(words[i]!=(i<2?mapped(r->heaps[h*4+i]):r->heaps[h*4+i]))bad=1;}return !bad;}
static int run(void){u32 i,j,killed['''+str(len(names))+r''']={0};void(*functions[])(s32)={'''+','.join(names)+r'''};for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return text,len(chosen)

if __name__=='__main__':unittest.main()
