"""Complete owner/image, independent semantics, retained callers and emitted faults."""
from dataclasses import replace
import itertools,json,re,struct,subprocess,unittest
from tools.experiments import game_resource_view_creator_1513b5e0_candidates as c
from tools.experiments import game_resource_view_creator_1513b5e0_match as m
from tools.tests import game_resource_view_creator_1513b5e0_oracle as g
from tools.tests import game_fixed_effect_factory_1513bae8_oracle as caller
from tools.tests.game_resource_view_creator_1513b5e0_native import harness,cases as native_cases,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class ResourceViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>110I',cls.rom,0x168A90))
        raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);normal,nr=m.derive(raw,refs);cls.raw=m.bound_blob(raw,refs,g.symbols());cls.words=m.bound_blob(normal,nr,g.symbols());cls.normal=normal;cls.refs=nr;cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case,connect=False,raw=True):
        initial=g.fixture(case);expected=g.reference(initial,case);machines=[]
        helpers=dict(zip(range(g.COPY,g.COPY+44,4),struct.unpack_from('>11I',self.rom,0x22EC0)))if connect else None
        for words in(self.truth,self.words,*([self.raw]if raw else [])):
            machine=g.Oracle(words,initial,case,helpers).run()
            self.assertEqual((g.public(machine.memory,case),machine.calls,machine.packets,machine.r[2]),(expected['observed'],expected['calls'],expected['packets'],expected['value']),case);machines.append(machine)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case)
        return machines
    def test_01_complete_owner_derived_guards_and_metadata(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(141,6052,338,0))
        self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(12,12,42,8));self.assertEqual(t['diagnostics'],dict(before=4,after=4,new=[]));self.assertEqual(self.truth,self.words)
        self.assertEqual(sum(bool(r[8])for r in m.guard_rows()),5);normal,refs,proof=m.normalization(c.RAW,c.TARGETS[0]['bindings']);self.assertEqual(len(proof['branches']),6)
        raw,refs=m.function_blob(self.q['qualified_compacts'][0])
        for offset in(0,24,68,92,128,188,220,264,324,416):
            bad=bytearray(raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        with self.assertRaises(ValueError):m.derive(raw,{**refs,92:[('R_MIPS_26','func_1502B6C0')]})
        old=self.out/'match-predecessor-0.o';new=self.q['qualified_compacts'][0];blob=new.read_bytes()
        for section in('.reginfo','.options'):
            at=m.dependent_sections(blob)[section][0][4];bad=bytearray(blob);bad[at+len(m.dependent_sections(blob)[section][1])-1]^=1;path=self.out/('bad'+section+'.o');path.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,path)
        self.receipts['owner']=q
        self.receipts['normalization']=dict(raw_words=105,retail_words=110,guards=42,real_stack_transfers=4,late_stride_handoff=1,private_home='SP+0x50',original_memory_and_service_order_preserved=True,all_105_instruction_identities_retained_once=True,closed_GPR_cycles=proof['early_cycle'],late_cycles=proof['late_cycles'],branch_identity_rebases=proof['branches'],raw_private_PC_and_fault_identity_not_claimed=True)
    def test_02_independent_guest_model_and_live_mutations(self):
        seen=set();rawseen=set();count=0
        cases=list(g.cases())
        for byte in range(256):cases.extend((g.Case(mode=0xA5A50000|byte),g.Case(priority=0x5A5A0000|byte)))
        for case in cases:
            machines=self.compare(case);seen.update(machines[0].visits);rawseen.update(machines[2].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+440,4))-seen,set());self.assertEqual(set(range(g.ENTRY,g.ENTRY+420,4))-rawseen,set())
        helpers=set()
        for case in(g.Case(extent=4),g.Case(extent=4,views=2),g.Case(extent=0)):
            for machine in self.compare(case,True):helpers.update(machine.visits)
        self.assertEqual(len(helpers&set(range(g.COPY,g.COPY+44,4))),11)
        for mutation,phase in itertools.product((8,9),(0,8)):self.compare(g.Case(views=1,mutation=mutation,phase=phase),raw=False)
        self.receipts['guest']=dict(cases_per_body=count,bodies=3,retail_words_covered=110,raw_words_covered=105,SDK_copy_cases=3,SDK_copy_words_covered=11,all_mode_and_priority_low_bytes=True,live_count_slot_asset_header_mutations=True,wrapped_handles_resources_guest_only=True,descriptor_output_and_resource_aliases_guest_only=True,private_stride_interventions=4,raw_model_compares_public_memory_calls_packets_and_return=True,normalized_retail_full_machine_states=True)
    def test_03_retained_callers_and_connected_fixed_factory(self):
        target=c.TARGETS[0];jal=0x0C000000|((g.ENTRY>>2)&0x03FFFFFF);sites=[];pointers=[]
        for offset,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:sites.append(offset*4)
            if g.ENTRY<=word<g.ENTRY+440:pointers.append((offset*4,word))
        self.assertEqual(sites,[0x3E328,0x135DDC,0x135F28,0x169048,0x1E74F0]);self.assertEqual(pointers,[])
        asm=(self.root/target['assembly']).read_text();self.assertEqual([int(w,16)for w in re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/',asm)],self.truth)
        child=list(struct.unpack_from('>69I',self.rom,0x168F98));before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,caller.ENTRY,276);self.assertEqual(before[at:at+276],struct.pack('>69I',*child))
        count=0;seen=set()
        for outcome,views,extent in itertools.product((0,1),(0,1),(64,1120,2240)):
            if extent==2240 and views==1:continue
            case=caller.Case(outcome=outcome,views=views,extent=extent,connected=3);initial=caller.fixture(case);expected=caller.reference(initial,case);machines=[]
            for body in(self.truth,self.words,self.raw):
                code=caller.helpers(self.rom,case);code.update(zip(range(g.ENTRY,g.ENTRY+len(body)*4,4),body))
                # Remove the five retained tail words when executing compact C.
                if len(body)==105:
                    for pc in range(g.ENTRY+420,g.ENTRY+440,4):code.pop(pc)
                machine=caller.Oracle(child,initial,case,connected=code).run();self.assertEqual((caller.observe(machine.memory,case),machine.calls,machine.packets,machine.r[2]),(expected['observed'],expected['calls'],expected['packets'],expected['value']),case);machines.append(machine)
            self.assertEqual(caller.state(machines[0]),caller.state(machines[1]));seen.update(machines[0].visits);count+=1
        self.assertEqual(len(set(range(caller.ENTRY,caller.ENTRY+276,4))&seen),69)
        self.receipts['caller']=dict(direct_sites=sites,entry_or_interior_pointers=0,five_preparation_windows_inspected=True,full_other_four_parents_not_claimed=True,connected_fixed_factory_cases_per_body=count,child_words_covered=69,creator_words=110,SDK_copy_words=11,production_child_already_exact=True)
    def test_04_fired_access_fault_prefixes_and_private_frames(self):
        count=delays=0
        for case,connected in((g.Case(),False),(g.Case(outcome=0),False),(g.Case(views=-1),False),(g.Case(mutation=4),False),(g.Case(mutation=8,views=1),False),(g.Case(extent=4,views=1),True)):
            full=self.compare(case,connected,raw=case.mutation!=8)[0]
            helpers=dict(zip(range(g.COPY,g.COPY+44,4),struct.unpack_from('>11I',self.rom,0x22EC0)))if connected else None
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    machine=g.Oracle(body,g.fixture(case),case,helpers);machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]),(case,cut));count+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=count,delay_cuts=delays,retail_and_normalized_full_private_memory_registers_HI_LO_PC_and_trace=True,raw_fault_identity_not_claimed=True,portable_C_fault_semantics_not_claimed=True)
    def test_05_native32_SDK_and_effective_compiled_negatives(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body),encoding='utf-8');exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));return subprocess.run([str(exe)]).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn 0;\n}',wrong_kind=s.replace('? 0x54 : 0x38','? 0x55 : 0x38'),wrong_total=s.replace('(u32)extraSize + bufferBytes + 248','(u32)extraSize + bufferBytes + 244'),short_descriptor=s.replace('descriptor, 60','descriptor, 56'),cached_second_destination=s.replace('memcpy(*(u8 **)(row + 0x68), source, bytes);','memcpy(cursor + bytes, source, bytes);'),wrong_loop_gate=s.replace('index <= D_80082FA0','index <= 0'),lost_handle=s.replace('return (s32)(u32)created;','return 0;'));rejected={}
        for label,body in variants.items():
            self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),all_60_seeded_descriptor_bytes=True,SDK_size_offset_and_pointer_assertions=True,fixed_disjoint_mapped_arena_addresses=True,UBSan_traps=True,compiled_semantic_negatives=rejected,private_stack_alias_wrap_and_FAULT_probes_guest_only=True)
    def test_06_independent_GNU_links_and_symbol_carry_rebases(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        count=0
        for entry,symbols in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(func_1502B6BC=0x17517FFC,D_80082FA0=0x81238004,func_15167A68=0x17528000,memcpy=0x10018000,func_1510CE60=0x1763FFFC))):
            lines=['.set noreorder','.text','.globl func_1513B5E0','func_1513B5E0:']
            for i,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.refs.get(4*i,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0]
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(word>>16&31,name)
                    else:self.assertEqual(kind,'R_MIPS_LO16');line='addiu $%d, $%d, %%lo(%s)'%(word>>16&31,word>>21&31,name)
                lines.append(line)
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack_from('>110I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.refs,symbols));count+=1
        self.receipts['relocations']=dict(independent_links=count,bindings=8,HI_LO_signed_carry_rebase=True,JAL_rebases=True)
    def test_07_literal_full_image_corruption_controls(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),338)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,440),0x2B7B6C,0x319C5B):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=338,exclusions=0,metadata_permutations=0,all_addresses_fixed=6052,protected_Game_bytes=189088,protected_owners=720,corruptions_rejected=4)

if __name__=='__main__':unittest.main()
