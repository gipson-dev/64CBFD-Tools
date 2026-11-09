"""Endpoint event callback: source, whole owner/image, actual dispatcher and native32."""
from dataclasses import replace
import csv,io,itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_endpoint_event_update_150ef910_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_endpoint_event_update_150ef910_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def corpus():
 for cmd in range(256):
  for upper in(0,0xA5A50000):yield guest.Case(command=cmd|upper,first=(0x300000,0x310000,0x320000)[cmd%3],second=(0x310000,0x300000,0x320000)[cmd%3],mode=cmd%4,phase=8*(cmd%2))
 for cmd,a,b,same,tag,code,mode,phase in itertools.product((0,45,67),range(3),range(3),(0,1),(0,1),(0,1),(0,1,3,8),(0,8)):
  after=0x300000 if same else 0x310000;refs=(0x300000,after,0x320000)
  yield guest.Case(command=cmd,first=refs[a],second=refs[b],after=after,event_identity=0x12^tag,event_code=0xA7^code,mode=mode,phase=phase)

def aliases():
 for cmd,off,relation,mode,phase in itertools.product((0,45,67),range(-4,24,4),range(3),(0,1,3,4),(0,8)):
  yield guest.Case(command=cmd,event=guest.OWNER+0x110+off,first=(0x300000,0x310000,0x320000)[relation],second=(0x310000,0x300000,0x320000)[relation],mode=mode,phase=phase)

def controls():
 b=match.SELECTED
 start=b.index('        if (event->before == links[1].owner)');end=b.index('    } else if (command == 0x43)',start)
 rows=dict(wrong_zero=b.replace('command == 0)','command == 1)'),wrong_swap=b.replace('command == 0x2D','command == 0x2C'),wrong_code=b.replace('command == 0x43','command == 0x42'),
  require_both=b.replace('current == first || firstIdentity == currentIdentity','current == first && firstIdentity == currentIdentity'),
  wrong_first_identity=b.replace('links[0].identity = event->after_identity','links[0].identity = event->before_identity'),
  wrong_second_identity=b.replace('links[1].identity = event->after_identity','links[1].identity = event->before_identity'),
  missing_second=b[:start]+b[end:],missing_release=b.replace('func_1516972C((struct102 *)owner);','(void)owner;'),
  missing_discriminator=b.replace('&& ((u8 *)event)[5] == ((u8 *)links)[0xD]',''),wrong_discriminator=b.replace('((u8 *)links)[0xD]','((u8 *)links)[0xC]'),
  wrong_first_pointer=b.replace('links[0].owner = event->after','links[0].owner = event->before'))
 cached=b.replace('        u8 *current = links[0].owner;\n        u8 *first = event->before;\n        if (first == current)', '        u8 *current = links[0].owner;\n        u8 *first = event->before;\n        u8 *cachedAfter = event->after;\n        u8 cachedBeforeIdentity = event->before_identity;\n        u8 cachedAfterIdentity = event->after_identity;\n        if (first == current)')
 a=cached.index('        if (event->before == links[1].owner)');z=cached.index('    } else if (command == 0x43)',a)
 part=cached[a:z].replace('event->before_identity','cachedBeforeIdentity').replace('event->after_identity','cachedAfterIdentity').replace('event->before','first').replace('event->after','cachedAfter')
 rows['cached_message']=cached[:a]+part+cached[z:];return rows

