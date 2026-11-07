"""Query payloads, four callers, original provider, commutative guards and ELF."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_record_position_query_candidates as candidate
from tools.experiments import game_record_position_query_match as match
from tools.tests import game_record_position_query_oracle as g
from tools.tests import game_record_position_query_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_record_address_relocator_match import dependent_sections
ROOT=candidate.ROOT
class RecordPositionQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.words==cls.retail and sum(a!=b for a,b in zip(cls.raw,cls.words))==2
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s);expected,calls,result,obs=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words,self.raw)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m);self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.observations),(g.public(expected,c),calls,result,obs),c)
        for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
        return pair
    def test_01_two_ADDU_guards_owner_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(72,888,2,27,27,5));raw,bindings=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,bindings);self.assertEqual((normalized,moved),match.function_blob(self.prepared['qualified_owner']))
        for i in range(288):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad)
        rows=list(match.csv.DictReader(match.io.StringIO((self.out/'proposed-guards.csv').read_text())));new=[r for r in rows if r['function']==match.FUNCTION];self.assertEqual([int(r['offset'],0)for r in new],[0xB4,0xD8]);self.assertTrue(all(r['omit']=='false'and not r['insert_after']and r['expected_relocations']==r['replacement_relocations']=='-'for r in new));self.assertTrue((self.out/'proposed-guards.csv').read_bytes().startswith((self.out/'match-frozen'/match.GUARDS).read_bytes()))
        a,b=[dependent_sections((self.out/n).read_bytes())for n in('match-predecessor.o','match-qualified.o')];x,y=a['.options'][1],b['.options'][1];self.assertEqual((x[:8],x[12:]),(y[:8],y[12:]));self.assertEqual((x[8:12].hex(),y[8:12].hex()),('a33ffffe','a37ffffe'))
        self.receipt('owner',raw_words=72,raw_differences=2,frame=888,real_query_bytes=812,query_home='SP+0x48',guards=2,byte_corruptions=288,binding_corruptions=5,neighbors=27,only_ADDU_rs_rt_swapped=True,raw_S6_mask_only_added=True)
    def test_02_filters_unsigned_count_float_rounding_and_mutable_queries(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        missing=[i for i in range(72)if match.ENTRY+4*i not in seen];self.assertEqual(missing,[55]);self.receipt('guest',cases_per_body=count,bodies=3,all_256_status_flags_subtype_bytes=True,fullword_filters_and_unsigned_count=True,signed32_to_float32_boundaries=True,seven_fields_once_then_mutable=True,live_base_count_and_first_zero_result=True,raw_C_full_literal_state_equal=True,unreachable_count_load_word=55)
    def test_03_query_table_global_aliases_homes_and_fault_prefixes(self):
        count=cuts=0
        for alias,kind,subtype,mutation,phase in itertools.product(range(4),(0,3),(0,6,11),(0,7,8,16),(0,8)):
            self.compare(g.Case(alias=alias,kind=kind,subtype=subtype,layout=1,outcomes=(1,0),mutation=mutation,phase=phase));count+=1
        for c in(g.Case(),g.Case(layout=1,mutation=31,outcomes=(1,0)),g.Case(alias=1,kind=0,subtype=0),g.Case(layout=1,connected=1)):
            initial=g.fixture(c);code=g.helper_code(self.rom,c);full=g.Oracle(self.retail,initial,c,connected=code).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words,self.raw):
                    m=g.Oracle(w,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
                cuts+=1
        self.receipt('faults',alias_home_cases_per_body=count,fired_access_cuts=cuts,bodies=3,full_812_byte_query_observations=True,query_table_base_count_aliases=True,incoming_homes_do_not_reinitialize_query=True,portable_private_bytes_faults_or_arbitrary_pointer_math_not_claimed=True)
    def test_04_original_provider_box_plane_and_initialized_read_boundary(self):
        count=0;seen=set();offsets=set()
        for geometry,coords,height,mode in itertools.product((2,3),((-11,1,0),(-9,1,9),(0,0,0),(0,1,0),(9,19,-9),(10,10,0),(0,20,0)),(0,1),(0,3)):
            c=g.Case(coords=coords,layout=1,geometry=geometry,height_gate=height,connected=1,mutation=mode)
            for m in self.compare(c):
                seen.update(m.visits);q=g.query_address(g.STACK+c.phase);offsets.update(at-q for op,at,n,v in m.trace if op=='R'and q<=at<q+812)
            count+=1
        self.assertEqual(offsets,set(g.FIELDS));self.assertTrue({0x150A1DF8,0x150A1E14,0x150A1E58,0x150A1E98,0x150A215C,0x150A2170,0x150A2188}<=seen)
        self.receipt('provider',cases_per_body=count,original_provider_words=401,connected_geometry_modes=[2,3],query_float_read_offsets=sorted(offsets),third_argument_zero_avoids_offset_E4=True,box_boundary_and_stationary_plane_contracts=True,other_geometry_hardware_and_full_provider_C_recovery_not_claimed=True)
    def test_05_all_four_original_callers_and_return_consumers(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(allwords)if w==jal],[0xAD4EC,0xAD528,0xB4154,0xC7D2C]);self.assertFalse(any(w in(match.ENTRY,0x08000000|(match.ENTRY>>2&0x3FFFFFF))for w in allwords));count=0
        for which,coords,floats,outcomes,mutation,phase in itertools.product(range(4),((-32768,0,32767),(17,-91,255)),((17.75,-91.25,255.875),(-32768.75,32767.75,.875)),((0,),(1,)),(0,7),(0,8)):
            pair=[]
            for w in(self.retail,self.words,self.raw):
                m,(expected,calls,result,obs,pointer),c=g.caller_machine(self.rom,w,g.Case(coords=coords,layout=0,outcomes=outcomes,mutation=mutation,phase=phase),which,floats)
                if which==2:m.run()
                else:
                    with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.observations),(g.public(expected,c),calls,result,obs));self.assertEqual(m.root_args,[g.args(c)]);self.assertEqual(tuple(m.r[i]for i in(*range(16,24),28,29,30)),m.saved);pair.append(m)
            for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
            count+=1
        self.receipt('callers',cases_per_body=count,bodies=3,original_sites=4,window_words=[15,13,19,23],full_19_word_table_wrapper=True,float_truncation_and_signed16_coordinates=True,fifth_stack_argument_and_pointer_return=True,null_branch_and_record_index_sentinel=True,full_large_parents_not_claimed=True)
    def test_06_independent_GNU_links_and_all_five_bindings(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:(entry+0x10000*(j+1)if n.startswith('func_')else 0x81007FFC+0x10000*j)for j,n in enumerate(s)}
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
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_owner']),s))
            for mode,outcome,count_rows in itertools.product((0,7,19),((0,),(1,0)),(0,6)):self.compare(g.Case(mutation=mode,outcomes=outcome,count=count_rows),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_five_bindings=True,signed_low16_carry=True,JAL_region=True,standalone_zero_tail=True)
    def test_07_SDK_native32_defined_address_math_and_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-2000:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=255,SDK_native32_UBSan=True,actor_record_pointer_and_field_ABI_assertions=True,integer_address_sums_within_signed32=True,high_count_positive_first_success=True,negative_controls_bounded_to_eight_records=True,only_initialized_query_fields_read=True)
    def test_08_literal_image_and_rejected_query_layouts(self):
        q=json.loads((self.out/'candidate-screens-initial.json').read_text());self.assertEqual((q[0]['words'],q[0]['frame'],q[0]['differences']),(72,888,27));before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),220);at=match.elf_slot_offset(before,match.ENTRY,288)
        for off in(0,at,at+287,at+288,0x29D100,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        m=g.Oracle(struct.unpack_from('>72I',before,at),g.fixture()).run();self.assertFalse(m.calls);self.assertEqual(m.r[2],0);self.receipt('image',strict_changed_bytes=220,exclusions=0,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,stub_rejected=True,initial_source_shape_rejected=True,guards_expected_word_pairs_only=True)
if __name__=='__main__':unittest.main()
