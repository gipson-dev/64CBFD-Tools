"""Direct descriptor C, real stack objects, original providers and strict image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_selected_point_effect_candidates as candidate
from tools.experiments import game_selected_point_effect_match as match
from tools.tests import game_selected_point_effect_oracle as g
from tools.tests import game_selected_point_effect_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class SelectedPointEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.words==cls.raw==cls.retail
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,initial=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;expected,calls,obs,emits=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m);self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.emits),(g.public(expected,c),calls,obs,emits),c)
        for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
        return pair
    def test_01_direct_owner_layout_bindings_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(72,72,104,0,12,12,14));raw,bindings=match.function_blob(self.prepared['qualified_compact']);self.assertEqual(match.derive(raw,bindings),match.function_blob(self.prepared['qualified_owner']))
        for i in range(288):
            b=bytearray(raw);b[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(b),bindings)
        for at in bindings:
            b=dict(bindings);b[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,b)
        self.assertEqual((ROOT/match.GUARDS).read_bytes(),(self.out/'proposed-guards.csv').read_bytes());self.assertFalse(any(r['function']==match.FUNCTION for r in match.csv.DictReader(match.io.StringIO((ROOT/match.GUARDS).read_text()))));self.receipt('owner',raw_words=72,guards=0,bindings=14,neighbors=12,frame=104,position_home='SP+0x5C',position_bytes=12,descriptor_home='SP+0x18',descriptor_bytes=68,real_objects_no_frame_padding=True,only_raw_T4_T5_masks_added=True,byte_corruptions_rejected=288,binding_corruptions_rejected=14)
    def test_02_context_width_raw_float_bits_live_constants_and_ignored_result(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertEqual([i for i in range(72)if match.ENTRY+4*i not in seen],[]);self.receipt('guest',cases_per_body=count,bodies=2,raw_C_identical_to_both=True,all_256_low_context_bytes=True,fullword_context_and_unused_argument=True,helper_zero_result_still_submits=True,raw_float_sign_zero_subnormal_infinity_quiet_and_signaling_NaN_bits=True,all_root_words_visited=True,three_padding_bytes_preserved_in_guest=True)
    def test_03_guest_aliases_all_access_cuts_and_disabled_inputs(self):
        count=cuts=0;raw,bindings=match.function_blob(self.prepared['qualified_compact'])
        for alias,active,context,mutation,phase in itertools.product(range(4),(0,0x250000),(1,2,255),(0,1,2,4,7),(0,8)):
            c=g.Case(alias=alias,active=active,context=context,mutation=mutation,phase=phase);s=g.symbols()
            if alias in(2,3):s['D_800A5708']=g.position(g.STACK+phase)if alias==2 else g.STACK+phase+8
            w=match.bound_blob(raw,bindings,s);self.compare(c,images=(w,w),s=s);count+=1
        for c in(g.Case(),g.Case(active=0),g.Case(fill=False,context=255),g.Case(mutation=7),g.Case(connected=1)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        c=g.Case(active=0);initial=g.fixture(c)
        for a in g.CONSTANTS:
            for i in range(4):initial.pop(a+i,None)
        for a in range(g.descriptor(g.STACK),g.STACK):initial.pop(a,None)
        self.compare(c,initial=initial);self.receipt('faults',alias_cases_per_body=count,fired_access_cuts=cuts,owner_gate_position_global_and_incoming_home_aliases=True,literal_full_state_and_fault_PC_equal=True,disabled_path_needs_no_constants_or_locals=True,private_bytes_and_faults_not_portable_C_claims=True)
    def test_04_original_point_helper_and_complete_descriptor_consumer(self):
        count=consumers=0;read_bytes=set()
        for context,active,phase in itertools.product((*range(256),0x101,0x102,0xABCD00FF),(0,0x250000),(0,8)):
            self.compare(g.Case(context=context,active=active,phase=phase,connected=1));count+=1
        for context,random,mutation,active in itertools.product((1,2,255),range(6),(0,1,2,4,7),(0,0x250000)):
            c=g.Case(context=context,random=random,emit_mutation=mutation,active=active,connected=3)
            for m in self.compare(c):
                p=g.descriptor(g.STACK)
                for op,a,n,v in m.trace:
                    if op=='R'and p<=a<p+68:read_bytes.update(range(a-p,a-p+n))
            consumers+=1
        self.assertTrue(read_bytes);self.assertFalse(set(g.HOLES)&read_bytes);self.assertTrue(set(range(0x14,0x3D))<=read_bytes)
        self.receipt('providers',point_cases_per_body=count,consumer_cases_per_body=consumers,original_point_words=56,original_consumer_words=155,invalid_point_modes_preserve_seeded_guest_position=True,real_NULL_result_avoids_height_branch=True,consumer_emits_5_to_27_packets=True,consumer_descriptor_read_bytes=sorted(read_bytes),no_padding_reads=True,live_position_spread_mode_and_lifetime_after_emit=True,cached_initial_double_spread_and_count=True,RNG_direction_and_final_emit_are_bounded_models=True,no_additional_provider_C_credit=True)
    def test_05_original_registry_and_two_dispatch_windows(self):
        r=self.rom;words=struct.unpack('>%dI'%(len(r)//4),r);self.assertEqual([4*i for i,w in enumerate(words)if w==match.ENTRY],[0x22EB84]);self.assertNotIn(0x0C000000|(match.ENTRY>>2&0x3FFFFFF),words);self.assertNotIn(0x08000000|(match.ENTRY>>2&0x3FFFFFF),words);self.assertEqual(struct.unpack_from('>2I',r,0x22EB84),(match.ENTRY,85));count=[0,0]
        for which,context,amount,active,phase in itertools.product(range(2),(1,2,0x101,0xABCD00FF),(-32768,0,85,32767),(0,0x250000),(0,8)):
            c=g.Case(context=context,unused=g.u32(0 if which==0 else amount),active=active,phase=phase);initial=g.fixture(c);g.put(initial,g.TABLE+2*8,match.ENTRY);g.put(initial,g.TABLE+2*8+4,85);record=0x270000
            for i in range(64):initial[record+i]=165
            g.put(initial,record+14,amount,2);start,rom,n,end=(0x15141B4C,0x16EFFC,5,0x15141B60)if which==0 else(0x15141BAC,0x16F05C,8,0x15141BCC);pair=[];expected,calls,obs,emits=g.reference(initial,c)
            for w in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+288,4),w));code[end]=0;m=g.Oracle(struct.unpack_from('>%dI'%n,r,rom),initial,c,entry=start,connected=code);m.r[18]=g.ACTOR;m.r[19]=g.u32(context);m.r[16]=g.TABLE;m.r[14]=g.TABLE+2*8;m.r[12]=2;m.r[2]=record;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.root_args,[g.args(c)]);self.assertEqual((g.public(m.memory,c),m.calls,m.observations,m.emits),(g.public(expected,c),[(match.ENTRY,g.args(c))]+calls,obs,emits));pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count[which]+=1
        start,rom,n,end=0x15141B28,0x16EFD8,14,0x15141B60;initial=g.fixture();g.put(initial,g.TABLE+2*8+4,85);m=g.Oracle(struct.unpack_from('>14I',r,rom),initial,entry=start);m.r[3]=g.TABLE+2*8;m.r[7]=2;m.r[18]=g.ACTOR;m.r[16]=g.TABLE;m.r[2]=2;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,);m.record_call=lambda t:m.calls.append((t,tuple(m.arguments(2))));m.hook=lambda t:self.assertEqual(t,0x15141E38)
        with self.assertRaises(WindowBoundary):m.run()
        self.assertEqual(m.calls,[(0x15141E38,(g.ACTOR,2))]);self.receipt('callers',cases_per_body=count,window_words=[5,8],table='D_8008A0B4',index=2,retail_count=85,fullword_context_and_signed16_third_argument=True,first_window_is_direct_boundary_only=True,actual_positive_count_uses_registration=True,full_parent_not_claimed=True)
    def test_06_independent_GNU_links_all_fourteen_bindings(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:entry+0x10000*(i+1)if n.startswith('func_')else 0x81007FFC+4*(i-2)+0x10000*(k-1)for i,n in enumerate(s)}
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
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_compact']),s))
            for active,context,mutation in itertools.product((0,0x250000),(1,2,0xABCD00FF),(0,3)):self.compare(g.Case(active=active,context=context,mutation=mutation),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_fourteen_bindings=True,six_constant_HI_LO_pairs_and_two_JALs=True,signed_low16_carries=True)
    def test_07_SDK_native32_real_objects_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-3500:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=511,SDK_native32_UBSan=True,descriptor_size_offsets_pointer_and_vector_ABI=True,distinct_escaped_position_and_descriptor_copy=True,promoted_helper_argument_and_typed_callback_ABI=True,padding_and_unfilled_position_not_read_by_native_fixture=True,all_float_patterns_moved_as_bits=True)
    def test_08_full_image_metadata_cycles_and_stub_rejection(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),376);at=match.elf_slot_offset(before,match.ENTRY,288)
        locations=[0,at,at+287,at+288,len(after)-1]+[next(p+4 for p,n,f,loc in match.symbol_rows(before)if n==names[0])for names,order in match.METADATA_GROUPS]
        for off in locations:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        c=g.Case();initial=g.fixture(c);m=g.Oracle(struct.unpack_from('>72I',before,at),initial,c).run();self.assertFalse(m.calls);self.assertNotEqual(m.observations,g.reference(initial,c)[2]);screens=json.loads((self.out/'candidate-screens-initial.json').read_text());self.assertEqual((screens[0]['words'],screens[0]['frame'],screens[0]['differences']),(72,104,6));self.receipt('image',strict_changed_bytes=376,exclusions=0,metadata_cycles=6,all_named_definitions_preserved=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=len(locations),stub_and_initial_six_difference_shape_rejected=True,guards_unchanged=True)
if __name__=='__main__':unittest.main()
