"""Damping source/ABI, ordinary-RAM schedule proof and strict image qualification."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_record_damping_update_1513f728_candidates as c
from tools.experiments import game_record_damping_update_1513f728_match as m
from tools.tests import game_record_damping_update_1513f728_oracle as g
from tools.tests.game_record_damping_update_1513f728_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class RecordDampingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>193I',cls.rom,0x16CBD8));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.raw_words=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_owner_closed_schedule_and_source_roundtrip(self):
        q=self.q['report'];t=q['targets'][0]
        self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,571,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(193,48,57,6,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth)
        before,after,installed=c.source_states((self.root/c.TARGETS[0]['source']).read_text());self.assertEqual(c.source_states(after),(before,after,True));self.assertIn(c.STUB,before);self.assertNotIn(c.STUB,after)
        for i in range(193):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        for at in self.refs:
            refs=dict(self.refs);refs[at]=[('R_MIPS_LO16','wrong_symbol')]
            with self.assertRaises(ValueError):m.derive(self.raw,refs)
        self.assertEqual(sorted(m.POST_LOOP_ORDER),list(range(120,176)))
        # Every loop word on the non-taken BEQL edge leaves AT alone. The
        # duplicated literal LUI is idempotent and dominates MTC1 on each exit.
        w=self.raw_words
        for i in range(42,120):
            op,rs,rt=w[i]>>26,w[i]>>21&31,w[i]>>16&31
            self.assertIn(op,(0,4,5,9,49,57,17));self.assertNotEqual(rs,1)
            if op==0:self.assertEqual(w[i],0)
            if op in(4,5,9):self.assertNotEqual(rt,1)
        self.assertEqual((self.words[41],self.words[120],self.words[122]),(0x3C013F00,0x3C013F00,0x44819000))
        self.assertEqual(self.nr,{16:[('R_MIPS_HI16','D_800BE9E4')],40:[('R_MIPS_LO16','D_800BE9E4')],484:[('R_MIPS_HI16','D_800BE9A4')],492:[('R_MIPS_LO16','D_800BE9A4')],508:[('R_MIPS_HI16','D_800BE9A8')],532:[('R_MIPS_LO16','D_800BE9A8')]})
        blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(self.out/'match-predecessor-0.o',p)
        self.assertEqual(m.guard_manifest((self.out/'predecessor-guards.csv').read_bytes()),(self.out/'qualified-guards.csv').read_bytes())
        with self.assertRaises(ValueError):m.guard_manifest(b'changed history')
        self.receipts['owner']=q

    def test_02_independent_float32_model_aliases_and_leaf_ABI(self):
        seen=set();count=0
        for case in g.cases():
            initial=g.fixture(case);e=g.reference(initial,case);machines=[]
            for words in(self.truth,self.words,self.raw_words):
                v=g.Oracle(words,initial,case);before_r=v.r[:];before_f=v.f[:];v.run()
                self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],[],1),case)
                self.assertEqual(v.r[16:24],before_r[16:24]);self.assertEqual((v.r[29],v.r[31]),(before_r[29],before_r[31]));self.assertEqual(v.f[20:],before_f[20:]);machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+772,4))-seen,set())
        broken=self.words[:];broken[41]=0
        case=g.Case(ticks=1);initial=g.fixture(case);bad=g.Oracle(broken,initial,case);bad.run()
        self.assertNotEqual(g.public(bad.memory,case),g.reference(initial,case)['observed'])
        self.receipts['guest']=dict(cases_per_body=count,bodies=3,all_words_executed=193,full_public_memory_and_return_model=True,normalized_private_machine_identity=True,raw_private_and_fault_identity_not_claimed=True,missing_delay_constant_effectively_rejected=True,four_time_inverse_tick_aliases=True,ticks_zero_remainders_unrolled_boundaries=True,finite_subnormal_signed_zero_and_bounded_nonfinite_model=True,FCSR_and_hardware_NaN_payloads_not_claimed=True)

    def test_03_actual_table_and_full_adopted_updater_connection(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);direct=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:direct.append(i*4)
            if g.ENTRY<=w<g.ENTRY+772:pointers.append((i*4,w))
        self.assertEqual((direct,pointers),([] ,[(0x22E7DC,g.ENTRY)]));self.assertEqual(g.updater.retained()[0][25],g.ENTRY)
        body=list(struct.unpack_from('>195I',self.rom,0x16A494));before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.updater.ENTRY,780);self.assertEqual(before[at:at+780],self.rom[0x16A494:0x16A7A0]);count=0;seen=set()
        for ticks,enabled,second,result,veto,mutation in itertools.product((0,1,3,4,5,8),(0,1),(0,1,29),(0,1),(0,1),(0,3)):
            case=g.Case(ticks=ticks,pattern=3);uc=g.connected_case(case,enabled,second,result,veto,mutation);uc=replace(uc,flags=0x08000001,timer=-1 if veto else 20);initial=g.connected_fixture(case,uc);e=g.connected_reference(initial,case,uc);machines=[]
            for words in(self.truth,self.words,self.raw_words):
                code=dict(zip(range(g.ENTRY,g.ENTRY+772,4),words));v=g.UpdaterOracle(body,initial,uc,connected=code);v.run();self.assertEqual((g.updater.public(v.memory,uc),v.calls,v.status),(e['observed'],e['calls'],'return'));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(sum(t==g.ENTRY for t,a in machines[0].calls),enabled);seen.update(machines[0].visits);count+=1
        self.assertTrue(set(range(g.ENTRY,g.ENTRY+772,4))<=seen)
        self.receipts['caller']=dict(cases_per_body=count,bodies=3,original_updater_words=195,production_updater_already_exact=True,actual_table_slot=25,entry_pointers=1,interior_pointers=0,direct_JALs=0,s32_one_pointer_ABI=True,return_one_keeps_record=True,other_update_and_exit_release_bounded=True,record_banks_extended_to512_and_disjoint=True)

    def test_04_every_access_prefix_frame_and_huge_count_prefixes(self):
        cuts=delays=0
        for case in(g.Case(ticks=0),g.Case(ticks=1),g.Case(ticks=3),g.Case(ticks=4),g.Case(ticks=5),g.Case(ticks=9),g.Case(alias=1),g.Case(alias=2),g.Case(alias=3),g.Case(alias=4)):
            initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run()
            stack=[(kind,p,n,v)for kind,p,n,v in full.trace if g.STACK+case.phase-1024<=p<g.STACK+case.phase+512]
            self.assertEqual([p for kind,p,n,v in stack if kind=='W'],[g.STACK+case.phase-16,g.STACK+case.phase-12,g.STACK+case.phase-8])
            for cut in range(full.all_accesses):
                machines=[]
                for words in(self.truth,self.words):
                    v=g.Oracle(words,initial,case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        class PrefixStop(Exception):pass
        class Prefix(dict):
            def __init__(self,code):super().__init__(code);self.original=code;self.count=0
            def __getitem__(self,pc):
                if pc==g.ENTRY+49*4:
                    self.count+=1
                    if self.count==4:raise PrefixStop
                return self.original[pc]
        for ticks in(0x7FFFFFFC,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFFE,0xFFFFFFFF):
            case=g.Case(ticks=ticks);initial=g.fixture(case);machines=[]
            for words in(self.truth,self.words,self.raw_words):
                v=g.Oracle(words,initial,case);v.code=Prefix(v.code)
                with self.assertRaises(PrefixStop):v.run()
                self.assertEqual(v.r[2],g.u32(ticks-(ticks&3)-16));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(g.state(machines[0]),g.state(machines[2]))
        counterexample=[];case=g.Case(ticks=0);initial=g.fixture(case)
        for words in(self.truth,self.raw_words):
            v=g.Oracle(words,initial,case);v.cut=8
            with self.assertRaises(AccessBoundary):v.run()
            counterexample.append(g.state(v))
        self.assertNotEqual(*counterexample)
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,normalized_full_private_fault_prefix_identity=True,raw_access_cut_counterexample=True,frame=48,local_snapshot_bytes=12,no_saved_register_writes=True,huge_unsigned_prefix_cases=6,source_loop_unclamped=True,huge_full_execution_not_claimed=True,hardware_FCSR_faults_not_modeled=True)

    def test_05_native32_typed_slot_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED
        variants=dict(stub=s[:s.index('{')+1]+'\nreturn 0;\n}',skip_last_tick=s.replace('ticks != 0','ticks > 1'),wrong_damping=s.replace('motion->velocity.z *= motion->damping;','motion->velocity.z *= 1.0f;'),wrong_gravity=s.replace('motion->verticalAcceleration * D_800BE9A4','motion->verticalAcceleration'),wrong_inverse=s.replace('* D_800BE9A8','* 1.0f'),wrong_destination=s.replace('actor + 0x3C','actor + 0x38'),wrong_time=s.replace('motion->angular.z * D_800BE9A4','motion->angular.z'),wrong_half=s.replace('0.5f','1.0f'),wrong_return=s.replace('return 1;','return 0;'))
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases()),SDK_types_pointer32_and_s32_table_slot=True,selected_slot_only_not_full_table_restoration=True,round_to_nearest_FTZ_DAZ_clear_checked=True,UBSan_traps=True,semantic_negatives=rejected,aliases_nonfinite_outputs_and_FCSR_guest_only=True)

    def test_06_two_GNU_links_and_explicit_relocation_moves(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        configs=((g.ENTRY,g.symbols()),(0x17407F50,dict(D_800BE9A4=0x81237FF8,D_800BE9A8=0x81238004,D_800BE9E4=0x82348010)))
        for i,(entry,symbols)in enumerate(configs):
            for label,raw,refs in(('raw',self.raw,self.refs),('normalized',self.normal,self.nr)):
                lines=['.set noreorder','.set noat','.text','.globl func_1513F728','func_1513F728:']
                for j,(word,)in enumerate(struct.iter_unpack('>I',raw)):
                    bindings=refs.get(j*4,[])
                    if not bindings:line='.word 0x%08X'%word
                    else:
                        self.assertEqual(len(bindings),1);kind,name=bindings[0];rt,rs=word>>16&31,word>>21&31
                        if kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                        elif word>>26==9:line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                        else:self.assertIn(word>>26,(35,49));line=('lw'if word>>26==35 else'lwc1')+' $%s%d, %%lo(%s)($%d)'%('f'if word>>26==49 else'',rt,name,rs)
                    lines.append(line)
                p=self.out/('rebase-'+str(i)+'-'+label);p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>193I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(raw,refs,symbols))
        self.receipts['relocations']=dict(independent_links=4,configurations=2,bindings=6,explicit_moves=4,signed_LO_carry=True,guard_rewrites=57)

    def test_07_zero_exclusion_whole_image_and_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),571)
        slot=[p for p,n,f,s in m.symbol_rows(before)if n=='func_1513F728'];self.assertEqual(len(slot),1)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,772),slot[0]+8,2979473,3227498,2857604):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=571,exclusions=0,named_definitions_fixed_except_target_size=True,metadata_reorderings=0,corruptions_rejected=6)

if __name__=='__main__':unittest.main()
