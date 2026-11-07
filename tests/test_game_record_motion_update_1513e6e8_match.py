"""Direct leaf: independent field model, actual updater ABI and complete image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_record_motion_update_1513e6e8_candidates as c
from tools.experiments import game_record_motion_update_1513e6e8_match as m
from tools.tests import game_record_motion_update_1513e6e8_oracle as g
from tools.tests.game_record_motion_update_1513e6e8_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class RecordMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>85I',cls.rom,0x16BB98));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.words=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_direct_owner_no_guards_and_historical_source_roundtrip(self):
        q=self.q['report'];t=q['targets'][0]
        self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,266,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(85,0,0,4,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(m.derive(self.raw,self.refs),(self.raw,self.refs));self.assertEqual(m.guard_rows(),[])
        before,after,installed=c.source_states((self.root/c.TARGETS[0]['source']).read_text());self.assertEqual(c.source_states(after),(before,after,True));self.assertIn(c.LEGACY,before);self.assertNotIn(c.LEGACY,after)
        for i in range(85):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        refs=dict(self.refs);refs[8]=[('R_MIPS_LO16','D_800BE9E4')]
        with self.assertRaises(ValueError):m.derive(self.raw,refs)
        old=self.out/'match-predecessor-0.o';blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,p)
        self.assertEqual(m.guard_manifest((self.out/'predecessor-guards.csv').read_bytes()),(self.root/m.GUARDS).read_bytes())
        with self.assertRaises(ValueError):m.guard_manifest(b'changed history')
        self.receipts['owner']=q

    def test_02_independent_float32_fields_aliases_and_leaf_ABI(self):
        seen=set();count=0
        for case in g.cases():
            initial=g.fixture(case);e=g.reference(initial,case);machines=[]
            for words in(self.truth,self.words):
                v=g.Oracle(words,initial,case);before_r=v.r[:];before_f=v.f[:];v.run()
                self.assertEqual((v.memory,v.calls,v.r[2]),(e['memory'],[],1),case)
                self.assertEqual(v.r[16:24],before_r[16:24]);self.assertEqual((v.r[29],v.r[31]),(before_r[29],before_r[31]));self.assertEqual(v.f[20:],before_f[20:]);machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+340,4))-seen,set())
        # Clear motion flags require no float/global/stack mapping at all.
        case=g.Case(flags=0);initial=g.fixture(case);minimal={p:v for p,v in initial.items()if g.RESOURCE+0x58<=p<g.RESOURCE+0x5C or p==g.RESOURCE+0x5D};e=g.reference(minimal,case)
        for words in(self.truth,self.words):v=g.Oracle(words,minimal,case);v.run();self.assertEqual((v.memory,v.r[2]),(e['memory'],1))
        self.receipts['guest']=dict(cases_per_body=count+1,bodies=2,all_words_executed=85,full_memory_and_return_model=True,private_machine_identity=True,all_512_low_flag_values=True,time_aliases_at_velocity_and_output=True,ordered_velocity_before_position=True,clear_flags_need_only_flags_and_reset_byte=True,finite_subnormal_signed_zero_and_bounded_nonfinite_model=True,FCSR_and_hardware_NaN_payloads_not_claimed=True)

    def test_03_actual_table_and_full_adopted_updater_connection(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);direct=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:direct.append(i*4)
            if g.ENTRY<=w<g.ENTRY+340:pointers.append((i*4,w))
        self.assertEqual((direct,pointers),([] ,[(0x22E77C,g.ENTRY)]));self.assertEqual(g.updater.retained()[0][1],g.ENTRY)
        body=list(struct.unpack_from('>195I',self.rom,0x16A494));before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.updater.ENTRY,780);self.assertEqual(before[at:at+780],self.rom[0x16A494:0x16A7A0]);count=0;seen=set()
        for flags,enabled,second,result,veto,mutation in itertools.product((0,0x20,0x1E0,0x080001E1),(0,1),(0,1,29),(0,1),(0,1),(0,3)):
            case=g.Case(flags=flags,time=0x3F000000,pattern=2);uc=g.connected_case(case,enabled,second,result,veto,mutation);uc=replace(uc,timer=0 if flags&1 else 20);initial=g.connected_fixture(case,uc);e=g.connected_reference(initial,case,uc);machines=[]
            for words in(self.truth,self.words):
                code=dict(zip(range(g.ENTRY,g.ENTRY+340,4),words));v=g.UpdaterOracle(body,initial,uc,connected=code);v.run();self.assertEqual((g.updater.public(v.memory,uc),v.calls,v.status),(e['observed'],e['calls'],'return'));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(sum(t==g.ENTRY for t,a in machines[0].calls),enabled);seen.update(machines[0].visits);count+=1
        self.assertTrue(set(range(g.ENTRY,g.ENTRY+340,4))<=seen)
        self.receipts['caller']=dict(cases_per_body=count,original_updater_words=195,production_updater_already_exact=True,actual_table_slot=1,entry_pointers=1,interior_pointers=0,direct_JALs=0,s32_one_pointer_ABI=True,return_one_keeps_record=True,other_update_and_exit_release_bounded=True,record_banks_extended_to512_and_disjoint=True)

    def test_04_every_access_prefix_and_no_private_frame(self):
        cuts=delays=0
        for case in(g.Case(flags=0),g.Case(flags=0x20),g.Case(),g.Case(alias=1),g.Case(alias=2)):
            initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run()
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    v=g.Oracle(body,initial,case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
            self.assertFalse(any(g.STACK+case.phase-1024<=p<g.STACK+case.phase+512 for kind,p,n,value in full.trace))
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,all_private_memory_GPR_FPR_HI_LO_PC_and_access_traces=True,no_stack_access_or_saved_register_lifetime=True,hardware_FCSR_faults_not_modeled=True)

    def test_05_native32_typed_slot_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;line='*(f32 *)(motion + 0x0C) += *(f32 *)(motion + 0x2C) * D_800BE9A4;'
        variants=dict(stub=s[:s.index('{')+1]+'\nreturn 0;\n}',wrong_flag=s.replace('& 0x20','& 0x10'),skip_velocity=s.replace(line,';'),wrong_source=s.replace('*(f32 *)(record + 0x38) += *(f32 *)(motion + 0x0C)','*(f32 *)(record + 0x38) += *(f32 *)(motion + 0x08)'),wrong_destination=s.replace('*(f32 *)(record + 0x54)','*(f32 *)(record + 0x50)'),wrong_time=s.replace('D_800BE9A4','1.0f'),wrong_reset=s.replace('record[0x5D] = 255','record[0x5D] = 254'),wrong_return=s.replace('return 1;','return 0;'))
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases()),SDK_types_pointer32_and_s32_table_slot=True,selected_slot_only_not_full_table_restoration=True,round_to_nearest_FTZ_DAZ_clear_checked=True,UBSan_traps=True,semantic_negatives=rejected,aliases_nonfinite_outputs_and_FCSR_guest_only=True)

    def test_06_two_GNU_links_and_literal_bindings(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        for i,(entry,symbols)in enumerate(((g.ENTRY,g.symbols()),(0x17407F50,dict(D_800BE9A4=0x81238004)))):
            lines=['.set noreorder','.set noat','.text','.globl func_1513E6E8','func_1513E6E8:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.raw)):
                refs=self.refs.get(j*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    else:self.assertEqual((kind,word>>26),('R_MIPS_LO16',9));line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>85I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.raw,self.refs,symbols))
        self.receipts['relocations']=dict(independent_links=2,bindings=4,signed_LO_carry=True,guard_rewrites=0)

    def test_07_zero_exclusion_whole_image_and_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),266)
        slot=[p for p,n,f,s in m.symbol_rows(before)if n=='func_1513E6E8'];self.assertEqual(len(slot),1)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,340),slot[0]+8,2979473,3227498,2857604):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=266,exclusions=0,named_definitions_fixed_except_target_size=True,metadata_reorderings=0,corruptions_rejected=6)

if __name__=='__main__':unittest.main()
