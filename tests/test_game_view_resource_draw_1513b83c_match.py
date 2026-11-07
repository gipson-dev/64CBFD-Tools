"""Direct SDK resource draw, original callback/dispatch windows and strict image."""
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_view_resource_draw_1513b83c_candidates as c
from tools.experiments import game_view_resource_draw_1513b83c_match as m
from tools.tests import game_view_resource_draw_1513b83c_oracle as g
from tools.tests.game_view_resource_draw_1513b83c_native import harness,cases as native_cases,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

class ViewResourceDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>75I',cls.rom,0x168CEC));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.words=m.bound_blob(*m.derive(cls.raw,cls.refs),g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case):
        initial=g.fixture(case);expected=g.reference(initial,case);machines=[]
        for words in(self.truth,self.words):
            machine=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case)).run();self.assertEqual((g.public(machine.memory,case),machine.calls,machine.r[2]),(expected['observed'],expected['calls'],expected['value']),case);machines.append(machine)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case);return machines
    def test_01_complete_owner_direct_words_and_metadata(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(147,6052,259,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(75,32,0,4,12,12));self.assertEqual(t['diagnostics'],dict(before=4,after=4,new=[]));self.assertEqual(self.truth,self.words)
        for offset in(0,24,40,80,104,112,156,160,292,296):
            bad=bytearray(self.raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        with self.assertRaises(ValueError):m.derive(self.raw,{**self.refs,112:[('R_MIPS_LO16','D_80089C2C')]})
        new=self.q['qualified_compacts'][0];blob=new.read_bytes();old=self.out/'match-predecessor-0.o'
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;path=self.out/('bad'+section+'.o');path.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,path)
        self.assertEqual(m.guard_manifest((self.out/'match-frozen'/m.GUARDS).read_bytes()),(self.root/m.GUARDS).read_bytes());self.receipts['owner']=q
    def test_02_independent_guest_commands_masks_and_aliases(self):
        seen=set();count=0
        for case in g.cases():seen.update(self.compare(case)[0].visits);count+=1
        missing=set(range(g.ENTRY,g.ENTRY+300,4))-seen;self.assertEqual(missing,{g.ENTRY+80})
        self.assertEqual(self.truth[18]>>16,0x1000)
        for i,word in enumerate(self.truth):
            if word>>26 in(1,4,5,6,7,20,21,22,23):
                imm=((word&65535)^32768)-32768;self.assertNotEqual(i+1+imm,20)
        self.receipts['guest']=dict(cases_per_body=count,bodies=2,reachable_words=74,literal_unreachable_word=20,all_75_words_compared=True,all_flag_and_mask_bytes=True,signed_callback_and_view_widths=True,live_callback_mutations=True,command_resource_and_page_aliases_guest_only=True,sparse_full_word_addresses_and_shift_counts_guest_only=True,full_machine_private_RAM_GPR_FPR_HI_LO_PC_and_trace=True)
    def test_03_original_callbacks_and_service_boundary(self):
        seen={1:set(),2:set()};count=0
        for connected,view,page,mutation in itertools.product((1,2),(0,1,31),(0,1),(0,1)):
            if connected==2 and mutation:continue
            case=g.Case(index=0 if connected==1 else 2,connected=connected,view=view,page=page,mutation=mutation)
            machines=self.compare(case);seen[connected].update(machines[0].visits);count+=1
        before=self.q['predecessor_elf'].read_bytes()
        for connected,index,rom,n in((1,0,0x168E18,16),(2,2,0x168F84,5)):
            entry=g.CALLBACKS[index];at=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[at:at+n*4],self.rom[rom:rom+n*4]);self.assertEqual(set(range(entry,entry+n*4,4))-seen[connected],set())
        self.receipts['callbacks']=dict(cases_per_body=count,original_words=[16,5],covered_words=[16,5],production_callbacks_already_exact=True,matrix_service_bounded=True,other_five_callback_bodies_not_claimed=True)
    def test_04_indirect_registry_and_original_dispatch_windows(self):
        direct=[];pointers=[];jal=0x0C000000|((g.ENTRY>>2)&0x03FFFFFF)
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:direct.append(i*4)
            if g.ENTRY<=word<g.ENTRY+300:pointers.append((i*4,word))
        self.assertEqual(direct,[]);self.assertEqual(pointers,[(0x230AD0,g.ENTRY),(0x231080,g.ENTRY)])
        for kind,rom in((0x38,0x230AD0),(0x54,0x231080)):
            address=0x8008B4A8+kind*52+8;self.assertEqual(address,0x8008C010 if kind==0x38 else 0x8008C5C0);self.assertEqual(struct.unpack_from('>I',self.rom,rom)[0],g.ENTRY)
        count=0;coverage={}
        for start,rom,n,end in((0x151677D8,0x194C88,10,0x15167800),(0x15167894,0x194D44,9,0x151678B8)):
            window=struct.unpack_from('>%dI'%n,self.rom,rom);seen=set()
            for kind,view,index,outcome in itertools.product((0x38,0x54),(0,7,0x12340001,0xFFFF),(-1,0,2),(0,1)):
                case=g.Case(view=view,index=index,outcome=outcome);initial=g.fixture(case);registry=0x8008B4A8+kind*52;g.wr(initial,registry+8,g.ENTRY);g.wr(initial,g.SLOT,0xDEADBEEF)
                expectedInitial=dict(initial);g.wr(expectedInitial,g.SLOT,g.rd(initial,g.RESOURCE+8));expected=g.reference(expectedInitial,case);wanted=[(g.ENTRY,(g.cursor(case),g.RESOURCE,g.u32(g.signed16(view))))]+expected['calls'];machines=[]
                for body in(self.truth,self.words):
                    code=dict(zip(range(g.ENTRY,g.ENTRY+300,4),body));code[end]=struct.unpack_from('>I',self.rom,rom+n*4)[0];machine=g.Oracle(window,initial,case,entry=start,connected=code)
                    for reg,value in((16,g.RESOURCE),(17,g.SLOT),(19,g.cursor(case)),(20,registry),(22,g.u32(view))):machine.r[reg]=value
                    machine.code=WindowCode(machine.code,machine);machine.code.ends=(end,)
                    with self.assertRaises(WindowBoundary):machine.run()
                    self.assertEqual((g.public(machine.memory,case),machine.calls,machine.r[2]),(expected['observed'],wanted,expected['value']));machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);count+=1
            self.assertEqual(len(seen&set(range(start,end,4))),n);coverage[hex(start)]=n
        self.receipts['callers']=dict(direct_JALs=0,entry_pointers=2,interior_pointers=0,resource_kinds=[56,84],connected_window_cases_per_body=count,window_words=coverage,signed16_view_ABI=True,original_delay_slot_next_link_store=True,full_348_word_dispatcher_not_claimed=True,portable_native_view_shift_contract='0..31')
    def test_05_fired_fault_prefixes_and_private_homes(self):
        cuts=delays=0
        for case in(g.Case(),g.Case(flags=2,mask=0,index=0),g.Case(index=0,outcome=0),g.Case(index=0,mutation=1),g.Case(index=0,mutation=3),g.Case(alias=1),g.Case(index=0,connected=1)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    machine=g.Oracle(body,g.fixture(case),case,connected=g.helpers(self.rom,case));machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,full_private_memory_registers_HI_LO_PC_and_trace=True,portable_C_fault_semantics_not_claimed=True)
    def test_06_native32_SDK_and_effective_compiled_negatives(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));return subprocess.run([str(exe)]).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn NULL;\n}',wrong_flag=s.replace('resource[0x10] & 2','resource[0x10] & 1'),wrong_mask=s.replace('1U << view','1U << (view & 7)'),wrong_callback=s.replace('D_80089C28[callbackIndex]','D_80089C28[0]'),wrong_callback_argument=s.replace('(resource, view)','(resource, view + 1)'),wrong_callback_gate=s.replace('](resource, view) == 0','](resource, view) < 0'),wrong_matrix=s.replace('D_800BE9C0 << 6','D_800BE9C0 << 5'),wrong_buffer=s.replace('(s32)view * 4','(s32)view * 8'),wrong_return=s.replace('    return displayList;\n}','    return displayList + 1;\n}'));rejected={}
        for label,body in variants.items():
            self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_Gfx8_Mtx64_pointer32_assertions=True,fixed_disjoint_resource_and_commands=True,all_three_command_words_and_payloads=True,view_indices_0_to_31_defined_unsigned_shift=True,UBSan_traps=True,semantic_negatives=rejected,aliases_private_homes_sparse_indices_and_wrap_guest_only=True)
    def test_07_GNU_rebases_and_closed_full_image(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        links=0
        for entry,symbols in((g.ENTRY,g.symbols()),(0x1740FFF0,dict(D_80089C28=0x81238004,D_800BE9C0=0x82348002))):
            lines=['.set noreorder','.text','.globl func_1513B83C','func_1513B83C:']
            for i,(word,)in enumerate(struct.iter_unpack('>I',self.raw)):
                refs=self.refs.get(4*i,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    elif word>>26==35:line='lw $%d, %%lo(%s)($%d)'%(rt,name,rs)
                    else:self.assertEqual(word>>26,9);line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                lines.append(line)
            p=self.out/('rebase-'+str(links));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack_from('>75I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.raw,self.refs,symbols));links+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),259)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,300),2749617,2750625,3038115,3038904):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=259,exclusions=0,closed_symbol_and_string_pair_swaps=2,named_definitions_preserved=True,corruptions_rejected=6,independent_rebases=links,indexed_LO16_and_signed_carry=True)
if __name__=='__main__':unittest.main()
