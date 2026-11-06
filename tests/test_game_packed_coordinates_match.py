"""Addressed homes, symbolic roles, coordinate boundaries and exact images."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_packed_coordinates_candidates as candidate
from tools.experiments import game_packed_coordinates_match as match
from tools.experiments import game_packed_coordinate_roles as roles
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_packed_coordinates_oracle as model
from tools.tests import game_packed_coordinates_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations
def window(rom,call):
    start=call-20
    for p in range(start,call,4):
        w=struct.unpack_from('>I',rom,p)[0];op=w>>26
        safe=(op==0 and w&63==37)or op==9 or(op==43 and w>>21&31==29 and(w&65535)in(16,20))
        if not safe:start=p+4
    return start,call+8,list(struct.unpack_from('>%dI'%((call+8-start)//4),rom,start))
def caller_fixture(c):
    m=model.fixture(c)
    for r in range(17,24):
        p=0x80000+r*0x100;m.update({p+i:(i*17+37)&255 for i in range(-64,128)})
    return m
def seed_caller(m,slot):
    m.r[16]=slot;m.r[8:16]=[0]*8;m.r[24:26]=[0]*2
    for r in range(17,24):m.r[r]=0x80000+r*0x100

class PackedCoordinatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>69I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.fitted=model.bound(cls.prepared['qualified_compact'],model.symbols(),True);cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('OriginalPackedCoordinates',(),dict(root=ROOT,out=cls.out));cls.original=ViewListSetupTests.original.__func__(ctx,'original-packed',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.fitted==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=model.Case(),s=None,entry=match.ENTRY,images=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s);expected=model.reference(initial,c,s);ms=[]
        for i,words in enumerate((self.retail,self.raw,self.fitted,self.words)if images is None else images):
            m=model.Oracle(words,initial,c,s,entry).run();self.assertEqual(m.memory,expected['memory'],c);self.assertFalse(m.calls)
            if i!=1:self.assertEqual(m.trace,expected['trace'],c)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            ms.append(m)
        for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
        return ms
    def test_01_owner_guards_symbolic_roles_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(69,0,39,4,88,88))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+276];fitted=match.normalized(raw,bindings,truth);r=roles.prove(match.rescheduled(raw),fitted,bindings);self.assertEqual((r['states'],r['paths']),(265,17))
        for at in range(276):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        for at in(52,76,132,264):
            bad=bytearray(fitted);w=struct.unpack_from('>I',bad,at)[0];struct.pack_into('>I',bad,at,w^(1<<16))
            with self.assertRaises((AssertionError,ValueError)):roles.prove(match.rescheduled(raw),bytes(bad),bindings)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();new=match.guard_manifest(old,raw);self.assertTrue(new.startswith(old));rows=list(csv.DictReader(io.StringIO(new.decode())));self.assertEqual(len([r for r in rows if r['function']==match.FUNCTION]),39)
        for offset,oldword,newword,rs in match.PATCHES:
            for field in('expected','expected_relocations'):
                bad=[dict(r)for r in rows];row=next(r for r in bad if r['function']==match.FUNCTION and int(r['offset'],0)==offset);row[field]='0x0'if field=='expected'else'R_MIPS_HI16:foreign';o=io.StringIO(newline='');w=csv.DictWriter(o,bad[0].keys());w.writeheader();w.writerows(bad)
                with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],o.getvalue().encode(),'bad-%d-%s'%(offset,field))
        self.receipt('owner-controls',raw_corruptions=276,binding_corruptions=4,guard_corruptions=78,symbolic_corruptions=4,all_88_neighbors_and_pools_unchanged=True,symbolic_states=265,symbolic_paths=17,schedule_swaps=[[80,112],[104,108]],branch_target_preserved=True)
    def test_02_independent_coordinate_contract_and_word_coverage(self):
        count=0;seen=set()
        for c in model.cases():
            ms=self.compare(c);seen.update(ms[0].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+276,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=4,all_69_words=True,full_memory_including_three_incoming_homes=True,width_and_height_plus_two=True,strict_greater_than_ties=True,single_correction_not_modulo=True,overflow_is_wrapping_32_bit=True,raw_read_schedule_equality_claimed=False)
    def test_03_aliases_sparse_gate_and_fault_prefixes(self):
        aliases=cuts=sparse=0
        for alias,dx,dy,absolute in itertools.product((0,1),(-1,0,1,0x7FFFFFFF),(0,1,0x80000000),(0,1)):
            self.compare(model.Case(alias=alias,dx=dx,dy=dy,absolute=absolute));aliases+=1
        for dx in(0,1,-1):
            c=model.Case(dx=dx);s=model.symbols();s['D_800D19A0']=model.STACK+8-c.slot*4;images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_compact'],self.prepared['qualified_owner'])];images[2]=model.bound(self.prepared['qualified_compact'],s,True);self.compare(c,s=s,images=images);aliases+=1
        self.compare(model.Case(slot=0x40000001,entry=0x20000005));aliases+=1
        for c in(model.Case(),model.Case(absolute=1),model.Case(flag=0),model.Case(alias=1)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.fitted,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        c=model.Case(flag=0);initial=model.fixture(c);keep={p:v for p,v in initial.items()if model.STACK<=p<model.STACK+20 or model.symbols()['D_800D19A0']+4<=p<model.symbols()['D_800D19A0']+8}
        for words in(self.retail,self.fitted,self.words):
            m=model.Oracle(words,keep,c);# Constructor supplies ABI words; remove unused absolute home again.
            for i in range(4):m.memory.pop(model.STACK+20+i,None)
            m.run();self.assertEqual(len(m.trace),5)
        sparse+=1
        for missing in(model.STACK+16,model.symbols()['D_800C4488']+4):
            c=model.Case(flag=0 if missing==model.STACK+16 else 1);initial=model.fixture(c);ms=[]
            for words in(self.retail,self.fitted,self.words):
                m=model.Oracle(words,initial,c)
                for i in range(4):m.memory.pop(missing+i,None)
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            sparse+=1
        self.receipt('aliases-faults',aliases=aliases,fired_access_prefixes=cuts,sparse_cases=sparse,gate_false_still_reads_bank_home=True,guest_only_sparse_or_home_alias_claims=True)
    def test_04_all_original_caller_windows(self):
        count=0;windows=[]
        for call in match.census(ROOT):
            start,end,body=window(self.rom,call);entry=start-0x2D4B0+0x15000000;boundary=end-0x2D4B0+0x15000000;windows.append(dict(call=hex(call),start=hex(start),words=len(body)))
            for slot,phase in itertools.product((1,2),(0,8)):
                seed=model.Case(slot=slot,phase=phase);initial=caller_fixture(seed);stub={match.ENTRY:0x03E00008,match.ENTRY+4:0,boundary:0}
                probe=model.Oracle(body,initial,seed,entry=entry,connected=stub);seed_caller(probe,slot);probe.code=model.WindowCode(probe.code,probe);probe.code.ends=(boundary,)
                with self.assertRaises(model.WindowBoundary):probe.run()
                self.assertEqual(len(probe.calls),1);actual=probe.calls[0][1];c=replace(seed,slot=actual[0],entry=actual[1],dx=actual[2],dy=actual[3],bank=actual[4],absolute=actual[5]);initial=caller_fixture(c);expected=model.reference(initial,c);ms=[]
                for words in(self.retail,self.raw,self.fitted,self.words):
                    code=dict(zip(range(match.ENTRY,match.ENTRY+276,4),words));code[boundary]=0;m=model.Oracle(body,initial,c,entry=entry,connected=code);seed_caller(m,slot);m.code=model.WindowCode(m.code,m);m.code.ends=(boundary,)
                    with self.assertRaises(model.WindowBoundary):m.run()
                    self.assertEqual(m.calls,[(match.ENTRY,actual)]);self.assertEqual(m.memory,expected['memory']);ms.append(m)
                for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
                count+=1
        self.receipt('caller-controls',call_sites=21,windows=windows,cases_per_body=count,bodies=4,six_word_O32_ABI=True,whole_parent_or_prior_argument_providers_claimed=False)
    def test_05_independent_GNU_rebases(self):
        links=count=0
        for i,(entry,gates,tables)in enumerate(((match.ENTRY,0x81007FFC,0x82008000),(0x18018000,0x8300FFFC,0x84017FFC),(0x1A02FFFC,0x85018000,0x8600FFFC))):
            s=model.symbols();s.update(D_800D19A0=gates,D_800C4488=tables);images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);f=fs[match.FUNCTION]
                if j==2:
                    raw,bindings=match.function_blob(obj);text=bytearray(text);text[f['value']:f['value']+276]=match.normalized(raw,bindings,self.rom[match.ROM:match.ROM+276])
                asm,unknown=emit_function(text,f,rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);self.assertEqual(images[0],images[3]);self.assertEqual(images[1],model.bound(self.prepared['qualified_compact'],s));self.assertEqual(images[0],model.bound(self.original,s))
            for c in list(model.cases())[::29]:self.compare(c,s=s,entry=entry,images=images);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_four_bindings=True,HI_LO_carries=True)
    def test_06_native_full_grid_and_effective_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            self.assertNotEqual(body,candidate.SELECTED,name);text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,diag=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);self.assertEqual(diag.count('Warning 712'),8);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c);expected=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c).run();fired=m.memory!=expected['memory']
                except(AssertionError,KeyError,IndexError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native.source(body));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);result=subprocess.run([str(exe)]).returncode
            if wanted:self.assertNotEqual(result,0,name)
            else:self.assertEqual(result,0,name)
        self.receipt('native-controls',rows_per_profile=655372,positive_executions=1966116,all_4096_coordinate_values=True,extents=[2,3,4096,4097],delta_values=10,absolute_modes=4,profiles=['O0','O2','O3'],IDO_controls=effective,native_controls=len(effective),UBSan=True,reference_is_widened_64_bit_formula=True)
    def test_07_literal_image_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+276];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,276)
        for off in(0,at,at+275,at+276,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>69I',before,match.elf_slot_offset(before,match.ENTRY,276)));initial=model.fixture();m=model.Oracle(stub,initial).run();self.assertNotEqual(m.memory,model.reference(initial)['memory'])
        self.receipt('image-controls',literal_changed_bytes=delta,metadata_permutations=0,exclusions=0,corruptions=5,old_stub_rejected=True)
if __name__=='__main__':unittest.main()
