"""Direct status switch: typed loads, caller homes, existing pool and full image."""
import json,itertools,re,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_player_status_accessor_candidates as candidate
from tools.experiments import game_player_status_accessor_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_player_status_accessor_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses

def section_offsets(obj):
    data=obj.read_bytes();h=match.ELF_HEADER.unpack_from(data);headers=[match.SECTION_HEADER.unpack_from(data,h[6]+i*h[11])for i in range(h[12])]
    names=headers[h[13]];strings=data[names[4]:names[4]+names[5]]
    return {match.read_c_string(strings,s[0]):s[4]for s in headers}

class PlayerStatusAccessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM));cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalStatus',(),dict(root=ROOT,out=cls.out));cls.original=ViewListSetupTests.original.__func__(context,'original-status',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.raw==cls.words
    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def contract(self,words,c,initial=None,s=None,entry=match.ENTRY):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s,entry)if initial is None else initial
        m=model.Oracle(words,initial,c,s,entry).run();expected,value=model.reference(initial,c,s)
        self.assertEqual((m.memory,m.r[2]),(expected,value),c);self.assertFalse(m.calls)
        for reg in(*range(16,24),28,29,30,31):self.assertEqual(m.r[reg],m.before[reg])
        return m
    def compare(self,c,initial=None,s=None,images=None,entry=match.ENTRY):
        images=(self.retail,self.words)if images is None else images
        ms=[self.contract(words,c,initial,s,entry)for words in images];self.assertEqual(state(ms[0]),state(ms[1]));return ms
    def test_01_direct_words_all_neighbors_and_caller_profiles(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(68,0,0,16,7,7))
        self.assertEqual((q['direct_calls'],q['caller_owners'],len(q['caller_profiles'])),(40,15,16))
        self.assertEqual(sum(p['unchanged_functions']for p in q['caller_profiles']),507)
        self.assertEqual(match.check_target_pool(self.prepared['qualified_compact'])['case_offsets'],list(match.CASE_OFFSETS))
        self.assertEqual(self.rom[match.TABLE_ROM:match.TABLE_ROM+32],struct.pack('>8I',*(match.ENTRY+o for o in match.CASE_OFFSETS),0))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+272]
        for offset in range(272):
            bad=bytearray(raw);bad[offset]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for offset in bindings:
            bad=dict(bindings);bad[offset]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        self.receipt('owner-contract',dict(words=68,frame=0,guards=0,bindings=16,neighbors=7,caller_owners=15,caller_profiles=16,caller_function_comparisons=507,raw_byte_controls=272,binding_controls=16))
    def test_02_complete_semantics_raw_homes_and_signed_fields(self):
        count=0;visited=set()
        for c in model.cases():
            ms=self.compare(c);self.contract(self.raw,c);visited.update(ms[0].visits);count+=1
        self.assertEqual(visited,set(range(match.ENTRY,match.ENTRY+272,4))-{match.ENTRY+0x2C})
        self.receipt('guest-contract',dict(cases_per_body=count,bodies=3,reachable_words=67,unreachable_literal_offset='0x2C',full_argument_homes=True,signed_word_and_byte_results=True,invalid_selector_incoming_v0_guest_only=True))
    def test_03_every_halfword_slot_and_selector(self):
        count=0
        for value in range(65536):
            self.compare(model.Case(slot=0xABCD0000|value,field=1+value%6,pattern=value%6,phase=(value&1)*8))
            self.compare(model.Case(slot=1,field=0xFEDC0000|value,pattern=value%6,incoming=0x12345678^value,phase=(value&1)*8));count+=2
        self.receipt('halfword-sweeps',dict(original_fitted_cases=count,all_slot_halfwords=True,all_selector_halfwords=True,noncanonical_upper_words=True))
    def test_04_home_aliases_and_fired_fault_prefixes(self):
        aliases=cuts=0
        for field,offset,phase in itertools.product(range(7),(-8,-4,0,4,8,12),(0,8)):
            s=model.symbols();name='D_800D2340'if field==0 else model.FIELDS[field-1];s[name]=model.STACK+phase+offset
            c=model.Case(field=field,phase=phase,slot=0,pattern=5);images=(model.bound(self.original,s),model.bound(self.prepared['qualified_owner'],s));self.compare(c,s=s,images=images);aliases+=1
        for c in(model.Case(field=0),model.Case(slot=65535,field=3),model.Case(field=7),model.Case(slot=255,field=6)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));cuts+=1
        c=model.Case(slot=255,field=0xFFFFFFFF);initial={a:b for a,b in model.fixture(c).items()if model.STACK-64<=a<model.STACK+128};self.compare(c,initial)
        self.receipt('aliases-faults',dict(home_aliases=aliases,fired_prefixes=cuts,three_bodies_same_fault_state=True,clipped_slot_needs_no_table_or_data=True,portable_native_stack_alias_claimed=False))
    def test_05_all_original_call_boundaries_and_HUD_result_branch(self):
        count=0;rows=match.census(ROOT)
        for row,c in itertools.product(rows,(model.Case(),model.Case(slot=1,field=3,pattern=1),model.Case(slot=254,field=6,pattern=2,phase=8),model.Case(slot=255,field=65535),model.Case(slot=65535,field=3,pattern=3))):
            at=row['rom'];pc=row['address'];body=list(struct.unpack_from('>2I',self.rom,at));delay=body[1]
            op,rs,rt,rd,fn=delay>>26,delay>>21&31,delay>>16&31,delay>>11&31,delay&63;immediate=model.short(delay)
            slot,field=model.u32(c.slot),model.u32(c.field)
            if op==9 and rt==5:field=model.u32(immediate)
            elif op==0 and fn==37 and rd==5:field=0
            elif op==33 and rt==5:field=model.u32(model.short(c.field))
            elif op==36 and rt==4:slot=c.slot&255
            effective=replace(c,slot=slot,field=field);initial=model.fixture(effective);ms=[]
            initial.update({model.STACK+i:(i*17+165)&255 for i in range(128,512)})
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+272,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code)
                if op==33:m.r[rs]=0x60000;model.put(m.memory,0x60000+immediate,c.field,2)
                elif op==36:m.r[rs]=0x60000;model.put(m.memory,0x60000+immediate,c.slot,1)
                elif op==0 and fn==37 and rd==4:m.r[rs]=model.u32(c.slot)
                before=dict(m.memory);regs=m.r[:]
                if op in(40,43):model.put(before,model.u32(regs[rs]+immediate),regs[rt],1 if op==40 else 4)
                elif op not in(0,9,33,36):self.fail(('Unqualified caller delay',hex(delay)))
                expected,value=model.reference(before,effective)
                end=pc+8;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.calls,[(match.ENTRY,(slot,field))]);self.assertEqual((m.memory,m.r[2]),(expected,value));ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(state(ms[0]),state(ms[2]));count+=1
        pc=0x151E9868;body=list(struct.unpack_from('>4I',self.rom,pc-0x15000000+0x2D4B0));branches=0
        for slot,pattern,phase in itertools.product((0,1,255),range(6),(0,8)):
            c=model.Case(slot=slot,field=3,pattern=pattern,phase=phase);initial=model.fixture(c);expected,value=model.reference(initial,c);ms=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+272,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code)
                ends=(pc+16,pc+44)
                for end in ends:m.code[end]=0
                m.code=WindowCode(m.code,m);m.code.ends=ends
                with self.assertRaises(WindowBoundary):m.run()
                self.assertIn(pc+44 if value==0 else pc+16,m.visits);self.assertEqual(m.memory,expected);ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[2]));branches+=1
        self.receipt('callers',dict(original_call_sites=40,boundary_cases_per_body=count,original_HUD_branch_words=4,HUD_branch_cases_per_body=branches,full_parent_functions_not_claimed=True))
    def test_06_independent_GNU_links_and_all_carry_edges(self):
        links=count=0
        for index,(entry,base,table)in enumerate(((match.ENTRY,0x800D7FFC,0x800B7FFC),(0x18017FFC,0x80208000,0x80307FFC),(0x1A028000,0x80407FFC,0x80508000))):
            s=model.symbols()
            for i,name in enumerate((*model.FIELDS,'D_800D2340')):s[name]=base+i*0x10000
            s['.rodata']=s['jtbl_8009D9A0']=table;images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj)
                # The independently checked private pool maps offset zero to
                # the existing retail table, exactly as the consumer padder does.
                rs={at:[(kind,'jtbl_8009D9A0'if name=='.rodata'else name)for kind,name in rows]for at,rows in rs.items()}
                asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>68I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in(model.Case(field=f,slot=0xFFFF0001,pattern=f%6)for f in range(8)):
                self.compare(c,s=s,images=(images[0],images[2]),entry=entry);self.contract(images[1],c,s=s,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,bindings=16,table_and_all_field_carry_edges=True))
    def test_07_native_defined_domains_and_effective_compiled_controls(self):
        for name,body,opt,wanted in [('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(model.native_source(body));exe=p.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-Wno-error=return-type','-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native-'+name+'-diagnostics.txt')).write_text(result.stdout+result.stderr);self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[:3000])
            warnings=re.findall(r'warning: ([^\n]+)',result.stderr);self.assertEqual(warnings,['control reaches end of non-void function [-Wreturn-type]'])
            self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        controls=dict(model.controls(),slot_width=candidate.SELECTED.replace('s16 slot','s32 slot'),field_width=candidate.SELECTED.replace('s16 field','s32 field'),default_zero=candidate.SELECTED.replace('    /* Other selectors','    return 0;\n    /* Other selectors'))
        witnesses=(model.Case(),model.Case(field=1,pattern=3),model.Case(field=2,pattern=4),model.Case(field=3,pattern=1),model.Case(field=4,pattern=1),model.Case(field=5,pattern=0),model.Case(field=6,pattern=3),model.Case(slot=254,field=1,pattern=2),model.Case(slot=15,mask=0x8000),model.Case(slot=31,mask=0x8000),model.Case(field=7),model.Case(slot=0x7FFF0001,field=1,pattern=2),model.Case(field=0x7FFF0001,pattern=2))
        for name,body in controls.items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+name);words=model.bound(obj,model.symbols());pool=match.normalized_pools(obj)['.rodata'];offsets=tuple(item[2]for item in pool[1]);effective=False
            for c in witnesses:
                initial=model.fixture(c,offsets=offsets);expected,value=model.reference(initial,c);m=model.Oracle(words,initial,c).run()
                if(m.memory,m.r[2])!=(expected,value):effective=True;break
            self.assertTrue(effective,name)
        self.receipt('native-contract',dict(positive_executions=model.NATIVE_EXECUTIONS,profiles=['O0','O2','O3'],typed_and_direct=True,native_controls=9,IDO_controls=12,
            native_mask_shift_counts='0..31',native_record_slots='0..254',native_clipped_slots='255..32767',invalid_selector_unclipped_result_guest_only=True,known_return_type_warning_qualified=True))
    def test_08_switch_pool_and_literal_image_corruptions(self):
        obj=self.prepared['qualified_compact'];data=obj.read_bytes();offsets=section_offsets(obj);bad_path=self.out/'bad-pool.o';checks=0
        for offset in range(32):
            bad=bytearray(data);bad[offsets['.rodata']+offset]^=1;bad_path.write_bytes(bad)
            with self.assertRaises(ValueError):match.check_target_pool(bad_path)
            checks+=1
        for index in range(7):
            bad=bytearray(data);bad[offsets['.rel.rodata']+8*index+7]^=1;bad_path.write_bytes(bad)
            with self.assertRaises(ValueError):match.check_target_pool(bad_path)
            checks+=1
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+272]
        self.assertEqual(match.strict_image(before,after,truth),318);at=match.elf_slot_offset(after,match.ENTRY,272);table=match.elf_slot_offset(after,match.TABLE,32)
        image_offsets=(0,at,at+272,table,table+28,*[offset for offset,names in match.SYMBOL_GROUPS],0x2EC96C,len(after)-1)
        for offset in image_offsets:
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('strict-controls',dict(pool_corruptions=checks,image_corruptions=len(image_offsets),literal_ELF_changes=318,named_serialization_bytes=96,exclusions=0,existing_retail_table_unchanged=True))

if __name__=='__main__':unittest.main()
