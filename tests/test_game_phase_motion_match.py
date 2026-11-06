"""Phase callback: literal origins, live helper ABI, private state and full image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_phase_motion_candidates as candidate
from tools.experiments import game_phase_motion_match as match
from tools.tests import game_phase_motion_oracle as g
from tools.tests import game_phase_motion_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):
    return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.events,m.calls,m.visits,m.trace,
           m.snapshots,m.current_pc,m.delay_of,m.all_accesses)

class PhaseMotionMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT)
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM))
        ctx=type('OriginalPhase',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'match-original-phase',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=g.bound(cls.prepared['qualified_compact']);cls.words=g.bound(cls.prepared['qualified_owner'])
        assert g.bound(cls.original)==cls.retail==cls.words
    def receipt(self,name,**v):
        (self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=None,initial=None,images=None,entry=match.ENTRY,connected=None,actual=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial
        expected,calls,result,snapshots=g.reference(initial,c,s,actual);models=[]
        for words in(self.retail,self.words)if images is None else images:
            m=g.Oracle(words,initial,c,s,entry,connected).run();models.append(m)
            self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.snapshots),(g.public(expected,c),calls,result,snapshots),c)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.before_f[20:])
        for m in models[1:]:self.assertEqual(state(models[0]),state(m))
        return models
    def test_01_owner_load_origins_binding_move_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(71,40,2,8))
        self.assertEqual((q['raw_neighbors'],q['neighbors']),(36,36))
        self.assertEqual((q['existing_compiler_warnings'],q['new_compiler_diagnostics']),(4,0))
        self.assertTrue(q['padded_pools_unchanged'])
        raw,b=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+284]
        self.assertEqual([4*i for i,(a,b)in enumerate(zip(self.raw,self.retail))if a!=b],[0xB4,0xB8])
        self.assertEqual(b[0xB4],[('R_MIPS_LO16','D_800BE9A4')]);self.assertNotIn(0xB8,b)
        normalized=match.function_blob(self.prepared['qualified_owner'])[1]
        self.assertEqual(normalized[0xB8],b[0xB4]);self.assertNotIn(0xB4,normalized)
        for at in range(284):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        rows=(self.out/'proposed-guards.csv').read_text(encoding='utf-8').splitlines()
        for i in range(2):
            bad=rows[:];fields=bad[-2+i].split(',');fields[3]=hex(int(fields[3],16)^1);bad[-2+i]=','.join(fields)
            p=self.out/('match-bad-guard-%d.csv'%i);p.write_text('\n'.join(bad)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p)
        self.receipt('owner-controls',raw_byte_corruptions=284,binding_corruptions=8,actual_padder_expected_word_controls=2,
                     load_origins_closed=True,LO16_moves_with_load=True,raw_neighbors=36,padded_neighbors=36,raw_FPR_mask_delta=q['raw_pool_delta'],
                     padded_pools_fixed=True,existing_warnings=4,new_diagnostics=0)
    def test_02_guest_reference_live_mutations_and_every_word(self):
        count=0;seen=set()
        for c in g.cases():
            initial=g.fixture(c);expected,calls,result,snapshots=g.reference(initial,c)
            models=self.compare(c,initial=initial)
            raw=g.Oracle(self.raw,initial,c).run()
            self.assertEqual((g.public(raw.memory,c),raw.calls,raw.r[2],raw.snapshots),(g.public(expected,c),calls,result,snapshots))
            for r in(*range(16,24),28,29,30,31):self.assertEqual(raw.r[r],raw.before[r])
            self.assertEqual(raw.f[20:],raw.before_f[20:]);seen.update(models[0].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+284,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=3,body_words_covered=71,all_256_values_per_phase_and_velocity=True,
                     extreme_tick_words=True,all_four_helper_snapshots=True,raw_external_state_equal=True,normalized_full_state_equal=True,
                     portable_hardware_FCSR_and_NaN_payload_claimed=False)
    def test_03_guest_aliases_private_homes_and_fault_prefixes(self):
        aliases=0;cuts=0
        for phase in(0,8):
            for name,locations in(('D_800BE9E4',(g.OWNER+0xAC,g.OWNER+0xA8,*[g.STACK+phase-40+i for i in range(0,52,4)])),
                                   ('D_800BE9A4',(g.OWNER+0xB0,g.OWNER+0xC4,*[g.STACK+phase-40+i for i in range(0,52,4)]))):
                for location in locations:
                    c=g.Case(128,0x80000000,phase,0 if g.STACK+phase-40<=location<g.STACK+phase+12 else 7);s=g.symbols();s[name]=location;initial=g.fixture(c,s)
                    words=[g.bound(obj,s)for obj in(self.original,self.prepared['qualified_owner'])]
                    pair=[g.Oracle(w,initial,c,s).run()for w in words]
                    self.assertEqual(state(pair[0]),state(pair[1]));aliases+=1
        for c in(g.Case(),g.Case(127,0xFFFFFFFF,8,7),g.Case(128,0x80000000,0,2)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.retail,self.words):
                    m=g.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipt('aliases-faults',guest_aliases_per_body=aliases,fired_access_prefixes=cuts,normalized_full_literal_state_equal=True,
                     raw_fault_order_claimed=False,portable_C_stack_aliases_or_faults_claimed=False)
    def test_04_original_registered_caller_window_and_old_stub(self):
        va,end=0x15130A0C,0x15130A50;body=list(struct.unpack_from('>17I',self.rom,0x15DEBC));seen=set();count=0
        for index,phase,mode,selector,gate in itertools.product((0,1,127,128,255),(0,8),(0,7),(255,12),(0,1)):
            c=g.Case(index,3,phase,mode);initial=g.fixture(c);initial[g.OWNER+0x72]=selector;g.put(initial,0x80089790,match.ENTRY)
            enabled=selector==12 and not gate;expected,calls,result,snapshots=g.reference(initial,c)if enabled else(initial,[],0,[])
            pair=[]
            for words in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+284,4),words));code[end]=0
                m=g.Oracle(body,initial,c,entry=va,connected=code);m.r[7]=gate;m.before=m.r[:]
                m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(g.public(m.memory,c),g.public(expected,c))
                self.assertEqual(m.calls,([(match.ENTRY,(g.OWNER,g.STACK+phase+0x48))]if enabled else[])+calls)
                self.assertEqual(m.snapshots,snapshots);self.assertEqual(m.r[7],gate);self.assertEqual(m.r[29],g.STACK+phase)
                pair.append(m);seen.update(m.visits)
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1
        before=self.prepared['predecessor_elf'].read_bytes();at=match.elf_slot_offset(before,match.ENTRY,284);stub=list(struct.unpack_from('>71I',before,at))
        c=g.Case();initial=g.fixture(c);initial[g.OWNER+0x72]=12;g.put(initial,0x80089790,match.ENTRY)
        code=dict(zip(range(match.ENTRY,match.ENTRY+284,4),stub));code[end]=0
        m=g.Oracle(body,initial,c,entry=va,connected=code);m.r[7]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
        with self.assertRaises(WindowBoundary):m.run()
        seen.update(m.visits);self.assertEqual(m.r[7],1);self.assertEqual(g.public(m.memory,c),g.public(initial,c))
        self.assertEqual(m.calls,[(match.ENTRY,(g.OWNER,g.STACK+0x48))])
        self.assertTrue(set(range(va,end,4))<=seen)
        parent=match.elf_slot_offset(before,0x151303EC,12);self.assertEqual(before[parent:parent+12],bytes.fromhex('0000102503E0000800000000'))
        self.receipt('caller-controls',cases_per_normalized_body=count,original_window_words=17,covered_window_words=17,registered_slot=12,
                     unused_workspace_pointer_forwarded=True,old_stub_fires_expiry=True,current_parent_still_stub=True,full_428_word_parent_claimed=False)
    def test_05_original_lookup_wrap_sine_and_pinned_data(self):
        before=self.prepared['predecessor_elf'].read_bytes();code={};spans=((g.LOOKUP,0x16F888,27),(g.WRAP,0x172018,24),(g.SINE,0x75210,104))
        for entry,pos,n in spans:
            at=match.elf_slot_offset(before,entry,4*n);truth=self.rom[pos:pos+4*n];self.assertEqual(before[at:at+4*n],truth)
            code.update(zip(range(entry,entry+4*n,4),struct.unpack('>%dI'%n,truth)))
        at=match.elf_slot_offset(before,0x8009A220,260);table=list(struct.unpack_from('>65I',before,at))
        at=match.elf_slot_offset(before,0x800A56A4,4);period=struct.unpack_from('>I',before,at)[0];self.assertEqual(period,0x40C90FDB)
        actual=dict(table=table,period=period);seen=set();count=0
        rows=[(g.Case(index,g.TICKS[index%6],phase),None)for index,phase in itertools.product(range(256),(0,8))]
        rows.extend((g.Case(phase=phase),g.bits(angle))for phase,angle in itertools.product((0,8),(-100.,-7.,-0.,0.,7.,100.)))
        for c,angle in rows:
            initial=g.fixture(c)
            if angle is not None:g.put(initial,g.OWNER+0xC4,angle);g.put(initial,g.OWNER+0xC8,0)
            for i,value in enumerate(table):g.put(initial,0x8009A220+i*4,value)
            g.put(initial,0x800A56A4,period)
            for address,value in g.trig.GLOBALS.items():
                at=match.elf_slot_offset(before,address,4);self.assertEqual(before[at:at+4],struct.pack('>I',value));g.put(initial,address,value)
            for m in self.compare(c,initial=initial,connected=code,actual=actual):seen.update(m.visits)
            count+=1
        coverage=[dict(entry=hex(entry),words=n,covered=len(set(range(entry,entry+4*n,4))&seen))for entry,pos,n in spans]
        self.assertEqual(coverage[0]['covered'],27);self.assertEqual(coverage[1]['covered'],24)
        self.receipt('original-helpers',cases_per_normalized_body=count,helpers=coverage,original_current_helpers_byte_identical=True,
                     pinned_quarter_wave_table_and_sine_constants=True,finite_wrap_domain=True,complete_parent_gameplay_or_hardware_FCSR_claimed=False)
    def test_06_GNU_rebases_and_moved_LO16_carry(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s.update(D_800BE9E4=0x88000000+(0x7FFC if k==1 else 0x8000),D_800BE9A4=0x89000000+(0x8000 if k==1 else 0x7FFC),
                          func_151423D8=entry+0x10000,func_15144B68=entry+0x20000,sinf=entry+0x30000)
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('match-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8')
                p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,
                                *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[284:],bytes(len(blob)-284))
                images.append(list(struct.unpack_from('>71I',blob)));links+=1
            self.assertEqual(images[0],images[2]);self.assertEqual(images[1],g.bound(self.prepared['qualified_compact'],s))
            for c in list(g.cases())[::127]:
                self.compare(c,s,entry=entry,images=(images[0],images[2]));count+=1
        self.receipt('rebases',GNU_links=links,cases_per_normalized_body=count,all_eight_bindings=True,moved_LO16_and_both_carry_boundaries=True,
                     raw_linker_binding_checked=True,standalone_zero_alignment_tail_checked=True)
    def test_07_native32_layout_snapshots_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native-contract.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native-contract'+opt+'.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt)
            self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native-controls',cases_per_profile=count,positive_executions=3*count,total_calls=3*count*9,profiles=['O0','O2','O3'],
                     SDK_native32=True,UBSan=True,compatible_two_pointer_callback=True,all_four_16_word_snapshots_checked=True,
                     complete_owner_and_workspace_canaries=True,controls=controls,checked_control_mask=255,sanitizer_trap_does_not_satisfy_control=True)
    def test_08_literal_whole_image_and_old_stub_rejection(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284]
        delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,284)
        for off in(0,at,at+283,at+284,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>71I',before,at));m=g.Oracle(stub,g.fixture(),g.Case()).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        self.receipt('image-controls',literal_changed_bytes=delta,exclusions=0,metadata_permutations=0,corruptions=5,old_stub_rejected=True)

if __name__=='__main__':unittest.main()
