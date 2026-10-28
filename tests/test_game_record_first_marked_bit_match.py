"""First marked record bit: direct C, bit31, signed indexing and original command17."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_first_marked_bit_match as source
from tools.tests import game_record_first_marked_bit_oracle as oracle
from tools.tests.game_record_first_marked_bit_oracle import Case,fixture,result,public,FirstBitOracle,RECORD,MASK_TABLE,STACK,put,read,faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
MASKS=(0,*(1<<i for i in range(32)),0xFFFFFFFF)

def controls():
 b=source.SELECTED
 return dict(wrong_flag=b.replace('record[0x4F] & 0x80','record[0x4F] & 0x40'),exact_flag=b.replace('record[0x4F] & 0x80','record[0x4F] == 0x80'),wrong_stride=b.replace('/ 0xA0','/ 0xA4'),wrong_slot=b.replace('/ 0xA0]','/ 0xA0 + 1]'),skip_bit31=b.replace('index < 32','index < 31'),wrong_result=b.replace('return index;','return index+1;'),reverse_bits=b.replace('1U << index','1U << (31-index)'),wrong_empty=b.replace('return 0;','return -1;'),positive_mask_only=b.replace('if (mask &','if (mask > 0 && mask &'))

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
u8 *D_800DBEF4;s32 *D_800DBF94;
static u8 arena[8192],expectedArena[8192];static s32 table[128],expectedTable[128];
typedef s32(*Fn)(u8 *);
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace(source.FUNCTION,'test_'+name)+'\n'
 t+=r'''
static s32 answer(u32 flags,u32 mask){s32 bit=0;if(!(flags&128)||!mask)return 0;while(!(mask&1)){mask>>=1;bit++;}return bit;}
static int one(Fn fn,u32 flag,u32 mask,s32 delta){u32 i;s32 slot=delta/160;u8 *record=arena+4096+delta;
 for(i=0;i<128;i++)table[i]=expectedTable[i]=(s32)(mask^((i+1)*0x1020304u));
 record[79]=expectedArena[4096+delta+79]=(u8)flag;table[64+slot]=expectedTable[64+slot]=(s32)mask;
 if(fn(record)!=answer(flag,mask))return 1;
 if(D_800DBEF4!=arena+4096||D_800DBF94!=table+64)return 2;
 for(i=0;i<128;i++)if(table[i]!=expectedTable[i])return 3;
 return 0;}
static int check(Fn fn){u32 i,n,half,flag,bit,mask;
 for(i=0;i<8192;i++)arena[i]=expectedArena[i]=(u8)(i*29+0xA5);
 D_800DBEF4=arena+4096;D_800DBF94=table+64;
 for(n=0;n<65536;n++)for(half=0;half<2;half++)if(one(fn,n>>8,half?n<<16:n,(s32)(n%641)-320))return 1;
 for(flag=0;flag<256;flag++)for(bit=0;bit<34;bit++){mask=bit<32?1u<<bit:bit==32?0:0xFFFFFFFFu;if(one(fn,flag,mask,(s32)(bit*19)-320))return 1;}
 for(i=0;i<8192;i++)if(arena[i]!=expectedArena[i])return 2;
 return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class RecordFirstMarkedBitTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',data,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,base=source.BASE,masks=source.MASKS):
  initial,record=fixture(c,base,masks);wanted=result(initial,record,base,masks);pair=[]
  for words in images or(self.truth,self.words,self.raw):
   m=FirstBitOracle(words,initial,c,entry,record=record).run();self.assertEqual((m.r[2],public(m.memory),m.calls),(wanted,public(initial),[]),c);self.assertFalse(any(e[0]=='W'for e in m.trace));pair.append(m)
  for other in pair[1:]:self.assertEqual(complete(pair[0]),complete(other));self.assertEqual(pair[0].trace,other.trace)
  return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);data=sections(p.with_suffix('.elf'))['.text'][1];length=functions[source.FUNCTION]['size'];return list(struct.unpack('>%dI'%(length//4),data[:length]))
 def test_01_owner_actual_Make_and_literal_call_census(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.raw,self.truth);self.assertEqual(source.payload(self.out/'selected.o'),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),34)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),33);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),5);self.assertFalse(any('-loopunroll'in x for row in commands for x in row));self.assertEqual((self.out/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM'),2)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0xCC340])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=49,frame=0,bindings=4,guards=0,neighbors=33,compact_functions=34,Make_commands=5,GLOBAL_ASM=2,normal_profile=True,diagnostics=0)
 def test_02_all_flags_bits_signed_quotients_and_read_aliases(self):
  count=0;seen=set()
  for flag,mask,phase in itertools.product(range(256),MASKS,(0,8)):
   m=self.compare(Case(flag,mask,phase=phase));seen.update(m.visits);count+=1
  for delta,mask in itertools.product((-2147483648,-2147483647,-321,-320,-319,-161,-160,-159,-1,0,1,159,160,161,319,320,321,2147483646,2147483647),(0,1,2,0x80000000,0xFFFFFFFF)):
   self.compare(Case(128,mask,delta));count+=1
  for alias,mask in itertools.product((1,2,3),(0,1,128,0x80000000,0x80000080,0xFFFFFFFF)):
   self.compare(Case(mask=mask,alias=alias));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+196,4))<=seen);self.receipt['guest']=dict(cases=count,visited_words=49,complete_state_trace_equal=True,all_flag_bytes=True,all_single_bits=True,signed_division_extremes=True,global_flag_and_table_aliases=True,no_memory_writes=True,disabled_globals_unmapped=True)
 def test_03_original_command17_caller_and_retained_lookup(self):
  parent=list(struct.unpack_from('>159I',self.rom,0xCC224));lookup=list(struct.unpack_from('>28I',self.rom,0x141E5C));table=self.rom[source.TABLE_ROM:source.TABLE_ROM+68];self.assertEqual(struct.unpack('>17I',table)[4],0x1509EE90)
  for va,size,data in((source.LOOKUP,112,struct.pack('>28I',*lookup)),(source.TABLE,68,table)):
   pos=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],va,size);self.assertEqual(self.values['conker/build/conker.us.elf'][pos:pos+size],data)
  count=0;seen=set();cases=[(selector|0xA5000000,0x17,Case(flags,mask,phase=phase),4)for selector,flags,mask,phase in itertools.product((1,4),(0,128,255),MASKS,(0,8))]
  cases +=[(selector,command,Case(),count)for selector,command,count in itertools.product((0,1,255),(0x12,0x17,0x24),(-1,0,4))]
  for selector,command,c,n in cases:
   initial,args,wanted,calls=oracle.caller_fixture(self.rom,selector,command,c,n);pair=[]
   for target in(self.truth,self.words,self.raw):
    connected={base+i*4:w for base,body in((source.ENTRY,target),(source.LOOKUP,lookup))for i,w in enumerate(body)};m=FirstBitOracle(parent,initial,c,source.PARENT,connected=connected,arguments=args).run();self.assertEqual((m.r[2],public(m.memory),m.calls),(wanted,public(initial),calls));seen.update(m.visits);pair.append(m)
   for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
   count+=1
  needed=set(range(source.PARENT,source.PARENT+0x5C,4))|set(range(0x1509EE90,0x1509EEA0,4))|{0x1509EEA8,0x1509EEAC}|set(range(0x1509EFD8,0x1509EFF0,4));self.assertTrue(needed<=seen,sorted(needed-seen));self.assertTrue(set(range(source.LOOKUP,source.LOOKUP+112,4))<=seen)
  for forced in(-1,-2147483648):
   initial,args,_,_=oracle.caller_fixture(self.rom);m=FirstBitOracle(parent,initial,entry=source.PARENT,connected={source.LOOKUP+i*4:w for i,w in enumerate(lookup)},arguments=args,forced_result=forced).run();self.assertEqual(m.r[2],0);self.assertTrue({0x1509EEA0,0x1509EEA4}<=m.visits)
  self.receipt['caller']=dict(cases=count,parent_words=159,parent_visited_words=sum(source.PARENT<=p<source.PARENT+636 for p in seen),qualified_original_command=0x17,all_reachable_target_route_words=True,lookup_words=28,all_lookup_words_visited=True,current_lookup_and_switch_table_exact=True,negative_result_parent_controls=2,parent_C_placeholder_uncredited=True,full_parent_all_commands_claimed=False)
 def test_04_native32_patterns_bit31_and_UB_negative(self):
  p=self.fresh/'native.c';body=native_harness();p.write_text(body);rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(p),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=139776,negative_controls=9,UBSan_trap=True,complete_arena_and_table_preserved=True))
  unsafe=self.fresh/'unsafe-shift.c';unsafe.write_text(body.replace('1U << index','1 << index',1));target=self.fresh/'unsafe-shift';build=subprocess.run(native_command('-O2')+[str(unsafe),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertLess(run.returncode,0,'Unsigned bit31 safety control did not trap');self.receipt['native']=rows;self.receipt['signed_shift_UB_control_trapped']=True
 def test_05_exact_read_fault_prefixes_and_disabled_access_gate(self):
  cuts=0
  for c in(Case(flags=0),Case(mask=0),Case(mask=1),Case(mask=0x80000000),Case(delta=-160),Case(delta=-159),Case(delta=2147483647),Case(alias=1),Case(alias=2,mask=0x80000080),Case(alias=3)):
   good=self.compare(c)
   for cut in range(good.access_count):
    pair=[]
    for words in(self.truth,self.words,self.raw):
     initial,record=fixture(c);m=FirstBitOracle(words,initial,c,record=record);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(m.current_pc,m.delay_of))
    cuts+=1
  self.receipt['faults']=dict(prefix_triples=cuts,all_direct_C_fault_state_equal=True,disabled_gate_reads_only_flag=True)
 def test_06_actual_padder_GNU_rebases_and_raw_rejection(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(source.NEW_GUARDS,[])
  for damaged,bindings in((raw[:-4],rs),(raw[:60]+bytes([raw[60]^1])+raw[61:],rs),(raw,{**rs,8:[('R_MIPS_HI16','wrong')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,(entry,base,masks)in enumerate(((source.ENTRY,source.BASE,source.MASKS),(0x17007FFC,0x80017FFC,0x80028000),(0x2500FFFC,0x8001FFFC,0x80030000))):
   symbols=dict(D_800DBEF4=base,D_800DBF94=masks);images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_13D350.c.o',self.out/'selected.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for flags,mask,delta in itertools.product((0,128,255),(0,1,0x80000000,0xFFFFFFFF),(-160,159,320)):self.compare(Case(flags,mask,delta),images,entry,base,masks);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=4,guards=0,actual_Make_raw_and_retail=True,HI16_LO16_carries=True,raw_binding_rejections=3)
 def test_07_actually_compiled_semantic_negatives(self):
  witnesses=[Case(flags=0),Case(flags=64),Case(flags=129),Case(mask=1),Case(mask=3),Case(mask=0),Case(mask=0x80000000),Case(delta=160),Case(delta=-160)]
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,dict(D_800DBEF4=source.BASE,D_800DBF94=source.MASKS),'negative-link-'+name);effective=False
   for c in witnesses:
    initial,record=fixture(c);wanted=result(initial,record)
    try:m=FirstBitOracle(words,initial,c,record=record).run();different=(m.r[2],public(m.memory))!=(wanted,public(initial))
    except (AssertionError,KeyError):different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_negatives=9,flag_index_bit31_and_result_failures=True)
 def test_08_strict_entire_image_and_unchanged_guards(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+196];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,196);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+196,source.elf_slot_offset(before,source.LOOKUP,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(v['conker/retail_word_patches.us.csv'],(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),149);self.receipt['image']=dict(changed_bytes=149,code_bytes=148,size_bytes=1,exclusions=0,effective_corruptions=6,entire_guard_manifest_unchanged=True,new_guards=0,protected_bytes=189088)
