"""Position/subtype query ABI, ordered local actor payload and complete image."""
import json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_position_subtype_150a3058_match as source
from tools.tests import game_position_subtype_150a3058_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections


def symbols():return {n:int(n.split('_')[1],16)for rows in source.BINDINGS.values()for _,n in rows}


class PositionSubtypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.elf=cls.q['qualified_elf'].read_bytes()
        cls.truth=list(struct.unpack_from('>79I',cls.rom,source.ROM));cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_direct_owner_scope_and_fail_closed_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(79,888,0,27,27))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,241,0,0));self.assertEqual(self.words,self.truth)
        self.assertEqual((self.q['raw'],self.q['refs']),(self.q['normal'],self.q['normal_refs']));self.assertEqual(source.guard_rows(self.q['raw'],self.q['refs']),[])
        before=(self.out/'predecessor-guards.csv').read_bytes();self.assertEqual(source.guard_manifest(before,self.q['raw'],self.q['refs']),before)
        for at in range(0,316,4):
            raw=bytearray(self.q['raw']);raw[at+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(raw),self.q['refs'])
        for at in self.q['refs']:
            refs=dict(self.q['refs']);refs[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.normalize(self.q['raw'],refs)
        with self.assertRaises(ValueError):source.guard_manifest(before+b'\n',self.q['raw'],self.q['refs'])
        self.receipts['scope']=dict(direct_words=79,frame=888,guards=0,bindings=5,neighbors=27,labels=31,
            raw_and_padded_metadata_fixed=True,raw_corruptions=79,binding_corruptions=5,guard_history_fixed=True)

    def test_02_ordered_model_payload_and_live_scan(self):
        visited=set();count=0
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);states=[]
            for words in(self.truth,self.words):
                m=guest.Oracle(words,initial,c);regs,floats=m.r[:],m.f[:];m.run()
                self.assertEqual((guest.public(m.memory,c),m.calls,m.r[2],m.query_observations),expected[:4],c)
                self.assertEqual(tuple(guest.rd(m.memory,guest.query_address(c)+p)for p in guest.FIELDS),tuple(guest.rd(expected[4],guest.query_address(c)+p)for p in guest.FIELDS))
                self.assertEqual(m.r[16:24],regs[16:24]);self.assertEqual(m.r[28:32],regs[28:32]);self.assertEqual(m.f[20:],floats[20:])
                states.append(guest.state(m));visited.update(m.visits)
            self.assertEqual(states[0],states[1]);count+=1
        missing=set(range(source.ENTRY,source.ENTRY+316,4))-visited;self.assertEqual(missing,{source.ENTRY+248})
        self.assertEqual(self.truth[62],0x8E6F0000)
        self.receipts['model']=dict(cases=count,public_words_reached=78,unreachable_original_word=62,all_79_words_retained=True,
            full_word_subtype=True,signed_short_coordinates=True,all_seven_query_fields=True,original_uninitialized_bytes_guest_only=True,
            live_unsigned_count_and_record_base=True,first_zero_provider_result=True,query_and_incoming_home_mutations=True,
            stack_table_and_global_aliases=True,literal_state_equal=True)

    def test_03_original_float_to_short_callers(self):
        jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF);sites=[p for p in range(0x1000,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,p)[0]==jal]
        self.assertEqual(sites,[0xE647C,0xE7428,0xE7474]);pointers=[p for p in range(0,len(self.rom)-3,4)if source.ENTRY<=struct.unpack_from('>I',self.rom,p)[0]<source.ENTRY+316];self.assertEqual(pointers,[])
        direct=[p for p in range(0x2D4B0,0x24D500,4) if struct.unpack_from('>I',self.rom,p)[0]>>26 in(2,3) and source.ENTRY<((0x10000000)|((struct.unpack_from('>I',self.rom,p)[0]&0x3FFFFFF)<<2))<source.ENTRY+316];self.assertEqual(direct,[])
        code=dict(zip(range(source.ENTRY,source.ENTRY+316,4),self.words));checks=0
        windows=((0xE643C,21,1,0x150B9400),(0xE73EC,19,2,0x150BA34C),(0xE7438,19,1,0x150BA348))
        for offset,size,kind,end in windows:
            entry=0x15000000+offset-0x2D4B0;words=struct.unpack_from('>%dI'%size,self.rom,offset)
            for coordinates in((123.75,-45.9,6.5),(-32768.75,32767.9,-1.25),(65536.25,-65537.75,1048577.5),(-0.0,0.0,0.999)):
                raw=tuple(guest.bits(v)for v in coordinates);coords=tuple(guest.half(guest.trunc(guest.floating(v)))for v in raw)
                for count,hit in((0,-1),(5,-1),(5,3)):
                    c=guest.Case(subtype=kind,coords=coords,count=count,hit=hit);initial=guest.fixture(c)
                    for i,v in enumerate(raw):guest.wr(initial,guest.ACTOR+0x14+i*4,v)
                    guest.wr(initial,guest.STACK+0x1A8,guest.bits(1.25));guest.wr(initial,guest.STACK+0x4C,0x13579BDF)
                    m=guest.Oracle(words,initial,c,entry=entry,connected=code);m.r[16]=guest.ACTOR;m.f[14]=guest.bits(-2.5);m.code=WindowCode(m.code,m);m.code.ends=(entry+size*4,end)
                    with self.assertRaises(WindowBoundary):m.run()
                    expected=guest.reference(initial,c);self.assertEqual(m.calls,[(source.ENTRY,tuple(map(guest.u32,(kind,*coords))))]+expected[1]);self.assertEqual((guest.public(m.memory,c),m.r[2],m.query_observations),(expected[0],expected[2],expected[3]));self.assertEqual(m.r[29],guest.STACK)
                    if offset==0xE643C:self.assertEqual((m.f[12],m.f[14]),(guest.bits(1.25),guest.bits(-2.5)))
                    if offset==0xE73EC:self.assertEqual(m.r[31],0x13579BDF if expected[2] else 0x150B9F80)
                    checks+=1
        self.receipts['callers']=dict(direct_calls=3,entry_or_interior_pointers=0,interior_direct_jumps=0,
            original_window_words=59,connected_cases=checks,original_float_truncation_and_signed_halfword_narrowing=True,
            original_branch_and_branch_likely_consumers=True,complete_large_callers_not_claimed=True)

    def test_04_executed_memory_fault_prefixes(self):
        count=0
        for c in(guest.Case(),guest.Case(count=0),guest.Case(pattern=1,hit=4,mutation=26),guest.Case(alias=1,pattern=1)):
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in(self.truth,self.words):
                    m=guest.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1],(c,cut));count+=1
        self.receipts['faults']=dict(executed_cuts=count,all_local_stores_and_live_scan_accesses=True,
            literal_low_word_state_equal=True,opaque_collision_faults_not_modeled=True)

    def test_05_native32_real_layout_and_effective_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        b=source.SELECTED;controls=dict(stub=b[:b.index('{')+1]+'\nreturn 0;\n}',unsigned_x=b.replace('query.x_position = x;','query.x_position = (u16)x;'),
            missing_secondary_y=b.replace('query.unk180 = y;','query.unk180 = z;'),wrong_class=b.replace('>> 2) == 3','>> 2) == 2'),
            byte_subtype=b.replace('== subtype','== (u8)subtype'),wrong_truth=b.replace('0) == 0','0) != 0'),
            cached_count=b.replace('    for (index','    u32 savedCount = (u32)D_800D3094;\n    for (index').replace('index < (u32)D_800D3094','index < savedCount'),
            reinitialize_query=b.replace('            if (func_150A1DA0','            query.x_position = x;\n            if (func_150A1DA0'))
        for name,bad in controls.items():self.assertNotEqual(b,bad,name);self.assertNotEqual(run('negative-'+name,bad),0,name)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,
            typed_s32_s16_s16_s16_query=True,actor812_descriptor52_pointer32=True,trapping_UBSan=True,
            only_initialized_fields_observed=True,effective_controls=list(controls),aliases_guest_only=True)

    def test_06_independent_links_and_complete_image_controls(self):
        original=symbols();moved={n:0x81238000+i*0x10000 for i,n in enumerate(original)};moved['func_150A1DA0']=0x17518000
        for i,bindings in enumerate((original,moved)):
            p=self.out/('rebase-'+str(i));lines=['.set noreorder','.set noat','.text','.globl query','query:']
            for j,(word,) in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                for kind,name in self.q['normal_refs'].get(j*4,[]):lines.append('.reloc ., '+kind+', '+name)
                lines.append('.word 0x%08X'%word)
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in bindings.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack('>79I',sections(p.with_suffix('.elf'))['.text'][1])),source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+316];self.assertEqual(source.strict_image(before,after,truth),241)
        sym=next(p for p,n,f,s in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,316),sym+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=241,exclusions=0,independent_links=2,all_five_bindings=True,
            signed_LO16_carries=True,corruption_controls=4,no_metadata_permutation=True)


if __name__=='__main__':unittest.main()
