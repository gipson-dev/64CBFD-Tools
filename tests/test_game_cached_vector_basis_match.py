"""Direct cached basis C, original helpers, return consumers and complete image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_cached_vector_basis_candidates as candidate
from tools.experiments import game_cached_vector_basis_match as match
from tools.tests import game_cached_vector_basis_oracle as g
from tools.tests import game_cached_vector_basis_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class CallerCode(WindowCode):
    def __getitem__(self,pc):
        if pc in self.ends:self.stopped=pc
        return super().__getitem__(pc)

class CachedVectorBasisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.words==cls.raw==cls.retail
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,initial=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c)if initial is None else initial;expected,calls,obs,result=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m);self.assertEqual((g.public(m.memory,c),g.data(m.memory,g.address(c)),m.calls,m.observations,m.r[2]),(g.public(expected,c),g.data(expected,g.address(c)),calls,obs,result),c)
        for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
        return pair
    def test_01_direct_owner_layout_bindings_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(72,72,32,0,40,40,4));raw,bindings=match.function_blob(self.prepared['qualified_compact']);self.assertEqual(match.derive(raw,bindings),match.function_blob(self.prepared['qualified_owner']))
        for i in range(288):
            b=bytearray(raw);b[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(b),bindings)
        for at in bindings:
            b=dict(bindings);b[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,b)
        self.assertEqual((ROOT/match.GUARDS).read_bytes(),(self.out/'proposed-guards.csv').read_bytes());self.receipt('owner',raw_words=72,guards=0,bindings=4,neighbors=40,frame=32,state_bytes=44,SDK_struct17=True,raw_and_padded_pools_and_register_metadata_fixed=True,byte_corruptions_rejected=288,binding_corruptions_rejected=4)
    def test_02_flags_helper_failures_partial_writes_and_live_reloads(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertEqual([i for i in range(72)if match.ENTRY+4*i not in seen],[40,63]);self.receipt('guest',cases_per_body=count,bodies=2,raw_C_identical=True,all_256_flag_bytes=True,fullword_helper_results=True,all_three_early_failures_and_partial_updates=True,helper_flag_vector_and_radius_mutations=True,unreachable_duplicate_load_words=[40,63],all_reachable_root_words_visited=True)
    def test_03_aliases_and_fired_access_cuts(self):
        count=cuts=0
        for alias,flags,mutation,phase in itertools.product(range(3),range(8),(0,1,3,7),(0,8)):
            self.compare(g.Case(alias=alias,flags=flags,mutation=mutation,phase=phase));count+=1
        for c in(g.Case(),g.Case(flags=3),g.Case(flags=7),g.Case(outcomes=(0,)),g.Case(flags=3,outcomes=(1,0)),g.Case(mutation=7),g.Case(connected=3)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        c=g.Case(flags=7);initial=g.fixture(c)
        for i in range(4,44):initial.pop(g.address(c)+i)
        for w in(self.retail,self.words):
            m=g.Oracle(w,initial,c).run();self.assertEqual((m.r[2],m.calls),(1,[]))
        self.receipt('faults',alias_cases_per_body=count,fired_access_cuts=cuts,state_and_incoming_homes=True,literal_state_fault_PC_and_delay_markers_equal=True,fully_cached_path_needs_only_flags=True,private_guest_stack_and_faults_not_portable_C_claims=True)
    def test_04_original_normalizer_cross_product_and_basis(self):
        count=0;vectors=[(0,0,0),(1,0,0),(-2,0,0),(0,3,0),(0,0,-4),(1,2,3),(1,2,0),(0,2,3),(-3,2,1),(.125,-.5,2)]
        for connected,flags,values,phase in itertools.product((1,2,3),range(8),vectors,(0,8)):
            c=g.Case(connected=connected,flags=flags,vectors=tuple(g.bits(v)for v in(*values,0,2,0,3,0,0)),phase=phase)
            self.compare(c);count+=1
        self.receipt('providers',cases_per_body=count,normalizer_words=50,basis_words=148,cross_words=29,zero_axis_general_and_signed_vectors=True,in_place_normalization=True,optional_nested_length_and_reciprocal_outputs=True,staged_float32_reference=True,basis_ignores_nested_normalizer_return=True,no_additional_helper_C_credit_or_hardware_FCSR_claim=True)
    def test_05_three_original_callers_and_result_branches(self):
        words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(words)if w==jal],[0x17D444,0x1811C4,0x1FE158]);self.assertNotIn(match.ENTRY,words);self.assertNotIn(0x08000000|(match.ENTRY>>2&0x3FFFFFF),words);counts=[]
        for start,rom,reg,end,fail,n in((0x1514FF94,0x17D444,22,0x1514FFA4,0x1515013C,4),(0x15153D14,0x1811C4,23,0x15153D24,0x15153EE0,4),(0x151D0CA8,0x1FE158,22,0x151D0CBC,0x151D0EA0,5)):
            count=0
            for flags,outcomes,mutation,phase in itertools.product(range(8),((0,),(1,),(1,0)),(0,1,7),(0,8)):
                c=g.Case(flags=flags,outcomes=outcomes,mutation=mutation,phase=phase);initial=g.fixture(c);expected,calls,obs,result=g.reference(initial,c);pair=[]
                for w in(self.retail,self.words):
                    code=dict(zip(range(match.ENTRY,match.ENTRY+288,4),w));code[end]=code[fail]=0;m=g.Oracle(struct.unpack_from('>%dI'%n,self.rom,rom),initial,c,entry=start,connected=code,arguments=());m.r[reg]=g.address(c);m.code=CallerCode(m.code,m);m.code.ends=(end,fail)
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual(m.root_args,[(g.address(c),)]);self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.r[2]),(g.public(expected,c),[(match.ENTRY,(g.address(c),))]+calls,obs,result));self.assertEqual(m.code.stopped,end if result else fail);pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
            counts.append(count)
        self.receipt('callers',cases_per_body=counts,full_ROM_JAL_census=[0x17D444,0x1811C4,0x1FE158],literal_pointer_and_tail_entries=0,void_pointer_input_compatible=True,both_result_branches_and_delay_slots=True,windows_end_before_RNG=True,complete_parents_not_claimed=True)
    def test_06_independent_GNU_links_all_four_bindings(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:entry+0x10000*(i+1)for i,n in enumerate(s)}
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:
                            typ,sym=match.BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[288:],bytes(len(blob)-288));images.append(list(struct.unpack_from('>72I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_compact']),s))
            for flags,outcomes,mutation in itertools.product(range(8),((1,),(0,),(1,0)),(0,7)):self.compare(g.Case(flags=flags,outcomes=outcomes,mutation=mutation),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_four_JAL_bindings=True,zero_standalone_tail=True)
    def test_07_SDK_native32_layout_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-3500:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=511,SDK_native32_UBSan=True,struct17_and_44_byte_state_offsets=True,typed_helpers_and_void_pointer_entry=True,full_state_calls_observations_and_partial_failure_checked=True)
    def test_08_literal_full_image_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),197);at=match.elf_slot_offset(before,match.ENTRY,288)
        locations=[0,at,at+287,at+288,len(after)-1,next(p+8 for p,n,f,loc in match.symbol_rows(before)if n==match.FUNCTION)]
        for off in locations:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        c=g.Case(flags=7);initial=g.fixture(c);m=g.Oracle(struct.unpack_from('>72I',before,at),initial,c).run();self.assertEqual(m.r[2],0);self.assertEqual(g.reference(initial,c)[3],1)
        self.receipt('image',strict_changed_bytes=197,exclusions=0,metadata_permutations=0,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=len(locations),former_stub_result_rejected=True,guards_unchanged=True)
if __name__=='__main__':unittest.main()
