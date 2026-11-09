"""Rolling matrix cache: literal image, indirect caller, mutable providers and native32."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_owner_cache_update_15188e48_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner,body as source_body
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_owner_cache_update_15188e48_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def corpus():
 for byte in range(256):
  yield guest.Case(type=byte,snapshots=1+byte%3,matrices=byte%2,page=byte,filled=byte,phase=8*(byte&1),seed=byte)
  yield guest.Case(type=byte,snapshots=byte,matrices=1,page=byte&1,filled=(byte*37)&255,phase=8*(byte&1),seed=byte)
 for kind,count,mutation,missing,alias,phase in itertools.product((0,1,2,3),(0,1,2),(0,1,2,4,7),(0,1),(0,1,2),(0,8)):
  yield guest.Case(snapshots=kind,matrices=count,mutation=mutation,missing=missing,alias=alias,page=mutation&1,filled=255,phase=phase)

def controls():
 b=match.SELECTED
 pairs=dict(first_instead_last=('if (snapshots == index)','if (1 == index)'),wrong_history=('index * matrices + otherPage','previous * matrices + otherPage'),wrong_destination=('previous * matrices + currentPage','index * matrices + currentPage'),wrong_xor=('page ^ 1','page ^ 2'),wrong_current_page=('currentPage = page * span','currentPage = (page ^ 1) * span'),wrong_length=('(u32)matrices << 6','(u32)matrices << 5'),wrong_type=('record->descriptor[4]','record->descriptor[5]'),fewer_snapshots=('snapshots = record->stride','snapshots = record->stride - 1'),missing_reset=('record->count = 0;','(void)record;'),clamped_counter=('record->count != record->stride','record->count < record->stride'),cached_final_kind=('record->count != record->stride','record->count != snapshots'),no_copy=('bcopy(source, destination, (u32)matrices << 6);','(void)source; (void)destination;'))
 result={n:b.replace(a,z)for n,(a,z)in pairs.items()}
 result['cached_page']=b.replace('    s32 snapshots =','    u32 earlyPage = D_800BE9C0;\n    s32 snapshots =').replace('u32 page = D_800BE9C0','u32 page = earlyPage')
 result['cached_owner']=b.replace('    s32 snapshots =','    u8 *earlyOwner = record->descriptor;\n    s32 snapshots =').replace('record->descriptor[4]','earlyOwner[4]').replace('record->descriptor + 0x1D4','earlyOwner + 0x1D4')
 result['cached_buffer']=b.replace('    s32 snapshots =','    Mtx *earlyBuffer = record->records;\n    s32 snapshots =').replace('= record->records +','= earlyBuffer +')
 assert all(v!=b for v in result.values());return result

def linked(obj,entry,label,out,defs=None):
 defs=guest.symbols()if defs is None else defs;t,fs,rs=parse_object(obj);f=fs[match.FUNCTION];assembly,unknown=emit_function(t,f,rs,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

def native_program():
 quick=[guest.Case(),guest.Case(snapshots=2,page=2),guest.Case(mutation=1),guest.Case(mutation=2),guest.Case(snapshots=2,filled=255),guest.Case(missing=1,filled=7),guest.Case(matrices=2,alias=2),guest.Case(snapshots=0,mutation=1)]
 cases=list(dict.fromkeys(quick+[replace(c,phase=0)for c in corpus()]));rows=[];copies=[]
 for c in cases:
  initial=guest.fixture(c);want,calls,_=guest.reference(initial,c);first=len(copies)
  for t,a in calls:
   if t==guest.COPY:copies.append('{0x%08Xu,0x%08Xu,%d}'%a)
  digest=[]
  for bank,base in enumerate(guest.BUFFERS):
   h=2166136261
   for i in range(guest.CAPACITY):h=((h^want.get(base+i,guest.pattern(c,bank,i)))*16777619)&0xFFFFFFFF
   digest.append(h)
  bytevals=','.join(str(want[guest.RECORD+i])for i in(*range(8),*range(12,16)))
  rows.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,0x%08Xu,0x%08Xu,{%s},%d,%d,%d,%d,%d}'%(c.snapshots,c.matrices,c.page,c.filled,c.type,c.mutation,c.missing,c.alias,c.seed,first,len(copies)-first,*digest,bytevals,int(guest.read(want,guest.RECORD+8)==guest.BUFFERS[1]),int(guest.read(want,guest.RECORD+16)==guest.OTHER),want[guest.FLAG],sum(t==guest.COUNT for t,a in calls),sum(t==guest.COPY for t,a in calls)))
 counter=source_body((ROOT/'conker/src/game/generated_58F80.c').read_text(),'func_1502DB20').replace('func_1502DB20','count_impl',1)
 text=match.ISOLATED_HEADER+r'''
typedef char descriptor_size[sizeof(DescriptorDraw151897A4)==20?1:-1];
typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef char buffer_offset[__builtin_offsetof(DescriptorDraw151897A4,records)==8?1:-1];
typedef char owner_offset[__builtin_offsetof(DescriptorDraw151897A4,descriptor)==16?1:-1];
typedef struct {u32 source,destination,length;} Copy;
typedef struct {u32 snapshots,matrices,page,filled,type,mutation,missing,alias,seed,first,n;u32 digest0,digest1;u8 bytes[12];u32 bank,owner,flag,countCalls,copyCalls;} Row;
static const Copy copies[]={
'''+',\n'.join(copies)+r'''
};static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static union {Mtx aligned[1024];u8 bytes[65536];} buffers[2];
static union {u32 align[128];u8 bytes[512];} owners[2];
static union {Mtx align[4];u8 bytes[256];} sources[2];
static DescriptorDraw151897A4 record;
u8 D_800BE9C0;u16 D_800C4ED0[256];
static const Row *current;static u32 countCalls,copyCalls,bad;
static void *real(u32 a){if(a>=0x100000&&a<0x110000)return buffers[0].bytes+(a-0x100000);if(a>=0x200000&&a<0x210000)return buffers[1].bytes+(a-0x200000);if(a>=0x70000&&a<0x70100)return sources[0].bytes+(a-0x70000);if(a>=0x71000&&a<0x71100)return sources[1].bytes+(a-0x71000);return 0;}
static void count_effect(void){if(current->mutation&1){D_800BE9C0^=1;record.stride^=1;record.count=current->snapshots;record.records=(Mtx*)buffers[1].bytes;record.descriptor=owners[1].bytes;}}
static void copy_effect(void){if(copyCalls!=1)return;if(current->mutation&2){D_800BE9C0^=1;record.stride^=1;record.count=current->snapshots;record.records=(Mtx*)(record.records==(Mtx*)buffers[1].bytes?buffers[0].bytes:buffers[1].bytes);record.descriptor=record.descriptor==owners[1].bytes?owners[0].bytes:owners[1].bytes;}if(current->mutation&4)record.count=254;}
'''+counter+r'''
s32 func_1502DB20(s32 t){s32 n;countCalls++;if(t!=(s32)current->type||countCalls!=1)bad=1;n=count_impl(t);count_effect();return n;}
void bcopy(const void *source,void *destination,int length){u32 i;u8 snapshot[128];const Copy *copy;
 if(copyCalls>=current->n){bad=1;copyCalls++;copy_effect();return;}copy=copies+current->first+copyCalls++;
 if(source!=real(copy->source)||destination!=real(copy->destination)||(u32)length!=copy->length||length<0||length>128){bad=1;copy_effect();return;}
 for(i=0;i<(u32)length;i++)snapshot[i]=((const u8*)source)[i];for(i=0;i<(u32)length;i++)((u8*)destination)[i]=snapshot[i];copy_effect();
}
'''
 names=['selected',*controls()]
 for name,fragment in dict(selected=match.SELECTED,**controls()).items():text+=fragment.replace(match.FUNCTION,name,1)+'\n'
 special='||'.join('i==%d'%t for t in sorted(guest.SPECIAL))
 typespecial='||'.join('r->type==%d'%t for t in sorted(guest.SPECIAL))
 text+=r'''
static int check(void(*fn)(DescriptorDraw151897A4*),const Row*r){u32 i,j,k,h[2]={2166136261u,2166136261u};u8 *source;
 current=r;bad=countCalls=copyCalls=0;for(i=0;i<20;i++)((u8*)&record)[i]=(u8)(i*13+r->seed*7+89);record.stride=r->snapshots;record.count=r->filled;record.records=(Mtx*)buffers[0].bytes;record.descriptor=owners[0].bytes;
 for(i=0;i<2;i++){for(j=0;j<512;j++)owners[i].bytes[j]=(u8)(j*13+r->seed*7+89);for(j=0;j<256;j++)sources[i].bytes[j]=(u8)(j*13+r->seed*7+89);for(j=0;j<65536;j++)buffers[i].bytes[j]=(u8)(j*13+i*29+r->seed*7+89);}
 owners[0].bytes[4]=r->type;owners[1].bytes[4]=(u8)(r->type+17);source=r->missing?0:r->alias?buffers[0].bytes+(r->alias==1?0:192):sources[0].bytes;*(u8**)(owners[0].bytes+0x1D4)=source;*(u8**)(owners[1].bytes+0x1D4)=sources[1].bytes;
 for(i=0;i<256;i++)D_800C4ED0[i]=1+('''+special+r'''?4:0);D_800C4ED0[r->type]=(u16)(r->matrices+('''+typespecial+r'''?4:0));D_800BE9C0=r->page;
 fn(&record);if(countCalls!=r->countCalls||copyCalls!=r->copyCalls||D_800BE9C0!=r->flag||record.records!=(Mtx*)buffers[r->bank].bytes||record.descriptor!=owners[r->owner].bytes)bad=1;
 for(i=0;i<12;i++){j=i<8?i:i+4;if(((u8*)&record)[j]!=r->bytes[i])bad=1;}
 for(k=0;k<2;k++)for(i=0;i<65536;i++)h[k]=(h[k]^buffers[k].bytes[i])*16777619u;if(h[0]!=r->digest0||h[1]!=r->digest1)bad=1;return !bad;
}
static int run(void){u32 i,j;u32 killed['''+str(len(names))+r''']={0};void(*functions[])(DescriptorDraw151897A4*)={'''+','.join(names)+r'''};
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
 for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return text,len(cases),len(copies)

class CacheUpdateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.truth==cls.fitted
 def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def compare(self,c,images=None,entry=match.ENTRY,s=None,initial=None):
  s=guest.symbols()if s is None else s;initial=guest.fixture(c,s)if initial is None else initial;expected,calls,packets=guest.reference(initial,c,s);pair=[]
  for w in images or(self.truth,self.raw,self.fitted):
   m=guest.Oracle(w,initial,c,entry,s).run();self.assertEqual((guest.public(m.memory),m.calls,m.copy_snapshots),(guest.public(expected),calls,packets),c);pair.append(m)
  self.assertTrue(all(guest.observable(m)==guest.observable(pair[0])for m in pair))
  if images is None:self.assertEqual(guest.state(pair[0]),guest.state(pair[-1]))
  return pair
 def test_01_owner_Make_guards_and_strict_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(79,48,28,14,14,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['exclusions']),(3,15,215,0));proof=match.certificate(self.blob,self.refs);self.assertEqual(proof['shared_destination_additions'],[46,58])
  for at in range(316):
   raw=bytearray(self.blob);raw[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(raw),self.refs)
  for at in self.refs:
   rs=dict(self.refs);rs[at]=[(rs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,rs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),28)
  for index in indices:
   altered=[dict(r)for r in rows];altered[index]['expected']='0x%08X'%(int(altered[index]['expected'],16)^1);p=self.out/'rejected-guard.csv'
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(altered)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/1B5CC0.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+316])
 def test_02_byte_domains_last_capture_and_live_mutations(self):
  count=0;seen=set()
  for c in corpus():seen.update(self.compare(c)[0].visits);count+=1
  self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+316,4)));self.receipt('guest-contract',dict(cases_per_body=count,visited_words=79,all_kind_page_filled_and_owner_type_bytes=True,last_slot_uses_live_owner=True,null_final_source_preserves_prior_copies=True,captured_loop_bound_and_page=True,live_final_kind_and_filled=True,raw_and_fitted_memory_access_and_call_order_equal=True,raw_caller_temporary_identity_claimed=False))
 def test_03_aliases_and_fired_memory_prefixes(self):
  aliases=0
  for count,alias,page,mutation in itertools.product((0,1,2),(0,1,2),(0,1),(0,2,7)):self.compare(guest.Case(snapshots=2,matrices=count,alias=alias,page=page,mutation=mutation));aliases+=1
  cuts=delay=0
  for c in(guest.Case(snapshots=0),guest.Case(snapshots=1,missing=1),guest.Case(snapshots=3,missing=1),guest.Case(mutation=7),guest.Case(snapshots=2,matrices=2,alias=2)):
   initial=guest.fixture(c);done=guest.Oracle(self.truth,initial,c).run()
   for cut in range(done.all_accesses):
    pair=[]
    for w in(self.truth,self.raw,self.fitted):
     m=guest.Oracle(w,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(guest.observable(pair[0]),guest.observable(pair[1],raw_fault=True));self.assertEqual(guest.state(pair[0]),guest.state(pair[-1]));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_cases_per_body=aliases,fired_prefix_triples=cuts,delay_slot_cuts=delay,raw_memory_call_access_and_saved_register_state_equal=True,raw_fault_PC_mapping={'40':42},fitted_literal_full_state_equal=True,raw_caller_temporaries_excluded=True,portable_C_fault_claimed=False))
 def test_04_original_indirect_call_and_registry(self):
  start,end=0x15188C00,0x15188C24;window=list(struct.unpack_from('>9I',self.rom,0x1B60B0));registry=(self.out/'registry.bin').read_bytes();self.assertEqual(registry,self.rom[0x232040:0x232048]);count=0
  for active,kind,filled,mutation in itertools.product((0,1),(0,2,3),(0,255),(0,7)):
   c=guest.Case(snapshots=kind,filled=filled,mutation=mutation);initial=guest.fixture(c);initial[guest.RECORD]=active
   for i,b in enumerate(registry):initial[guest.REGISTRY+i]=b
   expected,calls,packets=guest.reference(initial,c)if active==0 else(initial,[(0x15188F84,(guest.RECORD,))],[]);pair=[]
   for w in(self.truth,self.fitted):
    code=dict(zip(range(match.ENTRY,match.ENTRY+316,4),w));code[end]=0;m=guest.Oracle(window,initial,c,start,connected=code);m.r[16]=guest.RECORD;m.r[21]=guest.REGISTRY;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((guest.public(m.memory),m.calls,m.copy_snapshots),(guest.public(expected),([(match.ENTRY,(guest.RECORD,))]+calls)if active==0 else calls,packets));self.assertEqual(m.r[2],m.memory[guest.RECORD+3]);pair.append(m)
   self.assertEqual(guest.state(pair[0]),guest.state(pair[1]));count+=1
  words=struct.unpack_from('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(words)if match.ENTRY<=w<match.ENTRY+316],[0x232040]);self.assertFalse([w for w in words if w>>26 in(2,3)and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+316]);self.receipt('callers',dict(cases_per_body=count,actual_window_words=9,parent='func_15188B74',parent_complete_execution_claimed=False,registry_entries=2,callback_index=0,one_argument=True,return_overwritten=True,paired_callback_bounded=True))
 def test_05_original_count_and_overlap_safe_copy(self):
  count=0;seen=set();jump=(self.out/'count-jump-table.bin').read_bytes();before=self.prepared['predecessor_elf'].read_bytes()
  for t in range(256):
   c=guest.Case(type=t,snapshots=t%4,matrices=t%3,page=t&1,alias=t%3,residue=t%4,source_residue=(t//4)%4,missing=(t%7==0));initial=guest.fixture(c)
   for i,b in enumerate(jump):initial[guest.JUMP+i]=b
   expected,calls,packets=guest.reference(initial,c);pair=[]
   for w in(self.truth,self.fitted):
    m=guest.Oracle(w,initial,c,connected=guest.helpers(self.rom)).run();self.assertEqual((guest.public(m.memory),m.calls,m.copy_snapshots),(guest.public(expected),calls,packets),c);seen.update(m.visits);pair.append(m)
   self.assertEqual(guest.state(pair[0]),guest.state(pair[1]));count+=1
  for e,p,n in((guest.COUNT,0x5AFD0,25),(guest.COPY,0x23A10,196)):
   at=match.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4],self.rom[p:p+n*4])
  self.assertEqual(jump,before[match.elf_slot_offset(before,guest.JUMP,256):match.elf_slot_offset(before,guest.JUMP,256)+256]);self.assertTrue(set(range(guest.COUNT,guest.COUNT+100,4))<=seen);self.receipt('connections',dict(cases_per_body=count,count_helper_words=25,bcopy_slot_words=196,both_baselines_exact=True,copy_words_visited=len(seen&set(range(guest.COPY,guest.COPY+784,4))),forward_backward_identical_and_unaligned_copies=True,signed_ADD_overflow_distinction_retained=True))
 def test_06_rebased_code_and_data(self):
  count=0
  for j,entry in enumerate((0x15007FF0,0x16008010,0x1700FFF0)):
   s=dict(D_800BE9C0=0x81007FFF+j*0x10002,func_1502DB20=entry+0x10004,bcopy=entry+0x20008);images=[linked(p,entry,'rebase-%d-%d'%(j,i),self.out,s)for i,p in enumerate((self.out/'qualified-owner.o',self.prepared['qualified_object']))]
   for c in list(corpus())[::101]:self.compare(c,images,entry,s);count+=1
  self.receipt('rebases',dict(independent_GNU_links=6,cases_per_body=count,HI_LO_and_two_R26_bindings=True,raw_observable_contract_equal=True))
 def test_07_compiled_semantic_negatives(self):
  rows={};cases=[guest.Case(),guest.Case(snapshots=2,page=2),guest.Case(mutation=1),guest.Case(mutation=2),guest.Case(filled=255),guest.Case(missing=1,filled=7),guest.Case(snapshots=0,mutation=1)]
  for name,fragment in controls().items():
   obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+fragment,'negative-'+name);self.assertFalse(diag);ws=linked(obj,match.ENTRY,'negative-link-'+name,self.out);killed=False
   for c in cases:
    initial=guest.fixture(c);expected,calls,packets=guest.reference(initial,c)
    try:m=guest.Oracle(ws,initial,c).run();killed=(guest.public(m.memory),m.calls,m.copy_snapshots)!=(guest.public(expected),calls,packets)
    except(AssertionError,KeyError):killed=True
    if killed:break
   self.assertTrue(killed,name);rows[name]=dict(compiled=True,public_counterexample=True)
  self.receipt('compiled-controls',rows)
 def test_08_native32_copy_transactions_and_complete_banks(self):
  text,n,copies=native_program();p=self.out/'native.c';p.write_text(text)
  for opt in('-O0','-O2','-O3'):
   binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
  self.receipt('native-contract',dict(cases_per_profile=n,expected_copy_transactions=copies,profiles=['O0','O2','O3'],compiled_controls=len(controls()),all_controls_effective_in_each_profile=True,SDK_descriptor20=True,actual_C_count_helper=True,two_complete_65536_byte_bank_checksums=True,overlap_safe_copy_transactions=True,all_record_fields_and_pointer_updates=True,UBSan_traps=True,guest_unaligned_cases_excluded=True))

if __name__=='__main__':unittest.main()
