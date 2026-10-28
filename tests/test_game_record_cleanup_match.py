"""Shared record cleanup: literal guarded image, alias ABI, caller and original resource list."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_cleanup_match as source
from tools.tests import game_record_cleanup_oracle as oracle
from tools.tests.game_record_cleanup_oracle import Case,fixture,reference,public,CleanupOracle,BLOCK,RESOURCE_BLOCK,SHARED,DECREMENT,STACK,put,read,faults,u32
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 return dict(skip_resource=b.replace('        func_1510D630(resources);',''),wrong_resource=b.replace('func_1510D630(resources);','func_1510D630(resources + 1);'),resource_clear=b.replace('words[4] = 0','words[4] = 1'),resource_early_clear=b.replace('        func_1510D630(resources);\n        D_800DDE80[index].words[4] = 0;','        D_800DDE80[index].words[4] = 0;\n        func_1510D630(resources);'),flag8=b.replace('D_800DDF71 != -2','D_800DDF70 != -2'),unsigned_flag=b.replace('D_800DDF71 != -2','(u8)D_800DDF71 != -2'),no_retention=b.replace('            return;',''),shared_gate=b.replace('D_800DDF70 == -2','D_800DDF70 != -2'),shared_pointer=b.replace('func_10004074((void *)D_800DDF20);','func_10004074((void *)D_800DDE80[index].words[0]);'),shared_clear=b.replace('D_800DDF20 = 0','D_800DDF20 = 1'),shared_view=b.replace('D_800DDF98 = 0','D_800DDF98 = 1'),final_clear=b.replace('words[0] = 0','words[0] = 1'),final_view=b.replace('D_800DDF78[index] = 0','D_800DDF78[index] = 1'))

def native_harness():
 t=source.HEADERS+r'''
Record15183974 D_800DDE80[11];u32 D_800DDF78[11];static s8 flags[11];
#define D_800DDF70 flags[8]
#define D_800DDF71 flags[9]
#define D_800DDF20 D_800DDE80[8].words[0]
#define D_800DDF98 D_800DDF78[8]
static Record15183974 expected[11];static u32 views[11];static s8 expectedFlags[11];
static s16 resourceBlock[16];static u32 assets[16];static u32 actualLog[32],expectedLog[32],ac,ec;
static u32 indexValue,resourceMode,freeMode;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record15183974)==20)?1:-1];
static void resourceEffect(Record15183974 *records,s8 *f){records[indexValue].words[4]=(s32)0xDEAD1234u;if(resourceMode&1)records[indexValue].words[0]=0;if(resourceMode&2)records[indexValue].words[0]=(s32)&assets[4];if(resourceMode&4){f[8]=f[9]=-2;records[8].words[0]=(s32)&assets[8];}}
static void freeEffect(Record15183974 *records,u32 *v){if(freeMode&1){records[indexValue].words[0]=(s32)&assets[12];v[indexValue]=0xFEEDFACE;}if(freeMode&2){records[8].words[0]=(s32)&assets[2];v[8]=0x01234567;}}
__attribute__((noinline,noclone)) void func_1510D630(s16 *p){actualLog[ac++]=1;actualLog[ac++]=(u32)p;resourceEffect(D_800DDE80,flags);}
__attribute__((noinline,noclone)) void func_10004074(void *p){actualLog[ac++]=2;actualLog[ac++]=(u32)p;freeEffect(D_800DDE80,D_800DDF78);}
'''
 for name,body in dict(selected=source.SELECTED,**controls()).items():t+=body.replace(source.FUNCTION,'test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(s32);
static int check(Fn fn){u32 n,i,j;for(n=0;n<16384;n++){
 indexValue=n%11;resourceMode=(n>>3)&7;freeMode=(n>>6)&3;ac=ec=0;
 for(i=0;i<11;i++){for(j=0;j<5;j++)D_800DDE80[i].words[j]=expected[i].words[j]=(s32)(0x12340000u+n*101u+i*5u+j*17u);D_800DDF78[i]=views[i]=0x98760000u+n+i;flags[i]=expectedFlags[i]=(s8)(n+i);}
 flags[8]=expectedFlags[8]=(n&256)?-2:(s8)((n>>1)&255);flags[9]=expectedFlags[9]=(n&512)?-2:(s8)((n>>2)&255);
 D_800DDF20=expected[8].words[0]=(n&4)?(s32)&assets[1]:0;D_800DDE80[indexValue].words[0]=expected[indexValue].words[0]=(n&1)?(s32)assets:0;D_800DDE80[indexValue].words[4]=expected[indexValue].words[4]=(n&2)?(s32)resourceBlock:0;
 if(expected[indexValue].words[4]){expectedLog[ec++]=1;expectedLog[ec++]=(u32)expected[indexValue].words[4];resourceEffect(expected,expectedFlags);expected[indexValue].words[4]=0;}
 if(!(indexValue==8&&expectedFlags[9]!=-2)){
  if(indexValue==9&&expectedFlags[8]==-2&&expected[8].words[0]){expectedLog[ec++]=2;expectedLog[ec++]=(u32)expected[8].words[0];freeEffect(expected,views);expected[8].words[0]=0;views[8]=0;}
  if(expected[indexValue].words[0]){expectedLog[ec++]=2;expectedLog[ec++]=(u32)expected[indexValue].words[0];freeEffect(expected,views);expected[indexValue].words[0]=0;views[indexValue]=0;}
 }
 fn(indexValue);if(ac!=ec)return 1;for(i=0;i<ac;i++)if(actualLog[i]!=expectedLog[i])return 2;
 for(i=0;i<11;i++){for(j=0;j<5;j++)if(D_800DDE80[i].words[j]!=expected[i].words[j])return 3;if(D_800DDF78[i]!=views[i]||flags[i]!=expectedFlags[i])return 4;}
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

class RecordCleanupTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>64I',cls.rom,source.ROM));cls.images=[]
  for filename in('qualified-padded.o','selected.o'):
   local=cls.fresh/filename;local.write_bytes((cls.out/filename).read_bytes());blob,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.images.append(list(struct.unpack_from('>64I',blob,functions[source.FUNCTION]['value'])))
  cls.words,cls.raw=cls.images
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=None,s=None,connected=None,original_resource=False):
  initial=fixture(c,s);wanted,calls=reference(initial,c,s,original_resource);pair=[]
  for words in images or(self.truth,self.words):
   m=CleanupOracle(words,initial,c,entry=entry,s=s,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c);pair.append(m)
  for m in pair[1:]:self.assertEqual(complete(pair[0]),complete(m));self.assertEqual(pair[0].trace,m.trace)
  if images is None:
   m=CleanupOracle(self.raw,initial,c,entry=entry,s=s,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls),c)
  return pair[0]
 def rebased(self,obj,entry,symbols,label,normalize=False):
  text,functions,bindings=parse_object(obj);f=functions[source.FUNCTION]
  if normalize:
   raw,rs=source.normalized_payload(*source.payload(obj));text=text[:f['value']]+raw+text[f['value']+f['size']:]
  assembly,unknown=emit_function(text,f,bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];return list(struct.unpack('>%dI'%(f['size']//4),blob[:f['size']]))
 def test_01_owner_actual_Make_census_and_spill(self):
  self.assertEqual(self.truth,self.words);self.assertEqual([4*i for i,(a,b)in enumerate(zip(self.raw,self.truth))if a!=b],list(source.GUARDS));self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),9)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),8);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual((self.out/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM'),0)
  commands=json.loads((self.out/'Make-commands.json').read_text());self.assertEqual(len(commands),3);self.assertFalse(any('-loopunroll'in x for row in commands for x in row))
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x1B1470])
  self.assertEqual(self.raw[0],0x27BDFFE0);self.assertEqual(self.raw[-3],0x27BD0020);accesses={4*i:w for i,w in enumerate(self.raw)if w>>26 in(35,43)and(w>>21&31)==29 and(w&65535)in(24,28)};self.assertEqual(accesses,{n:a for n,(a,b)in source.GUARDS.items()});self.assertEqual(set(source.GUARDS),{48,60,152,176,200,216});self.assertTrue(all((a^b)==4 and(a>>16&31)==3 for a,b in source.GUARDS.values()))
  text=self.values[source.ASM].decode();self.assertEqual(text.count('lui        $v0, (0x800E0000 >> 16)'),1);self.assertEqual(text.count('lw         $v0, -0x20E0($v0)'),1);self.assertEqual((0x800E0000-0x20E0)&0xFFFFFFFF,source.TABLE+8*20)
  self.assertIn('void func_1510D630(s16 *arg0)',self.values['conker/src/game/generated_139FC0.c'].decode());self.assertIn('void func_10004074(void *arg0)',self.values['conker/src/init_3C40.c'].decode());at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.RESOURCE,100);self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+100],self.rom[0x13AAE0:0x13AB44])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=64,frame=32,bindings=17,guards=6,neighbors=8,compact_functions=9,Make_commands=3,GLOBAL_ASM=0,normal_profile=True,diagnostics=0,arguments=1,closed_spill_accesses=6,recovered_original_relocations=2,void_return=True)
 def test_02_guest_shared_aliases_live_gates_and_raw_C(self):
  count=0;seen=set()
  for index,asset,res,shared,flags,rm,fm,phase in itertools.product((0,7,8,9,10),(0,BLOCK),(0,RESOURCE_BLOCK),(0,SHARED),((0,0),(254,0),(0,254),(254,254)),(0,7),(0,3),(0,8)):
   m=self.compare(Case(index,asset,res,shared,*flags,rm,fm,phase=phase));seen.update(m.visits);count+=1
  for byte,index,res in itertools.product(range(256),(8,9),(0,RESOURCE_BLOCK)):
   self.compare(Case(index=index,flag8=byte,flag9=byte,resource=res));count+=1
  for index in range(11):self.compare(Case(index=index));count+=1
  for index in(-1,-32768,32767,0x7FFFFFFF,0x80000000,0xFFFFFFFF):self.compare(Case(index=index,resource_mode=7,free_mode=3));count+=1
  self.assertTrue(set(range(source.ENTRY,source.ENTRY+256,4))<=seen);self.receipt['guest']=dict(cases=count,visited_words=64,complete_normalized_state_trace_equal=True,raw_C_public_memory_calls_equal=True,defined_rows=11,all_signed_flag_bytes=256,shared_row_and_view_aliases=True,extreme_indices_guest_only=True)
 def test_03_original_caller_loop_and_resource_list(self):
  body=list(struct.unpack_from('>16I',self.rom,0x1B1448));seen=set();count=0
  for pattern,rm,fm,phase in itertools.product(range(8),(0,7),(0,3),(0,8)):
   c=Case(resource_mode=rm,free_mode=fm,phase=phase);initial=fixture(c);s=oracle.symbols()
   for i in range(11):initial[source.FLAG+i]=254 if(pattern==0 or(pattern+i)%3)else 0;put(initial,source.TABLE+20*i,BLOCK+4*i if(pattern+i)%2 else 0);put(initial,source.TABLE+20*i+16,RESOURCE_BLOCK if(pattern+i)%3 else 0)
   expected=dict(initial);calls=[]
   for i in range(11):
    if expected[source.FLAG+i]==254 and read(expected,source.TABLE+20*i):calls.append((source.ENTRY,(i,)));expected,extra=reference(expected,replace(c,index=i));calls+=extra
   pair=[]
   for target in(self.truth,self.words,self.raw):
    m=CleanupOracle(body,initial,c,entry=0x15183F98,connected={source.ENTRY+i*4:w for i,w in enumerate(target)});m.r[16]=0;m.r[17]=source.FLAG;m.r[19]=source.TABLE;m.r[20]=20;m.code[0x15183FD8]=0;m.code=WindowCode(m.code,m);m.code.ends=(0x15183FD8,)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((public(m.memory),m.calls),(public(expected),calls));self.assertEqual(m.r[16],11);self.assertEqual(m.r[17],source.FLAG+11);pair.append(m);seen.update(m.visits)
   self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
  self.assertTrue(set(range(0x15183F98,0x15183FD8,4))<=seen)
  resource=list(struct.unpack_from('>25I',self.rom,0x13AAE0));connected={source.RESOURCE+i*4:w for i,w in enumerate(resource)};visited=set();cases=0
  for index,n,rm,fm,flag,phase in itertools.product((0,8,9),(-32768,-1,0,1,3,7),(0,7),(0,3),(0,254),(0,8)):
   m=self.compare(Case(index=index,count=n,resource_mode=rm,free_mode=fm,flag8=flag,flag9=flag,phase=phase),connected=connected,original_resource=True);visited.update(m.visits);cases+=1
  self.assertTrue(set(range(source.RESOURCE,source.RESOURCE+100,4))<=visited);self.receipt['integration']=dict(caller_window_words=16,caller_window_cases=count,parent_total_words=252,all_caller_window_words=True,full_parent_all_routes_claimed=False,loop_rows=11,resource_words=25,resource_cases=cases,all_resource_words=True,existing_resource_and_heap_free_C_unchanged=True,parent_C_placeholder_uncredited=True,bounded_providers=['func_1510D694','func_10004074'],full_heap_claim=False)
 def test_04_native32_aliased_globals_and_controls(self):
  p=self.fresh/'native.c';p.write_text(native_harness());rows=[]
  for opt in('-O0','-O2','-O3'):
   target=self.fresh/('native'+opt);build=subprocess.run(native_command(opt)+[str(p),'-o',str(target)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(build.returncode,0,build.stdout+build.stderr);run=subprocess.run([str(target)],capture_output=True);self.assertEqual(run.returncode,0,(opt,run.stdout,run.stderr));rows.append(dict(profile=opt,cases=16384,negative_controls=len(controls()),UBSan_trap=True,defined_rows=11,real_shared_row_and_view_aliases=True,real_pointer_arguments=True))
  self.receipt['native']=rows
 def test_05_fault_prefixes_and_connected_resource_calls(self):
  cases=(Case(),Case(index=8,flag9=0),Case(index=8,resource=0),Case(index=0,asset=0,resource=0),Case(index=9,resource_mode=7,free_mode=3,phase=8));cuts=0;deep=0
  connected={source.RESOURCE+i*4:w for i,w in enumerate(struct.unpack_from('>25I',self.rom,0x13AAE0))}
  for linked in(None,connected):
   for c in cases:
    good=self.compare(c,connected=linked,original_resource=bool(linked))
    for cut in range(good.all_accesses):
     pair=[]
     for words in(self.truth,self.words):
      m=CleanupOracle(words,fixture(c),c,connected=linked);m.cut=cut
      with self.assertRaises(faults.AccessBoundary):m.run()
      pair.append(m)
     self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of))
     if linked:deep+=1
     else:cuts+=1
  self.receipt['faults']=dict(prefix_pairs=cuts,integrated_resource_prefix_pairs=deep,complete_state_trace_PC_delay_equal=True,portable_C_fault_semantics_claimed=False)
 def test_06_padder_rebases_guard_and_relocation_controls(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));rejects=0
  for at in source.GUARDS:
   damaged=raw[:at+3]+bytes([raw[at+3]^1])+raw[at+4:]
   with self.assertRaises(ValueError):source.normalized_payload(damaged,rs)
   rejects+=1
  for damaged,bindings in((raw[:-4],rs),(raw,{**rs,128:[('R_MIPS_HI16','D_800DDF98')]})):
   with self.assertRaises(ValueError):source.normalized_payload(damaged,bindings)
   rejects+=1
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=self.out/'proposed-guards.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  # Every expected-word guard fails if its compiled input changes.
  import csv,io
  before=self.values['conker/retail_word_patches.us.csv'];rows=list(csv.DictReader(io.StringIO(source.guard_manifest(before).decode())));new=[row for row in rows if row['function']==source.FUNCTION];self.assertEqual(len(new),6)
  for which in range(6):
   modified=[dict(row)for row in rows];selected=[row for row in modified if row['function']==source.FUNCTION];selected[which]['expected']=hex(int(selected[which]['expected'],0)^1);out=io.StringIO();writer=csv.DictWriter(out,list(rows[0]));writer.writeheader();writer.writerows(modified);q=self.fresh/('bad-guard-%d.csv'%which);q.write_text(out.getvalue())
   with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,filename=source.OWNER,word_patches_path=q)
  count=0
  for j,(entry,table,flag,views)in enumerate(((source.ENTRY,source.TABLE,source.FLAG,source.VIEWS),(0x17007FFC,0x80017FFC,0x80028000,0x80037FFC),(0x2500FFFC,0x8001FFFC,0x80037FFF,0x80047FE0))):
   s=dict(D_800DDE80=table,D_800DDF20=table+160,D_800DDF70=flag+8,D_800DDF71=flag+9,D_800DDF78=views,D_800DDF98=views+32,func_1510D630=source.RESOURCE if j==0 else entry+0x10004,func_10004074=source.FREE if j==0 else entry+0x20004)
   paths=(self.out/('original-'+source.FUNCTION+'.o'),self.out/'make-shadow/src/game/generated_1B0740.c.o',self.out/'selected.o');images=[self.rebased(p,entry,s,'rebase-%d-%d'%(j,k),normalize=k==2)for k,p in enumerate(paths)];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);unmodified=self.rebased(paths[2],entry,s,'unmodified-%d'%j)
   for index,res,flagbyte,mode,phase in itertools.product((0,8,9),(0,RESOURCE_BLOCK),(0,254),(0,7),(0,8)):
    c=Case(index=index,resource=res,flag8=flagbyte,flag9=flagbyte,resource_mode=mode,free_mode=3,phase=phase);self.compare(c,images,entry,s);initial=fixture(c,s);wanted,calls=reference(initial,c,s);m=CleanupOracle(unmodified,initial,c,entry=entry,s=s).run();self.assertEqual((public(m.memory),m.calls),(public(wanted),calls));count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,bindings=17,guards=6,actual_Make_normalized_and_retail=True,raw_C_public_equal=True,HI16_LO16_carries=True,alias_offsets_preserved=True,raw_binding_rejections=rejects,padder_guard_rejections=6,original_numeric_pair_recovered=True)
 def test_07_actually_compiled_semantic_negatives(self):
  witnesses=tuple(Case(index=index,asset=asset,resource=res,shared=shared,flag8=f8,flag9=f9,resource_mode=rm,free_mode=fm)for index,asset,res,shared,(f8,f9),rm,fm in itertools.product((0,8,9),(0,BLOCK),(0,RESOURCE_BLOCK),(0,SHARED),((0,0),(254,0),(0,254),(254,254)),(0,7),(0,3)))
  for name,body in controls().items():
   self.assertNotEqual(body,source.SELECTED,name);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,oracle.symbols(),'negative-link-'+name);effective=False
   for c in witnesses:
    initial=fixture(c);wanted,calls=reference(initial,c)
    try:m=CleanupOracle(words,initial,c).run();different=(public(m.memory),m.calls)!=(public(wanted),calls)
    except AssertionError as exc:
     if 'Unsupported word'in str(exc):raise
     different=True
    except KeyError:different=True
    if different:effective=True;break
   self.assertTrue(effective,name)
  self.receipt['compiled_control']=dict(IDO_negatives=len(controls()),signed_flags_and_shared_aliases=True,resource_and_free_call_order=True,post_provider_clears=True)
 def test_08_strict_entire_image_and_protected_helpers(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+256];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,256);named={n:(p,f)for p,n,f,_ in source.symbol_rows(before)};positions=[20,at,at+180,at+256,named[source.FUNCTION][0]+8,source.elf_slot_offset(before,source.RESOURCE,100),source.elf_slot_offset(before,source.FREE,4),0x2A0D94,0x2B03D4,0x2CF644,0x2E7160,0x30D508]
  for pos in positions:
   bad=bytearray(expected);bad[pos]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
  self.assertEqual(source.guard_manifest(v['conker/retail_word_patches.us.csv']),(self.out/'proposed-guards.csv').read_bytes());self.assertEqual(sum(x!=y for x,y in zip(before,expected)),266);self.receipt['image']=dict(changed_bytes=266,code_bytes=204,extent_bytes=2,symbol_serialization_bytes=60,closed_metadata_cycles=3,exclusions=0,effective_corruptions=len(positions)+1,all_named_definitions_preserved_except_target_extent=True,inherited_guard_prefix_unchanged=True,new_guards=6,protected_bytes=189088,existing_provider_sources_objects_and_linked_bodies_unchanged=True)
