"""Direct constructor, three complete owners, twelve original call setups."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_owner_vector_candidates as candidate
from tools.experiments import game_owner_vector_match as match
from tools.tests import game_owner_vector_oracle as g
from tools.tests import game_owner_vector_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):
    return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.copy_observations,
           m.snapshots,m.current_pc,m.delay_of,m.all_accesses,m.visits)

class OwnerVectorMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM));cls.raw=g.bound(cls.prepared['qualified_compact']);cls.words=g.bound(cls.prepared['qualified_owner'])
        assert cls.retail==cls.raw==cls.words
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),initial=None,arguments=None,s=None,images=None,entry=match.ENTRY,connected=None,actual=False):
        initial=g.fixture(c,arguments)if initial is None else initial
        expected,calls,result,copies,snapshots=g.reference(initial,c,arguments,s,connected=actual);pair=[]
        for body in(self.retail,self.words)if images is None else images:
            m=g.Oracle(body,initial,c,arguments,s,entry,connected).run();pair.append(m)
            self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.copy_observations,m.snapshots),(g.public(expected,c),calls,result,copies,snapshots),c)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.before_f[20:])
        self.assertEqual(state(pair[0]),state(pair[1]));return pair
    def test_01_three_owners_zero_guards_and_complete_body_controls(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(71,104,0,2))
        self.assertEqual([(x['raw_neighbors'],x['padded_neighbors'])for x in q['owners'].values()],[(77,77),(44,44),(78,78)])
        self.assertTrue(all(x['raw_pools_fixed']and x['padded_pools_fixed']for x in q['owners'].values()))
        self.assertTrue(all(x['object_completely_fixed']for n,x in q['owners'].items()if n!=candidate.OWNER))
        raw,b=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+284]
        for at in range(284):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        self.assertEqual((ROOT/match.GUARDS).read_bytes(),(self.out/'match-frozen'/match.GUARDS).read_bytes())
        self.receipt('owner-controls',raw_byte_corruptions=284,binding_corruptions=2,guards=0,owner_neighbors=[77,44,78],
                     all_raw_and_padded_pools_fixed=True,both_caller_objects_completely_fixed=True,old_guard_bytes_fixed=True)
    def test_02_sixteen_arguments_payload_capture_and_all_words(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+284,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=2,all_71_words=True,all_256_byte_axes=True,arbitrary_vector_words=True,
                     size_word_wrap=True,allocation_outcomes=3,mutable_inputs=True,full_literal_stack_RAM_registers_events_and_payload_padding=True)
    def test_03_private_vector_aliases_and_fault_prefixes(self):
        count=cuts=0
        for phase,off,outcome in itertools.product((0,8),range(-64,64,4),(0,2)):
            c=g.Case(128,vector=g.STACK+phase+off,outcome=outcome,phase=phase);initial=g.fixture(c)
            pair=[g.Oracle(w,initial,c).run()for w in(self.retail,self.words)]
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1
        for c in(g.Case(outcome=0),g.Case(127,outcome=1,mode=3,phase=8),g.Case(255,mode=3)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.retail,self.words):
                    m=g.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipt('aliases-faults',guest_vector_stack_aliases_per_body=count,fired_access_prefixes=cuts,full_literal_state_equal=True,
                     portable_stack_aliases_or_padding_values_not_claimed=True)
    def test_04_original_factory_record_allocator_and_copy(self):
        before=self.prepared['predecessor_elf'].read_bytes();code={};spans=((g.FACTORY,0x18D770,47),(g.CREATE,0x18D82C,32),(g.COPY,0x22EC0,11))
        for entry,at,n in spans:
            truth=self.rom[at:at+4*n];self.assertEqual(before[match.elf_slot_offset(before,entry,4*n):][:4*n],truth)
            code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,truth)))
        count=0;seen=set()
        for index,outcome,mode,phase in itertools.product(range(32),(0,1,2),(0,3),(0,8)):
            c=g.Case(index,outcome=outcome,mode=mode,phase=phase)
            for m in self.compare(c,connected=code,actual=True):seen.update(m.visits)
            count+=1
        coverage=[dict(entry=hex(entry),words=n,covered=len(set(range(entry,entry+4*n,4))&seen))for entry,at,n in spans]
        self.assertEqual([x['covered']for x in coverage],[47,32,11])
        self.receipt('original-helpers',cases_per_body=count,helpers=coverage,current_helpers_byte_exact=True,actor_constructor_allocator_and_free_opaque=True,
                     actor_failure_record_failure_and_success=True,header_copy_and_flags_and_actor_pointer=True,whole_engine_gameplay_claimed=False)
    def test_05_all_twelve_original_call_setups(self):
        count=0;coverage=[]
        for index in range(12):
            seen=set()
            for seed,outcome,mode,phase,owner in itertools.product((0,127,128,255),(0,1,2),(0,3),(0,8),(0,g.OWNER)):
                c=g.Case(seed,owner=owner,outcome=outcome,mode=mode,phase=phase);pair=[]
                for words in(self.retail,self.words):
                    m=g.caller_machine(self.rom,words,index,c)
                    with self.assertRaises(WindowBoundary):m.run()
                    expected=g.expected_caller(index,owner,m.target_home,seed,0x87654321)
                    self.assertEqual(m.a,expected,(index,c,m.a,expected))
                    memory,calls,result,copies,snapshots=m.entry_contract
                    self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.copy_observations,m.snapshots),
                                     (g.public(memory,c),[(match.ENTRY,expected)]+calls,result,copies,snapshots))
                    pair.append(m);seen.update(m.visits)
                self.assertEqual(state(pair[0]),state(pair[1]));count+=1
            addresses=set(range(g.CALLER_ENTRIES[index],g.CALLER_PCS[index]+8,4));self.assertTrue(addresses<=seen)
            coverage.append(dict(entry=hex(g.CALLER_ENTRIES[index]),jal=hex(g.CALLER_PCS[index]),words=len(addresses)))
        self.receipt('caller-contract',cases_per_body=count,call_sites=12,parent_functions=10,source_owners=5,windows=coverage,
                     complete_sixteen_word_argument_matrix=True,real_delay_slot_stores=True,prior_calls_and_parent_state_explicit_preconditions=True,
                     full_parents_not_claimed=True)
    def test_06_independent_GNU_links(self):
        count=links=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s=dict(func_151602C0=entry+0x10000,memcpy=entry+0x20000)
            images=[]
            # The retail words are independently assembled with their two real call bindings.
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:rows.append('.reloc ., R_MIPS_26, '+match.BINDINGS[4*i][0][1]);w&=0xFC000000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_compact']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,
                                *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[284:],bytes(len(blob)-284));images.append(list(struct.unpack_from('>71I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],g.bound(self.prepared['qualified_compact'],s))
            for c in list(g.cases())[::127]:self.compare(c,s=s,entry=entry,images=images);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,layouts=3,both_call_bindings=True,zero_standalone_tail_checked=True)
    def test_07_SDK_native32_layouts_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native-contract.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native-contract'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native-controls',cases_per_profile=count,positive_executions=3*count,total_calls=3*count*11,controls=controls,checked_control_mask=1023,
                     SDK_native32=True,UBSan=True,typed_16_argument_callback=True,header_and_payload_defined_fields_checked=True,
                     payload_owner_pointer_and_all_three_vector_words_checked=True,padding_values_guest_only=True,sanitizer_trap_cannot_satisfy_control=True)
    def test_08_strict_image_symbol_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(before,match.ENTRY,284)
        for off in(0,at,at+283,at+284,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>71I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        rows=[f for p,n,f,s in match.symbol_rows(before)if n==match.FUNCTION];self.assertEqual(rows[0][2],28)
        self.receipt('image-controls',literal_changed_bytes=delta,old_symbol_bytes=28,new_symbol_bytes=284,exclusions=0,metadata_permutations=0,corruptions=5,old_stub_rejected=True)

if __name__=='__main__':unittest.main()
