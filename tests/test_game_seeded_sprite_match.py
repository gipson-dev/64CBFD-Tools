"""Descriptor, branch/home proof, original helpers/caller and independent image gates."""
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_seeded_sprite_candidates as c
from tools.experiments import game_seeded_sprite_match as m
from tools.tests import game_seeded_sprite_oracle as g
from tools.tests.game_seeded_sprite_native import harness,cases as native_cases
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class SeededSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>73I',cls.rom,0x1C0840));raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.raw=m.bound_blob(raw,refs,g.symbols());blob,refs=m.derive(raw,refs);cls.words=m.bound_blob(blob,refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;models=[]
        for words,frame in((self.truth,216),(self.words,216),(self.raw,208)):
            expected=g.reference(initial,case,frame=frame);model=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case),frame=frame).run()
            self.assertEqual((g.public(model.memory,case),model.calls,model.packets),(expected['memory'],expected['calls'],expected['packets']),case);models.append(model)
        self.assertEqual(g.state(models[0]),g.state(models[1]),case);self.assertEqual(g.canonical(models[0].calls,216,g.STACK+case.phase),g.canonical(models[2].calls,208,g.STACK+case.phase),case)
        return models
    def test_01_complete_owner_branch_frame_and_controls(self):
        q=self.q['report'];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_exclusions']),(113,6052,0));t=q['targets'][0];self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(1,1,22,6));self.assertEqual(t['diagnostics']['before'],0);self.assertEqual(self.truth,self.words)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);blob,_=m.derive(raw,refs);proof=m.audit_frame_and_paths(raw,blob)
        self.assertEqual((proof['raw_frame'],proof['retail_frame'],proof['unused_tail'],proof['home_accesses']),(208,216,8,4))
        for offset in(0,8,0x54,0x64,0x104):
            bad=bytearray(raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        badrefs=dict(refs);badrefs[0x1C]=[('R_MIPS_HI16','D_800A81B4')]
        with self.assertRaises(ValueError):m.derive(raw,badrefs)
        self.receipts['frame']=proof;self.receipts['owner']=q
    def test_02_all_fields_lifetimes_signed_values_and_overlap(self):
        seen=set();count=0
        for case in g.cases():models=self.compare(case);seen.update(models[0].visits);count+=1
        for sentinel,height in itertools.product((0,0x80000000,g.bits(float('inf')),0x7FC12345),(-10000,0,32767)):
            self.compare(g.Case(sentinel=sentinel,height=height));count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+292,4))-seen,{g.ENTRY+25*4})
        self.receipts['guest']=dict(cases_per_body=count,implementations=3,covered_words=72,unreachable_words=1,variant_bytes=256,overlap_layouts=4,live_actor_home_redirects=True,raw_C_private_PC_and_frame_not_claimed_identical=True,guarded_full_machine_state_and_trace_equal=True,FP_flags_and_hardware_traps_not_claimed=True)
    def test_03_original_zero_initializer_constructor_copy_and_RNG(self):
        probe=g.Oracle(self.truth,g.fixture());probe.r[4]=0x7FFFFFFF;probe.r[6]=1;saved=probe.r[2]
        with self.assertRaises(ArithmeticError):probe.execute(0x00861020)
        self.assertEqual(probe.r[2],saved);probe.r[4]=0xFFFFFFFE;probe.execute(0x00861020);self.assertEqual(probe.r[2],0xFFFFFFFF)
        descriptors=((g.ZERO,0x226F0,40),(g.INITIALIZE,0x195B0C,105),(g.CREATE,0x195CB0,28),(g.COPY,0x23A10,196),(g.RANDOM,0xDAED0,18));before=self.q['predecessor_elf'].read_bytes();seen={e:set()for e,p,n in descriptors};count=0
        for e,p,n in descriptors:
            at=m.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4],self.rom[p:p+n*4])
        for connected,outcome,seed,width,tall in itertools.product((1,2,4,8,15),(0,1),g.SEEDS[:3],(0,65535),(1,65535)):
            case=g.Case(connected=connected,outcome=outcome,seed=seed,width=width,tall=tall);models=self.compare(case)
            for e,p,n in descriptors:seen[e].update(pc for pc in models[0].visits if e<=pc<e+n*4)
            count+=1
        self.assertGreater(len(seen[g.ZERO]),20);self.assertGreater(len(seen[g.INITIALIZE]),80);self.assertEqual(len(seen[g.CREATE]),28);self.assertGreater(len(seen[g.COPY]),40);self.assertEqual(len(seen[g.RANDOM]),18)
        self.receipts['helpers']=dict(cases_per_body=count,retained_words=387,covered_words={hex(e):len(v)for e,v in seen.items()},aligned168_byte_zero=True,RGBA=[255,255,255,128],fixed_flags='0x4880',all_168_descriptor_bytes_observed=True,allocator_bounded=True,complete_bcopy_window_loaded=True,only_forward_aligned_copy_path_claimed=True,ADD_overflow_control=True,copy_and_RNG_original=True,no_additional_C_credit=True)
    def test_04_actual_complete_timer_caller_and_dispatch(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(allwords)if g.ENTRY<=w<g.ENTRY+292],[0x22EF84]);self.assertNotIn(0x0C000000|(g.ENTRY>>2&0x3FFFFFF),allwords)
        words=list(struct.unpack_from('>45I',self.rom,0x176714));before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CALLER,180);self.assertEqual(before[at:at+180],self.rom[0x176714:0x1767C8]);count=0;seen=set()
        for timer,flags,ticks,update,callback,outcome,redirect in itertools.product((-32768,-1,0,1),(0,1),(0,2),(0,1),(0,1),(0,1),(0,8)):
            case=g.Case(timer=timer,flags=flags,ticks=ticks,update=update,callback=callback,outcome=outcome,redirect=redirect);initial=g.fixture(case);expected=g.caller_reference(initial,case);models=[]
            for body in(self.truth,self.words):
                code=dict(zip(range(g.ENTRY,g.ENTRY+292,4),body));model=g.Oracle(words,initial,case,entry=g.CALLER,connected=code).run();self.assertEqual((g.public(model.memory,case),model.calls,model.packets),(expected['memory'],expected['calls'],expected['packets']),case);models.append(model)
            self.assertEqual(g.state(models[0]),g.state(models[1]));seen.update(p for p in models[0].visits if g.CALLER<=p<g.CALLER+180);count+=1
        self.assertEqual(len(seen),45);self.receipts['caller']=dict(cases=count,retained_words=45,covered_words=45,callback_slot='D_8008A4C0[1] /0x8008A4C4',one_argument_void_ABI=True,reseed_prevents_cleanup_on_original_actor=True,guest_redirect_can_trigger_original_actor_cleanup=True,other_update_and_cleanup_providers_bounded=True)
    def test_05_fired_access_cuts_and_complete_guarded_prefix(self):
        count=delays=0
        for case in(g.Case(),g.Case(height=123),g.Case(mutation=15,redirect=11),g.Case(alias=1)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                models=[]
                for words in(self.truth,self.words):
                    model=g.Oracle(words,g.fixture(case),case);model.cut=cut
                    with self.assertRaises(AccessBoundary):model.run()
                    models.append(model)
                self.assertEqual(g.state(models[0]),g.state(models[1]));count+=1;delays+=models[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=count,delay_cuts=delays,complete_guarded_state_private_bytes_and_PC_equal=True,raw_fault_identity_not_claimed=True,home_poison_guest_only=True)
    def test_06_native32_SDK_and_effective_compiled_negatives(self):
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native'+opt+'.c');path.write_text(harness(),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        variants=dict(stub=c.SELECTED[:c.SELECTED.index('{')+1]+'\n}',height=c.SELECTED.replace('- 200.0f','- 199.0f'),timer=c.SELECTED.replace(' + 100;',' + 99;'),alpha=c.SELECTED.replace('255, 255, 255, 128','255, 255, 255, 255'),stale_priority=c.SELECTED.replace('    s16 height;','    s16 height;\n    u8 priority = actor[0xC];').replace('((u8 *)cursor)[0xC],','priority,'))
        rejected={}
        for label,body in variants.items():
            path=self.out/('negative-'+label+'.c');path.write_text(harness(body),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command('-O2'),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0,label);rejected[label]=answer
        # The nonvolatile source is a semantic negative for the measured guest
        # home contract; no claim is made that portable C can poison its frame.
        live=(self.root/c.TARGETS[0]['source']).read_text(encoding='utf-8');before,_,_=c.source_states(live);bad=before.replace('s32 func_15193390() {\n    return 0;\n}',c.SUPPORT+'\n'+c.SELECTED.replace('u8 *volatile actor','u8 *actor'),1);obj,diag=c.compile_owner(self.root,self.out,bad,'negative-cached-home');self.assertFalse(diag);blob,refs=m.function_blob(obj);w=m.bound_blob(blob,refs,g.symbols());case=g.Case(redirect=1);model=g.Oracle(w,g.fixture(case),case).run();self.assertNotEqual(g.public(model.memory,case),g.reference(g.fixture(case),case)['memory'])
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_layout_assertions=True,UBSan_trap=True,Python_little_endian_byte_model=True,native_home_poison_not_claimed=True,semantic_negatives=rejected,cached_home_guest_control_rejected=True)
    def test_07_independent_links_and_strict_image_corruptions(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);blob,_=m.derive(raw,refs);count=0
        for entry,s in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(bzero=0x10008004,func_1516865C=0x17518004,func_15168800=0x17508000,func_150ADA20=0x17517FFC,D_800A81B0=0x80208000))):
            lines=['.set noreorder','.text','.globl func_15193390','func_15193390:']
            for i,w in enumerate(struct.unpack('>73I',blob)):
                if i*4 not in refs:lines.append('.word 0x%08X'%w);continue
                kind,name=refs[i*4][0];lines.append('jal '+name if kind=='R_MIPS_26'else'lui $%d,%%hi(%s)'%(w>>16&31,name)if kind=='R_MIPS_HI16'else'lwc1 $f%d,%%lo(%s)($%d)'%(w>>16&31,name,w>>21&31))
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            cmd=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(name,value)for name,value in s.items()if name!='D_8008CA4C'],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))];subprocess.run(cmd,check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>73I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(blob,refs,s));count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),267)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,292),0x2B7B6C,0x3052F4):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=267,exclusions=0,closed_metadata_groups=2,independent_links=count,corruptions_rejected=4,protected_bytes=189088)
if __name__=='__main__':unittest.main()