def linked(obj,entry,label,out,defs=None):
 defs=defs or guest.symbols();text,functions,bindings=parse_object(obj);f=functions[match.FUNCTION];assembly,unknown=emit_function(text,f,bindings,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

class EndpointEventTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.fitted==cls.truth
 def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def compare(self,c,images=None,entry=match.ENTRY,defs=None,initial=None):
  initial=guest.fixture(c)if initial is None else initial;expected,calls,snaps=guest.reference(initial,c,helper=(defs or guest.symbols())['func_1516972C']);models=[]
  for words in images or(self.truth,self.raw,self.fitted):
   m=guest.Oracle(words,initial,c,entry,syms=defs).run();self.assertTrue((guest.public(m.memory),m.calls,m.snapshots)==(guest.public(expected),calls,snaps),(c,'public contract'));models.append(m)
  self.assertTrue(all(guest.full_state(m)==guest.full_state(models[0])for m in models),(c,'complete private state'));return models
 def test_01_owner_actual_Make_guard_and_whole_image_rejections(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(79,24,1,43,43));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions']),(3,44));self.assertEqual((q['strict_changed_bytes'],q['exclusions'],q['named_metadata_rows']),(223,0,0));proof=match.certificate(self.blob,self.refs);self.assertEqual((proof['commutative_branch_words'],proof['schedule_changes'],proof['insertions'],proof['omissions']),([37],0,0,0))
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom[:len(self.rom)&~3]);self.assertEqual([i*4 for i,w in enumerate(ws)if match.ENTRY<=w<match.ENTRY+316],[0x22EA38]);self.assertFalse([w for w in ws if w>>26 in(2,3)and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+316]);self.assertEqual(guest.TABLE+4*5,0x80089F78)
  for at in range(316):
   bad=bytearray(self.blob);bad[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(bad),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),1)
  for index in indices:
   altered=[dict(r)for r in rows];altered[index]['expected']='0x%08X'%(int(altered[index]['expected'],16)^1);p=self.out/'rejected-guard.csv'
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(altered)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/11C2B0.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+316])
 def test_02_guest_commands_live_links_and_reachable_words(self):
  seen=set();count=0
  for c in corpus():seen.update(self.compare(c)[0].visits);count+=1
  self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+316,4))-{match.ENTRY+4*i for i in(36,58)})
  for cmd in(1,44,66,255,0xA5A50001):
   c=guest.Case(command=cmd);initial=guest.fixture(c)
   for a in range(guest.OWNER-64,guest.OWNER+0x240):initial.pop(a,None)
   for a in range(guest.EVENT-64,guest.EVENT+64):initial.pop(a,None)
   self.compare(c,initial=initial)
  self.receipt('guest-contract',dict(cases_per_body=count,visited_words=len(seen),literal_words=79,dead_duplicate_words=[36,58],all_command_bytes_and_high_bits=True,ignored_payload_unmapped=True,raw_fitted_complete_state_equal=True))
 def test_03_aliases_and_literal_fault_prefixes(self):
  count=0
  for c in aliases():self.compare(c);count+=1
  cuts=delay=0
  for cmd,relation,tag,code,mode,phase in itertools.product((0,45,67,255),range(3),(0,1),(0,1),(0,3),(0,8)):
   c=guest.Case(command=cmd,first=(0x300000,0x310000,0x320000)[relation],event_identity=0x12^tag,event_code=0xA7^code,mode=mode,phase=phase);initial=guest.fixture(c);model=guest.Oracle(self.truth,initial,c).run()
   for cut in range(model.all_accesses):
    pair=[guest.Oracle(words,initial,c)for words in(self.truth,self.raw,self.fitted)]
    for m in pair:
     m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
    self.assertTrue(all(guest.full_state(m)==guest.full_state(pair[0])and(m.current_pc,m.delay_of)==(pair[0].current_pc,pair[0].delay_of)for m in pair));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_cases_per_body=count,fired_prefix_triples=cuts,delay_slot_cuts=delay,complete_raw_fitted_private_state=True,portable_C_fault_claimed=False))
 def test_04_actual_category_dispatcher(self):
  count=0;seen=set()
  for category,flags,cmd in itertools.product(range(256),(0,0x400000),(0,45,67,0xA5A500FF)):
   c=guest.Case(command=cmd,flags=flags,category=category);pair=[]
   for words in(self.truth,self.raw,self.fitted):
    m,initial=guest.caller_machine(self.rom,words,c);expected,calls,snaps,entries=guest.caller_reference(initial,c);m.run();self.assertTrue((guest.public(m.memory),m.calls,m.snapshots,m.target_entries)==(guest.public(expected),calls,snaps,entries),c);pair.append(m);seen.update(m.visits)
   self.assertTrue(all(guest.full_state(m)==guest.full_state(pair[0])for m in pair));count+=1
  # Word 11 is a dead duplicate of the taken branch-likely delay load.
  self.assertEqual(set(range(guest.PARENT,guest.PARENT+212,4))-seen,{guest.PARENT+44})
  parent=struct.unpack_from('>53I',self.rom,guest.PARENT_ROM);self.assertEqual((parent[7],parent[9]),(0x07020004,0x10000021));self.assertNotIn(44,guest.category.OFFSETS)
  before=self.prepared['predecessor_elf'].read_bytes();p=match.elf_slot_offset(before,guest.PARENT,212);self.assertEqual(before[p:p+212],self.rom[guest.PARENT_ROM:guest.PARENT_ROM+212])
  self.receipt('callers',dict(cases_per_body=count,original_words=53,visited_words=52,dead_duplicate_words=[11],before_ELF_equals_retail=True,category=7,table_index=5,return_ignored=True,nonselected_callbacks_bounded=True))
 def test_05_connected_release_and_cursor_detach(self):
  count=0;seen=set()
  for cmd,relation,tag,kind,depth,cache in itertools.product((0,45,67),range(3),(0,1),(0,1,2,70),(-1,0,1,3),(False,True)):
   c=guest.Case(command=cmd,first=(0x300000,0x310000,0x320000)[relation],event_identity=0x12^tag,record_type=kind,depth=depth,cursor_match=cache);initial=guest.connected_fixture(c,self.rom);expected,calls,snaps=guest.reference(initial,c,connected=True);pair=[]
   for words in(self.truth,self.raw,self.fitted):
    m=guest.ConnectedOracle(words,initial,c,self.rom).run();self.assertTrue((guest.public(m.memory),m.calls,m.snapshots)==(guest.public(expected),calls,snaps),c);pair.append(m);seen.update(m.visits)
   self.assertTrue(all(guest.full_state(m)==guest.full_state(pair[0])for m in pair));count+=1
  before=self.prepared['predecessor_elf'].read_bytes();helpers=[]
  for e,p,n in guest.HELPERS:
   at=match.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4],self.rom[p:p+n*4]);visits=len(set(range(e,e+n*4,4))&seen);self.assertEqual(visits,n);helpers.append(dict(entry=hex(e),literal_words=n,visited_words=visits,before_ELF_equals_retail=True))
  self.receipt('connections',dict(cases_per_body=count,helpers=helpers,null_destructor_type=2,negative_depth=True,destructor_and_fallback_bounded=True,full_gameplay_claimed=False))
 def test_06_independent_GNU_links_and_jump_regions(self):
  from tools.tests.test_game_view_list_setup import ViewListSetupTests
  ctx=type('Original',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-endpoint-event',(ROOT/'conker/asm/11C2B0.s').read_text(),match.FUNCTION);count=links=0
  for i,entry in enumerate((match.ENTRY,0x18017FFC,0x2500FFFC)):
   defs=guest.symbols()if i==0 else dict(func_1516972C=(entry&0xF0000000)+0x5048004)
   images=[linked(p,entry,'rebase-%d-%d'%(i,j),self.out,defs)for j,p in enumerate((original,self.out/'qualified-owner.o',self.prepared['qualified_object']))];links+=3;self.assertEqual(images[0],images[2])
   for cmd,relation,tag,mode,phase in itertools.product((0,45,67,255),range(3),(0,1),(0,1,3),(0,8)):
    self.compare(guest.Case(command=cmd,first=(0x300000,0x310000,0x320000)[relation],event_identity=0x12^tag,mode=mode,phase=phase),images,entry,defs);count+=1
  self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,independent_original_raw_fitted=True,jump_region_bindings=True))
 def test_07_effective_compiled_semantic_controls(self):
  rows=controls();self.assertEqual(len(rows),12);evidence={};cases=list(corpus())+list(aliases())
  for name,body in rows.items():
   self.assertNotEqual(body,match.SELECTED);obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+body,'negative-'+name);self.assertFalse(diag);words=linked(obj,match.ENTRY,'negative-link-'+name,self.out)
   for c in cases:
    initial=guest.fixture(c);expected,calls,snaps=guest.reference(initial,c);m=guest.Oracle(words,initial,c).run()
    if(guest.public(m.memory),m.calls,m.snapshots)!=(guest.public(expected),calls,snaps):evidence[name]=dict(command=c.command,event=hex(c.event),first=hex(c.first),second=hex(c.second),mode=c.mode);break
   self.assertIn(name,evidence,name)
  self.receipt('compiled-controls',evidence)
 def test_08_native32_profiles_and_record_canaries(self):
  text,count=native_source();out=self.out/'native';out.mkdir(exist_ok=True)
  for opt in('-O0','-O2','-O3'):
   path=out/(opt[1:]+'.c');binary=path.with_suffix('.elf');path.write_text(text);p=subprocess.run([*native_command(opt),'-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);p=subprocess.run([str(binary)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.returncode,p.stdout,p.stderr))
  self.receipt('native-contract',dict(cases_per_profile=count,profiles=['O0','O2','O3'],effective_controls=sorted(n for n in controls()if n!='cached_message'),trap_UBSan=True,typed_link_event_and_pointer_layout=True,whole_record_canaries=True,guest_overlapping_packets_excluded=True))

def native_source():
 from tools.experiments.game_actor_category_callback_match import SELECTED as parent
 rows={'selected':match.SELECTED,**{n:b for n,b in controls().items()if n!='cached_message'}}
 bodies='\n'.join(b.replace(match.FUNCTION,n).replace('void '+n+'(', '__attribute__((noinline,noclone)) void '+n+'(')for n,b in rows.items())
 checks='\n'.join('if(variant(%s)!=%d)return %d;'%(n,0 if n=='selected'else 23,40+i)for i,n in enumerate(rows))
 return match.ISOLATED_HEADER+'''
typedef char LinkSize[sizeof(EmbeddedOwnerLink)==8?1:-1];
typedef char EventSize[sizeof(OwnerLinkEvent)==12?1:-1];
typedef char PointerWidth[sizeof(void*)==4&&sizeof(s32)==4?1:-1];
typedef char IdentityOffset[__builtin_offsetof(EmbeddedOwnerLink,identity)==4?1:-1];
typedef void(*Callback)(u8*,s32,u8);
static u8 *arena,expected[640],references[6][256];
static OwnerLinkEvent packet;static Callback active;
static u32 calls,last,mode,otherCalls;
static void *allocate(u32 size){u32 old,got,begin,end;
 __asm__ volatile("int $0x80":"=a"(old):"0"(45),"b"(0):"memory","cc");
 begin=(old+15)&~15u;end=begin+size;
 __asm__ volatile("int $0x80":"=a"(got):"0"(45),"b"(end):"memory","cc");
 return got<end?0:(void*)begin;}
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){
 calls++;last=(u32)p;if(mode&1)((u8*)p)[0x3C]^=0x55;
 if(mode&2)((EmbeddedOwnerLink*)((u8*)p+0x110))->owner=references[5];}
''' + bodies + '''
static void target(void*p,s32 e,u8 c){active(p,e,c);}
static void other(void*p,s32 e,u8 c){otherCalls++;}
void(*D_80089F64[11])(void*,s32,u8)={other,other,other,other,other,target,other,other,other,other,other};
''' + parent + '''
static int one(Callback fn,u32 cmd,u32 first,u32 second,u32 same,u32 tag,u32 disc,u32 plan,u32 root,u32 category,u32 flag){
 u32 i,j,which,want=0,selected=!root||(flag&&category==7);u8 *owner=arena+32;
 EmbeddedOwnerLink *links=(EmbeddedOwnerLink*)(owner+0x110),wanted[2];
 for(i=0;i<640;i++)arena[i]=(u8)(i*13+37);
 packet.before=references[0];packet.after=same?packet.before:references[1];
 packet.before_identity=0x56;packet.after_identity=0xE7;
 links[0].owner=first==0?packet.before:first==1?packet.after:references[2];
 links[1].owner=second==0?packet.before:second==1?packet.after:references[2];
 links[0].identity=(u8)(((u8*)&packet)[4]^tag);links[1].identity=0x34;
 ((u8*)links)[13]=(u8)(((u8*)&packet)[5]^disc);
 owner[0x19]=(u8)category;*(u32*)(owner+0x58)=flag?0x400000:0;
 mode=plan?3:0;calls=last=otherCalls=0;
 for(i=0;i<640;i++)expected[i]=arena[i];wanted[0]=links[0];wanted[1]=links[1];
 if(selected){
  if((cmd&255)==45){
   for(j=0;j<2;j++){
    which=wanted[j].owner==packet.before?1:wanted[j].owner==packet.after?2:0;
    if(which){wanted[j].owner=which==1?packet.after:packet.before;wanted[j].identity=which==1?packet.after_identity:packet.before_identity;}
   }
  }else if((cmd&255)==0||(cmd&255)==67){
   want=wanted[0].owner==packet.before||wanted[0].identity==((u8*)&packet)[4];
   if((cmd&255)==67)want=want&&((u8*)wanted)[13]==((u8*)&packet)[5];
  }
 }
 for(i=0;i<16;i++)expected[32+0x110+i]=((u8*)wanted)[i];
 if(want&&(mode&1))expected[32+0x3C]^=0x55;
 /* Store the pointer representation, not bytes of the referenced array. */
 if(want&&(mode&2)){u8*p=references[5];for(i=0;i<4;i++)expected[32+0x110+i]=((u8*)&p)[i];}
 active=fn;
 if(root)func_1513DF9C(owner,(s32)&packet,(u8)cmd);else fn(owner,(s32)&packet,(u8)cmd);
 if(calls!=want||last!=(want?(u32)owner:0)||otherCalls!=(root&&!selected))return 23;
 for(i=0;i<640;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static int variant(Callback fn){u32 cmd,a,b,same,tag,disc,plan,cat,flag,k,count=0;static const u32 commands[4]={0,45,67,0xA5A500FF};
 for(cmd=0;cmd<256;cmd++)for(a=0;a<3;a++)for(b=0;b<3;b++)for(same=0;same<2;same++)
 for(tag=0;tag<2;tag++)for(disc=0;disc<2;disc++)for(plan=0;plan<2;plan++){
  if(one(fn,cmd,a,b,same,tag,disc,plan,0,7,1))return 23;count++;
 }
 for(cat=0;cat<256;cat++)for(flag=0;flag<2;flag++)for(k=0;k<4;k++){
  if(one(fn,commands[k],0,1,cat&1,cat&1,(cat>>1)&1,k&1,1,cat,flag))return 23;count++;
 }
 return count==38912?0:24;
}
static int run(void){arena=allocate(640);if(!arena)return 25;CHECKS return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''.replace('CHECKS',checks),38912
