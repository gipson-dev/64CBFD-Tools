"""Owner, linked-image, guest/native, caller and effective negative controls."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_reference_command_candidates as c
from tools.experiments import game_reference_command_match as m
from tools.tests import game_reference_command_oracle as g
from tools.tests.game_reference_command_native import harness
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
class ReferenceCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>73I',cls.rom,0x161C7C))
        raw,refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.raw=m.bound_blob(raw,refs,{'func_1516972C':g.FREE});blob,refs=m.derive(raw,refs);cls.words=m.bound_blob(blob,refs,{'func_1516972C':g.FREE});cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;expected=g.reference(initial,case);models=[]
        for words in(self.truth,self.raw,self.words):
            model=g.Oracle(words,initial,case,connected=g.helpers(self.rom,case)).run()
            self.assertEqual((g.public(model.memory,case),model.calls),expected,case);models.append(model)
        self.assertEqual(g.state(models[0]),g.state(models[1]),case);self.assertEqual(g.state(models[0]),g.state(models[2]),case)
        return models
    def test_01_owner_and_guard_fail_closed(self):
        q=self.q['report'];self.assertEqual((q['frozen_inputs'],q['strict_exclusions'],q['functions']),(109,0,6052));t=q['targets'][0]
        self.assertEqual((t['raw_neighbors'],t['padded_neighbors'],t['guards'],t['bindings']),(63,64,1,3));self.assertEqual(t['diagnostics']['new'],[]);self.assertEqual(t['diagnostics']['before'],2)
        self.assertEqual(self.words,self.truth);self.assertEqual([i for i,(a,b)in enumerate(zip(self.raw,self.truth))if a!=b],[64]);self.assertEqual((self.truth[0],self.truth[-3]),(0x27BDFFE8,0x27BD0018))
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);bad=bytearray(raw);bad[259]^=1
        with self.assertRaises(ValueError):m.derive(bytes(bad),refs)
        badrefs=dict(refs);badrefs[72]=[('R_MIPS_26','func_1516979C')]
        with self.assertRaises(ValueError):m.derive(raw,badrefs)
        badguard=bytearray((self.out/'match-frozen'/m.GUARDS).read_bytes());badguard[-1]^=1
        with self.assertRaises(ValueError):m.guard_manifest(bytes(badguard))
        self.receipts['owner']=q
    def test_02_complete_commands_aliases_and_access_order(self):
        count=0;seen=set()
        for case in g.cases():
            models=self.compare(case);seen.update(models[0].visits);count+=1
        unreachable={g.ENTRY+n for n in(0x58,0xA4,0xCC,0xFC)}
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+292,4))-seen,unreachable)
        self.receipts['guest']=dict(cases_per_body=count,implementations=3,commands=256,alias_layouts=8,covered_words=len(seen),unreachable_words=4,full_register_private_memory_and_access_trace_equal=True,void_result=True)
    def test_03_lazy_pointer_gates_and_fired_access_cuts(self):
        self.compare(g.Case(command=22,alias=8,situation=4))
        case=g.Case(command=254);initial=g.fixture(case)
        for a in list(initial):
            if g.RECORD-64<=a<g.RECORD+192 or g.REQUEST<=a<g.REQUEST+32:initial.pop(a)
        self.compare(case,initial)
        cuts=delay=0
        for case in(g.Case(),g.Case(command=17,situation=2),g.Case(command=45,alias=4),g.Case(command=45,situation=1)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                models=[]
                for words in(self.truth,self.raw,self.words):
                    model=g.Oracle(words,g.fixture(case),case);model.cut=cut
                    with self.assertRaises(AccessBoundary):model.run()
                    models.append(model)
                self.assertEqual(g.state(models[0]),g.state(models[1]));self.assertEqual(g.state(models[0]),g.state(models[2]));cuts+=1;delay+=models[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delay,all_three_bodies_identical=True,portable_C_fault_parity_not_claimed=True)
    def test_04_actual_cleanup_helper_and_live_type(self):
        count=0;seen=set();before=(self.out/'match-frozen'/m.ELF).read_bytes();at=m.elf_slot_offset(before,g.FREE,112)
        self.assertEqual(before[at:at+112],self.rom[0x196BDC:0x196C4C])
        for cmd,kind,cleanup,mutation,situation in itertools.product((0,3,17,22),(0,1,2,31,40),(1,2),(0,1),range(4)):
            models=self.compare(g.Case(command=cmd,kind=kind,cleanup=cleanup,mutation=mutation,situation=situation));seen.update(p for p in models[0].visits if g.FREE<=p<g.FREE+112);count+=1
        self.assertEqual(len(seen),28)
        self.receipts['helper']=dict(cases_per_body=count,retained_words=28,covered_words=len(seen),pending_list_repair_and_final_callbacks_bounded=True,live_type_after_repair=True,no_additional_C_credit=True)
    def test_05_actual_type40_callback_window(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom)
        self.assertEqual([i*4 for i,w in enumerate(allwords)if w==g.ENTRY],[0x2307A4]);self.assertNotIn(0x0C000000|(g.ENTRY>>2&0x3FFFFFF),allwords)
        self.assertEqual(0x8008B4A8+40*52+0x1C,0x8008BCE4)
        va=0x15169160;window=list(struct.unpack_from('>5I',self.rom,0x196610));count=0
        for command,alias,situation in itertools.product((0,3,17,22,45,255),(0,4),range(4)):
            case=g.Case(command=command,alias=alias,situation=situation);initial=g.fixture(case);g.put(initial,0x8008BCE4,g.ENTRY);expected=g.reference(initial,case);models=[]
            for body in(self.truth,self.words):
                connected=dict(zip(range(g.ENTRY,g.ENTRY+292,4),body));connected[va+20]=0
                model=g.Oracle(window,initial,case,entry=va,connected=connected,arguments=());model.r[16]=g.RECORD;model.r[18]=g.request(case);model.r[19]=command|0xABCDEF00;model.r[22]=0x8008BCC8
                model.code=WindowCode(model.code,model);model.code.ends=(va+20,)
                with self.assertRaises(WindowBoundary):model.run()
                self.assertEqual(model.calls[0],(g.ENTRY,(g.RECORD,g.request(case),command)));self.assertEqual((g.public(model.memory,case),model.calls[1:]),expected);models.append(model)
            self.assertEqual(g.state(models[0]),g.state(models[1]));count+=1
        self.receipts['caller']=dict(cases=count,actual_window_words=5,type_index=40,callback_slot='0x8008BCE4',arguments=3,result_unused=True,complete_dispatcher_not_claimed=True)
    def test_06_native32_SDK_and_effective_source_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt+'.c');p.write_text(harness(),encoding='utf-8');exe=p.with_suffix('.elf')
            run=subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((run.returncode,run.stdout,run.stderr),(0,'',''));self.assertEqual(subprocess.run([str(exe)]).returncode,0)
        cached=c.SELECTED.replace('    s32 first;','    u8 tag;\n    s32 first;').replace('            *(s32 *)((u8 *)record + 0x1C) = request[1];','            tag = *((u8 *)request + 9);\n            *(s32 *)((u8 *)record + 0x1C) = request[1];').replace('*((u8 *)record + 0x18) = *((u8 *)request + 9);','*((u8 *)record + 0x18) = tag;')
        variants={'stub':c.SELECTED[:c.SELECTED.index('{')+1]+'\n}', 'identity':c.SELECTED.replace('(s32)request == *(s32 *)((u8 *)record + 0x1C)','request[0] == *(s32 *)((u8 *)record + 0x1C)'), 'byte':c.SELECTED.replace('*((u8 *)request + 9)','*((u8 *)request + 8)'), 'early-tag':cached}
        rejected={}
        for label,body in variants.items():
            p=self.out/('negative-'+label+'.c');p.write_text(harness(body),encoding='utf-8');exe=p.with_suffix('.elf');run=subprocess.run([*native_command('-O2'),'-fno-strict-aliasing',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr);answer=subprocess.run([str(exe)]).returncode;self.assertNotEqual(answer,0);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=98304,SDK_headers=True,UBSan_trap=True,aliases_use_aligned_word_backing=True,semantic_controls_rejected=rejected)
    def test_07_independent_symbol_rebases_and_strict_image_controls(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        raw,refs=m.function_blob(self.q['qualified_compacts'][0]);blob,_=m.derive(raw,refs);count=0
        for entry,free in((g.ENTRY,g.FREE),(0x1740FFF0,0x17518004),(0x17508000,0x17407FFC)):
            words=list(struct.unpack('>73I',blob));lines=['.set noreorder','.text','.globl func_151347CC','func_151347CC:']
            lines+=['jal func_1516972C'if i*4 in refs else'.word 0x%08X'%w for i,w in enumerate(words)]
            p=self.out/('rebase-'+str(count));p.with_suffix('.s').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'--defsym=func_1516972C=0x%X'%free,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            expected=m.bound_blob(blob,refs,{'func_1516972C':free});got=list(struct.unpack_from('>73I',sections(p.with_suffix('.elf'))['.text'][1]));self.assertEqual(got,expected);count+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),201)
        for off in(64,m.elf_slot_offset(before,g.ENTRY,292)+4,m.elf_slot_offset(before,0x15134070,4)):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=201,exclusions=0,complete_function_census=6052,independent_links=count,corruption_controls=3)
if __name__=='__main__':unittest.main()
