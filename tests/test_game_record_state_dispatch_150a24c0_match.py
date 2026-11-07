"""Guard derivation, independent byte semantics, original windows and literal image."""
from dataclasses import replace
import itertools,json,re,struct,subprocess,unittest
from tools.experiments import game_record_state_dispatch_150a24c0_candidates as c
from tools.experiments import game_record_state_dispatch_150a24c0_match as m
from tools.tests import game_record_state_dispatch_150a24c0_oracle as g
from tools.tests.game_record_state_dispatch_150a24c0_native import harness,cases as native_cases
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class RecordStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes()
        cls.truth=list(struct.unpack_from('>69I',cls.rom,0xCF970));raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);normal,refs=m.derive(raw,refs)
        cls.raw=m.bound_blob(raw,refs,g.symbols());cls.words=m.bound_blob(normal,refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case):
        initial=g.fixture(case);expected=g.reference(initial,case);machines=[]
        for words in(self.truth,self.words,self.raw):
            machine=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case)).run()
            self.assertEqual((g.observed(machine.memory,case),machine.calls),(expected['observed'],expected['calls']),case);machines.append(machine)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case)
        self.assertEqual(g.state(machines[0],False),g.state(machines[2],False),case);return machines
    def test_01_complete_owner_closed_register_controls(self):
        q=self.q['report'];t=q['targets'][0]
        self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(125,6052,210,0))
        self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(27,27,25,1))
        self.assertEqual(t['diagnostics'],dict(before=0,after=0,new=[]));self.assertEqual(self.truth,self.words)
        self.assertEqual(sum(x!=y for x,y in zip(self.raw,self.truth)),25)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0])
        for offset in(0,48,68,156,176,212,232,272):
            bad=bytearray(raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        with self.assertRaises(ValueError):m.derive(raw,{156:[('R_MIPS_26','func_15183294')]})
        before=(self.out/'match-frozen'/m.GUARDS).read_bytes()
        self.assertEqual(m.guard_manifest(before)[:len(before)],before)
        self.receipts['owner']=q
    def test_02_byte_views_lifetimes_full_selectors_aliases(self):
        count=0;seen=set()
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+276,4))-seen,{g.ENTRY+56*4})
        self.receipts['guest']=dict(cases_per_body=count,bodies=3,covered_words=68,retained_words=69,unreachable_word=56,all_phase_and_mode_bytes=True,full_selector_width=True,record_aliases=2,null_record_exact_255=True,guarded_full_machine=True,raw_full_memory_trace_PC_and_callee_saved=True,raw_caller_saved_register_identity_not_claimed=True)
    def test_03_retained_original_service_all_busy_fast_path(self):
        before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.SERVICE,1568)
        self.assertEqual(before[at:at+1568],bytes.fromhex('0000102503e0000800000000')+bytes(1556))
        asm=(self.root/'conker/asm/1B0740.s').read_text();asm=asm[asm.index('glabel func_15183290'):asm.index('endlabel func_15183290')]
        retained=[int(w,16)for w in re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/',asm)]
        self.assertEqual(retained,list(struct.unpack_from('>392I',self.rom,0x1B0740)));count=0;seen=set()
        for alias,phase,mode in itertools.product((0,1,2),(0,8),(2,9)):
            case=g.Case(connected=1,alias=alias,phase=phase,mode=mode);machine=self.compare(case)[0];seen.update(p for p in machine.visits if g.SERVICE<=p<g.SERVICE+1568);count+=1
        self.assertEqual(len(seen),27)
        self.receipts['service']=dict(cases_per_body=count,retained_words=392,covered_busy_path_words=27,actual_ingress_homes_and_busy_loop=True,remaining_service_bounded=True,production_placeholder_unchanged=True,new_credit=0,fourth_byte_abi_inferred_from_original_LBU_home=True)
    def test_04_single_original_caller_window_and_input_census(self):
        jal=0x0C000000|(g.ENTRY>>2&0x3FFFFFF);calls=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:calls.append(i*4)
            if g.ENTRY<=w<g.ENTRY+276:pointers.append((i*4,w))
        self.assertEqual(calls,[0xCEFF8]);self.assertEqual(pointers,[]);count=0;seen=set()
        for alias,selector,low,mode,offset in itertools.product((0,1,2),(255,-1,0x100FF),(0,1,255),(2,9),(0,52,104,-52)):
            case=g.Case(alias=alias,selector=selector,phase_byte=low,mode=mode,mutation=4)
            machines=[]
            for body in(self.truth,self.words,self.raw):
                machine,expected=g.caller_machine(self.rom,body,case,offset)
                with self.assertRaises(g.WindowBoundary):machine.run()
                self.assertEqual((g.observed(machine.memory,case),machine.calls),(expected['observed'],expected['calls']))
                self.assertEqual(machine.r[16],g.u32(g.address(case)-offset));self.assertEqual(machine.r[29],g.STACK+case.phase);machines.append(machine)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(g.state(machines[0],False),g.state(machines[2],False));seen.update(p for p in machines[0].visits if g.WINDOW<=p<g.WINDOW+20);count+=1
        self.assertEqual(len(seen),5)
        self.receipts['caller']=dict(cases_per_body=count,retained_window_words=5,covered_window_words=5,direct_sites=1,raw_entry_or_interior_pointers=0,return_ignored=True,whole_parent_not_qualified=True,production_parent_placeholder_unchanged=True)
    def test_05_fired_access_prefixes_frame_and_branch_delays(self):
        count=delays=0
        for case in(g.Case(),g.Case(result=-1),g.Case(phase_byte=1),g.Case(mode=9,mutation=2),g.Case(alias=1,mutation=14),g.Case(alias=2),g.Case(alias=3,selector=255),g.Case(connected=1,alias=1)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for words in(self.truth,self.words,self.raw):
                    machine=g.Oracle(words,g.fixture(case),case,connected=g.helpers(self.rom,case));machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(g.state(machines[0],False),g.state(machines[2],False));count+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=count,delay_cuts=delays,guarded_all_registers_private_memory_PC_trace=True,raw_memory_PC_trace_callee_saved=True,portable_C_fault_semantics_not_claimed=True)
    def test_06_native32_byte_model_effective_compiled_negatives(self):
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native'+opt+'.c');path.write_text(harness(),encoding='utf-8');exe=path.with_suffix('.elf')
            p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        s=c.SELECTED
        stale_mode=s.replace('    u32 state;','    u32 state;\n    u8 oldMode = record->field17;').replace('result != -1 && record->field17 != 9','result != -1 && oldMode != 9')
        variants=dict(stub=s[:s.index('{')+1]+'\n}',selector_byte=s.replace('selector != 255','(u8)selector != 255'),floor_one=s.replace('if (result < 2) result = 2;','if (result < 2) result = 1;'),stale_state=s.replace('((u32)record->field1C & 0xFFFF0000)','(state & 0xFFFF0000)'),stale_mode=stale_mode,narrow_result=s.replace('(u32)result << 8','(u32)(u8)result << 8'),narrow_Y=s.replace('secondOrigin + (parameter1D << 4)','(s16)(secondOrigin + (parameter1D << 4))'),wrong_property=s.replace('property & 255','property & 127'));rejected={}
        for label,body in variants.items():
            path=self.out/('negative-'+label+'.c');path.write_text(harness(body),encoding='utf-8');exe=path.with_suffix('.elf')
            p=subprocess.run([*native_command('-O2'),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_layout_assertions=True,independent_little_endian_coherent_bytes=True,UBSan_traps=True,semantic_negatives=rejected,guest_stack_aliases_excluded=True)
    def test_07_independent_GNU_links_and_literal_image_corruptions(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);normal,refs=m.derive(raw,refs);count=0
        for entry,service in((g.ENTRY,g.SERVICE),(0x1740FFF0,0x17517FFC)):
            lines=['.set noreorder','.text','.globl func_150A24C0','func_150A24C0:']
            for i,w in enumerate(struct.unpack('>69I',normal)):lines.append('jal func_15183290'if i*4==156 else'.word 0x%08X'%w)
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'--defsym=func_15183290=0x%X'%service,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(normal,refs,dict(func_15183290=service)));count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),210)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,276),0x2B7B6C,0x319C5B):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=210,exclusions=0,metadata_permutations=0,independent_links=2,corruptions_rejected=4)
if __name__=='__main__':unittest.main()
