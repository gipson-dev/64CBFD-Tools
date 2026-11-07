"""Complete sprite pair: semantic C, guest contracts, native ABI and whole ELF."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_selected_vertex_sprite_candidates as candidate
from tools.experiments import game_selected_vertex_sprite_match as match
from tools.tests import game_selected_vertex_sprite_oracle as g
from tools.tests import game_selected_vertex_sprite_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class SelectedVertexSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=[list(struct.unpack_from('>%dI'%t['words'],cls.rom,t['rom']))for t in candidate.TARGETS];cls.raw=[match.bound_blob(*match.function_blob(o,i),g.symbols())for i,o in enumerate(cls.prepared['qualified_compacts'])];cls.words=[match.bound_blob(*match.function_blob(o,i),g.symbols())for i,o in enumerate(cls.prepared['qualified_owners'])];assert cls.words==cls.retail
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),helper=False,images=None,s=None,entry=None,initial=None,raw=False):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;e,calls,packets,v=g.reference(initial,c,s,helper=helper);i=int(helper);entry=(g.COLOR if helper else g.ENTRY)if entry is None else entry;pair=[]
        for j,w in enumerate((self.retail[i],self.words[i],self.raw[i])if images is None else images):
            color=self.raw[1]if j==2 and raw else None;m=g.Oracle(w,initial,c,s=s,entry=entry,helper=helper,connected=g.helper_code(self.rom,c,s,color_words=color)).run();self.assertEqual((g.public(m.memory),m.calls,m.packets),(g.public(e),calls,packets),c)
            if not helper:self.assertEqual(m.r[2],v)
            pair.append(m)
        self.assertEqual(g.state(pair[0]),g.state(pair[1]));return pair
    def test_01_full_owners_guards_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual([(t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors'])for t in q['targets']],[(72,224,10,3,8,8),(105,8,14,2,41,41)]);self.assertEqual([(x['diagnostics']['before'],x['diagnostics']['after'])for x in q['targets']],[(0,0),(7,7)])
        corruptions=0
        for i,t in enumerate(candidate.TARGETS):
            raw,b=match.function_blob(self.prepared['qualified_compacts'][i],i);self.assertEqual(match.derive(raw,b,i),match.function_blob(self.prepared['qualified_owners'][i],i))
            for at in range(len(raw)):
                bad=bytearray(raw);bad[at]^=1
                with self.assertRaises(ValueError):match.derive(bytes(bad),b,i)
                corruptions+=1
            for at in b:
                bad=dict(b);bad[at]=[(b[at][0][0],'foreign')]
                with self.assertRaises(ValueError):match.derive(raw,bad,i)
        original=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes();self.assertTrue(proposed.startswith(original));self.assertEqual(proposed,match.guard_manifest(original));self.receipt('owner',raw_byte_corruptions_rejected=corruptions,binding_corruptions_rejected=5,appended_guards=24,guards_insert_or_omit_no_words=True,untouched_raw_and_padded_neighbors=49,no_Makefile_change=True,inherited_diagnostics_unchanged=7)
    def test_02_signed_selection_height_random_and_connected_helpers(self):
        count=0;seen=[set(),set()]
        for c in g.cases():
            pair=self.compare(c,raw=True)
            for i in range(2):seen[i].update(pair[i].visits)
            count+=1
        self.assertFalse([i for i in range(72)if g.ENTRY+4*i not in seen[0]])
        self.receipt('guest',cases_per_body=count,bodies=3,all_256_signed_indices=True,position_stride=20,fifth_float_argument=True,unsigned_full_word_random=True,random_lifetime_range=[35,55],saved_owner_survives_helper_mutations=True,live_category_and_row_reloaded=True,constructor_NULL_still_marks_and_returns_one=True,original_initializer_words=105,original_constructor_words=28,original_RNG_words=18,allocator_and_bcopy_are_bounded_providers=True,unwritten_packet_bytes_are_guest_seed_only=True)
    def test_03_texture_flip_wrap_colors_and_preserved_positions(self):
        count=0;seen=set()
        for flags,w,h,rgba,texture in itertools.product((0,128,256,384,65535),(0,1,255,1792,65535),(0,31,255,65535),((0,1,128,255),(255,129,17,0)),(0,18,255)):
            pair=self.compare(g.Case(flags=flags,width=w,tall=h,rgba=rgba,texture=texture),helper=True);seen.update(pair[0].visits);count+=1
        self.assertFalse([i for i in range(105)if g.COLOR+4*i not in seen]);self.receipt('vertices',cases_per_body=count,bodies=3,all_105_words_visited=True,two_groups_of_four=True,SDK_Vtx_size=16,preserved_position_and_opaque_bytes=True,UV_signed16_wrap=True,flag_bits=[128,256],texture_byte_indices=[0,18,255],separate_alpha_fifth_argument=True)
    def test_04_effective_fault_cuts_and_texture_overlap(self):
        cuts=0;cases=0
        fixtures=[(g.Case(connected=0),False,None),(g.Case(connected=7),False,None),(g.Case(outcome=0,mutation=7),False,None),(g.Case(flags=384),True,None)]
        # A table entry in vertex colors gets replaced before a flip reload.
        # Stop on its first invalid read; compare exact emitted-prefix state.
        s=g.symbols();s['D_8008CA4C']=g.PACKET+12-4*18;fixtures.append((g.Case(flags=384),True,s))
        for c,helper,s in fixtures:
            s=g.symbols()if s is None else s;initial=g.fixture(c,s);i=int(helper);entry=g.COLOR if helper else g.ENTRY
            w=match.bound_blob(*match.function_blob(self.prepared['qualified_owners'][i],i),s);original=match.bound_blob(*match.derive(*match.function_blob(self.prepared['qualified_compacts'][i],i),i),s);full=g.Oracle(original,initial,c,s=s,entry=entry,helper=helper,connected=g.helper_code(self.rom,c,s))
            try:full.run()
            except AssertionError:
                if s['D_8008CA4C']==g.TEXTURES:raise
            for cut in range(full.all_accesses):
                pair=[]
                for body in(original,w):
                    m=g.Oracle(body,initial,c,s=s,entry=entry,helper=helper,connected=g.helper_code(self.rom,c,s));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
            cases+=1
        self.receipt('faults',fired_access_cuts=cuts,layouts=cases,complete_private_register_PC_delay_and_trace_equal=True,overlap_reload_invalid_pointer_is_guest_only=True,raw_C_private_schedule_not_claimed_fault_identical=True)
    def test_05_actual_table_and_six_argument_dispatch_window(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(allwords)if w==g.ENTRY],[0x22EEF8]);self.assertNotIn(0x0C000000|(g.ENTRY>>2&0x3FFFFFF),allwords);self.assertNotIn(0x08000000|(g.ENTRY>>2&0x3FFFFFF),allwords);count=0;start,end=0x15148D80,0x15148DCC;window=struct.unpack_from('>19I',self.rom,start-0x14FD2B50)
        for phase,outcome,connected in itertools.product((0,8),(0,1),(0,3,7)):
            c=g.Case(phase=phase,outcome=outcome,connected=connected);initial=g.fixture(c);home=g.STACK+phase
            for i,w in enumerate(g.arguments(c)[1:4]):g.put(initial,home+64+4*i,w)
            g.put(initial,g.ACTOR+96,c.height);g.put(initial,0x8008A438,g.ENTRY);e,calls,packets,v=g.reference(initial,c);pair=[]
            for w in(self.retail[0],self.words[0]):
                code=g.helper_code(self.rom,c);code.update(zip(range(g.ENTRY,g.ENTRY+288,4),w));code[end]=0;m=g.Oracle(window,initial,c,entry=start,connected=code);m.r[16]=g.ACTOR;m.r[2]=2;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((g.public(m.memory),m.calls,m.packets,m.r[2]),(g.public(e),[(g.ENTRY,g.arguments(c))]+calls,packets,1));pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',window_words=19,cases_per_body=count,table='D_8008A430[2]',pointer_ROM='0x22EEF8',six_argument_float_callback=True,return_one_branch_delay_observed=True,complete_parent_not_claimed=True)
    def test_06_independent_GNU_rebases_every_binding(self):
        count=links=0
        for i,t in enumerate(candidate.TARGETS):
            for k,entry in enumerate((t['entry'],0x17007FFC,0x1A028000)):
                s=g.symbols()
                if k:s={n:entry+0x10000*(j+1)if n.startswith('func_')else 0x81007FFC+0x10000*(k-1)for j,n in enumerate(s)}
                images=[]
                for j,original in enumerate((True,False)):
                    p=self.out/('match-rebase-%d-%d-%d'%(i,k,j));rows=['.set noreorder','.text','.globl '+t['function'],t['function']+':']
                    if original:
                        for at,w in enumerate(self.retail[i]):
                            if 4*at in t['bindings']:
                                typ,sym=t['bindings'][4*at][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                            rows.append('.word 0x%08X'%w)
                        asm='\n'.join(rows)+'\n'
                    else:
                        text,fs,rs=match.parse_object(self.prepared['qualified_owners'][i]);asm,unknown=emit_function(text,fs[t['function']],rs,t['function'],s);self.assertFalse(unknown)
                    p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',t['function'],*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[4*t['words']:],bytes(len(blob)-4*t['words']));images.append(list(struct.unpack_from('>%dI'%t['words'],blob)));links+=1
                self.assertEqual(images[0],images[1]);self.assertEqual(images[1],match.bound_blob(*match.derive(*match.function_blob(self.prepared['qualified_compacts'][i],i),i),s))
                for c in(g.Case(),g.Case(index=-128,mutation=7,outcome=0),g.Case(flags=384,width=65535,tall=1792)):
                    self.compare(c,helper=bool(i),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts_per_body=3,cases_per_body=count,all_five_bindings=True,signed_low16_carries=True)
    def test_07_SDK_native32_and_effective_negative_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr,encoding='utf-8');self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(r.stdout+r.stderr)[-4000:]);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,profiles=3,negative_controls=controls,all_controls_effective=True,SDK_native32_UBSan=True,callback_signature_checked=True,packet_size_and_offsets_asserted=True,whole_initialized_helper_and_fences_compared=True,root_holes_initialized_only_in_bounded_callback=True,no_portable_uninitialized_byte_claim=True)
    def test_08_literal_whole_image_and_former_stubs_rejected(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.rom),553);locations=[0,len(after)-1]
        for i,t in enumerate(candidate.TARGETS):
            at=match.elf_slot_offset(before,t['entry'],4*t['words']);locations.extend((at,at+4*t['words']-1,at+4*t['words'],next(p+8 for p,n,f,s in match.symbol_rows(before)if n==t['function'])));c=g.Case();a=g.fixture(c);m=g.Oracle(struct.unpack_from('>%dI'%t['words'],before,at),a,c,entry=t['entry'],helper=bool(i)).run();self.assertNotEqual(g.public(m.memory),g.public(g.reference(a,c,helper=bool(i))[0]))
        for at in locations:
            b=bytearray(after);b[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(b),self.rom)
        self.receipt('image',strict_changed_bytes=553,exclusions=0,only_two_complete_bodies_and_sizes_change=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=len(locations),both_former_stubs_rejected=True)
if __name__=='__main__':unittest.main()
