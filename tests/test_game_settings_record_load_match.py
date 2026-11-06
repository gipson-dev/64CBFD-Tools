"""Scalar checksum, retained byte, four-byte groups and exact installed image."""
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_settings_record_load_candidates as candidate
from tools.experiments import game_settings_record_load_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_settings_record_load_oracle as model
from tools.tests import game_settings_record_load_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations
class SettingsRecordLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>70I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.fitted=model.bound(cls.prepared['qualified_compact'],model.symbols(),True);cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('OriginalSettingsLoad',(),dict(root=ROOT,out=cls.out));cls.original=ViewListSetupTests.original.__func__(ctx,'original-settings-load',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.fitted==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=model.Case(),s=None,entry=match.ENTRY,images=None,raw_index=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s,self.rom);expected=model.reference(initial,c,s);ms=[]
        for words in(self.retail,self.raw,self.fitted,self.words)if images is None else images:
            m=model.Oracle(words,initial,c,s,entry,model.helper_code(self.rom,c)).run()
            self.assertEqual(model.public(m.memory),model.public(expected['memory']),c);self.assertEqual(m.calls,expected['calls'],c);self.assertEqual(m.observations,expected['observations'],c)
            if not c.connected:self.assertEqual([t for t in m.trace if not model.STACK-0x600<=t[1]<model.STACK+0x400],expected['trace'],c)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            ms.append(m)
        # Natural C has different caller-save roles; the complete fitted state is exact.
        raw_index=1 if images is None else raw_index;fitted=[m for i,m in enumerate(ms)if i!=raw_index]
        for m in fitted[1:]:self.assertEqual(state(fitted[0]),state(m))
        return ms
    def test_01_complete_owner_profile_guards_and_pools(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['retail_bindings']),(70,24,46,21,25));self.assertEqual((q['raw_neighbors'],q['neighbors']),(17,17))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+280]
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();new=match.guard_manifest(old);self.assertTrue(new.startswith(old));rows=list(csv.DictReader(io.StringIO(new.decode())));self.assertEqual(len([r for r in rows if r['function']==match.FUNCTION]),46)
        for offset in(36,120,168,252):
            for field in('expected','expected_relocations'):
                bad=[dict(r)for r in rows];row=next(r for r in bad if r['function']==match.FUNCTION and int(r['offset'],0)==offset);row[field]='0x0'if field=='expected'else'R_MIPS_HI16:foreign';out=io.StringIO(newline='');writer=csv.DictWriter(out,bad[0].keys());writer.writeheader();writer.writerows(bad)
                with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_normal'],out.getvalue().encode(),'bad-%d-%s'%(offset,field),self.prepared['qualified_compact'])
        before,after,installed=match.make_states((ROOT/match.MAKE).read_text());self.assertEqual(after.count(match.MAKE_RULE),1);self.assertNotIn(match.MAKE_RULE,before);self.assertEqual(after.replace(match.MAKE_RULE,'',1).replace(match.EXCLUDE_NEW,match.EXCLUDE_OLD,1),before)
        self.receipt('owner-controls',words=70,frame=24,guards=46,bindings=21,retail_bindings=25,neighbors=17,raw_corruptions=280,binding_corruptions=21,guard_corruptions=8,target_only_profile=True,pools_unchanged=True)
    def test_02_independent_protocol_all_saved_bytes_and_coverage(self):
        seen=set();raw_seen=set();count=0
        for c in model.cases():
            ms=self.compare(c);seen.update(ms[0].visits);raw_seen.update(ms[1].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+280,4)))
        self.assertEqual(raw_seen,seen)
        self.receipt('guest-contract',cases_per_body=count,bodies=4,all_70_words=True,all_256_saved_byte_patterns=True,checksum_bytes=[2,29],header_bytes=2,retained_trailing_bytes=2,copy_groups=7,read_before_snapshot=True,ordered_calls_and_observations=True,raw_private_caller_save_equality_claimed=False)
    def test_03_overlap_aliases_fault_prefixes_and_group_control(self):
        aliases=cuts=sparse=0
        for offset in(-4,-1,0,1,2,3,4,20,32):
            s=model.symbols();s['D_800E0BE0']=s['D_800BE358']+offset;s['D_800E0BFC']=s['D_800E0BE0']+28;images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])]
            for c in(model.Case(),model.Case(valid=False,saved=255,effects=3),model.Case(readmode=1,pattern=3)):self.compare(c,s=s,images=images,raw_index=1);aliases+=1
        for where in('D_800E0BE0','D_800BE358'):
            s=model.symbols();s['D_8008FE30']=s[where]+5;images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])]
            self.compare(model.Case(effects=3),s=s,images=images,raw_index=1);aliases+=1
        for c in(model.Case(),model.Case(valid=False),model.Case(readmode=1,effects=3)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.fitted,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
                self.assertEqual((model.public(ms[0].memory),ms[0].trace,ms[0].calls,ms[0].observations),(model.public(ms[1].memory),ms[1].trace,ms[1].calls,ms[1].observations));cuts+=1
        for missing in(0,4,16):
            c=model.Case();initial=model.fixture(c);del initial[model.symbols()['D_800E0BE0']+missing];ms=[]
            for words in(self.retail,self.fitted,self.words):
                m=model.Oracle(words,initial,c)
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            sparse+=1
        s=model.symbols();s['D_800E0BE0']=s['D_800BE358']+3;s['D_800E0BFC']=s['D_800E0BE0']+28;initial=model.fixture(s=s);expected=model.reference(initial,s=s);mutant=model.bound(self.original,s);mutant[196//4]=0xA0490000;mutant[216//4]=0x906AFFFF;m=model.Oracle(mutant,initial,s=s).run();self.assertNotEqual(model.public(m.memory),model.public(expected['memory']))
        self.receipt('aliases-faults',mapped_alias_cases=aliases,fired_prefixes=cuts,sparse_destination_faults=sparse,early_store_instruction_control=True,hardware_or_portable_invalid_access_claimed=False)
    def test_04_original_integrity_helper_and_caller_window(self):
        count=0;seen=set()
        for valid,bad,mode,effects,phase in itertools.product((False,True),(False,True),(0,1),(0,3),(0,8)):
            c=model.Case(valid=valid,bad_code=bad,readmode=mode,effects=effects,phase=phase,connected=True);ms=self.compare(c);seen.update(ms[0].visits);count+=1
        self.assertTrue(set(range(model.CHECK,model.CHECK+104,4))<=seen)
        self.assertEqual(match.census(ROOT),[0x49B84]);pc=0x1501C6D4;body=list(struct.unpack_from('>10I',self.rom,0x49B84));windows=0
        for valid,phase,gate in itertools.product((False,True),(0,8),(0,0x87654321)):
            c=model.Case(valid=valid,phase=phase,readmode=1,effects=3);initial=model.fixture(c);initial[0x80082BB4]=0xD3;model.put(initial,0x800BE3F0,gate);expected=model.reference(initial,c);expected['memory'][0x80082BB4]=0;ms=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+280,4),target));code[0x1501C6FC]=0;m=model.Oracle(body,initial,c,entry=pc,connected=code);m.code=model.WindowCode(m.code,m);m.code.ends=(0x1501C6FC,)
                with self.assertRaises(model.WindowBoundary):m.run()
                self.assertEqual(m.calls,[(match.ENTRY,())]+expected['calls']);self.assertEqual(m.observations,expected['observations']);self.assertEqual(model.public(m.memory),model.public(expected['memory']));self.assertEqual(m.r[2],gate);ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[2]));windows+=1
        self.receipt('helpers-caller',integrity_helper_words=26,original_code_checksum_bytes=model.CODE_END-model.CODE_START,helper_cases_per_body=count,bodies=4,pass_and_clear_task_paths=True,caller_window_words=10,caller_cases_per_body=windows,whole_parent_or_opaque_helpers_claimed=False)
    def test_05_independent_GNU_rebases_and_positive_group_bounds(self):
        links=count=0
        for i,(entry,start,dest)in enumerate(((match.ENTRY,0x81007FFC,0x82007FFC),(0x18018000,0x8300FFF0,0x84018000),(0x1A02FFFC,0x85018000,0x8600FFF0))):
            s=model.symbols();s.update(D_800BE358=start,D_800BE35A=start+2,D_800E0BE0=dest,D_800E0BFC=dest+28,D_8008FE30=0x87007FFC+i*0x10000,D_800BE900=0x88007FFC+i*0x10000)
            for j,name in enumerate(('func_151DD3A0','func_151DD9E4','func_151E7EF8')):s[name]=0x17008000+i*0x100000+j*0x10000
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'],self.prepared['qualified_compact'])):
                text,fs,rs=match.parse_object(obj);f=fs[match.FUNCTION]
                if j==1:
                    raw,bindings=match.function_blob(obj);text=bytearray(text);text[f['value']:f['value']+280]=match.normalized(raw,bindings,self.rom[match.ROM:match.ROM+280]);rs={at:r for at,r in rs.items()if not f['value']<=at<f['value']+280};rs.update({f['value']+at:r for at,r in match.RETAIL_BINDINGS.items()})
                asm,unknown=emit_function(text,f,rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>70I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);self.assertEqual(images[0],model.bound(self.original,s));self.assertEqual(images[2],model.bound(self.prepared['qualified_owner'],s));self.assertEqual(images[3],model.bound(self.prepared['qualified_compact'],s))
            for c in list(model.cases())[::37]:self.compare(c,s=s,entry=entry,images=[images[0],images[3],images[1],images[2]],raw_index=1);count+=1
        for length in(4,8,12,16,28,32,64):
            s=model.symbols();s['D_800E0BFC']=s['D_800E0BE0']+length;images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])]
            for valid in(False,True):self.compare(model.Case(valid=valid),s=s,images=images,raw_index=1);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_25_retail_bindings=True,HI_LO_carries=True,positive_four_byte_group_lengths=[4,8,12,16,28,32,64],physical_payload_still_28=True)
    def test_06_native_and_effective_IDO_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,diag=candidate.compile_owner(ROOT,self.out,text,'negative-'+name,True);self.assertFalse(diag);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c);expected=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c).run();fired=m.calls!=expected['calls']or m.observations!=expected['observations']or model.public(m.memory)!=model.public(expected['memory'])
                except(AssertionError,KeyError,IndexError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        rows=[model.Case(saved=b,valid=v,readmode=r,effects=e,pattern=b%4)for b,v,r,e in itertools.product(range(256),(False,True),(0,1,2,4),(0,3))]
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native.source(body,rows));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        self.receipt('native-controls',rows_per_profile=len(rows),positive_executions=3*len(rows),profiles=['O0','O2','O3'],IDO_controls=effective,native_controls=len(effective),UBSan=True,numeric_header_byte_order_adapted=True,guest_aliases_separate=True)
    def test_07_literal_image_corruption_and_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+280];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,280)
        for off in(0,at,at+279,at+280,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>70I',before,match.elf_slot_offset(before,match.ENTRY,280)));initial=model.fixture();m=model.Oracle(stub,initial).run();self.assertFalse(m.calls);self.assertEqual(len(model.reference(initial)['calls']),3)
        self.receipt('image-controls',literal_changed_bytes=delta,exclusions=0,corruptions=5,old_stub_rejected=True)
if __name__=='__main__':unittest.main()
