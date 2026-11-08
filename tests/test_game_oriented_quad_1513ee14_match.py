"""Direct orientation quad: ordered transforms, original caller and whole image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_oriented_quad_1513ee14_candidates as c
from tools.experiments import game_oriented_quad_1513ee14_match as m
from tools.tests import game_oriented_quad_1513ee14_oracle as g
from tools.tests.game_oriented_quad_1513ee14_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class OrientedQuadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>192I',cls.rom,0x16C2C4));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.words=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;e=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words):
            v=g.Oracle(body,initial,case);sr=v.r[:];sf=v.f[:];v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']),case);self.assertEqual(v.r[16:24],sr[16:24]);self.assertEqual((v.r[29],v.r[31]),(sr[29],sr[31]));self.assertEqual(v.f[20:],sf[20:]);machines.append(v)
            frame=g.STACK+case.phase-216
            for off in(0x3C,0x3D,0x3E):self.assertEqual(v.memory[frame+off],initial[frame+off])
        self.assertEqual(g.state(machines[0]),g.state(machines[1]));return machines
    def test_01_direct_owner_and_unchanged_guard_history(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,537,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(192,216,0,8,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(m.derive(self.raw,self.refs),(self.raw,self.refs));self.assertEqual(m.guard_rows(),[])
        before,after,installed=c.source_states((self.root/c.TARGETS[0]['source']).read_text());self.assertEqual(c.source_states(after),(before,after,True))
        for i in range(192):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        for at in self.refs:
            refs=dict(self.refs);refs[at]=[('R_MIPS_26','wrong_symbol')]
            with self.assertRaises(ValueError):m.derive(self.raw,refs)
        frozen=(self.out/'predecessor-guards.csv').read_bytes();self.assertEqual(m.guard_manifest(frozen),frozen)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed history')
        blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(self.out/'match-predecessor-0.o',p)
        self.assertEqual(m.METADATA_GROUPS,());self.receipts['owner']=q
    def test_02_independent_ordered_model_and_original_helpers(self):
        seen=set();count=0
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertTrue(set(range(g.ENTRY,g.ENTRY+768,4))<=seen)
        helpers=set()
        for entry,at,n in((g.COPY,0x22EC0,11),(g.MATRIX,0xD4E10,40),(g.BACKEND,0x203210,52)):
            helpers.update(range(entry,entry+n*4,4));before=self.q['predecessor_elf'].read_bytes();p=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[p:p+n*4],self.rom[at:at+n*4])
        self.assertEqual(helpers-seen,{g.BACKEND+13*4})
        case=g.Case(success=0);initial=g.fixture(case);initial={p:v for p,v in initial.items()if g.STACK-2048<=p<g.STACK+512};self.compare(case,initial)
        self.receipts['guest']=dict(cases_per_body=count+1,bodies=2,all_target_words_executed=192,helper_words_compared=103,helper_words_executed=102,unused_nonnull_fresh_fallback_words=1,orientation_before_corner_reads=True,all_four_transforms_before_first_output=True,three_cursor_advances_and_captured_first=True,stack_output_alias_in_model_observations=True,unused_three_alignment_bytes_fixed=True,full_private_machine_identity=True,orientation_and_allocation_bounded=True,FCSR_not_emulated=True)
    def test_03_original_renderer_dispatch_slot_and_pointer_ABI(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);direct=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:direct.append(i*4)
            if g.ENTRY<=word<g.ENTRY+768:pointers.append((i*4,word))
        self.assertEqual((direct,pointers),([] ,[(0x22E938,g.ENTRY)]));self.assertTrue(all(0x15000000<=v<0x15200000 for v in struct.unpack_from('>39I',self.rom,0x22E8DC)));self.assertEqual(struct.unpack_from('>I',self.rom,0x22E978)[0],0xE7000000)
        caller=list(struct.unpack_from('>295I',self.rom,0x16AFB0));seen=set();count=target_calls=0
        configs=[(*row,255,1)for row in itertools.product((0,8,0x1000000,0xC000,0x20000000,0x7FFFFFE0),(0,1),(0,1),(0,1),(0,255),(0,1,2))];configs.extend((8,1,1,1,255,0,0,b)for b in(0,1))
        for flags,enabled,view,success,animation,attached,visible,buffer in configs:
            case=g.Case(view=view,success=success,mutation=1,redirect=1);initial=g.caller_fixture(case,flags,enabled,visible,attached,animation)
            if not buffer:g.wr(initial,g.slot(case),0,4)
            reference=g.Oracle(caller,initial,case,entry=g.CALLER,arguments=(g.GFX,g.ACTOR,g.u32(case.view)),reference_leaf=True);reference.run();machines=[]
            for body in(self.truth,self.words):
                code=dict(zip(range(g.ENTRY,g.ENTRY+768,4),body));v=g.Oracle(caller,initial,case,entry=g.CALLER,arguments=(g.GFX,g.ACTOR,g.u32(case.view)),connected=code);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(g.public(reference.memory,case),reference.calls,reference.r[2]));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);target_calls+=sum(t==g.ENTRY for t,a in machines[0].calls);count+=1
        missing={i for i in range(295)if g.CALLER+i*4 not in seen};self.assertEqual(missing,{115,146});self.assertGreater(target_calls,0)
        for branch in(111,142):self.assertEqual((caller[branch]>>26,caller[branch+2]>>26,caller[branch]&65535,caller[branch+2]&65535),(1,4,4,2))
        before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CALLER,1180);self.assertNotEqual(before[at:at+1180],self.rom[0x16AFB0:0x16B44C])
        self.receipts['caller']=dict(cases_per_body=count,actual_leaf_calls_per_body=target_calls,original_renderer_words_compared=295,reachable_words_executed=293,unreachable_duplicate_defaults=sorted(missing),actual_renderer_prefix_entries=39,entry_slot=23,independent_leaf_provider_counterpart=True,pointer_s16_view_pointer_return_ABI=True,other_services_bounded=True,production_renderer_still_unrestored=True)
    def test_04_all_access_prefixes_and_saved_lifetimes(self):
        cuts=delays=0
        for case in(g.Case(success=0),g.Case(fresh=0),g.Case(private=1),g.Case(private=2,redirect=1),g.Case(private=4),g.Case(alias=3),g.Case(connected=7)):
            initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run()
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    v=g.Oracle(body,initial,case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,frame=216,full_memory_register_PC_delay_and_access_prefixes=True,RA_S0_actor_to_matrix_lifetimes=True,incoming_view_live_cursor_first_and_private_points=True,original_helper_prefixes=True)
    def test_05_native32_SDK_layout_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn NULL;\n}',lost_flags=s.replace('    scratch.cursor->v.flag = 0;',''),wrong_size=s.replace('view, 0x40,','view, 0x20,'),wrong_translation=s.replace('scratch.matrix[3][1] = *(f32 *)(actor + 0x38);','scratch.matrix[3][1] = 0.0f;'),wrong_corner=s.replace('scratch.corners[3][1] = -','scratch.corners[3][1] = '),wrong_z=s.replace('scratch.corners[0][1], 0.0f,','scratch.corners[0][1], 1.0f,'),wrong_axis=s.replace('scratch.cursor->v.ob[2] = (s32)scratch.points[0][2];','scratch.cursor->v.ob[2] = (s32)scratch.points[0][1];'),wrong_copy_offset=s.replace(' + 0x40, actor + 0xC0',' + 0x20, actor + 0xC0'),lost_advance=s.replace('    scratch.cursor++;',''),wrong_return=s.replace('return scratch.first;','return scratch.cursor;'))
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases()),SDK_Vtx16_pointer32_and_typed_services=True,relative_scratch_field_addresses_checked=True,all_transforms_before_emission=True,live_cursor_redirects_and_captured_return=True,UBSan_and_round_to_nearest_no_FTZ_DAZ=True,semantic_negatives=rejected,private_alias_homes_and_exceptional_casts_guest_only=True)
    def test_06_GNU_links_preserve_all_eight_calls(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        moved={n:v+0x1000000 for n,v in g.symbols().items()}
        for i,(entry,symbols)in enumerate(((g.ENTRY,g.symbols()),(0x17407F50,moved))):
            lines=['.set noreorder','.set noat','.text','.globl func_1513EE14','func_1513EE14:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.raw)):
                refs=self.refs.get(j*4,[])
                if refs:self.assertEqual(len(refs),1);kind,name=refs[0];self.assertEqual(kind,'R_MIPS_26');line='jal '+name
                else:line='.word 0x%08X'%word
                lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>192I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.raw,self.refs,symbols))
        self.receipts['relocations']=dict(independent_links=2,bindings=8,all_calls_literal=True,guards=0)
    def test_07_literal_whole_image_and_effective_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),537);slot=[p for p,n,f,s in m.symbol_rows(before)if n=='func_1513EE14'];self.assertEqual(len(slot),1)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,768),slot[0]+8,2790108,2853436,3071586,3123139):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=537,exclusions=0,body_bytes=535,target_size_bytes=2,metadata_reorderings=0,corruptions_rejected=7)

if __name__=='__main__':unittest.main()
