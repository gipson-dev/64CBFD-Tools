"""Resource scroll: real update caller/helper, float32 model and strict image."""
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_resource_scroll_update_1513beb0_candidates as c
from tools.experiments import game_resource_scroll_update_1513beb0_match as m
from tools.tests import game_resource_scroll_update_1513beb0_oracle as g
from tools.tests.game_resource_scroll_update_1513beb0_native import harness,cases as native_cases,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class ResourceScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>107I',cls.rom,0x169360));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.compact=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def compare(self,case):
        initial=g.fixture(case);e=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words,self.compact):
            v=g.Oracle(body,initial,case,connected=g.helpers(self.rom,case)).run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],1),case);machines.append(v)
        for v in machines[1:]:self.assertEqual(g.state(machines[0]),g.state(v),case)
        return machines
    def test_01_owner_commutative_word_and_pool_identity(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(150,6052,361,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(107,32,1,20,12,12));self.assertEqual(t['diagnostics'],dict(before=4,after=4,new=[]));self.assertEqual(self.words,self.truth)
        a,b=struct.unpack('>107I',self.raw),struct.unpack('>107I',self.normal);self.assertEqual([i for i in range(107)if a[i]!=b[i]],[9]);self.assertEqual((a[9],b[9]),(0x01C48021,0x008E8021));self.assertEqual(self.refs,self.nr)
        for at in(0,12,16,36,56,100,176,240,424):
            bad=bytearray(self.raw);bad[at+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        refs=dict(self.refs);refs[56]=[('R_MIPS_26','sinf')]
        with self.assertRaises(ValueError):m.derive(self.raw,refs)
        old=self.out/'match-predecessor-0.o';new=self.q['qualified_compacts'][0];blob=new.read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,p)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed predecessor')
        self.receipts['owner']=q;self.receipts['normalization']=dict(raw_words=107,retail_words=107,guards=1,commutative_ADDU_only=True,all_other_words_and_bindings_literal=True,raw_and_padded_pools_and_masks_unchanged=True)
    def test_02_float32_model_strict_endpoints_live_reads_and_aliases(self):
        seen=set();cases=list(g.cases())
        cases.extend(replace(g.Case(),base=base)for base in(0x7FFFFFF0,0x80000000,0xFFFFFFF0))
        for case in cases:seen.update(self.compare(case)[0].visits)
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+428,4))-seen,set())
        self.receipts['guest']=dict(cases_per_body=len(cases),bodies=3,all_107_words_executed=True,strict_inclusive_0_4096_boundaries=True,negative_zero_and_repeated_loops=True,live_frame_time_coefficients_and_payload_capture=True,output_global_aliases_and_wrapped_addresses_guest_only=True,full_private_machine_and_access_identity=True)
    def test_03_original_complete_angle_wrapper(self):
        seen=set();count=0
        for value,mutation in itertools.product((0.0,6.2831854820251465,20.0,-20.0),(0,1,2,3)):
            case=g.Case(phaseValue=g.bits(value),angleS=g.bits(value),angleT=g.bits(-value),mutation=mutation,connected=1);seen.update(self.compare(case)[0].visits);count+=1
        before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.WRAP,96);self.assertEqual(before[at:at+96],self.rom[0x172018:0x172078]);self.assertEqual(set(range(g.WRAP,g.WRAP+96,4))-seen,set());self.assertEqual(g.retained()[1],0x40C90FDB)
        self.receipts['helper']=dict(cases_per_body=count,original_words=24,all_words_executed=True,production_already_exact=True,retained_bound_word='40C90FDB',sine_service_bounded=True)
    def test_04_real_callback_table_and_complete_update_dispatcher(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x03FFFFFF);direct=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:direct.append(i*4)
            if g.ENTRY<=w<g.ENTRY+428:pointers.append((i*4,w))
        self.assertEqual(direct,[]);self.assertEqual(pointers,[(0x22E6E0,g.ENTRY)])
        words=struct.unpack_from('>41I',self.rom,0x168C48);before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CALLER,164);self.assertEqual(before[at:at+164],self.rom[0x168C48:0x168CEC]);seen=set();count=0
        for flag,mutation,connected in itertools.product((0,1),(0,1,2,3),(0,1)):
            case=g.Case(mutation=mutation,connected=connected);initial=g.fixture(case);initial[case.base+0x10]=flag;initial[case.base+0x11]=2;g.wr(initial,case.base+0x14,300,2);g.wr(initial,g.TICKS,3);g.wr(initial,g.TABLE+8,g.ENTRY)
            expected_initial=dict(initial)
            if flag:g.wr(expected_initial,case.base+0x14,297,2)
            e=g.reference(expected_initial,case);calls=[(g.ENTRY,(case.base,))]+e['calls'];machines=[]
            for body in(self.truth,self.words,self.compact):
                code=g.helpers(self.rom,case);code.update(zip(range(g.ENTRY,g.ENTRY+428,4),body));v=g.Oracle(words,initial,case,entry=g.CALLER,connected=code).run();self.assertEqual((g.public(v.memory,case),v.calls),(e['observed'],calls));machines.append(v)
            for v in machines[1:]:self.assertEqual(g.state(machines[0]),g.state(v))
            seen.update(machines[0].visits);count+=1
        self.receipts['caller']=dict(direct_JALs=0,entry_pointers=1,interior_pointers=0,callback_slot=2,cases_per_body=count,retained_dispatcher_words=41,executed_dispatcher_words=len(seen&set(range(g.CALLER,g.CALLER+164,4))),production_dispatcher_exact=True,one_resource_argument=True,active_lifetime_and_timer_gates=True)
    def test_05_fired_access_prefixes_and_saved_lifetimes(self):
        cuts=delays=0
        for case in(g.Case(),g.Case(scroll=g.bits(-8192.5),sine=g.bits(200.0)),g.Case(connected=1,phaseValue=g.bits(-20.0),mutation=2),g.Case(alias=1,scroll=g.bits(0.125))):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words,self.compact):
                    v=g.Oracle(body,g.fixture(case),case,connected=g.helpers(self.rom,case));v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                for v in machines[1:]:self.assertEqual(g.state(machines[0]),g.state(v))
                cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,all_three_bodies_private_state_equal=True,S0_RA_and_stack_lifetime_checked=True,no_FCSR_or_hardware_exception_claim=True)
    def test_06_native32_float_fixtures_and_effective_negatives(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));return subprocess.run([str(exe)]).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn 0;\n}',wrong_phase=s.replace('payload[2] +=','payload[3] +='),missing_phase_wrap=s.replace('payload[2] = func_15144B68(payload[2]);',';'),wrong_sine=s.replace('sinf(payload[2])','sinf(payload[3])'),wrong_delta=s.replace('D_800A4A90 *','D_800A4A94 *'),wrong_upper=s.replace('> 4096.0f','>= 4096.0f'),wrong_lower=s.replace('< 0.0f','<= 0.0f'),wrong_bound=s.replace('4096.0f','2048.0f'),wrong_result=s.replace('return 1;','return 0;'),reload_payload=s.replace('    payload[3] +=','    payload = (f32 *)(resource + *(u32 *)(resource + 0x50) + 0xF8);\n    payload[3] +='));rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(native_cases()),pointer32_float32_assertions=True,finite_disjoint_arenas=True,UBSan_traps=True,sine_controlled=True,semantic_negatives=rejected,global_output_aliases_wrapped_addresses_and_private_state_guest_only=True)
    def test_07_independent_GNU_rebases_and_complete_image(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        moved=dict(g.symbols());base=0x81237FF0
        for i,name in enumerate(('D_800A4A84','D_800A4A88','D_800A4A8C','D_800A4A90','D_800A4A94')):moved[name]=base+4*i
        moved.update(D_800BE9A4=0x8234E9A4,func_15144B68=0x17544B68,sinf=0x17547D60);links=0
        for entry,symbols in((g.ENTRY,g.symbols()),(0x17407F50,moved)):
            lines=['.set noreorder','.set noat','.text','.globl func_1513BEB0','func_1513BEB0:']
            for i,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.nr.get(i*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    elif word>>26==49:line='lwc1 $f%d, %%lo(%s)($%d)'%(rt,name,rs)
                    else:self.assertEqual(word>>26,9);line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                lines.append(line)
            p=self.out/('rebase-'+str(links));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>107I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.nr,symbols));links+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),361)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,428),2809568,2809587,3087637,2870180):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=361,exclusions=0,closed_symbol_string_pair_swaps=1,named_definitions_preserved=True,independent_links=links,bindings=20,signed_LO_carry=True,corruptions_rejected=6)

if __name__=='__main__':unittest.main()
