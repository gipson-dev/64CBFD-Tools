"""Billboard semantics, explicit pointer-return ABI and literal whole image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_billboard_quad_1513ead8_candidates as c
from tools.experiments import game_billboard_quad_1513ead8_match as m
from tools.tests import game_billboard_quad_1513ead8_oracle as g
from tools.tests.game_billboard_quad_1513ead8_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class BillboardQuadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>183I',cls.rom,0x16BF88));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.compact=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;e=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words,self.compact):
            v=g.Oracle(body,initial,case);sr=v.r[:];sf=v.f[:];v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']),case);self.assertEqual(v.r[16:24],sr[16:24]);self.assertEqual((v.r[29],v.r[31]),(sr[29],sr[31]));self.assertEqual(v.f[20:],sf[20:]);machines.append(v)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]));return machines

    def test_01_owner_header_and_three_commutative_words(self):
        q=self.q['report'];t=q['targets'][0]
        self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(571,6052,537,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(183,104,3,7,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(self.nr,self.refs)
        self.assertEqual([i for i,(a,b)in enumerate(zip(self.compact,self.words))if a!=b],[51,54,57]);self.assertEqual(len(m.guard_rows()),3)
        for i in(51,54,57):
            a,b=self.compact[i],self.words[i];self.assertEqual(a&~(31<<16|31<<11),b&~(31<<16|31<<11));self.assertEqual((a>>16&31,a>>11&31),(b>>11&31,b>>16&31))
        before,after,installed=c.source_states((self.root/c.TARGETS[0]['source']).read_text());self.assertEqual(c.source_states(after),(before,after,True))
        bh,ah,hi=c.header_states((self.root/c.HEADER).read_text());self.assertEqual(hi,installed);self.assertEqual(c.header_states(ah),(bh,ah,True));self.assertEqual(sum(a!=b for a,b in zip(bh.splitlines(),ah.splitlines())),2)
        for i in range(183):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        for at in self.refs:
            refs=dict(self.refs);refs[at]=[('R_MIPS_26','wrong_symbol')]
            with self.assertRaises(ValueError):m.derive(self.raw,refs)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed history')
        blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(self.out/'match-predecessor-0.o',p)
        self.assertEqual((len(c.HEADER_OBJECTS),len(c.HEADER_SOURCES),len(set(c.HEADER_OBJECTS))),(200,199,200))
        self.receipts['owner']=q

    def test_02_ordered_float_model_all_words_and_real_helpers(self):
        seen=set();count=0
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertTrue(set(range(g.ENTRY,g.ENTRY+732,4))<=seen)
        helpers=set()
        for entry,at,n in((g.COPY,0x22EC0,11),(g.BACKEND,0x203210,52)):
            helpers.update(range(entry,entry+n*4,4));before=self.q['predecessor_elf'].read_bytes();p=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[p:p+n*4],self.rom[at:at+n*4])
        missing=helpers-seen;self.assertEqual(missing,{g.BACKEND+13*4})
        case=g.Case(success=0);initial=g.fixture(case);minimal={p:v for p,v in initial.items()if g.STACK-2048<=p<g.STACK+512};self.compare(case,minimal)
        self.receipts['guest']=dict(cases_per_body=count+1,bodies=3,target_words_executed=183,helper_words_compared=63,helper_words_executed=62,unreachable_nonnull_fresh_fallback_words=1,original_copy_and_backend=True,allocation_bounded=True,rotated_is_cycle_not_reversed_winding=True,live_copy_slot_center_and_cursor_reads=True,first_return_home_mutation=True,canonical_NaN_model_only=True,FCSR_not_emulated=True,normalized_retail_private_machine_identity=True)

    def test_03_original_wrappers_and_complete_renderer_pointer_ABI(self):
        direct=[];pointers=[];jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF)
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:direct.append(i*4)
            if g.ENTRY<=word<g.ENTRY+732:pointers.append((i*4,word))
        self.assertEqual((direct,pointers),([0x16C27C,0x16C2AC],[]));self.assertEqual(struct.unpack_from('>2I',self.rom,0x22E964),(g.WRAP0,g.WRAP1));self.assertEqual(struct.unpack_from('>I',self.rom,0x22E978)[0],0xE7000000)
        wrapper=g.wrapper_code(self.rom);before=self.q['predecessor_elf'].read_bytes()
        for entry,at in((g.WRAP0,0x16C264),(g.WRAP1,0x16C294)):
            p=m.elf_slot_offset(before,entry,48);self.assertEqual(before[p:p+48],self.rom[at:at+48])
        caller=list(struct.unpack_from('>295I',self.rom,0x16AFB0));seen=set();count=0;target_calls=0
        configs=[(*row,255,1)for row in itertools.product((0,8,0x1000000,0xC000,0x20000000,0x7FFFFFE0),(0,1),(0,1),(0,1),(0,1),(0,1,2))]
        configs.extend((8,1,1,1,rotated,0,0,has_buffer)for rotated,has_buffer in itertools.product((0,1),(0,1)))
        for flags,enabled,view,success,rotated,attached,visible,has_buffer in configs:
            case=g.Case(view=view,success=success,rotated=rotated,mutation=1,redirect=1);initial=g.caller_fixture(case,flags,enabled,visible,attached,count%2*255)
            if not has_buffer:g.wr(initial,g.slot(case),0,4)
            reference=g.Oracle(caller,initial,case,entry=g.CALLER,args=(g.GFX,g.ACTOR,g.u32(case.view)),connected=wrapper,reference_leaf=True);reference.run();machines=[]
            for body in(self.truth,self.words,self.compact):
                code=dict(wrapper);code.update(zip(range(g.ENTRY,g.ENTRY+732,4),body));v=g.Oracle(caller,initial,case,entry=g.CALLER,args=(g.GFX,g.ACTOR,g.u32(case.view)),connected=code);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(g.public(reference.memory,case),reference.calls,reference.r[2]),case);machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);target_calls+=sum(t==g.ENTRY for t,a in machines[0].calls);count+=1
        missing={i for i in range(295)if g.CALLER+i*4 not in seen};self.assertEqual(missing,{115,146})
        self.assertTrue(set(wrapper)<=seen);self.assertGreater(target_calls,0)
        for branch in(111,142):self.assertEqual((caller[branch]>>26,caller[branch+2]>>26,caller[branch]&65535,caller[branch+2]&65535),(1,4,4,2))
        at=m.elf_slot_offset(before,g.CALLER,1180);self.assertNotEqual(before[at:at+1180],self.rom[0x16AFB0:0x16B44C])
        self.receipts['caller']=dict(cases_per_body=count,bodies=3,actual_leaf_calls_per_body=target_calls,original_renderer_words_compared=295,reachable_words_executed=293,unreachable_duplicate_defaults=sorted(missing),original_wrappers_words=24,wrappers_production_already_exact=True,slots=[34,35],renderer_table_prefix_entries=39,independent_leaf_provider_counterpart=True,explicit_pointer_return_and_s16_view=True,production_renderer_still_unrestored=True,other_renderer_services_bounded=True)

    def test_04_access_prefixes_frame_and_saved_register_lifetimes(self):
        cuts=delays=0
        for case in(g.Case(success=0),g.Case(fresh=0),g.Case(private=2,redirect=1),g.Case(private=4),g.Case(alias=3),g.Case(alias=4),g.Case(connected=5)):
            initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run()
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    v=g.Oracle(body,initial,case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,frame=104,full_memory_register_PC_delay_and_access_prefixes=True,saved_RA_S0_lifetimes=True,escaped_cursor_captured_first_and_incoming_homes=True,original_helpers_connected=True,guest_only_stack_aliases=True)

    def test_05_native32_typed_leaf_wrappers_and_effective_controls(self):
        def run(label,body,opt,wrappers=None):
            path=self.out/(label+'.c');path.write_text(harness(body,wrappers));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn NULL;\n}',lost_flags=s.replace('    cursor[0].v.flag = 0;',''),wrong_rotation=s.replace('if (rotated)','if (!rotated)'),wrong_side=s.replace('side = D_800DD1E8[view]','side = D_800DD1D8[view]'),wrong_lower=s.replace('lower = *(f32 *)(actor + 0x50)','lower = 1.0f'),wrong_upper=s.replace(' - lower;',' + lower;'),wrong_copy=s.replace(' + 0x40, actor + 0xC0',' + 0x20, actor + 0xC0'),wrong_size=s.replace('view, 0x40,','view, 0x20,'),wrong_return=s.replace('return first;','return cursor;'))
        variants['wrong_side']=variants['wrong_side'].replace('    extern f32 D_800DD1E8[];\n','')
        variants['wrong_return']=variants['wrong_return'].replace('return cursor;','(void)first; return cursor;')
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        from tools.tests.game_billboard_quad_1513ead8_native import WRAPPERS
        bad=WRAPPERS.replace('return func_1513EAD8(actor, 1, view);','func_1513EAD8(actor, 1, view); return NULL;');self.assertEqual(run('negative-wrapper',None,'-O2',bad),1);rejected['wrapper_drops_pointer']=1
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases())*3,SDK_Vtx16_pointer32=True,typed_callbacks_slots_34_35_and_direct_u8_leaf=True,escaped_cursor_and_copy_slot_mutations=True,finite_s32_casts_only=True,UBSan_and_round_to_nearest_no_FTZ_DAZ=True,semantic_negatives=rejected,guest_only_aliases_homes_and_exceptional_casts=True)

    def test_06_GNU_rebases_all_calls_and_HI_LO_pairs(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        configs=((g.ENTRY,g.symbols()),(0x17407F50,dict(func_151D5D60=0x17508010,memcpy=0x10431000,D_800DD1D8=0x81238002,D_800DD1E8=0x82347FF8)))
        for i,(entry,symbols)in enumerate(configs):
            lines=['.set noreorder','.set noat','.text','.globl func_1513EAD8','func_1513EAD8:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.nr.get(j*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    else:self.assertEqual(word>>26,49);line='lwc1 $f%d, %%lo(%s)($%d)'%(rt,name,rs)
                lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>183I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.nr,symbols))
        self.receipts['relocations']=dict(independent_links=2,bindings=7,calls=3,direction_HI_LO_pairs=2,signed_LO_carry=True,guards_overlap_no_bindings=True)

    def test_07_literal_image_zero_exclusions_and_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),537)
        slot=[p for p,n,f,s in m.symbol_rows(before)if n=='func_1513EAD8'];self.assertEqual(len(slot),1)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,732),slot[0]+8,2790108,2853436,3071586,3123139):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=537,exclusions=0,body_bytes=535,target_size_bytes=2,metadata_reorderings=0,all_other_named_definitions_fixed=True,corruptions_rejected=7)

if __name__=='__main__':unittest.main()
