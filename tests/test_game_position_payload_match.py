"""Exact owner, independent packet bytes, original callbacks/callers and image."""
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_position_payload_candidates as c
from tools.experiments import game_position_payload_match as m
from tools.tests import game_position_payload_oracle as g
from tools.tests.game_position_payload_native import harness,cases as native_cases
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class PositionPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>69I',cls.rom,0x1FE410));raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);m.derive(raw,refs);cls.words=m.bound_blob(raw,refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case):
        initial=g.fixture(case);expected=g.reference(initial,case);machines=[]
        for words in(self.truth,self.words):
            machine=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case)).run();self.assertEqual((g.public(machine.memory,case),machine.calls,machine.packets),(expected['memory'],expected['calls'],expected['packets']),case);machines.append(machine)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case);return machines
    def test_01_complete_owner_direct_words_and_closed_controls(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(120,6052,213,0));self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(51,51,0,8));self.assertEqual((t['diagnostics']['before'],t['diagnostics']['after']),(8,6));self.assertEqual(self.truth,self.words)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0])
        for offset in(0,20,60,64,92,196,248,272):
            bad=bytearray(raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        bad=dict(refs);bad[40]=[('R_MIPS_LO16','D_8008FC34')]
        with self.assertRaises(ValueError):m.derive(raw,bad)
        self.receipts['owner']=q
    def test_02_callback_lifetimes_full_packets_and_guest_aliases(self):
        count=0;seen=set()
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+276,4))-seen,set())
        self.receipts['guest']=dict(cases_per_body=count,covered_words=69,selector_and_identity_bytes=256,partial_callback_masks=8,overlap_layouts=5,all_56_packet_bytes=True,full_machine_and_access_trace=True,private_frame_and_argument_home_mutations_guest_only=True,stack_destination_aliases_bounded_factory_only=True)
    def test_03_original_callbacks_factory_zero_and_copy(self):
        descriptors=((g.CALLBACKS[0],0x1FE524,12),(g.CALLBACKS[1],0x1FE554,8),(g.CALLBACKS[2],0x1FE574,8),(g.COMMON,0x1FE594,21),(g.CREATE,0x1765E0,49),(g.ZERO,0x226F0,40),(g.COPY,0x22EC0,11));before=self.q['predecessor_elf'].read_bytes();seen={e:set()for e,p,n in descriptors};count=0
        for e,p,n in descriptors:at=m.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4],self.rom[p:p+n*4])
        at=m.elf_slot_offset(before,g.TABLE,12);self.assertEqual(struct.unpack_from('>3I',before,at),g.CALLBACKS);at=m.elf_slot_offset(before,g.DEFAULT,12);self.assertEqual(before[at:at+12],bytes(12))
        for connected,selector,matrix,vector,outcome in itertools.product(range(1,8),range(3),(0,1),range(3),(0,1)):
            case=g.Case(connected=connected,selector=selector,matrix=matrix,vector=vector,outcome=outcome);machine=self.compare(case)[0]
            for e,p,n in descriptors:seen[e].update(pc for pc in machine.visits if e<=pc<e+n*4)
            count+=1
        for alias in(1,3):self.compare(g.Case(connected=7,selector=0,alias=alias));count+=1
        self.assertEqual(len(seen[g.CALLBACKS[0]]),12);self.assertEqual(len(seen[g.CALLBACKS[1]]),8);self.assertEqual(len(seen[g.CALLBACKS[2]]),8);self.assertEqual(len(seen[g.COMMON]),21);self.assertEqual(len(seen[g.CREATE]),47);self.assertEqual(len(seen[g.COPY]),11)
        self.receipts['helpers']=dict(cases_per_body=count,retained_words=149,covered_words={hex(e):len(v)for e,v in seen.items()},production_table_and_default_checked=True,allocation_and_transform_bounded=True,original_factory_header_and_16_byte_clear=True,no_new_helper_credit=True)
    def test_04_complete_original_callers_and_three_call_sites(self):
        jal=0x0C000000|(g.ENTRY>>2&0x3FFFFFF);calls=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:calls.append(i*4)
            if g.ENTRY<=w<g.ENTRY+276:pointers.append((i*4,w))
        self.assertEqual(calls,[0x17B11C,0x17C660,0x17C674]);self.assertEqual(pointers,[]);count=0;coverage={};before=self.q['predecessor_elf'].read_bytes()
        for caller,rom,n in((0x1514DC5C,0x17B10C,10),(0x1514F194,0x17C644,93)):
            at=m.elf_slot_offset(before,caller,n*4)
            if n==10:self.assertEqual(before[at:at+n*4],self.rom[rom:rom+n*4])
            else:self.assertEqual(before[at:at+n*4],bytes.fromhex('0000102503e0000800000000')+bytes(n*4-12))
            words=list(struct.unpack_from('>%dI'%n,self.rom,rom));seen=set()
            for result,outcome,mutation,flag,link,phase in itertools.product((0,1),(0,1),(0,3,4,8,16,31),(0,1),(0,1),(0,8)):
                case=g.Case(result=result,outcome=outcome,mutation=mutation,flag=flag,link=link,phase=phase);initial=g.fixture(case);expected=g.caller_reference(initial,case,caller);machines=[]
                for body in(self.truth,self.words):
                    code=dict(zip(range(g.ENTRY,g.ENTRY+276,4),body));machine=g.Oracle(words,initial,case,entry=caller,connected=code).run();self.assertEqual((g.public(machine.memory,case),machine.calls,machine.packets),(expected['memory'],expected['calls'],expected['packets']),case);machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(p for p in machines[0].visits if caller<=p<caller+n*4);count+=1
            self.assertEqual(len(seen),n);coverage[hex(caller)]=len(seen)
        self.receipts['callers']=dict(cases=count,retained_words=103,coverage=coverage,direct_sites=3,raw_pointers=0,results_ignored=True,parent_services_bounded=True,production_larger_caller_placeholder_unchanged=True,retail_larger_caller_executed=True)
    def test_05_fired_fault_prefixes_private_bytes_and_delay_slots(self):
        count=delays=0
        for case in(g.Case(),g.Case(result=0,mutation=31),g.Case(outcome=0),g.Case(alias=5)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for words in(self.truth,self.words):
                    machine=g.Oracle(words,g.fixture(case),case);machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));count+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=count,delay_cuts=delays,full_private_memory_registers_PC_and_access_prefix=True)
    def test_06_native32_SDK_fields_and_effective_compiled_negatives(self):
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native'+opt+'.c');path.write_text(harness(),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        s=c.SELECTED
        late=s.replace('    payload.ownerId = owner[0x3B];\n','').replace('    payload.first =','    payload.ownerId = owner[0x3B];\n    payload.first =')
        stale=s.replace('    PositionPayload151D0F60 payload;','    PositionPayload151D0F60 payload;\n    PositionVector151D0F60 snapshot = D_800A5480;').replace('= D_800A5480;','= snapshot;').replace('snapshot = snapshot;','snapshot = D_800A5480;')
        variants=dict(stub=s[:s.index('{')+1]+'\n}',late_identity=late,stale_default=stale,always_default=s.replace('    payload.first =','    payload.second = D_800A5480;\n    payload.first ='),short_copy=s.replace('memcpy(created + 0x28, &payload, 56)','memcpy(created + 0x28, &payload, 52)'),wrong_kind=s.replace('0, 72, 56','0, 71, 56'));rejected={}
        for label,body in variants.items():
            path=self.out/('negative-'+label+'.c');path.write_text(harness(body),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command('-O2'),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),actual_callback_C_checks_per_executable=18,actual_callback_table_types_checked=True,SDK_layout_assertions=True,independent_little_endian_byte_model=True,UBSan_traps=True,semantic_negatives=rejected,implicit_padding_excluded_explicitly=True,partial_uninitialized_outputs_and_home_poison_guest_only=True)
    def test_07_independent_GNU_links_and_whole_image_corruptions(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);count=0
        for entry,s in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(D_8008FC30=0x80208000,D_800A5480=0x80218004,func_15149130=0x17517FFC,memcpy=0x10018000))):
            lines=['.set noreorder','.text','.globl func_151D0F60','func_151D0F60:']
            for i,w in enumerate(struct.unpack('>69I',raw)):
                if i*4 not in refs:lines.append('.word 0x%08X'%w);continue
                kind,name=refs[i*4][0];lines.append('jal '+name if kind=='R_MIPS_26'else'lui $%d,%%hi(%s)'%(w>>16&31,name)if kind=='R_MIPS_HI16'else('lw $%d,%%lo(%s)($%d)'%(w>>16&31,name,w>>21&31)if w>>26==35 else'addiu $%d,$%d,%%lo(%s)'%(w>>16&31,w>>21&31,name)))
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(name,value)for name,value in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(raw,refs,s));count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),213)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,276),0x2B7B6C,0x319C5B):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=213,exclusions=0,metadata_permutations=0,independent_links=2,corruptions_rejected=4)
if __name__=='__main__':unittest.main()
