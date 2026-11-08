"""Query C ABI, original SDK/callers, closed alias binding and full-image gates."""
import json,struct,subprocess,unittest
from dataclasses import replace
from pathlib import Path
from tools.experiments import game_record_occupancy_150a29c8_match as source
from tools.experiments import game_record_occupancy_150a29c8_dependencies as deps
from tools.tests import game_record_occupancy_150a29c8_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections

SITES=(0xBE30,0x8697C,0x86998,0x869B4,0x869F8,0xCDA30,0xCDB44,0xF1CB8,0xFDC34,0xFDC4C,0xFDC64,0xFDC7C,0xFDC94,0xFDCAC,0x13DFC4,0x13DFE8,0x1713E4,0x2062EC)
def symbols(refs):return {n:guest.SHIFT if n=='__ull_rshift' else int(n.split('_')[1],16) for rows in refs.values() for _,n in rows}


class RecordOccupancyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.elf=cls.q['qualified_elf'].read_bytes()
        cls.truth=list(struct.unpack_from('>73I',cls.rom,source.ROM));cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols(cls.q['normal_refs']));cls.raw=source.bound_blob(cls.q['raw'],cls.q['refs'],symbols(cls.q['refs']));cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_owner_header_dependency_and_guard_scope(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(73,32,2,27,27))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,258,0,0))
        self.assertEqual(self.words,self.truth);self.assertEqual(self.raw,self.truth)
        self.assertEqual(self.q['raw'][:136]+b'\x8c\xa5\x00\x00'+self.q['raw'][140:],self.q['normal'])
        for p in range(0,292,4):
            raw=bytearray(self.q['raw']);raw[p+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(raw),self.q['refs'])
        for p in self.q['refs']:
            refs=dict(self.q['refs']);refs[p]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.normalize(self.q['raw'],refs)
        before=(self.out/'predecessor-guards.csv').read_bytes();after=(self.out/'qualified-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before));self.assertEqual(len(after[len(before):].splitlines()),2)
        with self.assertRaises(ValueError):source.guard_manifest(before+b'\n',self.q['raw'],self.q['refs'])
        d=q['header_dependencies'];self.assertEqual((d['owners'],d['whole_object_identical'],d['discarded_input_debug_only']),(199,194,5))
        row=next(r for r in json.loads((self.out/'header-audit.json').read_text())['records'] if r['discarded_input_sections'])
        baseline=(self.root/row['baseline_object']).read_bytes();copied=(self.root/row['copied_object']).read_bytes();self.assertEqual(deps.section_scope(baseline,copied),['.mdebug'])
        raw=bytearray(copied);h=source.pad_generated_object.ELF_HEADER.unpack_from(copied);headers=[source.pad_generated_object.SECTION_HEADER.unpack_from(copied,h[6]+i*h[11]) for i in range(h[12])]
        target=next(x for x in headers if x[2]&2 and x[1]!=8 and x[5]);raw[target[4]]^=1
        with self.assertRaises(ValueError):deps.section_scope(baseline,bytes(raw))
        self.receipts['scope']=dict(words=73,frame=32,guards=2,scheduling_guards=0,bindings=14,neighbors=27,preserved_labels=31,
            all_retained_dependency_sections_fixed=True,dependent_owners=199,whole_identical=194,input_mdebug_only=5,
            actual_header_recipe_commands=643,raw_word_corruptions=73,binding_corruptions=14,dependency_corruption_rejected=True)

    def test_02_ordered_model_width_bounds_and_original_shift(self):
        visited=set();sdk=set();count=0
        for case in guest.cases():
            initial=guest.fixture(case);expected=guest.reference(initial,case);states=[]
            for body in (self.truth,self.words,self.raw):
                m=guest.Oracle(body,initial,case);registers,floats=m.r[:],m.f[:];m.run()
                self.assertEqual((guest.public(m.memory,case),m.calls,m.r[2]),expected,case)
                self.assertEqual(m.r[16:24],registers[16:24]);self.assertEqual(m.r[28:32],registers[28:32]);self.assertEqual(m.f[20:],floats[20:])
                states.append(guest.state(m));visited.update(p for p in m.visits if source.ENTRY<=p<source.ENTRY+292);sdk.update(p for p in m.visits if guest.SHIFT<=p<guest.SHIFT+44)
            self.assertEqual(states[0],states[1]);self.assertEqual(states[0],states[2]);count+=1
        self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+292,4)));self.assertEqual(sdk,set(range(guest.SHIFT,guest.SHIFT+44,4)))
        case=guest.Case(index=0x100,identity=65,enabled=1,result=0);initial=guest.fixture(case)
        guest.wr(initial,guest.MASKS+8,0);guest.wr(initial,guest.MASKS+12,0)
        control=guest.Oracle([0x308400FF]+self.truth,initial,case);control.run()
        self.assertNotEqual(control.r[2],guest.reference(initial,case)[2])
        self.receipts['model']=dict(effective_byte_actor_guest_negative=True,cases=count,target_words_reached=73,SDK_words_reached=11,all_64_shift_counts=True,
            full_u32_actor_and_ID=True,unsigned_inclusive_bound=True,zero_limit_ID_zero_admitted=True,
            collision_result_unmodified=True,one_provider_only=True,private_home_mutations=True,literal_state_equal=True)

    def test_03_original_all_calls_delay_consumers_and_complete_caller(self):
        jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF)
        sites=tuple(p for p in range(0x1000,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,p)[0]==jal);self.assertEqual(sites,SITES)
        pointers=[p for p in range(0,len(self.rom)-3,4) if source.ENTRY<=struct.unpack_from('>I',self.rom,p)[0]<source.ENTRY+292];self.assertEqual(pointers,[])
        code=dict(zip(range(source.ENTRY,source.ENTRY+292,4),self.words));checks=0
        for p in sites:
            entry=0x10000000+p if p<0x290D0 else 0x15000000+p-0x2D4B0
            original=struct.unpack_from('>4I',self.rom,p);delay,consumer=original[1:3];branch=consumer>>26 in(4,5,20,21);size=4 if branch else 3
            for index,enabled,result in ((0,1,0),(3,0,0),(15,0xFFFF,1),(25,0,0x80000001)):
                identity=0x4041
                if delay>>26==9 and delay>>16&31==5:identity=((delay&65535)^32768)-32768
                case=guest.Case(index=index,identity=identity,enabled=enabled,result=result);initial=guest.fixture(case);m=guest.Oracle(original[:size],initial,case,entry=entry,connected=code)
                m.r[19]=guest.u32(identity);answer=guest.reference(initial,case)[2];ends=[entry+size*4]
                if branch:ends.append(guest.u32(entry+12+((((consumer&65535)^32768)-32768)<<2)))
                m.code=WindowCode(m.code,m);m.code.ends=tuple(ends)
                with self.assertRaises(WindowBoundary):m.run()
                expected=guest.reference(initial,case);self.assertEqual(guest.public(m.memory,case),expected[0]);self.assertEqual(m.calls,[(source.ENTRY,(guest.u32(index),guest.u32(identity)))]+expected[1])
                value=answer
                if branch and consumer>>26==21 and answer and original[3]>>26==9 and original[3]>>16&31==2:value=guest.u32(((original[3]&65535)^32768)-32768)
                self.assertEqual(m.r[2],value,(hex(p),case));self.assertEqual(m.r[29],guest.STACK)
                if not branch and consumer>>26==43:self.assertEqual(guest.rd(m.memory,guest.STACK+((consumer&65535)^32768)-32768),answer)
                checks+=1
        caller,offset,size=0x151D8E20,0x2062D0,19;at=source.elf_slot_offset(self.elf,caller,size*4);self.assertEqual(self.elf[at:at+size*4],self.rom[offset:offset+size*4])
        for mode,bits,result in ((0,0,0),(0,1,0),(0,0,1),(1,0,0)):
            case=guest.Case(index=0,identity=28,enabled=1 if bits else 0,result=result);initial=guest.fixture(case);guest.wr(initial,0x800BE9F0,mode);guest.wr(initial,0x800E0A10,0xE3,1)
            m=guest.Oracle(struct.unpack_from('>19I',self.rom,offset),initial,case,entry=caller,connected=code);m.run();answer=guest.reference(initial,case)[2]
            self.assertEqual(m.r[2],10 if mode==0 and answer==0 else 0xE3);self.assertEqual(m.r[29],guest.STACK);checks+=1
        self.receipts['callers']=dict(direct_calls=18,entry_or_interior_pointers=0,connected_cases=checks,all_original_JAL_delay_consumer_windows=True,
            branch_likely_annulled_delay=True,complete_original_caller_words=19,complete_other_callers_not_claimed=True)

    def test_04_executed_fault_prefixes(self):
        count=0
        for c in (guest.Case(),guest.Case(bits=0),guest.Case(limit=0),guest.Case(enabled=0,mutation=31,result=0x80000001)):
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in (self.truth,self.words,self.raw):
                    m=guest.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1]);self.assertEqual(states[0],states[2]);count+=1
        self.receipts['faults']=dict(executed_cuts=count,SDK_accesses_included=True,literal_low_word_states_equal=True)

    def test_05_native32_real_SDK_and_effective_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in ('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        body=source.SELECTED;controls=dict(stub=body[:body.index('{')+1]+'\nreturn 0;\n}',exclusive=body.replace('< identity','<= identity'),
            wrong_mask=body.replace('&= 0xFFF','&= 0xFFE'),
            wrong_bit=body.replace('(identity & 0x3F)','((identity + 1) & 0x3F)'),wrong_stride=body.replace('[actorIndex][identity >> 6]','[0][identity >> 6]'),
            boolean_result=body.replace('    return func_150A1DA0','    return !!func_150A1DA0'))
        for label,bad in controls.items():self.assertNotEqual(body,bad);self.assertNotEqual(run('negative-'+label,bad),0,label)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,typed_u32_u32_query=True,
            actor812_descriptor52_pointer32=True,trapping_UBSan=True,effective_controls=list(controls),valid_arrays_only=True)

    def test_06_independent_relocations_low_alias_carry_and_image_controls(self):
        def link(label,raw,refs,bindings):
            p=self.out/label;lines=['.set noreorder','.set noat','.text','.globl query','query:']
            for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
                for kind,name in refs.get(i*4,[]):lines.append('.reloc ., '+kind+', '+name)
                lines.append('.word 0x%08X'%word)
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v) for n,v in bindings.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            return list(struct.unpack('>73I',sections(p.with_suffix('.elf'))['.text'][1]))
        original=symbols(self.q['normal_refs']);moved={n:0x81238000+i*0x10000 for i,n in enumerate(original)};moved.update(D_800D30F0=0x81337FFC,D_800D30F4=0x81338000,__ull_rshift=0x17518010,func_150A1DA0=0x17528000)
        for i,bindings in enumerate((original,moved)):
            actual=link('normal-link-'+str(i),self.q['normal'],self.q['normal_refs'],bindings);self.assertEqual(actual,source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        raw=link('raw-carry-negative',self.q['raw'],self.q['refs'],moved);normal=link('normal-carry-control',self.q['normal'],self.q['normal_refs'],moved)
        addr=lambda w:guest.u32(((w[30]&65535)<<16)+(((w[34]&65535)^32768)-32768))
        self.assertEqual(addr(raw),0x81328000);self.assertEqual(addr(normal),0x81338000)
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+292];self.assertEqual(source.strict_image(before,after,truth),258)
        sym=next(p for p,n,f,s in source.symbol_rows(before) if n==source.FUNCTION)
        for offset in (64,source.elf_slot_offset(before,source.ENTRY,292),sym+8,source.METADATA_GROUPS[0][0],3238933,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=258,exclusions=0,independent_links=4,all_bindings=True,signed_LO16_crossing=True,
            raw_relocation_carry_negative_effective=True,closed_two_symbol_metadata_swap=True,corruptions=6)


if __name__=='__main__':unittest.main()
