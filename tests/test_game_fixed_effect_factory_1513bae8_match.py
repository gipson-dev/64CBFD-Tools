"""Full owner, literal image, independent packets and original caller/creator."""
from dataclasses import replace
import itertools,json,re,struct,subprocess,unittest
from tools.experiments import game_fixed_effect_factory_1513bae8_candidates as c
from tools.experiments import game_fixed_effect_factory_1513bae8_match as m
from tools.tests import game_fixed_effect_factory_1513bae8_oracle as g
from tools.tests.game_fixed_effect_factory_1513bae8_native import harness,cases as native_cases
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
class FixedEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>69I',cls.rom,0x168F98))
        raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);normal,refs=m.derive(raw,refs);cls.raw=m.bound_blob(raw,refs,g.symbols());cls.words=m.bound_blob(normal,refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case):
        initial=g.fixture(case);expected=g.reference(initial,case);machines=[]
        for words in(self.truth,self.words,self.raw):
            machine=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case)).run()
            self.assertEqual((g.observe(machine.memory,case),machine.calls,machine.packets,machine.r[2]),(expected['observed'],expected['calls'],expected['packets'],expected['value']),case);machines.append(machine)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case);self.assertEqual(g.state(machines[0]),g.state(machines[2]),case);return machines
    def test_01_complete_owner_guard_and_closed_metadata(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(136,6052,212,0))
        self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(12,12,1,3));self.assertEqual(t['diagnostics'],dict(before=4,after=4,new=[]));self.assertEqual(self.truth,self.words);self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),1)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0])
        for offset in(0,24,68,176,212,240,244,272):
            bad=bytearray(raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        with self.assertRaises(ValueError):m.derive(raw,{**refs,244:[('R_MIPS_26','func_10022EC4')]})
        old=self.out/'match-predecessor-0.o';new=self.q['qualified_compacts'][0];blob=new.read_bytes()
        for section in('.reginfo','.options'):
            at=m.dependent_sections(blob)[section][0][4];bad=bytearray(blob);bad[at+len(m.dependent_sections(blob)[section][1])-1]^=1;path=self.out/('bad'+section+'.o');path.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,path)
        self.receipts['owner']=q
    def test_02_descriptor_payload_handle_and_guest_aliases(self):
        seen=set();count=0
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+276,4))-seen,set())
        self.receipts['guest']=dict(cases_per_body=count,bodies=3,covered_words=69,all_60_seeded_descriptor_bytes=True,initialized_descriptor_bytes=len(g.DEFINED),implicit_descriptor_padding_bytes=len(g.PADDING),live_20_byte_payload=True,returned_release_handle_preserved=True,three_stack_copy_aliases=True,private_return_home_mutations_guest_only=True,full_machine_registers_memory_PC_trace=True)
    def test_03_original_creator_and_copy_windows(self):
        before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CREATE,440);self.assertEqual(before[at:at+440],bytes.fromhex('0000102503e0000800000000')+bytes(428))
        asm=(self.root/'conker/asm/nonmatchings/game_168A90/func_1513B5E0.s').read_text();self.assertEqual([int(w,16)for w in re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/',asm)],list(struct.unpack_from('>110I',self.rom,0x168A90)))
        at=m.elf_slot_offset(before,g.COPY,44);self.assertEqual(before[at:at+44],self.rom[0x22EC0:0x22EEC])
        seen={g.CREATE:set(),g.COPY:set()};count=0
        for connected,outcome,views,extent in itertools.product((1,3),(0,1),(0,1),(64,1120,2240)):
            if views==1 and extent==2240:continue
            case=g.Case(connected=connected,outcome=outcome,views=views,extent=extent);machine=self.compare(case)[0]
            for entry,n in((g.CREATE,110),(g.COPY,11)):seen[entry].update(pc for pc in machine.visits if entry<=pc<entry+4*n)
            count+=1
        self.assertEqual(len(seen[g.CREATE]),110);self.assertEqual(len(seen[g.COPY]),11)
        self.receipts['helpers']=dict(cases_per_body=count,retained_creator_words=110,creator_covered_words=110,retained_copy_words=11,copy_covered_words=11,descriptor_resource_copies_and_final_payload_connected=True,allocator_resource_resolution_release_and_tail_services_bounded=True,production_creator_placeholder_unchanged=True,creator_new_credit=0)
    def test_04_complete_original_caller_and_census(self):
        jal=0x0C000000|(g.ENTRY>>2&0x3FFFFFF);calls=[];pointers=[]
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if w==jal:calls.append(i*4)
            if g.ENTRY<=w<g.ENTRY+276:pointers.append((i*4,w))
        self.assertEqual(calls,[0x10D7D4]);self.assertEqual(pointers,[]);count=0;seen=set()
        caller=list(struct.unpack_from('>18I',self.rom,0x10D7B0));before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.CALLER,72);production_exact=before[at:at+72]==self.rom[0x10D7B0:0x10D7F8]
        for flag,outcome,offset,mutation,phase in itertools.product((0,1,255),(0,1),(0x1180,0),(0,3,11),(0,8)):
            case=g.Case(flag=flag,outcome=outcome,offset=offset,mutation=mutation,phase=phase);initial=g.fixture(case);expected=g.reference(initial,case,home=g.STACK+phase-24)if not flag else None;machines=[]
            for body in(self.truth,self.words,self.raw):
                code=dict(zip(range(g.ENTRY,g.ENTRY+276,4),body));machine=g.Oracle(caller,initial,case,entry=g.CALLER,connected=code).run()
                if flag:self.assertEqual((g.public(machine.memory,case),machine.calls,machine.packets),(g.public(initial,case),[],[]))
                else:
                    expected['memory'][g.FLAG]=1
                    self.assertEqual((g.public(machine.memory,case),machine.calls,machine.packets),(g.public(expected['memory'],case),[(g.SETUP,(6,0)),(g.ENTRY,())]+expected['calls'],expected['packets']))
                machines.append(machine)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(g.state(machines[0]),g.state(machines[2]));seen.update(pc for pc in machines[0].visits if g.CALLER<=pc<g.CALLER+72);count+=1
        self.assertEqual(len(seen),18)
        self.receipts['caller']=dict(cases_per_body=count,retained_words=18,covered_words=18,direct_sites=1,entry_or_interior_pointers=0,result_ignored=True,production_caller_exact=production_exact,setup_service_bounded=True)
    def test_05_fired_fault_prefixes_private_frames(self):
        count=delays=0
        for case in(g.Case(),g.Case(outcome=0),g.Case(offset=0),g.Case(alias=2,mutation=3,connected=2),g.Case(connected=3,extent=64)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words,self.raw):
                    machine=g.Oracle(body,g.fixture(case),case,connected=g.helpers(self.rom,case));machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));self.assertEqual(g.state(machines[0]),g.state(machines[2]));count+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=count,delay_cuts=delays,all_three_bodies_full_private_registers_PC_and_trace=True)
    def test_06_native32_SDK_and_effective_compiled_negatives(self):
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native'+opt+'.c');path.write_text(harness(),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn 0;\n}',wrong_descriptor=s.replace('descriptor.field30 = 9','descriptor.field30 = 8'),wrong_payload=s.replace('payload.value8 = 0.0f','payload.value8 = 1.0f'),wrong_size_gate=s.replace('!= 0x1180','!= 0x1181'),short_copy=s.replace('&payload, 20','&payload, 16'),clear_released_handle=s.replace('func_1516972C((struct102 *)handle);','func_1516972C((struct102 *)handle);\n            handle = 0;'),omit_release=s.replace('func_1516972C((struct102 *)handle);',';'));rejected={}
        for label,body in variants.items():
            path=self.out/('negative-'+label+'.c');path.write_text(harness(body),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command('-O2'),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_layout_assertions=True,independent_little_endian_defined_descriptor_bytes=True,implicit_padding_excluded=True,UBSan_traps=True,semantic_negatives=rejected,private_payload_return_home_and_stack_aliases_guest_only=True,release_provider_does_not_deallocate_native_fixture=True)
    def test_07_GNU_rebases_and_whole_image_corruption_controls(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);normal,refs=m.derive(raw,refs);count=0
        for entry,symbols in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(func_1513B5E0=0x17517FFC,func_1516972C=0x17528000,memcpy=0x10018000))):
            lines=['.set noreorder','.text','.globl func_1513BAE8','func_1513BAE8:']
            for i,w in enumerate(struct.unpack('>69I',normal)):lines.append('jal '+refs[4*i][0][1]if 4*i in refs else'.word 0x%08X'%w)
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(normal,refs,symbols));count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),212)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,276),0x2B7B6C,0x319C5B):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=212,exclusions=0,metadata_permutations=0,independent_links=2,corruptions_rejected=4)
if __name__=='__main__':unittest.main()
