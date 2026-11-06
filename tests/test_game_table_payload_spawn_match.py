"""Split payload constructor: exact owner, byte boundaries, original caller/factory."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_table_payload_spawn_candidates as candidate
from tools.experiments import game_table_payload_spawn_match as match
from tools.tests import game_table_payload_spawn_oracle as g
from tools.tests import game_table_payload_spawn_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses
def public(mm):return{k:v for k,v in mm.items()if not g.STACK-1024<=k<g.STACK+1024}

class ReturnPoison(TrackedCode):
    def __getitem__(self,pc):
        if pc==0x151A90AC:self.owner.r[2]=self.owner.poison
        return super().__getitem__(pc)

class FactoryOracle(g.Oracle):
    def record_call(self,t):
        if t in (0x15149130,0x1510F800,0x1510FD20,0x15144598):
            count={0x15149130:9,0x1510F800:1,0x1510FD20:2,0x15144598:1}[t]
            args=tuple(self.arguments(count));self.calls.append((t,args,None));self.events.append(('CALL',t,args));return
        return super().record_call(t)
    def hook(self,t):
        assert t in(0x15149130,0x1510F800,0x1510FD20,0x15144598),hex(t)
        value=(g.OUTPUT if self.c.allocated else 0)if t==0x15149130 else 0
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        if t==0x15144598:self.f[0]=0x3F400000
        self.r[2]=value

class TablePayloadSpawnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.truth=cls.rom[match.ROM:match.ROM+272];cls.retail=list(struct.unpack('>68I',cls.truth))
        ctx=type('OriginalTablePayload',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'table-payload-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.SYMS)
        cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.SYMS)
        assert cls.retail==cls.raw==cls.words==match.bound_blob(*match.function_blob(cls.original),g.SYMS)
        cls.blobs=[match.function_blob(obj)for obj in(cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]

    def receipt(self,n,**v):(self.out/('payload-'+n+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

    def compare(self,c=g.Case(),s=g.SYMS,images=None,entry=match.ENTRY):
        initial=g.fixture(c,s);expected,calls=g.reference(initial,c,s);models=[]
        for w in((self.retail,self.raw,self.words)if images is None else images):
            m=g.Oracle(w,initial,c,entry,s).run();self.assertEqual((m.memory,m.calls),(expected,calls),c)
            self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[-1]));return models

    def test_01_direct_owner_and_fail_closed_words(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(68,136,0,4,36))
        raw,b=match.function_blob(self.prepared['qualified_compact'])
        for at in range(272):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,self.truth)
        self.receipt('owner',raw_and_padded_neighbors=36,raw_corruptions=272,binding_corruptions=4,guards=0,complete_68_words=True)

    def test_02_independent_byte_reference_and_all_gate_values(self):
        count=0;seen=set()
        for gate,allocated,mode,pattern,phase in itertools.product(range(256),(False,True),(0,7),range(4),(0,8)):
            m=self.compare(g.Case(gate,allocated,mode,pattern,phase))[0];seen.update(m.visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+272,4)))
        self.receipt('guest',cases_per_body=count,bodies=3,all_256_unsigned_gate_values=True,all_68_words=True,request_bytes=40,retained_padding=[1,2,3,39],payload_bytes=44,header_and_aligned_copy_loop=True,bit_patterns_including_NaNs_copied_verbatim=True,saved_register_ABI=True)

    def test_03_live_table_aliases_and_private_fault_prefixes(self):
        count=0
        for off,phase,pattern,allocated in itertools.product(range(-0x100,0x104,4),(0,8),(0,3),(False,True)):
            # Move the data relocation across every request/payload/home slot.
            s=dict(g.SYMS,D_800A636C=g.STACK+phase-136+off)
            images=[match.bound_blob(raw,bindings,s)for raw,bindings in self.blobs]
            self.compare(g.Case(allocated=allocated,pattern=pattern,phase=phase),s,images);count+=1
        for alias,mode,phase,pattern in itertools.product(range(5),(0,15),(0,8),range(4)):
            c=g.Case(mode=mode,pattern=pattern,phase=phase,alias=alias)
            self.compare(c)
            count+=1
        cuts=0
        for c in(g.Case(),g.Case(gate=255),g.Case(allocated=False),g.Case(mode=15),g.Case(alias=2,phase=8)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipt('aliases',cases_per_body=count,table_frame_offsets=129,request_payload_and_incoming_homes=True,forward_copy_output_aliases=True,provider_payload_mutations_guest_only=True,fault_prefixes=cuts,literal_fault_states_equal=True,portable_C_private_fault_claim=False)

    def test_04_complete_original_parent_and_ignored_return(self):
        va=0x151A9060;body=list(struct.unpack_from('>24I',self.rom,0x1D6510));seen=set();count=0
        for index,null,gate,allocated,phase,poison in itertools.product((-1,0,6,7,8,0x80000000),(False,True),(0,255),(False,True),(0,8),(0,0xFFFFFFFF)):
            c=g.Case(gate,allocated,7,1,phase,unused=6);initial=g.fixture(c);g.put(initial,c.actor+0x18,index&0xFFFFFFFF);initial[c.actor+0x16]=128
            for slot in range(8):g.put(initial,g.REGISTRY+4*slot,match.ENTRY if slot==6 and not null else 0)
            prepared=dict(initial);prepared[c.actor+0x16]|=4;want,calls=g.reference(prepared,c,home=g.STACK+phase-24-136)
            pair=[]
            for w in(self.retail,self.words):
                m=g.Oracle(body,initial,c,entry=va,connected=dict(zip(range(match.ENTRY,match.ENTRY+272,4),w)),home=g.STACK+phase-24-136)
                m.poison=poison;m.code=ReturnPoison(dict(m.code),m);m.run()
                called=index==6 and not null
                self.assertEqual(public(m.memory),public(want if called else prepared));self.assertEqual(m.calls,[(match.ENTRY,(c.actor,6),None),*calls]if called else[])
                self.assertEqual(m.r[2],1);pair.append(m);seen.update(m.visits)
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1
        self.assertTrue(set(range(va,va+96,4))<=seen)
        self.receipt('caller',cases_per_body=count,whole_parent_words=24,all_parent_words=True,callback_slot=6,void_result_poison_values=2,invalid_signed_indices_and_null_entries=True,parent_returns1=True)

    def test_05_original_memcpy_and_complete_original_factory(self):
        copy=list(struct.unpack_from('>11I',self.rom,0x22EC0));factory=list(struct.unpack_from('>115I',self.rom,0x1D5FD0));seen=set();count=0
        before=(self.out/'match-frozen'/match.ELF).read_bytes();at=match.elf_slot_offset(before,0x800A8F50,8);constants=before[at:at+8]
        for allocated,pattern,phase in itertools.product((False,True),range(4),(0,8)):
            c=g.Case(allocated=allocated,pattern=pattern,phase=phase);initial=g.fixture(c)
            initial.update({0x800A8F50+i:v for i,v in enumerate(constants)})
            models=[]
            for w in(self.retail,self.raw,self.words):
                code=dict(zip(range(g.COPY,g.COPY+44,4),copy));code.update(zip(range(g.CREATE,g.CREATE+460,4),factory))
                m=FactoryOracle(w,initial,c,connected=code).run();models.append(m);seen.update(m.visits)
                root=m.calls[0];self.assertEqual(root[0:2],(g.CREATE,(g.STACK+phase-136+96,0xFFFFFFFF,44,255,0)))
                alloc=[a for t,a,_ in m.calls if t==0x15149130];self.assertEqual(alloc,[(300,0xFFFFFFFF,0x25,0xFFFFFFFF,0,0x22,0x84,255,0)])
                firstcopy=[x for x in m.calls if x[0]==g.COPY][0]
                self.assertEqual(firstcopy[1][2],40);self.assertEqual(firstcopy[2],root[2])
                if allocated:self.assertEqual(bytes(m.memory[g.OUTPUT+128+i]for i in range(44)),bytes(initial[g.TABLE+8+i]for i in range(44)))
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.assertTrue(set(range(g.COPY,g.COPY+44,4))<=seen)
        self.receipt('factory',cases_per_body=count,whole_original_factory_words=115,covered_factory_words=len(seen&set(range(g.CREATE,g.CREATE+460,4))),original_memcpy_words=11,all_memcpy_words=True,actual_40_byte_request_copy_includes_padding=True,actual_allocator_nine_argument_ABI=True,successful_and_null_allocation=True,allocator_and_three_geometry_helpers_bounded=True,full_gameplay_claim=False)

    def test_06_independent_GNU_rebases(self):
        links=count=0
        for k,(entry,table,create,copy)in enumerate(((match.ENTRY,g.TABLE,g.CREATE,g.COPY),(0x18017FFC,0x89007FFC,0x18028000,0x18038000),(0x1A028000,0x89008000,0x1A038004,0x1A048008))):
            syms=dict(D_800A636C=table,func_151A8B20=create,memcpy=copy);images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,syms);self.assertFalse(unknown)
                p=self.out/('payload-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in syms.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>68I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for gate,allocated,pattern in itertools.product((0,1,128,255),(False,True),range(4)):
                self.compare(g.Case(gate,allocated,pattern=pattern),syms,images,entry);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,HI_LO_carry_boundaries=True,both_R26_helpers=True)

    def test_07_native_SDK_and_effective_controls(self):
        p=self.out/'payload-native.c';p.write_text(native.program(),encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('payload-native'+opt);r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',positive_calls=147456,rows_per_profile=24576,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,request40_payload44_table52=True,header_alignment1_values_alignment4=True,direct_and_callback_ABI=True,defined_request_fields_only=True,padding_value_claim=False,table_and_owner_output_aliases=True,effective_controls=list(g.controls()))

    def test_08_literal_image_and_old_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();delta=match.strict_image(before,after,self.truth);at=match.elf_slot_offset(after,match.ENTRY,272)
        for off in(0,at,at+271,at+272,match.METADATA_GROUPS[0][0],len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        stub=list(struct.unpack_from('>68I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertEqual(m.calls,[])
        self.assertNotEqual(m.calls,g.reference(g.fixture())[1])
        self.receipt('image',changed_bytes=delta,exclusions=0,metadata_permutations=len(match.METADATA_GROUPS),corruptions=6,stub_rejected=True)

if __name__=='__main__':unittest.main()
