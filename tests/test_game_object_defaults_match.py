"""Full 812-byte clear, FPR-only fit, six callers and complete production image."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_object_defaults_candidates as candidate
from tools.experiments import game_object_defaults_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_object_defaults_oracle as model
from tools.tests import game_object_defaults_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations

class ObjectDefaultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.fitted=model.bound(cls.prepared['qualified_compact'],model.symbols(),True);cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('OriginalObjectDefaults',(),dict(root=ROOT,out=cls.out));cls.original=ViewListSetupTests.original.__func__(ctx,'original-defaults',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.fitted==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=model.Case(),s=None,entry=match.ENTRY,images=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s);expected=model.reference(initial,c,s);ms=[]
        for words in(self.retail,self.raw,self.fitted,self.words)if images is None else images:
            m=model.Oracle(words,initial,c,s,entry,model.helper_code(self.rom,c)).run()
            self.assertEqual(model.public(m.memory),model.public(expected['memory']),c);self.assertEqual(m.calls,expected['calls'],c);self.assertEqual(m.observations,expected['observations'],c);self.assertEqual(m.semantic_trace,expected['trace'],c)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            ms.append(m)
        for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
        return ms
    def test_01_owner_FPR_guards_bindings_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(68,24,9,6,88,88))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+272]
        for at in range(272):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();new=match.guard_manifest(old,raw);self.assertTrue(new.startswith(old));rows=list(csv.DictReader(io.StringIO(new.decode())));self.assertEqual(len([r for r in rows if r['function']==match.FUNCTION]),9)
        for offset in match.GUARD_OFFSETS:
            for field in('expected','expected_relocations'):
                bad=[dict(r)for r in rows];row=next(r for r in bad if r['function']==match.FUNCTION and int(r['offset'],0)==offset);row[field]='0x0'if field=='expected'else'R_MIPS_HI16:foreign';o=io.StringIO(newline='');w=csv.DictWriter(o,bad[0].keys());w.writeheader();w.writerows(bad)
                with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],o.getvalue().encode(),'bad-%d-%s'%(offset,field))
        self.receipt('owner-controls',raw_corruptions=272,binding_corruptions=6,guard_corruptions=18,FPR_fields_only=9,all_other_59_words_unchanged=True,normal_profile=True,all_88_neighbors_unchanged=True,all_pools_unchanged=True)
    def test_02_independent_byte_protocol_and_original_helpers(self):
        count=0;seen=set();helper_seen=set()
        for c in model.cases():
            ms=self.compare(c);seen.update(ms[0].visits);helper_seen.update(ms[0].visits);count+=1
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+272,4))<=seen)
        self.assertTrue(set(range(model.RANDOM,model.RANDOM+72,4))<=helper_seen);self.assertTrue(set(range(model.COMPONENT,model.COMPONENT+48,4))<=helper_seen)
        for owner in(0xFFFFFCD4,0xFFFFFF00):self.compare(model.Case(owner=owner));count+=1
        self.receipt('guest-contract',cases_per_body=count,bodies=4,all_68_words=True,clear_bytes=812,clear_word_stores=203,complete_original_RNG_words=18,complete_original_component_words=12,unsigned_remainder=True,full_object_call_snapshots=True,float_payloads_including_sNaN=True,guest_wrapping_clear_gate=True,raw_private_FPR_equality_claimed=False)
    def test_03_aliases_fault_prefixes_and_incoming_homes(self):
        count=cuts=sparse=0
        for first,second in((0x30010,0x80099630),(0x8009962C,0x3014C),(0x30038,0x30038),(0x8009962C,0x30084),(0x30118,0x30180)):
            s=model.symbols();s.update(D_8009962C=first,D_80099630=second);images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_compact'],self.prepared['qualified_owner'])];images[2]=model.bound(self.prepared['qualified_compact'],s,True)
            for mutation in(0,3):self.compare(model.Case(mutation=mutation,component=False),s=s,images=images);count+=1
        for redirect,component,phase in itertools.product(range(1,4),(False,True),(0,8)):
            self.compare(model.Case(redirect=redirect,component=component,phase=phase,mutation=3));count+=1
        for c in(model.Case(component=False),model.Case(connected=True,mutation=3),model.Case(redirect=3,component=False)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c,connected=model.helper_code(self.rom,c)).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.fitted,self.words):
                    m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
                self.assertEqual((model.public(ms[0].memory),ms[0].trace,ms[0].calls),(model.public(ms[1].memory),ms[1].trace,ms[1].calls));cuts+=1
        for owner in(0,0x30001):
            c=model.Case(owner=owner);initial=model.fixture(c)
            if owner==0:
                for i in range(0x32C):initial.pop(i,None)
            ms=[]
            for words in(self.retail,self.fitted,self.words):
                m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c))
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            sparse+=1
        self.receipt('aliases-faults',alias_and_home_cases=count,fired_access_prefixes=cuts,sparse_cases=sparse,byte_order_and_load_timing=True,guest_only_invalid_or_home_probes=True)
    def test_04_all_six_original_caller_contexts(self):
        windows=((0x1505EE94,3,0x1505EEA0),(0x150611CC,2,0x150611D4),(0x150724A8,3,0x150724B4),(0x15082AC8,7,0x15082B4C),(0x15082B20,7,0x15082B4C));count=0;parent_count=0
        self.assertEqual(len(match.census(ROOT)),6)
        for entry,n,end in windows:
            body=list(struct.unpack_from('>%dI'%n,self.rom,entry-0x15000000+0x2D4B0))
            for value,phase,component in itertools.product((0,49,0x80000000,0xFFFFFFFF),(0,8),(False,True)):
                c=model.Case(random=value,phase=phase,component=component,mutation=3);initial=model.fixture(c);home=model.STACK+phase
                model.put(initial,home+0x34,c.owner);model.put(initial,home+0x24,17);expected=model.reference(initial,c,home=home);ms=[]
                for words in(self.retail,self.raw,self.fitted,self.words):
                    code=model.helper_code(self.rom,c);code.update(zip(range(match.ENTRY,match.ENTRY+272,4),words));code[end]=0;m=model.Oracle(body,initial,c,entry=entry,connected=code);m.r[17]=c.owner;m.r[11]=model.u32(c.owner-0x800CC2D0+812);m.r[13]=0x800CC2D0;m.r[15]=model.u32(c.owner-0x800CC2D0)>>2;m.r[24]=0x800CC2D0;m.r[5]=17;m.code=model.WindowCode(m.code,m);m.code.ends=(end,)
                    with self.assertRaises(model.WindowBoundary):m.run()
                    self.assertEqual(model.public(m.memory),model.public(expected['memory']));self.assertEqual(m.calls,[(match.ENTRY,(c.owner,))]+expected['calls']);self.assertEqual(m.observations,expected['observations'])
                    if entry==0x1505EE94:self.assertEqual(m.r[2],c.owner)
                    if entry==0x150724A8:self.assertEqual(m.r[5],17)
                    if entry in(0x15082AC8,0x15082B20):self.assertEqual((m.r[16],m.r[3]),(c.owner,17))
                    ms.append(m)
                for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
                count+=1
        parent=list(struct.unpack_from('>61I',self.rom,0x8A674))
        for value,component,connected,phase in itertools.product((0,0xFFFFFFFF),(False,True),(False,True),(0,8)):
            c=model.Case(random=value,owner=0x800D121C,component=component,connected=connected,phase=phase,mutation=3);initial=model.fixture(c);home=model.STACK+phase;args=(0x41280000,0xC0A00000,0x7FC12345,0x1234FFFF,0xFF,0xABCDEF80,0x81,0x12345678)
            for i,v in enumerate(args[4:]):model.put(initial,home+16+4*i,v)
            expected=model.reference(initial,c,home=home-32);em=expected['memory'];old_index=initial[0x800C3E78]
            for at,v,n in((0x14,args[0],4),(0x18,args[1],4),(0x1C,args[2],4),(0x124,args[4]+1,1),(0x13D,args[6],1),(0x76,args[5],2),(0x2F4,args[7],4),(0x114,0x42C80000,4),(0xD0,args[3]+1,1),(0x14C,0x3F000000,4),(0x150,0x3F000000,4)):model.put(em,c.owner+at,v,n)
            obs=(model.ADAPTER,c.owner,model.block(em,c.owner,0x32C),25);model.put(em,c.owner+0x24,0xC2400000);model.put(em,model.MARK+8,0xA5000002);em[0x800C3E78]=old_index;ms=[]
            for words in(self.retail,self.raw,self.fitted,self.words):
                code=model.helper_code(self.rom,c);code.update(zip(range(match.ENTRY,match.ENTRY+272,4),words));m=model.Oracle(parent,initial,c,entry=model.PARENT,connected=code,arguments=args[:4]);m.f[12],m.f[14]=args[:2];m.run()
                self.assertEqual(model.public(m.memory),model.public(em));self.assertEqual(m.calls,[(match.ENTRY,(c.owner,))]+expected['calls']+[(model.ADAPTER,(c.owner,25))]);self.assertEqual(m.observations,expected['observations']+[obs]);self.assertEqual(m.r[29],home);ms.append(m)
            for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
            parent_count+=1
        self.receipt('caller-controls',direct_calls=6,other_call_windows=5,window_cases_per_body=count,complete_parent_words=61,parent_cases_per_body=parent_count,original_slot25_and_index_restore=True,whole_other_parents_claimed=False)
    def test_05_independent_GNU_links(self):
        links=count=0
        for i,(entry,base,gravity)in enumerate(((match.ENTRY,0x81007FFC,0x82008000),(0x18018000,0x8300FFFC,0x84017FFC),(0x1A02FFFC,0x85018000,0x8600FFFC))):
            s=model.symbols();s.update(D_8009962C=base,D_80099630=gravity,func_150ADA20=0x17008000+i*0x100000,func_150615DC=0x17018000+i*0x100000);images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);f=fs[match.FUNCTION]
                if j==2:
                    raw,bindings=match.function_blob(obj);text=bytearray(text);text[f['value']:f['value']+272]=match.normalized(raw,bindings,self.rom[match.ROM:match.ROM+272])
                asm,unknown=emit_function(text,f,rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>68I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);self.assertEqual(images[0],images[3]);self.assertEqual(images[1],model.bound(self.prepared['qualified_compact'],s));self.assertEqual(images[0],model.bound(self.original,s))
            for c in list(model.cases())[::47]:self.compare(replace(c,connected=False,component=False),s=s,entry=entry,images=images);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_six_bindings=True,HI_LO_carries_and_both_JALs=True)
    def test_06_native_and_effective_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            self.assertNotEqual(body,candidate.SELECTED,name);text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,diag=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);self.assertEqual(diag.count('Warning 712'),8);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c);expected=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c)).run();fired=m.calls!=expected['calls']or m.observations!=expected['observations']or model.public(m.memory)!=model.public(expected['memory'])or m.semantic_trace!=expected['trace']
                except(AssertionError,KeyError,IndexError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native.source(body,witnesses));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);result=subprocess.run([str(exe)]).returncode
            if wanted:self.assertNotEqual(result,0,name)
            else:self.assertEqual(result,0,name)
        self.receipt('native-controls',rows_per_profile=len(witnesses),positive_executions=3*len(witnesses),profiles=['O0','O2','O3'],IDO_controls=effective,native_controls=len(effective),UBSan=True,numeric_multibyte_fields_adapted_to_native_order=True,pointer_checked_separately=True,all_812_object_bytes=True)
    def test_07_literal_image_metadata_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+272];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,272)
        offsets=(0,at,at+271,at+272,len(after)-1,*[p+4 for p,n,o in match.SYMBOL_GROUPS],*[next(s for p,n,f,s in match.symbol_rows(after)if n==names[0])for off,names,order in match.SYMBOL_GROUPS])
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>68I',before,match.elf_slot_offset(before,match.ENTRY,272)));initial=model.fixture();m=model.Oracle(stub,initial).run();self.assertFalse(m.calls);expected=model.reference(initial);self.assertNotEqual(model.public(m.memory),model.public(expected['memory']))
        self.receipt('image-controls',literal_changed_bytes=delta,closed_symbol_groups=2,exclusions=0,corruptions=len(offsets),old_stub_rejected=True)
if __name__=='__main__':unittest.main()
