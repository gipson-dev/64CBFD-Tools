"""Owner cache registration: complete owner/image, original callers/helpers and native32."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_owner_cache_registration_15188810_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner,body as source_body
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_owner_cache_registration_15188810_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def corpus():
 for t,found in itertools.product(range(256),(-1,0)):
  yield guest.Case(nodes=1,match=found,type=t,count=1+t%3,mode=0xA5A50000|t,phase=8*(t&1))
 for found,old,timer,mode,phase in itertools.product((0,2,4),(-32768,-1,0,32767),guest.TIMERS,(0,255,0xFFFFFF80),(0,8)):
  yield guest.Case(nodes=4,match=found,old=old,timer=timer,mode=mode,phase=phase)
 for nodes,outcome,count,mutation,phase,residue in itertools.product((0,4),range(3),(0,1,3,-1),(0,1,2,4,8,16,31),(0,8),(0,1,3)):
  yield guest.Case(nodes=nodes,outcome=outcome,count=count,mutation=mutation,phase=phase,residue=residue)

def controls():
 b=match.SELECTED
 rows=dict(unsigned_timer=('node->timer < timer','(u16)node->timer < (u32)timer'),narrow_timer=('node->timer < timer','node->timer < (s16)timer'),decrease_timer=('node->timer < timer','1'),ignore_match=('(s32)owner == node->key','0'),mode_byte=('node->mode = mode','node->mode = mode >> 8'),header_size=('sizeof(OwnerBufferNode15188810)','20'),owner_type=('owner[4]','owner[5]'),buffer_scale=('(count * 3) << 7','(count * 3) << 6'),buffer_flags=('allocate_memory(size, 1, 1, 1)','allocate_memory(size, 1, 1, 0)'),rollback=('        func_10004074(node);','        (void)node;'),active_byte=('node->active = 0','node->active = 1'),retained_byte=('    node->recordSize = 20;','    node->recordSize = 20;\n    node->retained05 = 0;'),tail_word=('((OwnerBufferNode15188810 *)node)->cleared14 = 0','((OwnerBufferNode15188810 *)node)->cleared14 = 1'),short_clear=('bzero(buffer, size)','bzero(buffer, size - 1)'),wrong_head=('(ListNode15188A58 *)&D_800DF7C8','(ListNode15188A58 *)&node'),missing_append=('    func_15188A58(node, (ListNode15188A58 *)&D_800DF7C8);','    (void)node;'))
 result={n:b.replace(a,z)for n,(a,z)in rows.items()}
 result['cached_type']=b.replace('    u32 count;','    u8 type = owner[4];\n    u32 count;').replace('func_1502DB20(owner[4])','func_1502DB20(type)')
 assert all(v!=b for v in result.values());return result

def linked(obj,entry,label,out,defs=None):
 defs=guest.symbols()if defs is None else defs;t,fs,rs=parse_object(obj);f=fs[match.FUNCTION];assembly,unknown=emit_function(t,f,rs,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

def native_program():
 # Native pointers are real, aligned objects. Guest-private frame aliases are
 # excluded; fields and complete buffers come from the independent reference.
 cases=list(dict.fromkeys(replace(c,phase=0,mutation=c.mutation&~4)for c in corpus()));rows=[]
 ids={0:0,**{guest.NODES+32*i:i+1 for i in range(4)},guest.OTHER:5,guest.NEW:6}
 for c in cases:
  initial=guest.fixture(c);wanted,calls=guest.reference(initial,c);nodes=[]
  for p in(*[guest.NODES+32*i for i in range(4)],guest.OTHER,guest.NEW):
   key=guest.read(wanted,p+16);nxt=guest.read(wanted,p+12);buf=guest.read(wanted,p+8);nid=ids.get(nxt,-1);hasbuf=buf==guest.BUFFER+c.residue
   if nid<0:assert bytes(wanted[p+12+i]for i in range(4))==bytes(initial[p+12+i]for i in range(4))
   if not hasbuf:assert bytes(wanted[p+8+i]for i in range(4))==bytes(initial[p+8+i]for i in range(4))
   nodes.append('{{%s},%d,0x%08Xu,%d,%d,0x%08Xu}'%(','.join(str(wanted[p+i])for i in range(6)),guest.signed16(guest.read(wanted,p+6,2)),0 if key==guest.OWNER else key,nid,int(hasbuf),guest.read(wanted,p+20)))
  digest=2166136261
  for i in range(4096):digest=((digest^wanted[guest.BUFFER+i])*16777619)&0xFFFFFFFF
  counts=[sum(t==guest.symbols()[n]for t,a in calls)for n in('allocate_memory','func_1502DB20','func_10004074','bzero','func_15188A58')]
  rows.append('{%d,%d,%d,%d,0x%08Xu,%d,%d,%d,%d,%d,%d,0x%08Xu,{%s},{%s}}'%(c.nodes,c.match,c.old,c.timer,c.mode,c.count,c.type,c.outcome,c.mutation,c.residue,ids[guest.read(wanted,guest.HEAD)],digest,','.join(map(str,counts)),','.join(nodes)))
 helper=source_body((ROOT/match.SOURCE).read_text(),'func_15188A58').replace('func_15188A58','append_impl',1)
 counter=source_body((ROOT/'conker/src/game/generated_58F80.c').read_text(),'func_1502DB20').replace('func_1502DB20','count_impl',1)
 text=match.ISOLATED_HEADER+r'''
typedef char prefix_size[sizeof(ListNode15188A58)==20?1:-1];
typedef char wrapper_size[sizeof(OwnerBufferNode15188810)==24?1:-1];
typedef char tail_offset[__builtin_offsetof(OwnerBufferNode15188810,cleared14)==20?1:-1];
static OwnerBufferNode15188810 nodes[4],other,fresh;
static u8 actor[256],storage[4112],saved[6][24];
u8 *D_800DF7C8;ListNode15188A58 *D_800DF7CC;u16 D_800C4ED0[256];
static u32 calls[5],bad,outcome,mutation,residue,expectedSize;
static u8 *buffer;
static void effects(u32 stage){u32 i;
 if(stage==0){if(mutation&1){other.prefix.next=(ListNode15188A58*)D_800DF7C8;D_800DF7C8=(u8*)&other;}if(mutation&2)actor[4]^=0x5A;}
 if(stage==1&&(mutation&8)){fresh.prefix.retained05=0xED;for(i=0;i<4096;i++)storage[i]=0xD3;}
 if(stage==2&&(mutation&16)){fresh.prefix.mode=0xAB;fresh.prefix.timer=(s16)0x8123;}
}
s32 allocate_memory(s32 n,s32 tag,s32 pool,s32 flags){u32 stage=calls[0]++;if(stage>1||tag!=1||pool!=(stage?1:0)||flags!=(stage?1:0)||(u32)n!=(stage?expectedSize:24))bad=1;effects(stage);return stage?(outcome==2?(s32)buffer:0):(outcome?(s32)&fresh:0);}
void func_10004074(void*p){calls[2]++;if(p!=&fresh)bad=1;}
void bzero(void*p,int n){s32 i;calls[3]++;if(p!=buffer||(u32)n!=expectedSize)bad=1;if(n>4096){bad=1;return;}for(i=0;i<n;i++)((u8*)p)[i]=0;effects(2);}
'''+helper+'\n'+counter+r'''
s32 func_1502DB20(s32 type){s32 n;calls[1]++;if(type!=actor[4])bad=1;n=count_impl(type);expectedSize=(u32)n*384;return n;}
void func_15188A58(ListNode15188A58*p,ListNode15188A58*head){calls[4]++;if(p!=(ListNode15188A58*)&fresh||head!=(ListNode15188A58*)&D_800DF7C8){bad=1;return;}append_impl(p,head);}
'''
 names=['selected',*controls()]
 for name,fragment in dict(selected=match.SELECTED,**controls()).items():text+=fragment.replace(match.FUNCTION,name,1)+'\n'
 special='||'.join('i==%d'%i for i in sorted(guest.SPECIAL))
 text+=r'''
typedef struct {u8 bytes[6];s16 timer;u32 key;s32 next;u32 buffer;u32 tail;} Expected;
typedef struct {s32 nodes,match,old,timer;u32 mode;s32 count,type,outcome;u32 mutation,residue,head,digest;u32 calls[5];Expected expected[6];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static ListNode15188A58 *pointer(u32 n){return n==0?0:n<5?&nodes[n-1].prefix:n==5?&other.prefix:&fresh.prefix;}
static int check(void(*fn)(u8*,s32,s32),const Row*r){u32 i,j,h=2166136261u;OwnerBufferNode15188810 *all[6]={nodes,nodes+1,nodes+2,nodes+3,&other,&fresh};
 for(i=0;i<256;i++)actor[i]=(u8)(i*13+89);actor[4]=r->type;
 for(i=0;i<256;i++)D_800C4ED0[i]=1+i%3+('''+special+r'''?4:0);
 D_800C4ED0[r->type]=(u16)(r->count+('''+'||'.join('r->type==%d'%i for i in sorted(guest.SPECIAL))+r'''?4:0));
 for(i=0;i<6;i++){for(j=0;j<24;j++)((u8*)all[i])[j]=(u8)((j+(i<4?32*i:0))*13+89);all[i]->cleared14=((u32)((u8*)all[i])[20]<<24)|((u32)((u8*)all[i])[21]<<16)|((u32)((u8*)all[i])[22]<<8)|((u8*)all[i])[23];if(i<4){all[i]->prefix.key=(i==(u32)r->match||(r->match==4&&(i==0||i==2)))?(s32)actor:(s32)(0x38000+i);all[i]->prefix.next=i+1<(u32)r->nodes?pointer(i+2):0;all[i]->prefix.timer=r->old;}else {all[i]->prefix.timer=(s16)0xA7B4;if(i==4){all[i]->prefix.next=0;all[i]->prefix.key=0x2D555;}else all[i]->prefix.key=0x29364350;}for(j=0;j<24;j++)saved[i][j]=((u8*)all[i])[j];}
 for(i=0;i<4096;i++)storage[i]=(u8)((i+16)*13+89);buffer=storage+r->residue;
 D_800DF7C8=(u8*)pointer(r->nodes?1:0);for(i=0;i<5;i++)calls[i]=0;bad=0;outcome=r->outcome;mutation=r->mutation;residue=r->residue;expectedSize=0;fn(actor,r->timer,r->mode);
 if(D_800DF7C8!=(u8*)pointer(r->head))bad=1;for(i=0;i<5;i++)if(calls[i]!=r->calls[i])bad=1;
 for(i=0;i<6;i++){const Expected*e=&r->expected[i];ListNode15188A58*n=&all[i]->prefix;for(j=0;j<6;j++)if(((u8*)n)[j]!=e->bytes[j])bad=1;if(n->timer!=e->timer||all[i]->cleared14!=e->tail||(u32)n->key!=(e->key?e->key:(u32)actor))bad=1;
 if(e->next>=0){if(n->next!=pointer(e->next))bad=1;}else for(j=12;j<16;j++)if(((u8*)n)[j]!=saved[i][j])bad=1;
 if(e->buffer){if(n->buffer!=buffer)bad=1;}else for(j=8;j<12;j++)if(((u8*)n)[j]!=saved[i][j])bad=1;}
 for(i=0;i<4096;i++)h=(h^storage[i])*16777619u;if(h!=r->digest)bad=1;return !bad;
}
static int run(void){u32 i,j;u32 killed['''+str(len(names))+r''']={0};void(*functions[])(u8*,s32,s32)={'''+','.join(names)+r'''};
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
 for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return text,len(cases)

class OwnerCacheTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.truth==cls.fitted
 def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def compare(self,c,images=None,entry=match.ENTRY,s=None,initial=None):
  s=guest.symbols()if s is None else s;initial=guest.fixture(c,s)if initial is None else initial;expected,calls=guest.reference(initial,c,s);pair=[]
  for words,raw in images or((self.truth,False),(self.raw,True),(self.fitted,False)):
   memory=guest.swapped(initial,guest.STACK+c.phase)if raw else initial;m=guest.Oracle(words,memory,c,entry,s).run();self.assertEqual((guest.public(m.memory),m.calls),(guest.public(expected),calls),c);pair.append((m,raw))
  self.assertTrue(all(guest.state(m,raw)==guest.state(pair[0][0],pair[0][1])for m,raw in pair));return pair
 def test_01_owner_Make_closed_spill_guards_and_entire_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(79,56,2,14,14,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['exclusions']),(3,15,237,0));self.assertEqual(match.certificate(self.blob,self.refs)['raw_spill'],36)
  for at in range(316):
   b=bytearray(self.blob);b[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(b),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),2)
  for index in indices:
   changed=[dict(r)for r in rows];changed[index]['expected']='0x%08X'%(int(changed[index]['expected'],16)^1);p=self.out/'rejected-guard.csv'
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(changed)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/1B5CC0.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316)):
   b=bytearray(after);b[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(b),self.rom[match.ROM:match.ROM+316])
 def test_02_signed_timers_live_count_aliases_and_raw_home_mapping(self):
  count=0;seen=set()
  for c in corpus():seen.update(self.compare(c)[0][0].visits);count+=1
  self.assertEqual(set(range(match.ENTRY,match.ENTRY+316,4))-seen,{match.ENTRY+96});self.receipt('guest-contract',dict(cases_per_body=count,visited_words=78,dead_duplicate_word=24,all79_literal=True,all_mode_and_owner_type_bytes=True,signed16_vs_signed32=True,lowword_unsigned_size=True,raw_private_home_permutation=True,retained_byte5_and_new_tail=True))
 def test_03_heap_aliases_and_fired_literal_faults(self):
  aliases=0
  for address in(guest.NEW,guest.NEW+4,guest.NEW+8,guest.NODES):
   for mutation in(0,3,8,16):
    c=guest.Case(buffer=address,count=1,mutation=mutation);initial=guest.fixture(c)
    for i in range(4096):initial[address+i]=initial.get(address+i,(i*13+89)&255)
    self.compare(c,initial=initial);aliases+=1
  count=delay=0
  for c in(guest.Case(nodes=4,match=2,timer=65535),guest.Case(outcome=0),guest.Case(count=0),guest.Case(outcome=1),guest.Case(mutation=31,residue=3),guest.Case(count=-1)):
   initial=guest.fixture(c);done=guest.Oracle(self.truth,initial,c).run()
   for cut in range(done.all_accesses):
    pair=[]
    for words,raw in((self.truth,False),(self.raw,True),(self.fitted,False)):
     m=guest.Oracle(words,guest.swapped(initial,guest.STACK+c.phase)if raw else initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append((m,raw))
    self.assertTrue(all(guest.state(m,raw)==guest.state(pair[0][0])for m,raw in pair));count+=1;delay+=pair[0][0].delay_of is not None
  self.receipt('aliases-faults',dict(heap_aliases_per_body=aliases,fired_prefix_triples=count,delay_slot_cuts=delay,raw_private_memory_projected_by_closed_four_byte_swap=True,fitted_literal_private_bytes_exact=True,portable_frame_alias_claimed=False))
 def test_04_original_packed_caller_and_four_other_windows(self):
  caller=0x1506EE60;body=list(struct.unpack_from('>19I',self.rom,0x9C310));count=0
  for packed,outcome,phase in itertools.product((0,1,65535,0x80000001,0xFFFF8000),(0,1,2),(0,8)):
   c=guest.Case(timer=packed&65535,mode=guest.u32(guest.signed(packed)>>16),outcome=outcome,phase=phase);initial=guest.fixture(c);guest.put(initial,0x800D154C,guest.OWNER);guest.put(initial,0x800D1580,packed);expected,calls=guest.reference(initial,c,entered=guest.STACK+phase-24)if packed else(initial,[(0x15188A9C,(guest.OWNER,))]);pair=[]
   for w in(self.truth,self.fitted):
    m=guest.Oracle(body,initial,c,caller,connected=dict(zip(range(match.ENTRY,match.ENTRY+316,4),w))).run();self.assertEqual((guest.public(m.memory),m.calls),(guest.public(expected),([(match.ENTRY,(guest.OWNER,c.timer,c.mode))]+calls)if packed else calls));pair.append(m)
   self.assertEqual(guest.state(pair[0]),guest.state(pair[1]));count+=1
  windows=((0x1502A7D0,0x1502A88C,4),(0x15054B4C,0x15054B78,11),(0x150C39B4,0x150C3A78,49),(0x150C3BF4,0x150C3C04,4));window_cases=0
  for start,end,n in windows:
   words=list(struct.unpack_from('>%dI'%n,self.rom,start-0x15000000+0x2D4B0))
   for outcome,mode in itertools.product(range(3),(0,255)):
    c=guest.Case(outcome=outcome,mode=mode)if start==0x1502A7D0 else guest.Case(outcome=outcome,timer=100,mode=0);initial=guest.fixture(c);guest.put(initial,guest.OWNER+0x2E4,1);guest.put(initial,guest.OTHER+8,0);initial[guest.OTHER+5]=mode;guest.put(initial,guest.STACK+0x4C,guest.OTHER);expected,calls=guest.reference(initial,c);pair=[]
    for w in(self.truth,self.fitted):
     code=dict(zip(range(match.ENTRY,match.ENTRY+316,4),w));code[end]=0;m=guest.Oracle(words,initial,c,start,connected=code);m.r[16]=guest.OTHER if start==0x1502A7D0 else guest.OWNER;m.r[3]=guest.OTHER;m.r[5]=c.timer;m.r[6]=c.mode
     # The two effect callers explicitly zero A2; the event caller sign-extends its byte.
     passed=replace(c,mode=guest.u32((mode^128)-128))if start==0x1502A7D0 else replace(c,mode=0)if start in(0x150C39B4,0x150C3BF4)else c
     wanted,pcalls=guest.reference(initial,passed);m.code=WindowCode(m.code,m);m.code.ends=(end,)
     with self.assertRaises(WindowBoundary):m.run()
     self.assertEqual((guest.public(m.memory),m.calls),(guest.public(wanted),[(match.ENTRY,(guest.OWNER,c.timer,passed.mode))]+pcalls));pair.append(m)
    self.assertEqual(guest.state(pair[0]),guest.state(pair[1]));window_cases+=1
  ws=struct.unpack_from('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w>>26 in(2,3)and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+316],[0x57C80,0x82014,0x9C334,0xF0F1C,0xF10A8]);self.receipt('callers',dict(full_wrapper_words=19,full_wrapper_cases=count,other_original_windows=4,window_cases=window_cases,all_five_call_sites=True,return_ignored=True,complete_other_parents_claimed=False))
 def test_05_original_count_allocator_zero_and_append(self):
  count=0;seen=set();jump=(self.out/'count-jump-table.bin').read_bytes();before=self.prepared['predecessor_elf'].read_bytes()
  cases=[guest.Case(type=t,nodes=t%5,count=t%3,mutation=t%4,residue=t%4)for t in range(256)]+[guest.Case(count=c,outcome=o,nodes=4)for c,o in itertools.product((-4,-1,0,1,3),range(3))]
  at=match.elf_slot_offset(before,guest.JUMP,256);self.assertEqual(jump,before[at:at+256]);self.assertEqual(jump,self.rom[0x23B8B8:0x23B9B8])
  for c in cases:
   initial=guest.fixture(c)
   for i,b in enumerate(jump):initial[guest.JUMP+i]=b
   expected,calls=guest.reference(initial,c);pair=[]
   for w in(self.truth,self.fitted):
    m=guest.Oracle(w,initial,c,connected=guest.helper_code(self.rom)).run();self.assertEqual((guest.public(m.memory),[(p,a)for p,a in m.calls if p!=guest.CORE]),(guest.public(expected),calls));roots=[a for t,a in m.calls if t==guest.ALLOC];cores=[a for t,a in m.calls if t==guest.CORE];self.assertEqual(cores,[(a[0],a[1],a[2],0,a[3])for a in roots]);seen.update(m.visits);pair.append(m)
   self.assertEqual(guest.state(pair[0]),guest.state(pair[1]));count+=1
  for row in json.loads((self.out/'helper-audit.json').read_text())[:5]:
   e,p,n=int(row['entry'],16),int(row['rom'],16),row['words'];at=match.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4],self.rom[p:p+n*4])
  self.assertTrue(set(range(guest.COUNT,guest.COUNT+100,4))<=seen);self.receipt('connections',dict(cases_per_body=count,count_helper_words=25,all_count_words_visited=True,allocator_wrapper_words=11,bzero_slot_words=40,append_words=17,baseline_all_five_helpers_exact=True,free_and_allocator_core_bounded=True,original_jump_table_bytes=256))
 def test_06_rebases_and_private_slot_invariance(self):
  count=0
  for j,entry in enumerate((0x15007FF0,0x16008010,0x1700FFF0)):
   s={n:entry+0x10004*(i+1)if n!='D_800DF7C8'else 0x81007FFC+j*0x10004 for i,n in enumerate(guest.symbols())};images=[(linked(p,entry,'rebase-%d-%d'%(j,i),self.out,s),i==0)for i,p in enumerate((self.out/'qualified-owner.o',self.prepared['qualified_object']))]
   for c in list(corpus())[::131]:self.compare(c,images,entry,s);count+=1
  self.receipt('rebases',dict(independent_GNU_links=6,cases_per_body=count,all_six_external_bindings_rebased=True,closed_home_permutation=True))
 def test_07_compiled_semantic_counterexamples(self):
  receipts={};cases=[guest.Case(),guest.Case(count=0),guest.Case(outcome=1),guest.Case(nodes=1,match=0,old=-1,timer=-32769),guest.Case(nodes=1,match=0,old=32767,timer=65535),guest.Case(nodes=1,match=0,old=32767,timer=-1),guest.Case(mutation=2),guest.Case(mutation=8)]
  for name,fragment in controls().items():
   obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+fragment,'negative-'+name);self.assertFalse(diag);ws=linked(obj,match.ENTRY,'negative-link-'+name,self.out);killed=False
   for c in cases:
    initial=guest.fixture(c);expected,calls=guest.reference(initial,c)
    try:m=guest.Oracle(ws,initial,c).run();killed=(guest.public(m.memory),m.calls)!=(guest.public(expected),calls)
    except(AssertionError,KeyError):killed=True
    if killed:break
   self.assertTrue(killed,name);receipts[name]=dict(compiled=True,public_counterexample=True)
  self.receipt('compiled-controls',receipts)
 def test_08_native32_shared_prefix_and_actual_C_helpers(self):
  text,n=native_program();p=self.out/'native.c';p.write_text(text)
  for opt in('-O0','-O2','-O3'):
   binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
  self.receipt('native-contract',dict(profiles=['O0','O2','O3'],cases_per_profile=n,compiled_controls=len(controls()),all_controls_effective_in_each_profile=True,SDK_types=True,prefix20_wrapper24=True,complete_node_fields_and_4096_buffer_bytes=True,actual_count_and_append_C=True,UBSan_traps=True,private_frame_aliases_excluded=True))

if __name__=='__main__':unittest.main()
