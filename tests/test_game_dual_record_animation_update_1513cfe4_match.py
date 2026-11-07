"""Record updater: mapped-RAM model, original registry caller and closed image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_dual_record_animation_update_1513cfe4_candidates as c
from tools.experiments import game_dual_record_animation_update_1513cfe4_match as m
from tools.tests import game_dual_record_animation_update_1513cfe4_oracle as g
from tools.tests.game_dual_record_animation_update_1513cfe4_native import harness,cases as native_cases,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class DualRecordAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>195I',cls.rom,0x16A494));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.compact=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def run_body(self,body,initial,case,**kw):
        v=g.Oracle(body,initial,case,**kw)
        try:v.run()
        except g.GuestTrap:pass
        return v
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;e=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words,self.compact):
            v=self.run_body(body,initial,case);self.assertEqual((g.public(v.memory,case),v.calls,v.status),(e['observed'],e['calls'],e['status']),case);machines.append(v)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case);return machines
    def test_01_complete_owner_guards_rodata_anchor_and_metadata(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,540,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(195,32,12,13,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(self.refs,self.nr)
        self.assertEqual([i for i,(a,b)in enumerate(zip(struct.unpack('>195I',self.raw),struct.unpack('>195I',self.normal)))if a!=b],[49,50,68,70,135,136,137,139,167,168,169,170]);self.assertEqual(len(m.guard_rows()),12)
        for off in(0,108,136,140,216,296,320,496,500,512,644,656,748):
            bad=bytearray(self.raw);bad[off+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        refs=dict(self.refs);refs[44]=[('R_MIPS_HI16','D_80090B64')]
        with self.assertRaises(ValueError):m.derive(self.raw,refs)
        old=self.out/'match-predecessor-0.o';new=self.q['qualified_compacts'][0];blob=new.read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,p)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed predecessor')
        self.receipts['owner']=q;self.receipts['normalization']=dict(raw_words=195,retail_words=195,flags_role_words=4,self_store_forwarding_words=8,guards=12,no_insertions_deletions_or_branch_retargeting=True,raw_and_padded_pools_masks_and_options_unchanged=True,existing_rodata_anchor='jtbl_800A5188_game',raw_private_and_fault_identity_not_claimed=True)
    def test_02_independent_integer_model_aliases_homes_and_trap(self):
        seen=set();traps=0;cases=list(g.cases())
        for case in cases:
            v=self.compare(case)[0];seen.update(v.visits);traps+=v.status!='return'
        missing={(p-g.ENTRY)//4 for p in set(range(g.ENTRY,g.ENTRY+780,4))-seen};self.assertEqual(missing,{125,131,157});self.assertEqual(traps,1)
        for frames in range(256):
            limit=(frames<<16)-1;self.assertNotEqual(limit,0);self.assertFalse(-2147483648>limit)
        # A disabled record needs only its active word and the actual private frame.
        case=g.Case(enabled=0);initial=g.fixture(case);initial={p:v for p,v in initial.items()if g.STACK-1024<=p<g.STACK+512 or g.RESOURCE+16<=p<g.RESOURCE+20};self.compare(case,initial)
        self.receipts['guest']=dict(cases_per_body=len(cases)+1,bodies=3,reachable_words=192,literal_unreachable_trap_words=sorted(missing),all_195_words_compared=True,zero_divisors_impossible_for_all_256_frame_counts=True,positive_division_overflow_guard_unreachable=True,reachable_negative_overflow_traps=traps,raw_public_model_only=True,normalized_retail_full_private_machine_identity=True,private_homes_aliases_wrapped_arithmetic_guest_only=True,disabled_record_needs_no_other_mapping=True)
    def test_03_actual_tables_and_full_original_registry_updater(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x03FFFFFF);direct=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:direct.append(i*4)
            if g.ENTRY<=w<g.ENTRY+780:pointers.append((i*4,w))
        self.assertEqual(direct,[]);self.assertEqual(pointers,[(0x230518,g.ENTRY),(0x230E3C,g.ENTRY),(0x2310E0,g.ENTRY)])
        caller=struct.unpack_from('>74I',self.rom,0x194570);seen=set();count=0
        for kind,bank,chain,depth,mutation in itertools.product((0x1C,0x49,0x56),(0,1),(1,2),(0,1),(0,1,2,3,4)):
            case=g.Case(update=1,second=1,exit=1,mutation=mutation,answer=0 if mutation==4 else 1,second_answer=0 if mutation==4 else 1,exit_answer=0);initial=g.caller_fixture(case,kind,bank,chain,depth);e=g.caller_reference(initial,case,kind,bank,chain,depth);machines=[]
            for body in(self.truth,self.words,self.compact):
                code=dict(zip(range(g.ENTRY,g.ENTRY+780,4),body));v=self.run_body(caller,initial,case,entry=g.CALLER,connected=code);self.assertEqual((g.public(v.memory,case),v.calls,v.status),(e['observed'],e['calls'],'return'));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);count+=1
        self.assertEqual(set(range(g.CALLER,g.CALLER+296,4))-seen,set());before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CALLER,296);self.assertNotEqual(before[at:at+296],self.rom[0x194570:0x194698])
        self.receipts['caller']=dict(cases_per_body=count,original_dispatcher_words=74,all_dispatcher_words_executed=True,registry_kinds=[0x1C,0x49,0x56],registry_slot=0,two_banks_and_linked_records=True,next_link_stored_before_callback=True,void_one_pointer_interface=True,direct_JALs=0,entry_pointers=3,interior_pointers=0,production_dispatcher_still_unrestored=True,callbacks_and_release_bounded_providers=True)
    def test_04_loop_forwarding_invariant_and_effective_counterexamples(self):
        checked=0;negative=0;case=g.Case()
        for start,n,values in((135,5,(65536,131071,196606)),(167,4,(-1,-65536,-131071))):
            entry=g.ENTRY+start*4;raw=self.compact[start:start+n]+[0x03E00008,0];normal=self.words[start:start+n]+[0x03E00008,0]
            for cursor in values:
                memory=g.fixture(case);g.wr(memory,g.RESOURCE+0x20,cursor);results=[]
                for body in(raw,normal):
                    v=g.Oracle(body,memory,case,entry=entry);v.r[2]=g.u32(cursor);v.r[3]=65535;v.run();results.append(g.rd(v.memory,g.RESOURCE+0x20))
                self.assertEqual(results[0],results[1]);checked+=1
            cursor=65536 if start==135 else -1;memory=g.fixture(case);g.wr(memory,g.RESOURCE+0x20,cursor+1);results=[]
            for body in(raw,normal):
                v=g.Oracle(body,memory,case,entry=entry);v.r[2]=g.u32(cursor);v.r[3]=65535;v.run();results.append(g.rd(v.memory,g.RESOURCE+0x20))
            self.assertNotEqual(results[0],results[1]);negative+=1
        self.receipts['loop_proof']=dict(checked_closed_loops=checked,effective_broken_invariant_counterexamples=negative,entry_invariant='V0 equals last stored RAM[A0+0x20]',fixed_A0_V1_and_only_self_store=True,ordinary_RAM_no_concurrent_or_volatile_side_effects=True,raw_redundant_reads_not_fault_equivalent=True)
    def test_05_normalized_access_prefixes_and_saved_lifetime(self):
        cuts=delays=0
        for case in(g.Case(cursor=g.u32(-131071)),g.Case(flags=0x400,cursor=131071),g.Case(update=1,second=1,exit=1,mutation=2),g.Case(frames=0,flags=0x400,cursor=0x80000000,ticks=0),g.Case(enabled=0)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    v=g.Oracle(body,g.fixture(case),case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,normalized_retail_full_private_memory_registers_PC_trace=True,RA_stack_and_byte_flag_home_lifetime_checked=True,raw_fault_prefix_and_hardware_exception_identity_not_claimed=True)
    def test_06_native32_typed_callbacks_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED
        stale=s.replace('    s32 flags;','    s32 flags = *(u32 *)(record + 0x58);').replace('    flags = *(u32 *)(record + 0x58);','    ;')
        variants=dict(stub=s[:s.index('{')+1]+'\nreturn;\n}',skip_timer=s.replace('*(s16 *)(record + 0x1C) -= D_800BE9E4;',';'),wrong_update=s.replace('D_80089CB8[callback](record) == 0','D_80089CB8[callback](record) != 0'),wrong_second=s.replace('D_80089D60[callback](record) == 0','D_80089D60[callback](record) != 0'),short_circuit_second=s.replace('callback != 0 && D_80089D60','remove == 0 && callback != 0 && D_80089D60'),wrong_exit=s.replace('D_80089E10[callback](record) != 0','D_80089E10[callback](record) == 0'),missing_release=s.replace('func_1516972C((struct102 *)record);','(void)record;'),wrong_fade=s.replace('if (adjusted < record[0x5C]) record[0x2B]','if (adjusted < record[0x2B]) record[0x2B]'),wrong_period=s.replace('(frames << 16) - 1','(frames << 16)'),wrong_reflect=s.replace('limit - cursor % limit','cursor % limit'),wrong_reverse=s.replace('(u32)0 - (u32)rate','(u32)rate'),stale_flags=stale)
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(native_cases()),SDK_types_and_pointer32=True,typed_void_update_and_s32_callback_tables=True,disjoint_record_frame_time_and_marker_banks=True,UBSan_traps=True,semantic_negatives=rejected,private_homes_aliases_out_of_table_indices_and_exceptional_arithmetic_guest_only=True)
    def test_07_GNU_relocations_and_zero_exclusion_image(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        moved=dict(g.symbols(),D_800BE9E4=0x82348004,D_80089CB8=0x81237FF0,D_80089D60=0x81238098,D_80089E10=0x81238148,D_80090B64=0x83458004,func_1516972C=0x1756972C);links=0
        for entry,symbols in((g.ENTRY,g.symbols()),(0x17407F50,moved)):
            lines=['.set noreorder','.set noat','.text','.globl func_1513CFE4','func_1513CFE4:']
            for i,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.nr.get(i*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    elif word>>26==35:line='lw $%d, %%lo(%s)($%d)'%(rt,name,rs)
                    else:self.assertEqual(word>>26,36);line='lbu $%d, %%lo(%s)($%d)'%(rt,name,rs)
                lines.append(line)
            p=self.out/('rebase-'+str(links));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>195I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.nr,symbols));links+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),540)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,780),2979473,2979491,3227498,2857604):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=540,exclusions=0,closed_symbol_string_pair_swaps=0,named_definitions_preserved=True,independent_links=links,bindings=13,signed_LO_carry=True,corruptions_rejected=6)

if __name__=='__main__':unittest.main()
