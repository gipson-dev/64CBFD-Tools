"""Actor-context semantic schedule, callback ABI and exact overflow compaction."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_actor_context_1504add0_match as source
from tools.tests import game_actor_context_1504add0_oracle as guest
class ActorContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
        cls.q['retail_words']=struct.unpack_from('>73I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM)
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_owner_closed_schedule_and_fail_closed_guards(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(73,88,44,57,57));self.assertEqual(q['diagnostics'],0)
        self.assertEqual((q['functions_before'],q['functions_after'],q['canonical_functions']),(6053,6052,6047));self.assertTrue(q['all_canonical_addresses_fixed'])
        raw,refs=self.q['raw'],self.q['refs'];normal,nrefs=source.normalize(raw,refs);self.assertEqual(len(refs),16)
        self.assertEqual(source.Counter(r for rows in refs.values()for r in rows),source.Counter(r for rows in nrefs.values()for r in rows))
        self.assertEqual(source.Counter(w[0]>>26 for w in struct.iter_unpack('>I',raw)),source.Counter(w[0]>>26 for w in struct.iter_unpack('>I',normal)))
        for i in range(73):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();manifest=source.guard_manifest(prefix,raw,refs);self.assertEqual(manifest,(self.out/'qualified-guards.csv').read_bytes());self.assertTrue(manifest.startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        from tools import pad_c_object
        text,fs,relocs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return pad_c_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=self.out/'qualified-guards.csv')
        for row in source.guard_rows(raw,refs):
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(pad_c_object,'parse_object',return_value=(bytes(bad),fs,relocs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad=dict(relocs);bad[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(pad_c_object,'parse_object',return_value=(text,fs,bad)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        paths=[self.out/(n+'-owner.o')for n in('predecessor','qualified')];sections=[source.sections(p)for p in paths]
        for which in range(2):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.receipts['scope']=dict(words=73,frame=88,guards=44,raw_word_corruptions=73,altered_bindings=16,stale_guard_words=44,stale_guard_relocations=44,register_metadata_corruptions=48,
          raw_and_padded_neighbors=57,closed_opcode_multiset=True,closed_binding_multiset=True,pools_and_reginfo_unchanged=True)
    def test_02_signed_limits_context_order_aliases_and_faults(self):self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_caller_census_and_void_following_argument(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4]);entry=source.ENTRY
        self.assertEqual([4*i for i,w in enumerate(words)if entry<=w<entry+292],[])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and entry<=((w&0x3FFFFFF)<<2|0x10000000)<entry+292],[0x466C8])
        self.receipts['connections']=guest.connected(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_links_and_literal_overflow_closure(self):
        names=('D_800C35EA','D_800CC2D0','D_800BE728','D_8008FD8C','D_800C3E78','D_800D154C','D_800CC284','bzero','func_150ED578')
        maps=[{n:(0x100226F0 if n=='bzero'else int(n.split('_')[1],16))for n in names},dict(zip(names,(0x81308001,0x8030FFF8,0x8131FFF8,0x81328003,0x81338004,0x81348008,0x8135800C,0x17501230,0x17408000))),dict(zip(names,(0x80507FFF,0x80318004,0x8050FFF8,0x80518009,0x80520003,0x80528008,0x8053800C,0x1720FFF0,0x17308000)))]
        executed=0
        for i,symbols in enumerate(maps):
            p=self.out/('independent-link-'+str(i));entry=source.ENTRY if i==0 else 0x17508000;lines=['.set noreorder','.set noat','.text','.globl context','context:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                label='w%d'%j;lines.append(label+': .word 0x%08X'%w);lines+=['.reloc '+label+', '+kind+', '+name for kind,name in self.q['normal_refs'].get(j*4,[])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('\n'.join(n+' = 0x%X;'%a for n,a in symbols.items())+'\nSECTIONS{.text 0x%X : SUBALIGN(4) { *(.text) }}\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=struct.unpack('>73I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['normal'],self.q['normal_refs'],symbols)))
            for c in(guest.Case(disable=1),guest.Case(),guest.Case(pattern=1,mode=63)):
                initial=guest.fixture(c,symbols);wanted,calls,obs=guest.reference(initial,c,symbols);m=guest.Oracle(linked,initial,c,entry=entry,s=symbols);m.run()
                expected=[(symbols['bzero']if t==guest.ZERO else symbols['func_150ED578'],a)for t,a in calls];self.assertEqual((guest.public(m.memory),m.calls,m.observations),(guest.public(wanted),expected,obs));executed+=1
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=struct.pack('>73I',*self.q['retail_words']);proof=source.strict_image(before,after,truth)
        self.assertEqual((proof['removed_private_bytes'],proof['removed_file_bytes'],proof['rom_cursor_bytes_removed'],proof['strict_exclusions']),(296,328,288,0))
        self.assertEqual(proof['retargeted_trampolines'],['func_1505210C','func_150768DC']);self.assertEqual(len(proof['moved_private_definitions']),5)
        old_overflow=source.sections(self.q['predecessor_elf'])['.game_overflow'][1];new_overflow=source.sections(self.q['qualified_elf'])['.game_overflow'][1];self.assertEqual(new_overflow,old_overflow[296:])
        h=source.ELF_HEADER.unpack_from(after);sections=[source.SECTION_HEADER.unpack_from(after,h[6]+i*h[11])for i in range(h[12])]
        root=next(r for r in source.symbol_rows(after)if r[1]==source.FUNCTION)
        sites=(64,source.elf_slot_offset(after,source.ENTRY,292),source.elf_slot_offset(after,0x1505210C,4),sections[8][4],root[0]+8,sections[10][4]+1,h[5]+16,source.elf_slot_offset(after,0x80082B20,4))
        for at in sites:
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        # Both live overflow trampolines must forward the entire untouched
        # caller state to the same byte-identical body at its derived address.
        forwarded=0
        for name in proof['retargeted_trampolines']:
            va=int(name.split('_')[1],16);old=proof['moved_private_definitions']['__retail_overflow_'+name];machines=[]
            for image,target in((before,old),(after,old-296)):
                at=source.elf_slot_offset(image,va,8);words=struct.unpack_from('>2I',image,at);m=guest.Oracle(words,guest.fixture(),entry=va);m.code[target]=0;m.code=guest.BoundaryCode(m.code,m,{target})
                try:m.run()
                except guest.WindowBoundary:pass
                else:raise AssertionError('Missing overflow forwarding boundary')
                self.assertEqual(m.boundary,target);machines.append(m)
            self.assertEqual((machines[0].r,machines[0].f,machines[0].memory),(machines[1].r,machines[1].f,machines[1].memory));forwarded+=1
        self.receipts['image']=dict(prediction=proof,independent_links=3,rebased_guest_cases=executed,bindings=16,corruption_controls=len(sites),trampolines_forwarded=forwarded,all_canonical_addresses_fixed=True)
    def test_06_frozen_inputs_complete_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),107)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertEqual((self.root/source.GUARDS).read_bytes(),(self.out/('qualified-guards.csv'if installed else'predecessor-guards.csv')).read_bytes())
        wanted=self.out/('qualified-padded'if installed else'predecessor-padded')/'game_77AD0.c.o';self.assertEqual((self.root/source.OBJECT).read_bytes(),wanted.read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],5);self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.receipts['inputs']=dict(frozen_inputs=107,actual_Make_commands=5,complete_owner_functions=58,current_installed=installed)
if __name__=='__main__':unittest.main()
