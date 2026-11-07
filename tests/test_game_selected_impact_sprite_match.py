"""Impact sprite: real frame tail, six JALs, callback, native32 and whole ELF."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_selected_impact_sprite_candidates as candidate
from tools.experiments import game_selected_impact_sprite_match as match
from tools.tests import game_selected_impact_sprite_oracle as g
from tools.tests import game_selected_impact_sprite_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class SelectedImpactSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>109I',cls.rom,0x1B9B4C));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owners'][0],0),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compacts'][0],0),g.symbols());assert cls.words==cls.retail
        before=cls.prepared['predecessor_elf'].read_bytes();at=match.elf_slot_offset(before,g.COLORS,768);g.COLORS_DATA=before[at:at+768]
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),images=None,s=None,entry=g.ENTRY,initial=None,include_raw=True):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;pair=[]
        for j,w in enumerate((self.retail,self.words,self.raw)if images is None and include_raw else(self.retail,self.words)if images is None else images):
            frame=256 if images is None and j==2 else 248;e=g.reference(initial,c,s,frame=frame);m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c,s),frame=frame).run();self.assertEqual((g.public(m.memory),m.calls,m.packets,m.vectors,m.services,m.marks,m.r[2]),(g.public(e['memory']),e['calls'],e['packets'],e['vectors'],e['services'],e['marks'],1),c);pair.append(m)
        self.assertEqual(g.state(pair[0]),g.state(pair[1]));return pair
    def test_01_owner_frame_extent_and_guard_closure(self):
        q=self.prepared['report']['targets'][0];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['padded_neighbors']),(109,248,21,6,8,8));self.assertEqual((q['diagnostics']['before'],q['diagnostics']['after']),(0,0));raw,b=match.function_blob(self.prepared['qualified_compacts'][0],0);normalized,nb=match.derive(raw,b,0);self.assertEqual((normalized,nb),match.function_blob(self.prepared['qualified_owners'][0],0));proof=match.audit_schedule(raw,normalized,0);self.assertEqual((proof['raw_frame'],proof['retail_frame'],proof['unused_tail_bytes'],proof['incoming_homes']),(256,248,8,6))
        for at in range(436):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),b,0)
        for at in b:
            bad=dict(b);bad[at]=[(b[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad,0)
        for word,replacement in((14,0xA7AF00F8),(54,0x27A400F8),(4,0xAFA50100)):
            a=bytearray(raw);n=bytearray(normalized);struct.pack_into('>I',a,4*word,replacement);struct.pack_into('>I',n,4*word,replacement)
            with self.assertRaises(ValueError):match.audit_schedule(bytes(a),bytes(n),0)
        old=(self.out/'match-frozen'/match.GUARDS).read_bytes();new=(self.out/'proposed-guards.csv').read_bytes();self.assertTrue(new.startswith(old));self.assertEqual(new,match.guard_manifest(old));self.receipt('owner',words=109,guards=21,inserted_or_omitted_words=0,byte_corruptions_rejected=436,binding_corruptions_rejected=6,frame_extent_controls=3,frame_proof=proof,raw_and_padded_neighbors=8,whole_pools_fixed_except_explicit_raw_FPR_mask=True,no_Makefile_or_shared_header_changes=True)
    def test_02_complete_guest_reference_and_raw_frame_semantics(self):
        count=0;seen=set()
        for c in g.cases():
            pair=self.compare(c);seen.update(pair[0].visits);count+=1
        self.assertFalse([i for i in range(109)if g.ENTRY+4*i not in seen]);self.receipt('guest',cases_per_body=count,bodies=3,all_109_words_visited=True,all_256_signed_indices=True,initial_integer_and_later_float_height_distinct=True,original_position_table_retained_across_constructor=True,index_and_position_reloaded_after_constructor=True,position_snapshot_precedes_selector_and_float_draw=True,selector_saved_as_byte=True,scale_float32_multiply_then_add=True,all_seven_effect_arguments=True,mark_precedes_effect_and_is_not_rewritten_afterward=True,raw_C_uses_256_byte_reference_frame_and_its_own_seeded_holes=True,no_portable_uninitialized_byte_claim=True)
    def test_03_complete_original_helpers_and_actual_palette(self):
        before=self.prepared['predecessor_elf'].read_bytes();descriptions=((g.INTEGER,0xDAED0,18),(g.FLOAT,0xDAF18,25),(g.COLOR,0x195B0C,105),(g.CREATE,0x195CB0,28),(g.SELECTOR,0x2062D0,19),(g.SUBMIT,0x20916C,113));seen={e:set()for e,p,n in descriptions};count=0
        for entry,offset,n in descriptions:
            at=match.elf_slot_offset(before,entry,4*n);self.assertEqual(before[at:at+4*n],self.rom[offset:offset+4*n])
        for state,query,selector,context,outcome,seed in itertools.product((0,1),(0,1),(0,129,255),(0,1),(0,1),(1,0xFFFFFFFFFFFFFFFF)):
            c=g.Case(connected=63,state=state,query=query,selector=selector,context=context,outcome=outcome,seed=seed);pair=self.compare(c)
            for e,p,n in descriptions:seen[e].update(v for v in pair[0].visits if e<=v<e+4*n)
            count+=1
        coverage={hex(e):len(v)for e,v in seen.items()};self.assertEqual(coverage[hex(g.SUBMIT)],113);self.assertEqual(coverage[hex(g.SELECTOR)],19);self.assertEqual(coverage[hex(g.FLOAT)],25);self.assertEqual(coverage[hex(g.INTEGER)],18);self.assertEqual(coverage[hex(g.CREATE)],28)
        self.receipt('providers',cases_per_body=count,retained_helper_words=308,coverage=coverage,actual_palette_sha256=match.sha(g.COLORS_DATA),NULL_and_successful_sprite_allocation=True,shared_64bit_seed_for_integer_float_and_three_effect_draws=True,complete_selector_and_both_effect_branches=True,defined_service_descriptor_fields_and_all14_low_level_arguments=True,three_unwritten_service_bytes_excluded_only_from_semantic_packet_observation=True,allocator_bcopy_query_and_low_level_emitters_are_bounded=True,no_additional_helper_C_credit=True)
    def test_04_fired_access_cuts_and_argument_homes(self):
        cuts=0;delays=0
        for c in(g.Case(mode=15,mutation=7,alias=7),g.Case(connected=63,state=0,query=0,context=0,outcome=0),g.Case(connected=63,state=0,query=1,context=1)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1;delays+=pair[0].delay_of is not None
        self.receipt('faults',fired_access_cuts=cuts,delay_slot_cuts=delays,all_owned_64bit_RNG_accesses_tracked=True,complete_emitted_state_private_bytes_and_trace_equal=True,incoming_height_context_and_position_home_mutations=True,raw_C_private_frame_not_claimed_fault_identical=True,guest_homes_not_portable_C_aliases=True)
    def test_05_original_table_callback_window_and_skip(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(allwords)if w==g.ENTRY],[0x22EF14]);self.assertNotIn(0x0C000000|(g.ENTRY>>2&0x3FFFFFF),allwords);self.assertNotIn(0x08000000|(g.ENTRY>>2&0x3FFFFFF),allwords);count=0;start,end=0x15148D30,0x15148DCC;window=struct.unpack_from('>19I',self.rom,0x1761E0)
        for phase,outcome,connected,enabled in itertools.product((0,8),(0,1),(0,63),(False,True)):
            c=g.Case(phase=phase,outcome=outcome,connected=connected,context=g.ACTOR+100);initial=g.fixture(c);home=g.STACK+phase;initial[g.OWNER+36]=int(enabled)
            for i,w in enumerate(g.arguments(c)[1:4]):g.put(initial,home+64+4*i,w)
            g.put(initial,g.ACTOR+96,c.height);g.put(initial,0x8008A454,g.ENTRY);e=g.reference(initial,c)if enabled else dict(memory=initial,calls=[],packets=[],vectors=[],services=[],marks=[]);pair=[]
            for w in(self.retail,self.words):
                code=g.helper_code(self.rom,c);code.update(zip(range(g.ENTRY,g.ENTRY+436,4),w));code[end]=0;code[0x15148DC8]=0x24020001;m=g.Oracle(window,initial,c,entry=start,connected=code,arguments_override=());m.r[16]=g.ACTOR;m.r[8]=g.OWNER;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((g.public(m.memory),m.calls,m.packets,m.vectors,m.services,m.marks,m.r[2]),(g.public(e['memory']),([(g.ENTRY,g.arguments(c))]if enabled else[])+e['calls'],e['packets'],e['vectors'],e['services'],e['marks'],1));pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',window_words=19,cases_per_body=count,table='D_8008A450[1]',literal_ROM='0x22EF14',six_argument_float_callback=True,zero_selector_skip_and_return_one_delay=True,complete_parent_not_claimed=True)
    def test_06_independent_GNU_links_all_six_calls(self):
        links=count=0;t=candidate.TARGETS[0]
        for k,entry in enumerate((g.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s.update({n:entry+0x10000*(j+1)for j,n in enumerate(s)if n.startswith('func_')})
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j));rows=['.set noreorder','.text','.globl '+t['function'],t['function']+':']
                if original:
                    for at,w in enumerate(self.retail):
                        if 4*at in t['bindings']:
                            typ,sym=t['bindings'][4*at][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    text,fs,rs=match.parse_object(self.prepared['qualified_owners'][0]);asm,unknown=emit_function(text,fs[t['function']],rs,t['function'],s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',t['function'],*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[436:],bytes(len(blob)-436));images.append(list(struct.unpack_from('>109I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[1],match.bound_blob(*match.derive(*match.function_blob(self.prepared['qualified_compacts'][0],0),0),s))
            for c in(g.Case(),g.Case(index=-128,mode=15,mutation=7,context=0),g.Case(index=127,mode=1,float_random=g.bits(.33),outcome=0)):self.compare(c,images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_six_JAL_bindings=True,original_and_padded_objects_agree=True)
    def test_07_SDK_native32_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr,encoding='utf-8');self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(r.stdout+r.stderr)[-4000:]);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,profiles=3,negative_controls=controls,all_controls_effective=True,SDK_native32_UBSan=True,six_argument_callback_and_seven_argument_service=True,whole_packet_and_owner_fences=True,root_holes_initialized_only_by_bounded_initializer=True,original_position_table_capture_and_live_index=True,mark_checked_at_selector_float_and_submission=True)
    def test_08_literal_image_and_former_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.rom),329);at=match.elf_slot_offset(before,g.ENTRY,436);loc=[0,at,at+435,at+436,len(after)-1,next(p+8 for p,n,f,s in match.symbol_rows(before)if n=='func_1518C69C')]
        for p in loc:
            b=bytearray(after);b[p]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(b),self.rom)
        c=g.Case();initial=g.fixture(c);stub=g.Oracle(struct.unpack_from('>109I',before,at),initial,c).run();self.assertNotEqual((g.public(stub.memory),stub.r[2]),(g.public(g.reference(initial,c)['memory']),1));self.receipt('image',strict_changed_bytes=329,exclusions=0,only_target_body_and_size_change=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,former_stub_rejected=True)
if __name__=='__main__':unittest.main()
