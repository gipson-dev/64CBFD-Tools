"""Queue drain, closed argument schedule, typed dependent stub and literal ELF."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_position_queue_drain_candidates as candidate
from tools.experiments import game_position_queue_drain_match as match
from tools.tests import game_position_queue_drain_oracle as g
from tools.tests import game_position_queue_drain_native as native
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

class PositionQueueDrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.words==cls.retail;assert sum(a!=b for a,b in zip(cls.raw,cls.retail))==20
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,initial=None,raw=False):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;expected,calls,obs,result=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m);self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.r[2]),(g.public(expected,c),calls,obs,result),c)
        for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
        if raw:
            m=g.Oracle(self.raw,initial,c,s=s).run();self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.r[2]),(g.public(expected,c),calls,obs,result),c)
        return pair
    def test_01_owner_dependencies_guards_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(72,72,80,20,12,12,11));self.assertEqual(q['raw_metadata_changes'],['F4 mask 0x1000 to 0x1010']);self.assertEqual(q['padded_metadata_changes'],[]);self.assertEqual(q['dependent_helper']['additional_matching_credit'],0)
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);self.assertEqual(match.derive(raw,bindings),match.function_blob(self.prepared['qualified_owner']));self.assertEqual(match.schedule_dependencies(list(struct.unpack('>72I',raw))),10)
        for i in range(288):
            b=bytearray(raw);b[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(b),bindings)
        for at in bindings:
            b=dict(bindings);b[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,b)
        before=(self.out/'match-frozen'/match.GUARDS).read_bytes();guards=(self.out/'proposed-guards.csv').read_bytes();self.assertTrue(guards.startswith(before));self.assertEqual(guards,match.guard_manifest(before,raw,bindings));rows=list(match.csv.DictReader(match.io.StringIO(guards.decode())));self.assertEqual(len([r for r in rows if r['function']==match.FUNCTION]),20)
        self.receipt('owner',raw_words=72,raw_differences=20,guards=20,bindings=11,other_neighbors=12,frame=80,closed_instruction_permutation=True,register_and_HI_LO_dependency_edges=10,dependent_helper_fully_audited=True,new_helper_credit=0,byte_corruptions_rejected=288,binding_corruptions_rejected=11)
    def test_02_phase_wrap_reverse_queue_live_mutations_and_arguments(self):
        count=0;seen=set();cycles=set()
        for c in g.cases():
            initial=g.fixture(c);self.assertEqual(initial[g.PHASE],c.cycle);cycles.add(initial[g.PHASE])
            for m in self.compare(c,initial=initial,raw=True):seen.update(m.visits)
            count+=1
        self.assertEqual(cycles,set(range(256)));self.assertEqual([i for i in range(72)if match.ENTRY+4*i not in seen],[]);self.receipt('guest',cases_per_body=count,literal_bodies=2,raw_C_semantics_checked_separately=True,all_256_phase_and_null_pixel_count_bytes=True,all_root_words_visited=True,signed_coordinates_unsigned_record_values_and_raw_float_bits=True,live_count_refill_record_and_phase_changes=True,original_index_restored=True,NULL_and_chained_Gfx_returns=True)
    def test_03_incoming_home_aliases_and_fired_access_cuts(self):
        count=cuts=0;raw,bindings=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,bindings)
        for name,offset,phase,n,mutation in itertools.product(('D_800DDD1C','D_8008CEB0','D_800DDD28','D_800DDD58'),(0,64),(0,8),range(4),(0,7)):
            c=g.Case(count=n,phase=phase,mutation=mutation);s=g.symbols();s[name]=g.STACK+phase+offset;w=match.bound_blob(normalized,moved,s);self.compare(c,images=(w,w),s=s);count+=1
        for c in(g.Case(),g.Case(count=0),g.Case(pixels=0),g.Case(count=255,pixels=0),g.Case(mutation=7),g.Case(returns=1),g.Case(connected=1)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        c=g.Case(count=255,pixels=0);initial=g.fixture(c)
        for i in range(48):initial.pop(g.QUEUE+i)
        self.compare(c,initial=initial);self.receipt('faults',alias_cases_per_body=count,fired_access_cuts=cuts,literal_state_fault_PC_and_delay_markers_equal=True,NULL_pixels_need_no_record_data=True,raw_load_schedule_not_claimed_fault_equivalent=True,guest_homes_not_portable_alias_claims=True)
    def test_04_original_capacity_gate_producer_and_dependent_stub(self):
        count=producers=stubs=0
        for n,cycle,index,view,phase in itertools.product(range(4),(0,194,195,250,251,255),(0,1,0x80000000,0xFFFFFFFF),range(3),(0,8)):
            self.compare(g.Case(count=n,cycle=cycle,index=index,capacity=index,view=view,phase=phase,connected=1));count+=1
        pwords=struct.unpack_from('>33I',self.rom,0x1AAA28)
        for n,seed,phase in itertools.product(range(5),range(8),(0,8)):
            c=g.Case(count=n,pixels=0 if n>3 else g.PIXELS,seed=seed,phase=phase);initial=g.fixture(c);args=(0xABCD8001,0x12347FFF,0xFFFFFFFE,(0x80000000,1,0x7F800000,0x7FC12345,0x7FA12345,0xBF800000,0x7F7FFFFF,0)[seed],0x1234FFFF,0xABCD8000,0x123400FF)
            machine=g.Oracle(pwords,initial,c,entry=g.PRODUCER,arguments=args).run();self.assertEqual(g.public(machine.memory,c),g.public(g.producer(initial,c,args),c));self.compare(c,initial=machine.memory);producers+=1
        for n,pixels,phase in itertools.product(range(4),(0,g.PIXELS),(0,8)):
            c=g.Case(count=n,pixels=pixels,phase=phase,stub=1);initial=g.fixture(c);expected,calls,obs,result=g.reference(initial,c);variants=[]
            for blob in(match.HELPER_BEFORE,match.HELPER_AFTER):
                connected=dict(zip(range(g.HELPER,g.HELPER+len(blob),4),struct.unpack('>%dI'%(len(blob)//4),blob)));pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=connected).run();self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.r[2]),(g.public(expected,c),calls,obs,result));pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));variants.append(pair[0])
            differences={p for p in set(variants[0].memory)|set(variants[1].memory)if variants[0].memory.get(p)!=variants[1].memory.get(p)};self.assertLessEqual(differences,set(range(g.STACK+phase-80,g.STACK+phase-64)));stubs+=1
        self.receipt('providers',capacity_gate_cases_per_body=count,original_helper_words=321,complete_helper_capacity_reject_only=True,producer_cases_per_body=producers,original_producer_words=33,dependent_stub_cases_per_body=stubs,old_and_typed_stub_call_semantics_preserved=True,private_home_difference_exactly_bounded=True,no_extra_C_or_rendering_credit=True)
    def test_05_original_caller_and_Gfx_result_store(self):
        words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(words)if w==jal],[0x1AACC8]);self.assertNotIn(match.ENTRY,words);self.assertNotIn(0x08000000|(match.ENTRY>>2&0x3FFFFFF),words);count=0;start,end=0x1517D814,0x1517D824
        for n,pixels,mutation,returns,phase in itertools.product(range(4),(0,g.PIXELS),(0,1,2,7),range(3),(0,8)):
            c=g.Case(count=n,pixels=pixels,mutation=mutation,returns=returns,phase=phase);initial=g.fixture(c);expected,calls,obs,result=g.reference(initial,c);g.put(expected,g.CURSOR,result);pair=[]
            for w in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+288,4),w));code[end]=0;m=g.Oracle(struct.unpack_from('>4I',self.rom,0x1AACC4),initial,c,entry=start,connected=code);m.r[16]=g.CURSOR;m.r[5]=0x800E0000;m.code=CallerCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.root_args,[(c.display,c.pixels)]);self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.r[2]),(g.public(expected,c),[(match.ENTRY,(c.display,c.pixels))]+calls,obs,result));self.assertEqual(m.code.stopped,end);pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',cases_per_body=count,window_words=4,call_VA=0x1517D818,JAL_ROM=0x1AACC8,pixel_global='D_800DDD24',NULL_pixels_and_Gfx_result_store=True,full_ROM_literal_and_tail_entries=0,complete_parent_not_claimed=True)
    def test_06_independent_GNU_links_all_eleven_bindings(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:entry+0x10000 if n.startswith('func_')else 0x81007FFC+0x10000*(k-1)+256*i for i,n in enumerate(s)}
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
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[288:],bytes(len(blob)-288));images.append(list(struct.unpack_from('>72I',blob)));links+=1
            self.assertEqual(images[0],images[1]);raw,bindings=match.function_blob(self.prepared['qualified_compact']);self.assertEqual(images[0],match.bound_blob(*match.derive(raw,bindings),s))
            for n,pixels,mutation in itertools.product(range(4),(0,g.PIXELS),(0,7)):self.compare(g.Case(count=n,pixels=pixels,mutation=mutation),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_eleven_bindings=True,signed_low16_carries=True)
    def test_07_SDK_native32_layout_calls_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-3500:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=1023,SDK_native32_UBSan=True,real_three_record_bounds=True,typed_ten_argument_ABI_and_pixel_stride=True,raw_float_bits_moved_without_arithmetic=True,complete_state_calls_observations_and_result_checked=True,unfinished_typed_helper_still_returns_NULL=True)
    def test_08_literal_full_image_two_functions_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),249);at=match.elf_slot_offset(before,match.ENTRY,288);helper=match.elf_slot_offset(before,g.HELPER,28)
        locations=[0,at,at+287,at+288,helper,helper+27,helper+28,len(after)-1]+[p+8 for p,n,f,loc in match.symbol_rows(before)if n in(match.FUNCTION,match.HELPER)]
        for off in locations:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        c=g.Case(count=0);initial=g.fixture(c);m=g.Oracle(struct.unpack_from('>72I',before,at),initial,c).run();self.assertEqual(m.r[2],0);self.assertNotEqual(g.public(m.memory,c),g.public(g.reference(initial,c)[0],c));self.receipt('image',strict_changed_bytes=249,exclusions=0,metadata_permutations=0,changed_bodies=[match.FUNCTION,match.HELPER],helper_footprint_and_symbol_size_predicted=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=len(locations),former_stub_phase_and_return_rejected=True,matching_credit=1)
if __name__=='__main__':unittest.main()
