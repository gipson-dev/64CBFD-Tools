"""Save prefix/defaults: exact owner, live pointer aliases and original callers."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_save_defaults_candidates as candidate
from tools.experiments import game_save_defaults_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_save_defaults_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses
class SaveDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>69I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        cls.fitted=model.bound(cls.prepared['qualified_compact'],model.symbols(),True)
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalSaveDefaults',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-save-defaults',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.words==cls.fitted
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=model.Case(),s=None,entry=match.ENTRY,images=None,initial=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s,entry)if initial is None else initial;expected,trace,clear=model.reference(initial,s);ms=[]
        for words in(self.retail,self.raw,self.fitted,self.words)if images is None else images:
            m=model.Oracle(words,initial,c,s,entry).run();self.assertEqual(model.public(m.memory),model.public(expected),c)
            self.assertEqual([t for t in m.trace if not s['jtbl_80095A00_game']<=t[1]<s['jtbl_80095A00_game']+40],trace,c)
            self.assertFalse(m.calls);self.assertEqual(m.r[2],10)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            ms.append(m)
        for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
        return ms,clear
    def test_01_owner_guards_pools_and_original_bytes(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(69,0,2,8));self.assertEqual(q['raw_neighbors'],17);self.assertEqual(q['neighbors'],17)
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+276]
        self.assertEqual([i for i,(a,b)in enumerate(zip(self.raw,self.retail))if a!=b],[0,1])
        for at in range(276):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_HI16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();new=match.guard_manifest(old);self.assertTrue(new.startswith(old))
        for index in range(2):
            for field in('expected','expected_relocations'):
                rows=list(csv.DictReader(io.StringIO(new.decode())));rows[-2+index][field]='0x0'if field=='expected'else'R_MIPS_HI16:foreign'
                out=io.StringIO(newline='');writer=csv.DictWriter(out,rows[0].keys());writer.writeheader();writer.writerows(rows)
                with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],out.getvalue().encode(),'bad-guard-%d-%s'%(index,field))
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22767C)[0],model.symbols()['D_800BE2F0']+2)
        self.assertEqual(struct.unpack_from('>10I',self.rom,match.TABLE_ROM),tuple(match.ENTRY+v for v in match.TARGET_OFFSETS))
        self.receipt('owner-controls',words=69,guards=2,bindings=8,neighbors=17,raw_corruptions=276,binding_corruptions=8,guard_corruptions=4,original_table_entries=10,compact_pool_bytes=48,loaded_pool_added=False)
    def test_02_ordered_protocol_aliases_and_all_words(self):
        count=0;seen=set()
        for c in model.cases():
            ms,clear=self.compare(c);self.assertEqual(clear,104);seen.update(ms[0].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+276,4)))
        # Only one retired instruction separates the two schedules; no memory access occurs there.
        a=model.Oracle(self.retail,model.fixture());b=model.Oracle(self.raw,model.fixture())
        a.execute(self.retail[0]);b.execute(self.raw[0]);self.assertNotEqual(a.r,b.r);self.assertEqual(a.memory,b.memory)
        a.execute(self.retail[1]);b.execute(self.raw[1]);self.assertEqual(a.r,b.r)
        self.receipt('guest-contract',cases_per_body=count,bodies=4,all_69_words=True,clear_bytes=104,ten_record_stride=10,byte_aliases_into_all_pointer_bytes=True,reloaded_pointer_each_store=True,raw_schedule_converges_after_two_words=True)
    def test_03_access_prefixes_and_sparse_faults(self):
        cuts=sparse=0
        for c in(model.Case(),model.Case(placement=3),model.Case(pointer_alias=3)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.fitted,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        for missing in(model.symbols()['D_800BE2F0']+17,model.symbols()['D_80082BBC']+1,match.TABLE+9*4,model.PAYLOAD+99):
            c=model.Case(placement=3);initial=model.fixture(c);del initial[missing];ms=[]
            for words in(self.retail,self.raw,self.fitted,self.words):
                m=model.Oracle(words,initial,c)
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            sparse+=1
        self.receipt('fault-prefixes',fired_prefixes=cuts,bodies=4,sparse_faults=sparse,hardware_MMU_claimed=False)
    def test_04_original_reader_and_selection_caller(self):
        self.assertEqual(match.census(ROOT),[0x347F8,0x49AF0]);reader=list(struct.unpack_from('>57I',self.rom,0x3472C));count=windows=0
        for packet,valid,phase in itertools.product(range(8),(False,True),(0,8)):
            c=model.Case(packet=packet,checksum_match=valid,phase=phase);initial=model.fixture(c);expected=dict(initial)
            for i,v in enumerate(model.packet_bytes(c)):expected[model.symbols()['D_800BE2F0']+i]=v
            if not valid:expected=model.reference(expected)[0]
            ms=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+276,4),target));m=model.Oracle(reader,initial,c,entry=0x1500727C,connected=code).run()
                self.assertEqual(m.calls,[(model.READ,(0x800BE900,0x44,0x800BE2F0,112))]+([]if valid else[(match.ENTRY,())]))
                self.assertEqual(model.public(m.memory),model.public(expected));ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            count+=1
        pc=0x1501C638;window=list(struct.unpack_from('>6I',self.rom,0x49AE8))
        for selector,phase in itertools.product((0,3,4,5,255),(0,8)):
            c=model.Case(phase=phase);initial=model.fixture(c);initial[0x80082BB4]=0xD3;expected=model.reference(initial)[0]if selector==4 else dict(initial);expected[0x80082BB4]=0;ms=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+276,4),target));code[0x1501C650]=0;m=model.Oracle(window,initial,c,entry=pc,connected=code);m.r[4]=selector;m.r[1]=4;m.before=m.r[:];m.code=model.WindowCode(m.code,m);m.code.ends=(0x1501C650,)
                with self.assertRaises(model.WindowBoundary):m.run()
                self.assertEqual(m.calls,[(match.ENTRY,())]if selector==4 else[]);self.assertEqual(model.public(m.memory),model.public(expected));ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            windows+=1
        self.receipt('callers',complete_original_reader_words=57,reader_cases_per_body=count,selection_window_words=6,selection_cases_per_body=windows,bodies=3,whole_selection_parent_claimed=False,opaque_reader_contract=True)
    def test_05_independent_GNU_rebases_and_clear_boundaries(self):
        count=links=0
        for i,(entry,start)in enumerate(((match.ENTRY,0x81007FFC),(0x18018000,0x8200FFF0),(0x1A02FFFC,0x83018000))):
            s=model.symbols();s.update(D_800BE2F0=start,D_800BE358=start+104,D_80082BBC=0x84008000+i*0x10000,jtbl_80095A00_game=0x85007FFC+i*0x10000);s['.rodata']=s['jtbl_80095A00_game'];images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);f=fs[match.FUNCTION]
                if j==1:
                    raw,bindings=match.function_blob(obj);text=bytearray(text);text[f['value']:f['value']+276]=match.normalized(raw,bindings,self.rom[match.ROM:match.ROM+276]);rs={at:values[:]for at,values in rs.items()}
                    for at,a,b,old,new in match.PATCHES:rs[f['value']+at]=[('R_MIPS_HI16',new)]
                    for at in(136,144):rs[f['value']+at]=[(match.BINDINGS[at][0][0],match.RODATA_SYMBOL)]
                asm,unknown=emit_function(text,f,rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()if not v[0].startswith('.')],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in list(model.cases())[::7]:self.compare(c,s=s,entry=entry,images=images);count+=1
        for length in(0,1,7,103,104,105,112):
            s=model.symbols();s['D_800BE358']=s['D_800BE2F0']+length;images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_owner'])]
            ms,n=self.compare(model.Case(placement=3),s=s,images=images);self.assertEqual(n,max(1,length));count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_8_bindings=True,HI_LO_carries=True,zero_length_still_one_store=True)
    def test_06_native_and_effective_IDO_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,diag=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);self.assertFalse(diag);words=link_control(obj,self.out/('negative-link-'+name));fired=False
            pool=match.alloc_pools(obj).get('.rodata');table=[]if pool is None else pool[-1]
            for c in witnesses:
                initial=model.fixture(c)
                for at,kind,target in table:
                    self.assertEqual((kind,target[:2]),(2,('text',match.FUNCTION)));model.put(initial,match.TABLE+at,match.ENTRY+target[2])
                expected=model.reference(initial)[0]
                try:fired=model.public(model.Oracle(words,initial,c).run().memory)!=model.public(expected)
                except(AssertionError,KeyError,IndexError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        rows=[model.Case(pattern=p,placement=q)for p,q in itertools.product(range(256),range(6))]
        variants=[('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()if n!='cached_pointer']
        for name,body,opt,wanted in variants:
            p=self.out/('native-'+name+'.c');p.write_text(native_source(body,rows));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        self.receipt('native-controls',rows_per_profile=len(rows),positive_executions=3*len(rows),profiles=['O0','O2','O3'],native_controls=len(variants)-3,IDO_controls=effective,UBSan=True,guest_only_pointer_object_aliases=True)
    def test_07_literal_image_and_old_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+276];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,276)
        for off in(0,at,at+275,at+276,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>69I',before,match.elf_slot_offset(before,match.ENTRY,276)));initial=model.fixture();m=model.Oracle(stub,initial).run();self.assertEqual(m.memory,initial);self.assertNotEqual(model.public(initial),model.public(model.reference(initial)[0]))
        self.receipt('image-controls',literal_changed_bytes=delta,exclusions=0,corruptions=5,old_stub_rejected=True)

def link_control(obj,p):
    text,fs,rs=match.parse_object(obj);rs={at:[(kind,match.RODATA_SYMBOL if name=='.rodata'else name)for kind,name in values]for at,values in rs.items()};s=model.symbols()
    asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);assert not unknown,unknown
    p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%match.ENTRY)
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()if not v[0].startswith('.')],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
    n=fs[match.FUNCTION]['size']//4;return list(struct.unpack_from('>%dI'%n,sections(p.with_suffix('.elf'))['.text'][1]))

def digest(values):
    v=2166136261
    for b in values:v=((v^b)*16777619)&0xFFFFFFFF
    return v
def native_source(body,cases):
    rows=[];s=model.symbols()
    for c in cases:
        expected=model.reference(model.fixture(c))[0];values=[expected[s['D_800BE2F0']+i]for i in range(232)]+[expected[model.PAYLOAD-16+i]for i in range(400)];rows.append('{%d,%d,0x%Xu}'%(c.pattern,c.placement,digest(values)))
    return '#include <ultra64.h>\n'+r'''
typedef union {u16 checksum;u8 bytes[112];} SaveBlock33990;
typedef union {struct{u8 prefix[104];u8 scratch[128];}layout;SaveBlock33990 save;u8 bytes[232];} Arena;
static Arena arena;static u8 payload[400];
#define D_800BE2F0 (arena.save)
#define D_800BE358 (arena.layout.scratch)
'''+candidate.DECLARATIONS+body+r'''
s8 *D_80082BBC;
typedef char record_layout[sizeof(SaveDefaultRecord33990)==10&&__builtin_offsetof(SaveDefaultRecord33990,value5)==5&&__builtin_offsetof(SaveDefaultRecord33990,value9)==9?1:-1];
typedef struct {u32 pattern,placement,expected;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static void(*volatile probe)(void)=func_15007168;
static int run(void){
 for(u32 n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  const Row *r=&rows[n];for(u32 i=0;i<232;i++)arena.bytes[i]=(u8)((i+16)*29+r->pattern*71+123);
  for(u32 i=0;i<400;i++)payload[i]=(u8)(i*29+r->pattern*71+123);
  u8 *p[6]={arena.bytes+2,arena.bytes,arena.bytes+4,payload+16,payload+17,payload+26};D_80082BBC=(s8*)p[r->placement];probe();
  u32 v=2166136261u;for(u32 i=0;i<232;i++)v=(v^arena.bytes[i])*16777619u;for(u32 i=0;i<400;i++)v=(v^payload[i])*16777619u;
  if(v!=r->expected)return 1;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
if __name__=='__main__':unittest.main()
