"""Direct C constructor: two owners, all byte axes, real parents and helpers."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_selector_table_payload_candidates as candidate
from tools.experiments import game_selector_table_payload_match as match
from tools.tests import game_selector_table_payload_oracle as g
from tools.tests import game_selector_table_payload_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.copy_observations,m.snapshots,m.current_pc,m.delay_of,m.all_accesses,m.visits)
class SelectorTablePayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM));cls.words=g.bound(cls.prepared['qualified_owner'])
        assert cls.retail==cls.words==g.bound(cls.prepared['qualified_compact'])
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,entry=match.ENTRY,s=None,connected=None,actual=False):
        initial=g.fixture(c,s);expected,calls,result,copies,snapshots=g.reference(initial,c,s=s,connected=actual);pair=[]
        for body in(self.retail,self.words)if images is None else images:
            m=g.Oracle(body,initial,c,s=s,entry=entry,connected=connected).run();pair.append(m)
            self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.copy_observations,m.snapshots),(g.public(expected,c),calls,result,copies,snapshots),c)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.before_f[20:])
        self.assertEqual(state(pair[0]),state(pair[1]));return pair
    def test_01_owner_and_binding_corruption_controls(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(71,80,0,8))
        self.assertEqual([(x['raw_neighbors'],x['padded_neighbors'])for x in q['owners'].values()],[(77,77),(82,82)])
        self.assertTrue(q['owners']['game_36680']['object_completely_fixed'])
        raw,b=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+284]
        for at in range(284):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,truth)
        for at in b:
            bad=dict(b);bad[at]=[(b[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        self.receipt('owner-controls',raw_corruptions=284,binding_corruptions=8,neighbors=[77,82],caller_object_fixed=True,guards=0)
    def test_02_all_byte_axes_table_capture_and_71_words(self):
        seen=set();count=0
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+284,4)))
        self.receipt('guest-contract',cases_per_body=count,all_256_selectors=True,all_byte_axes=True,all_71_words=True,header_padding_guest_only=True,mutable_tables_and_incoming_homes=True,null_actor_accepted=True)
    def test_03_guest_stack_table_aliases_and_fired_fault_prefixes(self):
        count=cuts=0
        for name,phase,off,selector in itertools.product(('D_800A670C','D_800A6730','D_800A6754'),(0,8),range(-64,64,4),(0,1,2)):
            c=g.Case(128,selector=selector,phase=phase);s=g.symbols();s[name]=g.STACK+phase+off;initial=g.fixture(c,s)
            retail=list(self.retail)
            for at,rs in match.BINDINGS.items():
                typ,sym=rs[0];value=s[sym]
                if typ=='R_MIPS_HI16':retail[at//4]=(retail[at//4]&0xFFFF0000)|(((value+0x8000)>>16)&65535)
                elif typ=='R_MIPS_LO16':retail[at//4]=(retail[at//4]&0xFFFF0000)|(value&65535)
            pair=[g.Oracle(w,initial,c,s=s).run()for w in(retail,g.bound(self.prepared['qualified_owner'],s))]
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1
        for c in(g.Case(selector=255),g.Case(127,allocated=0,mode=3),g.Case(128,selector=2,mode=3,phase=8)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.retail,self.words):
                    m=g.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipt('aliases-faults',guest_stack_table_aliases=count,fired_access_prefixes=cuts,literal_state_equal=True,portable_stack_aliases_not_claimed=True)
    def test_04_original_record_allocator_and_memcpy(self):
        before=self.prepared['predecessor_elf'].read_bytes();code={};spans=((g.CREATE,0x18D82C,32),(g.COPY,0x22EC0,11))
        for entry,at,n in spans:
            truth=self.rom[at:at+4*n];self.assertEqual(before[match.elf_slot_offset(before,entry,4*n):][:4*n],truth)
            code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,truth)))
        seen=set();count=0
        for i,selector,allocated,mode,phase in itertools.product((0,127,128,255),(0,1,2,3),(0,1),(0,3),(0,8)):
            for m in self.compare(g.Case(i,selector=selector,allocated=allocated,mode=mode,phase=phase),connected=code,actual=True):seen.update(m.visits)
            count+=1
        self.assertTrue(all(set(range(e,e+4*n,4))<=seen for e,at,n in spans))
        self.receipt('original-helpers',cases_per_body=count,record_words=32,memcpy_words=11,all_words_visited=True,allocator_opaque=True,allocation_size_56=True,whole_engine_claimed=False)
    def test_05_both_complete_original_callers(self):
        count=0;coverage=[]
        for start,rom in((0x150098F8,0x36DA8),(0x1500A55C,0x37A0C)):
            # Both callers are complete 19-word wrappers, including saved RA and epilogue.
            body=list(struct.unpack_from('>19I',self.rom,rom));seen=set()
            for i,allocated,mode,phase,owner in itertools.product((0,127,128,255),(0,1),(0,3),(0,8),(0,g.OWNER)):
                c=g.Case(i,allocated=allocated,mode=mode,phase=phase,owner=owner);pair=[]
                for words in(self.retail,self.words):
                    code=dict(zip(range(match.ENTRY,match.ENTRY+284,4),words))
                    m=g.Oracle(body,g.fixture(c),c,entry=start,connected=code).run();pair.append(m);seen.update(m.visits)
                    expected=(owner,1,22,0,0xFFFFFFFF,300,255,1);self.assertEqual(m.a,expected)
                    memory,calls,result,copies,snapshots=m.entry_contract
                    self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.copy_observations,m.snapshots),(g.public(memory,c),[(match.ENTRY,expected)]+calls,result,copies,snapshots))
                self.assertEqual(state(pair[0]),state(pair[1]));count+=1
            self.assertTrue(set(range(start,start+76,4))<=seen);coverage.append(dict(entry=hex(start),words=19))
        self.receipt('callers',cases_per_body=count,complete_parents=coverage,eight_arguments=True,real_delay_stores=True)
    def test_06_independent_GNU_table_and_call_rebases(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s=dict(D_800A670C=0x80107FFC+0x10000*k,D_800A6730=0x80208000+0x10000*k,D_800A6754=0x8030FFFC+0x10000*k,func_1516037C=entry+0x10000,memcpy=entry+0x20000)
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:
                            typ,sym=match.BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_compact']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[284:],bytes(len(blob)-284));images.append(list(struct.unpack_from('>71I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],g.bound(self.prepared['qualified_compact'],s))
            for i,selector,allocated in itertools.product((0,127,128,255),(0,1,2,3),(0,1)):self.compare(g.Case(i,selector=selector,allocated=allocated),images=images,entry=entry,s=s);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_eight_bindings=True,low16_carry_boundaries=True,standalone_tail_zero=True)
    def test_07_SDK_native32_and_ten_checked_controls(self):
        text,controls,count=native.program();p=self.out/'match-native-contract.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native-contract'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native-controls',cases_per_profile=count,positive_executions=3*count,total_calls=33*count,controls=controls,checked_control_mask=1023,SDK_native32=True,UBSan=True,padding_values_guest_only=True,typed_8_argument_callback=True)
    def test_08_strict_image_and_old_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(before,match.ENTRY,284)
        for off in(0,at,at+283,at+284,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>71I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        self.receipt('image-controls',literal_changed_bytes=delta,old_symbol_bytes=12,new_symbol_bytes=284,exclusions=0,metadata_permutations=0,corruptions=5,old_stub_rejected=True)
if __name__=='__main__':unittest.main()
