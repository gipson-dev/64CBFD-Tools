"""Whole-image, frame, guest/native, original helpers and callback qualification."""
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_below_height_effect_candidates as c
from tools.experiments import game_below_height_effect_match as m
from tools.tests import game_below_height_effect_oracle as g
from tools.tests.game_below_height_effect_native import harness,cases as native_cases
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
class BelowHeightEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>69I',cls.rom,0x1B736C));raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.raw=m.bound_blob(raw,refs,g.symbols());blob,refs=m.derive(raw,refs);cls.words=m.bound_blob(blob,refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case,initial=None):
        initial=g.fixture(self.rom,case)if initial is None else initial;models=[]
        for body,frame in((self.truth,80),(self.words,80),(self.raw,72)):
            expected=g.reference(initial,case,frame=frame);model=g.Oracle(body,initial,case,connected=g.helper_code(self.rom,case),frame=frame).run()
            self.assertEqual((g.public(model.memory,case),model.calls,model.vectors,model.services,model.r[2]),(expected['memory'],expected['calls'],expected['vectors'],expected['services'],1),case);models.append(model)
        self.assertEqual(g.state(models[0]),g.state(models[1]),case)
        self.assertEqual(g.canonical(models[0].calls,80,case.phase),g.canonical(models[2].calls,72,case.phase),case)
        return models
    def test_01_owner_frame_and_fail_closed_controls(self):
        q=self.q['report'];self.assertEqual((q['frozen_inputs'],q['strict_exclusions'],q['functions']),(108,0,6052));t=q['targets'][0];self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(3,3,4,7));self.assertEqual(t['diagnostics']['before'],0);self.assertEqual(self.truth,self.words)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);blob,_=m.derive(raw,refs);proof=m.audit_frame(raw,blob)
        self.assertEqual((proof['raw_frame'],proof['retail_frame'],proof['private_accesses'],proof['retail_unused_tail']),(72,80,14,12))
        for at in(0,76,92,272):
            bad=bytearray(raw);bad[at+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        bad=bytearray(blob);bad[0xBF]^=4
        with self.assertRaises(ValueError):m.audit_frame(raw,bytes(bad))
        badrefs=dict(refs);badrefs[80]=[('R_MIPS_HI16','D_800A73B0')]
        with self.assertRaises(ValueError):m.derive(raw,badrefs)
        self.receipts['frame']=proof;self.receipts['owner']=q
    def test_02_guest_retained_pointers_and_ordered_FP_gates(self):
        count=0;seen=set()
        for case in g.cases():
            models=self.compare(case);seen.update(models[0].visits);count+=1
        self.assertEqual(seen,set(range(g.ENTRY,g.ENTRY+276,4)))
        for random,threshold in itertools.product((g.bits(.8),g.bits(.79999995),0x7FCABCDE),(g.dbits(.80000003),g.dbits(.79999999),g.dbits(float('nan')))):
            self.compare(g.Case(random=random,threshold=threshold));count+=1
        self.receipts['guest']=dict(cases_per_body=count,implementations=3,covered_words=69,signed_indices=256,alias_layouts=4,double_threshold=True,retained_position_and_payload=True,live_post_selector_fields=True,raw_C_private_frame_not_claimed_identical=True,FP_flags_and_hardware_traps_not_claimed=True)
    def test_03_access_cuts_minimal_mapping_and_frame_boundaries(self):
        case=g.Case(y=g.bits(20.));initial=g.fixture(self.rom,case)
        for address in(g.SEED,g.UNIT,g.STATE,g.GLOBAL_SELECTOR):
            for i in range(8):initial.pop(address+i,None)
        self.compare(case,initial)
        cuts=delays=0
        for case in(g.Case(),g.Case(random=g.bits(1.)),g.Case(mutation=7),g.Case(alias=2,mutation=3)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                models=[]
                for body in(self.truth,self.words):
                    model=g.Oracle(body,g.fixture(self.rom,case),case);model.cut=cut
                    with self.assertRaises(AccessBoundary):model.run()
                    models.append(model)
                self.assertEqual(g.state(models[0]),g.state(models[1]));cuts+=1;delays+=models[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,complete_guarded_private_memory_PC_and_trace_equal=True,raw_C_fault_identity_not_claimed=True)
    def test_04_original_RNG_selector_and_effect_submitter(self):
        count=0;seen={g.FLOAT:set(),g.SELECTOR:set(),g.SUBMIT:set()};descriptors=((g.FLOAT,0xDAF18,25),(g.SELECTOR,0x2062D0,19),(g.SUBMIT,0x20916C,113));before=self.q['predecessor_elf'].read_bytes()
        at=m.elf_slot_offset(before,g.UNIT,4);self.assertEqual(before[at:at+4],bytes.fromhex('37800080'))
        at=m.elf_slot_offset(before,g.COLORS,768);self.assertEqual(before[at:at+768],self.rom[0x24FED4:0x24FED4+768])
        for entry,offset,n in descriptors:
            at=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[at:at+n*4],self.rom[offset:offset+n*4])
        for connected,seed,state,query in itertools.product((1,2,4,7),g.SEEDS,(0,1),(0,1)):
            case=g.Case(connected=connected,seed=seed,state=state,query=query);models=self.compare(case)
            for entry,offset,n in descriptors:seen[entry].update(p for p in models[0].visits if entry<=p<entry+n*4)
            count+=1
        for selector in range(256):
            models=self.compare(g.Case(selector=selector,connected=4));seen[g.SUBMIT].update(p for p in models[0].visits if g.SUBMIT<=p<g.SUBMIT+452);count+=1
        self.assertEqual(len(seen[g.FLOAT]),25);self.assertEqual(len(seen[g.SELECTOR]),19);self.assertGreater(len(seen[g.SUBMIT]),70)
        self.receipts['providers']=dict(cases_per_body=count,retained_words=157,covered_words={hex(p):len(v)for p,v in seen.items()},actual_RNG_unit='0x37800080',actual_palette_bytes=768,submit_context_zero=True,lower_effect_provider_bounded=True,nonzero_context_path_not_reached_by_target=True,no_additional_C_credit=True)
    def test_05_actual_callback_dispatch_and_return_gate(self):
        words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(words)if w==g.ENTRY],[0x22EEE0]);self.assertNotIn(0x0C000000|(g.ENTRY>>2&0x3FFFFFF),words)
        va=0x15147F04;window=list(struct.unpack_from('>17I',self.rom,0x1753B4));count=0
        for enabled,blocked,mutation,y in itertools.product((0,1),(0,1),(0,7),(g.bits(1.),g.bits(20.))):
            case=g.Case(mutation=mutation,y=y);initial=g.fixture(self.rom,case);p=g.read(initial,g.ACTOR+0x98);initial[p+0x21]=10 if enabled else 0;g.put(initial,0x8008A420,g.ENTRY);expected=g.reference(initial,case)if enabled and not blocked else dict(memory=g.public(initial,case),calls=[],vectors=[]);models=[]
            for body in(self.truth,self.words):
                connected=dict(zip(range(g.ENTRY,g.ENTRY+276,4),body));connected[0x15147F48]=0;connected[0x15147F4C]=0
                model=g.Oracle(window,initial,case,entry=va,connected=connected,arguments=(g.ACTOR,));model.r[3]=p;model.r[6]=blocked
                model.code=WindowCode(model.code,model);model.code.ends=(0x15147F48,0x15147F4C)
                with self.assertRaises(WindowBoundary):model.run()
                called=enabled and not blocked;self.assertEqual(model.calls[:1],[(g.ENTRY,(g.ACTOR,))]if called else[]);self.assertEqual((g.public(model.memory,case),model.calls[1:]if called else model.calls,model.vectors),(expected['memory'],expected['calls'],expected['vectors']));self.assertEqual(model.r[6],blocked);models.append(model)
            self.assertEqual(g.state(models[0]),g.state(models[1]));count+=1
        self.receipts['caller']=dict(cases=count,actual_window_words=17,callback_index=10,slot='0x8008A420',one_argument=True,return1_preserves_clear_block_flag=True,full_dispatcher_not_claimed=True)
    def test_06_native32_and_compiled_semantic_negatives(self):
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native'+opt+'.c');path.write_text(harness(self.rom),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        variants=dict(stub=c.SELECTED[:c.SELECTED.index('{')+1]+'\n    return 0;\n}',outer_boundary=c.SELECTED.replace('].y <','].y <='),reload_positions=c.SELECTED.replace('            point[0] =','            positions = *(BelowHeightPosition **)(actor + 0x94);\n            point[0] ='),reload_payload=c.SELECTED.replace('            choice = func_151D8E20();','            choice = func_151D8E20();\n            payload = *(u8 **)(actor + 0x98);'),float_threshold=c.SELECTED.replace('< D_800A73A8','< (f32)D_800A73A8'))
        rejected={}
        for label,body in variants.items():
            path=self.out/('negative-'+label+'.c');path.write_text(harness(self.rom,body),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command('-O2'),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_headers=True,UBSan_trap=True,Python_little_endian_byte_reference=True,finite_FP_domain=True,alias_layouts=[0,2,3],actor_plus80_alias_guest_only=True,semantic_negatives=rejected)
    def test_07_independent_links_and_literal_image_negatives(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);blob,_=m.derive(raw,refs);count=0
        for entry,s in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(func_150ADA68=0x17518004,func_151D8E20=0x17507FFC,func_151DBCBC=0x17518008,D_800A73A8=0x80207FF8,D_800A73B0=0x80208000))):
            words=struct.unpack('>69I',blob);lines=['.set noreorder','.text','.globl func_15189EBC','func_15189EBC:']
            for i,w in enumerate(words):
                rr=refs.get(i*4)
                if not rr:lines.append('.word 0x%08X'%w);continue
                kind,name=rr[0];rt=w>>16&31;rs=w>>21&31
                lines.append('jal '+name if kind=='R_MIPS_26'else'lui $%d,%%hi(%s)'%(rt,name)if kind=='R_MIPS_HI16'else('ldc1'if w>>26==53 else'lwc1')+' $f%d,%%lo(%s)($%d)'%(rt,name,rs))
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(blob,refs,s));count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),248)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,276),0x2B8ABC,0x2FA832):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=248,exclusions=0,named_symbol_permutations=2,independent_links=count,corruptions_rejected=4,protected_bytes=189088)
if __name__=='__main__':unittest.main()
