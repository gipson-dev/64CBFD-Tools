"""Complete reset owner, live aliases, helpers/callers, SDK and image gates."""
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_active_entry_reset_candidates as c
from tools.experiments import game_active_entry_reset_match as m
from tools.tests import game_active_entry_reset_oracle as g
from tools.tests.game_active_entry_reset_native import harness,cases as native_cases
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class ActiveEntryResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>72I',cls.rom,0x1BE8B0));raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);m.derive(raw,refs);cls.words=m.bound_blob(raw,refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case):
        initial=g.fixture(case);expected=g.reference(initial,case);models=[]
        for words in(self.truth,self.words):
            machine=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case)).run()
            self.assertEqual((g.public(machine.memory,case),machine.calls),(expected['memory'],expected['calls']),case);models.append(machine)
        self.assertEqual(g.state(models[0]),g.state(models[1]),case);return models
    def test_01_complete_owner_no_guards_and_controls(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(115,6052,219,0));self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(60,60,0,5));self.assertEqual((t['diagnostics']['before'],t['diagnostics']['after']),(4,4));self.assertEqual(self.truth,self.words)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0])
        for offset in(0,44,84,176,204,244,284):
            bad=bytearray(raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        bad=dict(refs);bad[48]=[('R_MIPS_HI16','D_800A9D44')]
        with self.assertRaises(ValueError):m.derive(raw,bad)
        self.receipts['owner']=q
    def test_02_all_selectors_signed_modulo_live_slots_and_overlaps(self):
        count=0;seen=set()
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+288,4))-seen,{g.ENTRY+51*4})
        self.receipts['guest']=dict(cases_per_body=count,covered_words=71,unreached_break_word=51,selector_bytes=256,overlap_layouts=5,full_machine_and_trace_equal=True,nonzero_divisors_only=True,guest_home_redirect=True,timer_overlapping_entry_pointer=True,zero_divisor_hardware_and_portable_C_effects_not_claimed=True)
    def test_03_original_configuration_integer_RNG_and_zero(self):
        descriptors=((g.CONFIG,0x16CB30,16),(g.RANDOM,0xDAED0,18),(g.ZERO,0x226F0,40));before=self.q['predecessor_elf'].read_bytes();seen={e:set()for e,p,n in descriptors};count=0
        for e,p,n in descriptors:at=m.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4],self.rom[p:p+n*4])
        for connected,seed,pattern in itertools.product(range(1,8),g.SEEDS[:3],(1,2,4)):
            case=g.Case(connected=connected,seed=seed,pattern=pattern);machine=self.compare(case)[0]
            for e,p,n in descriptors:seen[e].update(pc for pc in machine.visits if e<=pc<e+n*4)
            count+=1
        self.assertEqual(len(seen[g.CONFIG]),16);self.assertEqual(len(seen[g.RANDOM]),18);self.assertGreater(len(seen[g.ZERO]),20)
        self.receipts['helpers']=dict(cases_per_body=count,retained_words=74,covered_words={hex(e):len(v)for e,v in seen.items()},exact_production_helper_bytes=True,full_720_byte_clear=True,remaining_providers_bounded=True)
    def test_04_two_complete_original_callers_and_saved_arguments(self):
        before=self.q['predecessor_elf'].read_bytes();count=0;coverage={}
        for caller,rom,cleanup in((0x15190840,0x1BDCF0,0x15169804),(0x1519086C,0x1BDD1C,0x15169824)):
            at=m.elf_slot_offset(before,caller,44);self.assertEqual(before[at:at+44],self.rom[rom:rom+44]);words=list(struct.unpack_from('>11I',self.rom,rom));seen=set()
            for pattern,mutation,phase in itertools.product((0,1,2,5),(0,4,8,63),(0,8)):
                case=g.Case(pattern=pattern,mutation=mutation,phase=phase);initial=g.fixture(case);expected=g.reference(initial,case,home=g.STACK+phase-24);owner=g.addresses(case)[0];g.wr(expected['memory'],g.MARK,owner);calls=[(g.ENTRY,(owner,)),*expected['calls'],(cleanup,(owner,))];models=[]
                for body in(self.truth,self.words):
                    code=dict(zip(range(g.ENTRY,g.ENTRY+288,4),body));machine=g.Oracle(words,initial,case,entry=caller,connected=code).run();self.assertEqual((g.public(machine.memory,case),machine.calls),(expected['memory'],calls),case);models.append(machine)
                self.assertEqual(g.state(models[0]),g.state(models[1]));seen.update(p for p in models[0].visits if caller<=p<caller+44);count+=1
            self.assertEqual(len(seen),11);coverage[hex(caller)]=len(seen)
        self.receipts['callers']=dict(cases=count,retained_words=22,coverage=coverage,one_argument_void_target=True,original_wrapper_argument_retained=True,post_target_services_bounded=True)
    def test_05_fired_access_prefixes_and_private_state(self):
        count=delays=0
        for case in(g.Case(pattern=0),g.Case(mutation=63),g.Case(alias=5,base=0,span=0,random=0)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for words in(self.truth,self.words):
                    machine=g.Oracle(words,g.fixture(case),case);machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));count+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=count,delay_cuts=delays,full_private_state_registers_PC_and_access_prefix=True,no_zero_divisor_trap_claim=True)
    def test_06_native32_SDK_and_compiled_negatives(self):
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native'+opt+'.c');path.write_text(harness(),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        selected=c.SELECTED
        stale=selected.replace('    u8 *state;','    u8 *state;\n    u8 *capturedActor;').replace('            func_1513F680','            capturedActor = entry->actor;\n            func_1513F680').replace('*(s16 *)(entry->actor + 0x1C)','*(s16 *)(capturedActor + 0x1C)').replace('*(u32 *)(entry->actor + 0x58)','*(u32 *)(capturedActor + 0x58)')
        early=selected.replace('    u8 *state;','    u8 *state;\n    u32 divisor;\n    s32 base;').replace('            func_1513F680','            divisor = preset->range + 1U;\n            base = preset->base;\n            func_1513F680').replace('random % (preset->range + 1U) + preset->base','random % divisor + base')
        clear=selected.replace('    u8 *state;','    u8 *state;\n    ActiveResetEntry15191400 *capturedList;').replace('    entry = owner->entries;','    entry = owner->entries;\n    capturedList = entry;').replace('bzero(owner->entries,','bzero(capturedList,')
        variants=dict(stub=selected[:selected.index('{')+1]+'\n}',signed_modulo=selected.replace('random % (preset->range + 1U)','(s32)random % (preset->range + 1)'),stale_actor=stale,early_preset=early,short_scan=selected.replace('index < 60','index < 59'),stale_clear=clear);rejected={}
        for label,body in variants.items():
            path=self.out/('negative-'+label+'.c');path.write_text(harness(body),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command('-O2'),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_layout_assertions=True,independent_little_endian_byte_model=True,UBSan_traps=True,semantic_negatives=rejected,home_redirection_and_exotic_aliases_guest_only=True)
    def test_07_independent_GNU_rebases_and_image_corruptions(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);count=0
        for entry,s in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(bzero=0x10008004,func_1513F680=0x17518004,func_150ADA20=0x17517FFC,D_800A9D40=0x80208000))):
            lines=['.set noreorder','.text','.globl func_15191400','func_15191400:']
            for i,w in enumerate(struct.unpack('>72I',raw)):
                if i*4 not in refs:lines.append('.word 0x%08X'%w);continue
                kind,name=refs[i*4][0];lines.append('jal '+name if kind=='R_MIPS_26'else'lui $%d,%%hi(%s)'%(w>>16&31,name)if kind=='R_MIPS_HI16'else'addiu $%d,$%d,%%lo(%s)'%(w>>16&31,w>>21&31,name))
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(name,value)for name,value in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>72I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(raw,refs,s));count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),219)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,288),0x2DE86C,0x319C5B):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=219,exclusions=0,closed_metadata_swaps=1,independent_links=2,corruptions_rejected=4)
if __name__=='__main__':unittest.main()
