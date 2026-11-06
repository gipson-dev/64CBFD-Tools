"""Direct constructor qualification: ABI, original caller/helper, aliases and production."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_oriented_effect_parameters_candidates as candidate
from tools.experiments import game_oriented_effect_parameters_match as match
from tools.tests import game_oriented_effect_parameters_oracle as g
from tools.tests import game_oriented_effect_parameters_native as native
from tools.tests import game_oriented_effect_factory_oracle as factory
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.packets,m.payloads

class OrientedEffectParametersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM))
        ctx=type('OriginalParameters',(),dict(root=ROOT,out=cls.out));cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'original-parameters',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=g.bound(cls.prepared['qualified_compact']);cls.words=g.bound(cls.prepared['qualified_owner']);assert g.bound(cls.original)==cls.retail==cls.raw==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=None,initial=None,entry=match.ENTRY,images=None):
        s=g.symbols() if s is None else s;initial=g.fixture(c,s) if initial is None else initial;models=[]
        for words in((self.retail,self.raw,self.words) if images is None else images):
            m=g.Oracle(words,initial,c,s,entry);expected,calls,packet=g.reference(initial,c,s,m.before[31]);m.run()
            self.assertEqual((m.memory,m.calls,m.packets),(expected,calls,[packet]))
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        for m in models[1:]:self.assertEqual(state(models[0]),state(m))
        return models
    def test_01_owner_bindings_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(68,68,112,0,9,11,11))
        raw,b=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+272]
        for at in range(272):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        self.receipt('owner-controls',raw_corruptions=272,binding_corruptions=9,all_11_neighbors_and_pools_fixed=True,compact_IDO_register_mask_change_pinned=True,no_new_guards=True)
    def test_02_complete_guest_descriptor_ABI_and_coverage(self):
        seen=set();count=0
        for c in g.cases():
            ms=self.compare(c);seen.update(ms[0].visits);count+=1
            p=g.STACK+c.phase-88
            for off in g.PADDING:self.assertEqual(ms[0].packets[0][0][off],g.fixture(c)[p+off])
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+272,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=3,all_68_words=True,complete_seeded_88_byte_input=True,all_256_mode_bytes=True,untouched_private_bytes=list(g.PADDING),full_RAM_and_state_trace_equal=True,helper_mutations=True)
    def test_03_private_aliases_access_order_and_fault_prefixes(self):
        count=cuts=0
        for phase,off,kind in itertools.product((0,8),range(88),('owner','late-global','early-global')):
            p=g.STACK+phase-88;s=g.symbols();c=g.Case(173,phase,1)
            if kind=='owner':c=replace(c,owner=p+off-12)
            else:s['D_800A0C30' if kind=='late-global' else 'D_800A0C24']=p+(off//4)*4
            images=[g.bound(o,s) for o in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])]
            self.compare(c,s,images=images);count+=1
        for c in(g.Case(),g.Case(255,8,9,owner=g.STACK+8-88+0x39-12,mutation=3)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.words):
                    m=g.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        self.receipt('aliases-faults',aliases_per_body=count,fired_prefixes=cuts,late_owner_and_fourth_global_reads=True,guest_private_stack_aliases_only=True,portable_C_fault_semantics_claimed=False)
    def test_04_original_oriented_factory_and_independent_payloads(self):
        helper=list(struct.unpack_from('>202I',self.rom,0x180420));code=dict(zip(range(g.HELPER,g.HELPER+808,4),helper));count=0;particles=set();seen=set()
        # The qualified opaque integer provider is varied to include all 1..3 counts.
        def rng(i,c):return (0,1,2,0xFFFFFFFF)[(i+c.seed)%4]
        with patch.object(factory.old,'ri',rng):
            for mode,phase,seed in itertools.product((0,1,128,255),(0,8),range(8)):
                c=g.Case(mode,phase,seed);initial=g.fixture(c)
                for n,v in zip(('D_800A0C24','D_800A0C28','D_800A0C2C','D_800A0C30'),(0x3FA00000,0xC0200000,0x40700000,0x40100000)):g.put(initial,g.symbols()[n],v)
                models=[]
                for words in(self.retail,self.raw,self.words):
                    m=g.Oracle(words,initial,c,connected=code);m.run();models.append(m);seen.update(m.visits)
                for m in models[1:]:self.assertEqual(state(models[0]),state(m))
                m=models[0];packet,p=g.packet(initial,g.STACK+phase,g.symbols(),m.before[31]);fc=factory.Case(seed=seed,mode=mode,phase=phase-112)
                with patch.object(factory,'INPUT',p):expected,calls,payloads,ni,nf,nt,ns=factory.reference(packet,fc,g.providers())
                self.assertEqual(m.calls,[(g.HELPER,(p,mode))]+calls);self.assertEqual(m.payloads,payloads)
                self.assertEqual((m.rng_i,m.rng_f,m.trig_i,m.submits),(ni,nf,nt,ns));particles.add(ns);count+=1
        self.assertEqual(particles,{1,2,3})
        traps={g.HELPER+4*i for i,w in enumerate(helper) if w&0xFC00003F==13}
        # countBase=1 and countRange=2 cannot take the factory's zero-count
        # early-return likely delay slot. Its ordinary epilogue is exercised.
        self.assertEqual(set(range(g.HELPER,g.HELPER+808,4))-seen,traps|{g.HELPER+0x10C})
        self.receipt('helper-contract',cases_per_body=count,bodies=3,original_helper_words=202,covered_helper_words=196,zero_count_only_RA_load='0x1515307C',unreachable_divisor_traps=len(traps),particle_counts=sorted(particles),independent_final_payload_reference=True,RNG_trig_and_submission_providers_opaque=True,whole_gameplay_claimed=False)
    def test_05_original_record_callback_caller(self):
        va,end=0x15149264,0x15149318;body=list(struct.unpack_from('>45I',self.rom,va-0x15000000+0x2D4B0));count=0
        for mode,phase,flag,enabled in itertools.product(range(256),(0,8),(0,1),(False,True)):
            c=g.Case(mode,phase);initial=g.fixture(c);initial[g.OWNER+13]=flag;initial[g.OWNER+17]=0 if enabled else 255;g.put(initial,g.OWNER+14,100,2);g.put(initial,0x800BE9E4,7);g.put(initial,0x8008A4E8,match.ENTRY);models=[]
            for words in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+272,4),words));m=g.Oracle(body,initial,c,entry=va,connected=code);m.home=g.STACK+phase-24-112;m.run();models.append(m)
                self.assertEqual(m.target_calls,[(g.OWNER,)] if enabled else []);self.assertEqual(len(m.packets),int(enabled));self.assertEqual(g.read(m.memory,g.OWNER+14,2),100-7*flag);self.assertEqual(m.r[29],g.STACK+phase)
                if enabled:self.assertEqual(m.packets[0][1],(g.STACK+phase-24-88,mode))
            for m in models[1:]:self.assertEqual(state(models[0]),state(m))
            count+=1
        self.receipt('caller-controls',cases_per_body=count,bodies=3,whole_original_parent_words=45,callback_slot=0,site='0x151492B0',original_void_owner_ABI=True,skip_sentinel_and_lifetime_tick=True,return_value_discarded=True,negative_lifetime_cleanup_path_claimed=False)
    def test_06_independent_GNU_rebases_and_carries(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:
                base=0x81000000+k*0x08000000;s.update({n:base+v for n,v in zip(('D_800A0C24','D_800A0C28','D_800A0C2C','D_800A0C30'),(0x7FFC,0x8000,0x17FFC,0x18000))});s['func_15152F70']=entry+0x10000
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>68I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in list(g.cases())[::127]:self.compare(c,s,entry=entry,images=images);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_9_bindings=True,HI_LO_carries=True)
    def test_07_native32_SDK_and_effective_controls(self):
        controls=g.controls();live=candidate.source_states((ROOT/candidate.SOURCE).read_text(encoding='utf-8'))[1];effective=[]
        for name,body in controls.items():
            obj,diag=candidate.compile_owner(ROOT,self.out,live.replace(candidate.SELECTED,body,1),'negative-'+name);self.assertEqual(diag,'');words=g.bound(obj);fired=False
            for c in(g.Case(173,seed=1),g.Case(255,seed=2)):
                initial=g.fixture(c);m=g.Oracle(words,initial,c);m.run();expected,calls,packet=g.reference(initial,c,ra=m.before[31]);fired|=(m.memory,m.calls,m.packets)!=(expected,calls,[packet])
            self.assertTrue(fired,name);effective.append(name)
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0) for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1) for n,b in controls.items() if n!='cleared_padding']:
            p=self.out/('native-'+name+'.c');p.write_text(native.source(body),encoding='utf-8');exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);r=subprocess.run([str(exe)]).returncode
            if wanted:self.assertNotEqual(r,0,name)
            else:self.assertEqual(r,0,name)
        self.receipt('native-controls',calls_per_profile=25600,positive_executions=76800,profiles=['O0','O2','O3'],UBSan=True,SDK_size_offsets=True,IDO_controls=effective,native_controls=6,padding_contents_not_asserted_native=True)
    def test_08_literal_image_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+272];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,272)
        for off in(0,at,at+271,at+272,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>68I',before,match.elf_slot_offset(before,match.ENTRY,272)));m=g.Oracle(stub,g.fixture()).run();self.assertFalse(m.packets);self.assertNotEqual(m.memory,g.reference(g.fixture(),ra=m.before[31])[0])
        self.receipt('image-controls',literal_changed_bytes=delta,metadata_permutations=len(match.METADATA_GROUPS),exclusions=0,corruptions=5,old_stub_rejected=True)

if __name__=='__main__':unittest.main()
