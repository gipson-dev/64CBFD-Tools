"""Scaled record vertices: live ABI, real helper/caller paths and closed image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_record_vertex_callback_1513e83c_candidates as c
from tools.experiments import game_record_vertex_callback_1513e83c_match as m
from tools.tests import game_record_vertex_callback_1513e83c_oracle as g
from tools.tests.game_record_vertex_callback_1513e83c_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class RecordVertexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=g.rom();cls.truth=list(struct.unpack_from('>167I',cls.rom,0x16BCEC));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.compact=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;e=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words,self.compact):
            v=g.Oracle(body,initial,case);saved_r=v.r[:];saved_f=v.f[:];v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']),case);self.assertEqual(v.r[16:24],saved_r[16:24]);self.assertEqual((v.r[29],v.r[31]),(saved_r[29],saved_r[31]));self.assertEqual(v.f[20:],saved_f[20:]);machines.append(v)
            frame=g.STACK+case.phase-216
            for off in(0x58,0x59,0x5A,0x94,0x95,0x96,0x97):self.assertEqual(v.memory[frame+off],initial[frame+off])
        self.assertEqual(g.state(machines[0]),g.state(machines[1]));return machines
    def test_01_whole_owner_and_eight_closed_normalization_words(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,502,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(167,216,8,5,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(self.nr,self.refs)
        self.assertEqual([i for i,(a,b)in enumerate(zip(self.compact,self.words))if a!=b],[40,43,44,45,78,79,117,119]);self.assertEqual(len(m.guard_rows()),8)
        for i in range(167):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        refs=dict(self.refs);refs[80]=[('R_MIPS_26','func_150A7960')]
        with self.assertRaises(ValueError):m.derive(self.raw,refs)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed guard history')
        blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(self.out/'match-predecessor-0.o',p)
        self.receipts['owner']=q
    def test_02_independent_quad_model_all_words_and_real_helpers(self):
        seen=set();count=0
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertTrue(set(range(g.ENTRY,g.ENTRY+668,4))<=seen)
        helper_ranges=set()
        for entry,at,n in((g.COPY,0x22EC0,11),(g.MATRIX,0xD4E10,40),(g.BACKEND,0x203210,52)):
            helper_ranges.update(range(entry,entry+n*4,4));before=self.q['predecessor_elf'].read_bytes();p=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[p:p+n*4],self.rom[at:at+n*4])
        missing=helper_ranges-seen;self.assertEqual(missing,{g.BACKEND+13*4})
        # The only unexecuted helper word supplies a fallback fresh pointer,
        # while this caller always passes its real nonzero byte address.
        self.assertEqual(struct.unpack_from('>I',self.rom,0x203210+13*4)[0],0xAFB90038)
        case=g.Case(success=0);initial=g.fixture(case);initial={p:v for p,v in initial.items()if g.STACK-2048<=p<g.STACK+512};self.compare(case,initial)
        self.receipts['guest']=dict(cases_per_body=count+1,bodies=3,target_words_executed=167,helper_words_compared=103,helper_words_executed=102,unreachable_nonnull_fresh_fallback_words=1,original_copy_11_matrix_40_backend_52=True,allocation_bounded=True,views_widths_scales_copies_live_cursor_and_first_home=True,unused_scratch_gaps_fixed=True,raw_public_equivalence_only=True,normalized_retail_private_machine_identity=True,FCSR_not_emulated=True)
    def test_03_complete_original_dispatcher_against_independent_leaf_provider(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);direct=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:direct.append(i*4)
            if g.ENTRY<=word<g.ENTRY+668:pointers.append((i*4,word))
        self.assertEqual((direct,pointers),([] ,[(0x22E8DC,g.ENTRY)]));self.assertTrue(all(0x15000000<=v<0x15200000 for v in struct.unpack_from('>39I',self.rom,0x22E8DC)));self.assertEqual(struct.unpack_from('>I',self.rom,0x22E978)[0],0xE7000000)
        caller=list(struct.unpack_from('>295I',self.rom,0x16AFB0));seen=set();count=0
        def check(case,initial):
            reference=g.Oracle(caller,initial,case,entry=g.CALLER,arguments=(g.GFX,g.ACTOR,g.u32(case.view)),reference_leaf=True);reference.run();machines=[]
            for body in(self.truth,self.words,self.compact):
                code=dict(zip(range(g.ENTRY,g.ENTRY+668,4),body));v=g.Oracle(caller,initial,case,entry=g.CALLER,arguments=(g.GFX,g.ACTOR,g.u32(case.view)),connected=code);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(g.public(reference.memory,case),reference.calls,reference.r[2]));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits)
        for flags,enabled,view,success,animation,attached in itertools.product((0,8,0x1000000,0xC000,0x20000000,0x7FFFFFE0),(0,1),(0,1),(0,1),(0,255),(0,1,2)):
            case=g.Case(view=view,success=success,scale=2,mutation=1,redirect=1);check(case,g.caller_fixture(case,flags,enabled,255,attached,animation));count+=1
        for has_buffer in(0,1):
            case=g.Case(view=1);initial=g.caller_fixture(case,8,1,0);g.wr(initial,g.slot(case),g.BUFFER if has_buffer else 0);check(case,initial);count+=1
        missing={i for i in range(295)if g.CALLER+i*4 not in seen};self.assertEqual(missing,{115,146})
        for i,branch in((115,111),(146,142)):
            self.assertEqual(caller[branch]>>26,1);self.assertEqual(caller[branch+2]>>26,4);self.assertEqual(caller[branch]&65535,4);self.assertEqual(caller[branch+2]&65535,2)
        before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CALLER,1180);self.assertNotEqual(before[at:at+1180],self.rom[0x16AFB0:0x16B44C])
        self.receipts['caller']=dict(cases_per_body=count,original_words_compared=295,reachable_words_executed=293,unreachable_duplicate_default_words=sorted(missing),actual_renderer_prefix_entries=39,entry_slot=0,following_graphics_words_excluded=True,pointer_one_s16_view_and_pointer_return_ABI=True,independent_leaf_provider_counterpart=True,other_render_services_bounded=True,production_dispatcher_still_unrestored=True)
    def test_04_fault_prefixes_saved_lifetimes_and_effective_role_controls(self):
        cuts=delays=0
        for case in(g.Case(success=0),g.Case(fresh=0),g.Case(private=2,redirect=1),g.Case(connected=7)):
            initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run()
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    v=g.Oracle(body,initial,case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        case=g.Case(fresh=0);initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run();cut=next(i for i,row in enumerate(full.trace)if row[:3]==('R',g.ACTOR+0x2C,4));different=[]
        for body in(self.truth,self.compact):
            v=g.Oracle(body,initial,case);v.cut=cut
            with self.assertRaises(AccessBoundary):v.run()
            different.append(v)
        self.assertNotEqual(g.state(different[0]),g.state(different[1]))
        bad=self.words[:];bad[119]=self.compact[119];v=g.Oracle(bad,g.fixture(),g.Case());v.run();self.assertNotEqual(g.public(v.memory,g.Case()),g.reference(g.fixture())['observed'])
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,normalized_full_memory_registers_PC_and_access_prefixes=True,F20_pair_and_S0_through_S4_lifetimes=True,effective_omitted_closed_role_guard_control=True,effective_raw_private_prefix_counterexample=True,raw_fault_identity_not_claimed=True)
    def test_05_native32_SDK_layout_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn NULL;\n}',lost_flags=s.replace('        scratch.cursor->v.flag = 0;',''),three_vertices=s.replace('i < 4','i < 3'),wrong_size=s.replace('view, 0x40,','view, 0x20,'),wrong_translation=s.replace('scratch.matrix[3][1] = *(f32 *)(actor + 0x38);','scratch.matrix[3][1] = 0.0f;'),wrong_scale=s.replace('scratch.matrix[1][1] *= *(f32 *)(actor + 0x50);','scratch.matrix[1][1] *= 1.0f;'),wrong_axis=s.replace('scratch.cursor->v.ob[2] = (s32)point[2];','scratch.cursor->v.ob[2] = (s32)point[1];'),wrong_z=s.replace('point[0], point[1], 0.0f,','point[0], point[1], 1.0f,'),wrong_copy_offset=s.replace(' + 0x40, actor + 0xC0',' + 0x20, actor + 0xC0'),wrong_return=s.replace('return scratch.first;','return scratch.cursor;'))
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases()),SDK_Vtx_pointer32_and_typed_services=True,scratch_relative_field_addresses_checked=True,u32_point_address_contract=True,live_escaped_cursor_and_copy_slot_mutations=True,UBSan_and_round_to_nearest_no_FTZ_DAZ=True,semantic_negatives=rejected,private_home_alias_and_exceptional_casts_guest_only=True)
    def test_06_GNU_relocation_links_preserve_all_five_calls(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        moved={n:v+0x1000000 for n,v in g.symbols().items()}
        for i,(entry,symbols)in enumerate(((g.ENTRY,g.symbols()),(0x17407F50,moved))):
            lines=['.set noreorder','.set noat','.text','.globl func_1513E83C','func_1513E83C:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.nr.get(j*4,[])
                if refs:self.assertEqual(len(refs),1);kind,name=refs[0];self.assertEqual(kind,'R_MIPS_26');line='jal '+name
                else:line='.word 0x%08X'%word
                lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>167I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.nr,symbols))
        self.receipts['relocations']=dict(independent_links=2,bindings=5,all_calls_literal=True,guards_overlap_no_bindings=True)
    def test_07_zero_exclusion_image_and_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),502)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,668),2979473,2979491,3227498,2857604):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=502,exclusions=0,metadata_reorderings=0,named_definitions_fixed_except_target_size=True,corruptions_rejected=6)

if __name__=='__main__':unittest.main()
