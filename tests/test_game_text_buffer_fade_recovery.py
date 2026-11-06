"""Private recovery gates explicitly reject byte-match credit and frame normalization."""
import hashlib,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_text_buffer_fade_recovery as source
from tools.tests import game_text_buffer_fade_oracle as g
from tools.tests import game_text_buffer_fade_native as native
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_view_list_setup as view_setup
ROOT=source.ROOT

class TextBufferFadeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>69I',cls.rom,source.ROM))
        cls.inputs=json.loads((cls.out/'screen-inputs.json').read_text(encoding='utf-8'))
        for p,h in cls.inputs.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
        cls.live=(ROOT/source.SOURCE).read_text(encoding='utf-8');assert cls.live.count(source.OLD)==1
        cls.obj,diag=source.compile_owner(ROOT,cls.out,cls.live.replace(source.OLD,source.SELECTED,1),'qualified-private');assert not diag
        cls.raw=g.bound(cls.obj)
        ctx=type('OriginalTextFade',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'original-text-fade',(ROOT/'conker/asm/FC5F0.s').read_text(encoding='utf-8'),source.FUNCTION)
        assert g.bound(cls.original)==cls.truth
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def test_01_emission_is_unmatched_and_uninstalled(self):
        self.assertEqual(len(self.raw),69);self.assertEqual(self.raw[0],0x27BDFFD0)
        self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),34)
        self.assertEqual(len(g.payload(self.obj)[1]),6);self.assertEqual((ROOT/source.SOURCE).read_text(encoding='utf-8'),self.live)
        self.receipt('private-shape',words=69,frame=48,word_differences=34,bindings=6,source_installed=False,guards_added=0,matching_credit=0)
    def test_02_guest_external_contract_all_bytes_and_original_coverage(self):
        count=0;seen=set();paths=set()
        for c in g.cases():
            initial=g.fixture(c);expected,calls,result=g.reference(initial,c)
            for w in(self.truth,self.raw):
                m=g.Oracle(w,initial,c).run();self.assertEqual((g.public(m.memory,c),m.calls,m.r[2]),(g.public(expected,c),calls,result));seen.update(m.visits)
                for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                self.assertEqual(m.f[20:],m.before_f[20:])
            paths.add(tuple(t for t,a in calls));count+=1
        self.assertEqual(seen&set(range(source.ENTRY,source.ENTRY+276,4)),set(range(source.ENTRY,source.ENTRY+276,4)))
        self.assertEqual(len(paths),2)
        self.receipt('private-guest',cases_per_body=count,bodies=2,original_words_covered=69,all_count_bytes=True,extreme_tick_words=True,mutable_index_and_buffers=True,external_state_and_call_order_equal=True,full_private_state_equal=False,matching_credit=0)
    def test_03_private_home_and_access_trace_are_real_mismatches(self):
        c=g.Case(count=0,flags=0,ticks=7);s=g.symbols();s['D_800BE9E4']=g.STACK-48+32;initial=g.fixture(c,s)
        ms=[g.Oracle(w,initial,c,s).run() for w in(g.bound(self.original,s),g.bound(self.obj,s))]
        self.assertEqual(g.read(ms[0].memory,s['D_800BE9E4']),7);self.assertEqual(g.read(ms[1].memory,s['D_800BE9E4']),0)
        self.assertNotEqual(ms[0].trace,ms[1].trace);self.assertEqual(ms[0].calls,ms[1].calls)
        self.receipt('private-home-boundary',SP_offset=32,original_tick_word=7,raw_tick_word=0,extra_spill_observable_under_guest_alias=True,access_trace_differs=True,scheduling_only_proof=False,matching_credit=0)
    def test_04_native32_semantics_and_effective_controls(self):
        controls=g.controls();effective=[]
        for name,body,opt,want in [('positive-'+x[1:],source.SELECTED,x,0)for x in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in controls.items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native.program(body),encoding='utf-8');exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);r=subprocess.run([str(exe)]).returncode
            if want:self.assertNotEqual(r,0,name);effective.append(name)
            else:self.assertEqual(r,0,name)
        self.receipt('private-native',cases_per_profile=20480,positive_executions=61440,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,controls=effective,defined_external_state_only=True,matching_credit=0)
    def test_05_registration_and_immutable_production(self):
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);entry=source.ENTRY
        self.assertEqual([i*4 for i,w in enumerate(ws)if w==entry],[0x22D360])
        self.assertFalse(any(w==0x0C000000|((entry>>2)&0x3FFFFFF) for w in ws))
        parent=(ROOT/'conker/asm/FC5F0.s').read_text(encoding='utf-8').split('glabel func_150D0034\n',1)[1].split('endlabel func_150D0034',1)[0]
        self.assertIn('FD528 150D0078 0320F809',parent);self.assertIn('FD534 150D0084 14400005',parent)
        self.assertIn('s32 (*D_800888A0[])(u8 *arg0)',self.live)
        for p,h in self.inputs.items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
        self.receipt('private-production',frozen_inputs=len(self.inputs),registered_callback=0,parent='func_150D0034',caller_site='0x150D0078',return1_consumed=True,complete_caller_execution_claimed=False,production_unchanged=True,matching_credit=0)

if __name__=='__main__':unittest.main()
