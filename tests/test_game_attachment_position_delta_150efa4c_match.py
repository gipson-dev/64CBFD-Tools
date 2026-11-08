"""Attachment callback C, closed normalization, real dispatcher and entire ELF."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_attachment_position_delta_150efa4c_match as source
from tools.tests import game_attachment_position_delta_150efa4c_oracle as guest
class AttachmentPositionDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
        cls.q['retail_words']=struct.unpack_from('>77I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM)
        guest.original_object(source,cls.q,cls.out)
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_words_frame_closed_roles_and_effective_scope_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['preserved_labels']),(77,77,24,42,43,43,0))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6052,271,0,0))
        raw,refs=self.q['raw'],self.q['refs'];self.assertEqual(source.normalize(raw,refs),(self.q['normal'],self.q['normal_refs']))
        certificate=source.certificate(raw);self.assertEqual(len(certificate['register_closures']),4)
        self.assertEqual([r['independent_adjacent_swaps']for r in certificate['schedule_blocks']],[24,4,2])
        w=struct.unpack('>77I',raw)
        with self.assertRaises(AssertionError):source.rename_closure(w,14,46,{10:3},(4,5,6,29,31))
        wrong=list(range(46,64));wrong[2],wrong[6]=wrong[6],wrong[2]
        with self.assertRaises(AssertionError):source.reorder(w,46,wrong)
        for i in range(77):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();rows=source.guard_rows(raw,refs)
        self.assertEqual((len(rows),sum(r[-1]=='true'for r in rows)),(42,0));self.assertTrue(source.guard_manifest(prefix,raw,refs).startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        paths=[self.out/(n+'.o')for n in('predecessor-owner','qualified-owner','qualified-isolated')];sections=[source.sections(p)for p in paths]
        for which in range(3):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.receipts['scope']=dict(words=77,frame=24,guards=42,omissions=0,insertions=0,raw_word_corruptions=77,altered_bindings=5,register_metadata_corruptions=72,raw_and_padded_neighbors=43,diagnostics=0,certificate=certificate)
    def test_02_mutable_guest_snapshots_aliases_and_normalized_fault_prefixes(self):self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_point_helper_and_registered_return_consumer(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if source.ENTRY<=w<source.ENTRY+308],[0x234400])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and source.ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<source.ENTRY+308],[])
        self.receipts['connections']=guest.connections(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_symbol_links_rebased_execution_and_literal_image(self):
        executed=0
        for i,symbols in enumerate(guest.symbols(i)for i in range(3)):
            p=self.out/('independent-link-'+str(i));entry=source.ENTRY if i==0 else 0x17508000;lines=['.set noreorder','.set noat','.text','.globl selection','selection:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                label='w%d'%j;lines.append(label+': .word 0x%08X'%w)
                lines+=['.reloc '+label+', '+kind+', '+name for kind,name in self.q['normal_refs'].get(j*4,[])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('\n'.join(n+' = 0x%X;'%a for n,a in symbols.items())+'\nSECTIONS{.text 0x%X : SUBALIGN(4) { *(.text) }}\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=struct.unpack('>77I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['normal'],self.q['normal_refs'],symbols)))
            for gate,matrix,mode in((0,0,0),(1,0,0),(1,guest.MATRIX,15),(255,guest.MATRIX,8)):
                c=guest.Case(gate=gate,matrix=matrix,mutation=mode,index=255);initial,s=guest.fixture(c,symbols)
                wanted,calls,obs=guest.reference(initial,c,s);m=guest.Oracle(linked,initial,c,entry=entry,s=s).run()
                self.assertEqual((m.memory,m.calls,m.point_observations),(wanted,calls,obs));executed+=1
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=struct.pack('>77I',*self.q['retail_words'])
        self.assertEqual(source.strict_image(before,after,truth),271)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        at=[64,source.elf_slot_offset(before,source.ENTRY,308),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)]
        for names,order in source.METADATA_GROUPS:
            group=sorted((r for r in source.symbol_rows(before)if r[1]in names),key=lambda r:r[0]);at.extend(r[0]+4 for r in group);at.append(group[0][3])
        self.assertEqual(len(at),11)
        for offset in at:
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=271,exclusions=0,independent_links=3,rebased_guest_cases=executed,bindings=5,corruption_controls=11,named_metadata_groups=2,named_metadata_rows=5)
    def test_06_frozen_inputs_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),106)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertTrue((self.out/'qualified-guards.csv').read_bytes().startswith((self.out/'frozen'/source.GUARDS).read_bytes()))
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],3);self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.receipts['inputs']=dict(frozen_inputs=106,actual_Make_commands=3,complete_owner_functions=44,current_installed=installed,guard_prefix_unchanged=True)
if __name__=='__main__':unittest.main()
