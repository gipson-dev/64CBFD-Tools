"""Raw C, state/record aliases, literal bit helpers/caller, native32 and ELF."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_actor_state_command_selector_candidates as candidate
from tools.experiments import game_actor_state_command_selector_match as match
from tools.tests import game_actor_state_command_selector_oracle as g
from tools.tests import game_actor_state_command_selector_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_record_address_relocator_match import dependent_sections
ROOT=candidate.ROOT
class ActorStateCommandSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());assert cls.words==cls.retail==match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols())
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s);expected,calls=g.reference(initial,c,s);pair=[]
        for words in(self.retail,self.words)if images is None else images:
            m=g.Oracle(words,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m);self.assertEqual((g.public(m.memory,c),[v for v in m.calls if v[0]==s['func_15080738']]),(g.public(expected,c),calls),c)
        self.assertEqual(g.state(pair[0]),g.state(pair[1]));return pair
    def test_01_direct_body_bindings_owner_and_local_pointer_ABI(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(72,32,0,10,10,11));raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+288]
        for i in range(288):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        a,b=[dependent_sections((self.out/n).read_bytes())for n in('match-predecessor.o','match-qualified.o')];x,y=a['.options'][1],b['.options'][1];self.assertEqual((x[:8],x[12:]),(y[:8],y[12:]));self.assertEqual((x[8:12].hex(),y[8:12].hex()),('a300c37e','a301fffe'))
        self.assertEqual((ROOT/match.GUARDS).read_bytes(),(self.out/'match-frozen'/match.GUARDS).read_bytes());self.receipt('owner',raw_words=72,frame=32,guards=0,byte_corruptions=288,binding_corruptions=11,neighbors=10,raw_options_GPR_mask_closed=True,local_record_pointer_not_legacy_array=True,shared_headers_unchanged=True)
    def test_02_fullword_commands_byte_gates_and_live_callbacks(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        missing=[i for i in range(72)if match.ENTRY+4*i not in seen];self.assertEqual(missing,[52]);self.receipt('guest',cases_per_body=count,bodies=2,all_256_commands_gate_and_status_bytes=True,fullword_query_commands_and_secondary=True,live_state_and_base_pointer=True,unreachable_duplicate_load_word=52,raw_C_literal_identity=True)
    def test_03_aliases_incoming_homes_and_access_prefixes(self):
        count=cuts=0
        for alias,command,mutation,phase in itertools.product(range(5),(0,7,0x2B,0x2C,255),(0,7,8),(0,8)):self.compare(g.Case(alias=alias,command=command,mutation=mutation,phase=phase));count+=1
        for c in(g.Case(),g.Case(mutation=7,connected=1),g.Case(alias=2),g.Case(alias=3),g.Case(mutation=8)):
            initial=g.fixture(c);code=g.helper_code(self.rom,c);full=g.Oracle(self.retail,initial,c,connected=code).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        self.receipt('faults',alias_home_cases_per_body=count,fired_access_cuts=cuts,literal_full_state_equal=True,global_command_base_and_owner_state_pointer_aliases=True,guest_home_mutations=True,portable_C_fault_or_arbitrary_pointer_difference_not_claimed=True)
    def test_04_original_bit_helpers_and_unmapped_early_outs(self):
        count=0;seen=set()
        for command,query,mask in itertools.product(range(256),(0,1),(0,255)):
            for m in self.compare(g.Case(command=command,query=query,mask=mask,connected=1)):seen.update(m.visits)
            count+=1
        self.assertTrue(set(range(g.QUERY,g.QUERY+76,4))<=seen);self.assertTrue(set(range(g.BITS,g.BITS+32,4))<=seen)
        for c in(g.Case(null=True),g.Case(active=0),g.Case(gate=255)):
            initial=g.fixture(c)
            for i in range(256):initial.pop(g.STATE+i,None);initial.pop(g.OTHER+i,None)
            if c.null:
                for i in range(0x32C):initial.pop(g.ACTOR+i,None)
            m=g.Oracle(self.words,initial,c).run();self.assertFalse(m.calls)
        self.receipt('helpers',cases_per_body=count,original_predicate_words=19,original_bit_split_words=8,all_helper_words_visited=True,early_outs_need_no_state_storage=True)
    def test_05_original_script_caller_window(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(allwords)if w==jal],[0xCF0C0]);self.assertFalse(any(w in(match.ENTRY,0x08000000|(match.ENTRY>>2&0x3FFFFFF))for w in allwords));start,end=0x150A1BFC,0x150A1CF8;count=0;descriptor=0xA0000
        for command,record,phase,mutation in itertools.product((0,7,0x2B,0x2C,128,255),(0,36,72),(0,8),(0,7)):
            c=g.Case(command=command,record=record,phase=phase,mutation=mutation);initial=g.fixture(c);initial[descriptor+0x17]=command;g.put(initial,descriptor+0x18,0x87654321);expected,calls=g.reference(initial,c);pair=[]
            for w in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+288,4),w));code[end]=0;m=g.Oracle(struct.unpack_from('>9I',self.rom,start-0x15000000+0x2D4B0),initial,c,entry=start,connected=code,arguments=());m.r[2]=descriptor;m.r[16]=g.TABLE;m.r[17]=g.ACTOR;m.r[3]=record*52;m.code=WindowCode(m.code,m);m.code.ends=(end,);saved=tuple(m.r[i]for i in(*range(16,24),28,29,30))
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.calls,[(match.ENTRY,g.args(c))]+calls);self.assertEqual(g.public(m.memory,c),g.public(expected,c));self.assertEqual(g.read(m.memory,g.STACK+phase+0x10),0x87654321);self.assertEqual(tuple(m.r[i]for i in(*range(16,24),28,29,30)),saved);pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('caller',cases_per_body=count,original_window_words=9,actor_record_secondary_and_unsigned_command_verified=True,extra_fifth_home_word_preserved_and_unused=True,saved_GPR_GP_SP_FP_fixed=True,full_script_interpreter_not_claimed=True)
    def test_06_independent_GNU_links_and_rebases(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:(entry+0x10000*(j+1)if n.startswith('func_')else 0x81007FFC+0x10000*j)for j,n in enumerate(s)}
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:
                            typ,sym=match.BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[288:],bytes(len(blob)-288));images.append(list(struct.unpack_from('>72I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_owner']),s))
            for command,mutation,secondary in itertools.product((7,0x2B,0x2C,255),(0,7),(0,1)):self.compare(g.Case(command=command,mutation=mutation,secondary=secondary),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_eleven_bindings=True,signed_low16_carry=True,JAL_region=True,zero_standalone_tail=True)
    def test_07_SDK_native32_and_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-2000:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=255,SDK_native32_UBSan=True,record_differences_within_single_73_entry_array=True,private_guest_aliases_and_negative_array_indices_not_claimed=True)
    def test_08_literal_full_image_and_rejected_array_shape(self):
        q=json.loads((self.out/'candidate-screens-legacy-array-rejected.json').read_text());self.assertEqual((q[0]['words'],q[0]['frame'],q[0]['differences']),(72,32,10));before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),226);at=match.elf_slot_offset(before,match.ENTRY,288)
        for off in(0,at,at+287,at+288,0x29D100,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        m=g.Oracle(struct.unpack_from('>72I',before,at),g.fixture()).run();self.assertFalse(m.calls);self.receipt('image',strict_changed_bytes=226,exclusions=0,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,legacy_array_control_differences=10,stub_rejected=True,CSV_and_Make_fixed=True)
if __name__=='__main__':unittest.main()
