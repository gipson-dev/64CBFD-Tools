"""Nearest-height guarded C, both padders, real Make and complete image gates."""
import csv,json,struct,subprocess,unittest
from tools.experiments import game_nearest_height_15104634_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_nearest_height_15104634_recovery import SYMS
from tools.tests import test_game_nearest_height_15104634_recovery as recovered

class NearestHeightMatchTests(recovered.NearestHeightRecoveryTests):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def test_01_complete_owner_profile_frozen_inputs_and_corruption_gates(self):
        p=self.prepared;r=p['report']
        self.assertEqual((r['body_words'],r['frame'],r['real_word_differences'],r['unchanged_raw_neighbors']),(272,224,121,4))
        self.assertEqual(r['matching_credit'],int(r['source_installed']))
        for i in range(1088):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.checked(p['raw'],wrong)
    def test_07_register_guards_both_padders_and_actual_Make(self):
        p=self.prepared;r=p['report'];normalized=match.normalize(p['raw'])
        self.assertEqual(sum(a!=b for a,b in zip(struct.unpack('>272I',p['raw']),struct.unpack('>272I',normalized))),121)
        self.assertTrue(r['independent_padders']);self.assertTrue(r['Make']['padded_object_equal'])
        self.assertEqual((r['guards'],r['conversion_rows'],r['exclusions']),(121,0,0))
        self.assertEqual(match.payload(p['after'],match.FUNCTION),(normalized,p['refs']))
        self.receipt('guard-build-gates',dict(guards=121,independent_padders=True,actual_Make=r['Make'],all_raw_word_and_binding_corruptions_rejected=True))
    def test_08_GNU_relocations_and_closed_guard_binding_controls(self):
        p=self.prepared;out=p['out'];raw=match.normalize(p['raw']);refs={int(k):v for k,v in p['refs'].items()}
        asm,missing=emit_function(raw,dict(value=0,size=1088),refs,match.FUNCTION,SYMS);self.assertFalse(missing)
        obj=match.assemble(out,'normalized-isolated',asm);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,p['refs']))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));cmd=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                cmd+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(cmd+[str(source)],check=True,capture_output=True)
                image=elf.read_bytes();at=match.elf_slot_offset(image,entry,1088);bodies.append(image[at:at+1088])
            self.assertEqual(*bodies)
        with(out/'proposed-guards.csv').open(newline='')as stream:
            reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
        for control in('expected-word','expected-relocation'):
            broken=[dict(row)for row in rows]
            row=next(v for v in broken if v['function']==match.FUNCTION and(control=='expected-word'or v['expected_relocations']!='-'))
            if control=='expected-word':row['expected']='0x%08X'%(int(row['expected'],0)^1)
            else:row['expected_relocations']='R_MIPS_HI16:wrong_symbol'
            path=out/('bad-guard-'+control+'.csv')
            with path.open('w',newline='')as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(broken)
            with self.assertRaises(ValueError):
                match.pg.emit_padded_assembly(out/'after.o',match.ROOT/match.SPEC['full_assembly'],filename=match.SPEC['owner'],word_patches_path=path)
        self.receipt('GNU-rebases',dict(independent_links=12,rebases=6,body_bytes=1088,guards=121,effective_guard_controls=2))
    def test_09_complete_image_prediction_and_effective_corruptions(self):
        p=self.prepared;truth=(match.ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE]
        before=p['oldelf'].read_bytes();image=p['elf'].read_bytes();at=match.elf_slot_offset(image,match.ENTRY,match.SIZE)
        self.assertEqual(image,match.expected_image(before,truth));self.assertEqual(truth[-12:],b'\0'*12)
        self.assertEqual(p['report']['changed_bodies'],[match.FUNCTION]);self.assertEqual(p['report']['symbol_extent'],[12,1088])
        for pos in(0x80,len(image)-1,at,at+1088):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(wrong),truth)
        self.receipt('strict-image-controls',dict(changed_bytes=p['report']['strict_changed_bytes'],exclusions=0,slot_words=275,effective_controls=4))

if __name__=='__main__':unittest.main()
