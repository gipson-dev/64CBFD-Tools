"""Complete guarded match gates, extending the independent raw-C recovery tests."""
from copy import deepcopy
from pathlib import Path
import json,struct,subprocess
from tools.tests.test_game_list_render_1517e28c_recovery import ListRenderRecoveryTests
from tools.experiments import game_list_render_1517e28c_recovery as s
from tools.experiments import game_list_render_1517e28c_match as match
from tools.tests.game_list_render_1517e28c_normalizer import derive,original,OUT
from tools.tests.game_list_render_1517e28c_proof import prove,negative_controls
from tools.experiments.game_actor_classifier_candidates import sections

class ListRenderMatchTests(ListRenderRecoveryTests):
    def test_06_closed_derivation_and_independent_links(self):
        raw,refs=s.payload(s.OUT/'banked-screen/candidate.o',s.FUNCTION)
        derived,bindings,report=derive(raw,refs);expected,oldrefs=original()
        self.assertEqual((derived,bindings),(expected,oldrefs))
        self.assertEqual(s.bind(derived,bindings),self.retail)
        self.assertEqual(report['source_origins_retained'],130)
        self.assertEqual(report['omitted_duplicate_origins'],[67,76])
        bad=bytearray(raw);bad[3]^=1
        with self.assertRaisesRegex(ValueError,'payload'):derive(bytes(bad),refs)
        altered=deepcopy(refs);at=next(at for at,rs in altered.items()if rs[0][0]=='R_MIPS_26')
        altered[at]=[('R_MIPS_26','func_1517E28C')]
        with self.assertRaisesRegex(ValueError,'bindings'):derive(raw,altered)
        linked=[];folder=OUT/'independent-links';folder.mkdir(exist_ok=True)
        for n,(entry_shift,code_shift,data_shift)in enumerate(((0,0,0),(0x1000,0x2000,0x12348))):
            objects=[]
            for label,payload,relocs in(('derived',derived,bindings),('original',expected,oldrefs)):
                text=['.set noat','.set noreorder','.text','.globl '+s.FUNCTION,'.type '+s.FUNCTION+', @function',s.FUNCTION+':']
                for i,w in enumerate(struct.unpack('>135I',payload)):
                    for kind,name in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+name)
                    text.append('.word 0x%08X'%w)
                text.append('.size '+s.FUNCTION+',.-'+s.FUNCTION)
                p=folder/(label+'-'+str(n)+'.s');p.write_text('\n'.join(text)+'\n');obj=p.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
                script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(s.ENTRY+entry_shift))
                anchors={name:int(name.split('_')[1],16)+(code_shift if name.startswith('func_')else data_shift)for rs in relocs.values()for kind,name in rs}
                elf=p.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
                objects.append(sections(elf)['.text'][1])
            self.assertEqual(objects[0],objects[1]);linked.append(dict(entry_shift=entry_shift,code_shift=code_shift,data_shift=data_shift))
        report.update(independent_GNU_links=linked,payload_and_binding_controls_rejected=True)
        (OUT/'derivation.json').write_text(json.dumps(report,indent=2)+'\n')

    def test_07_inductive_normal_execution_relation(self):
        report=prove(self.words,self.retail);self.assertEqual(report['paths'],{'prefix-kind0':2,'prefix-kind1':2,'loop-kind0':38,'loop-kind1':38})
        controls=negative_controls(self.words,self.retail);self.assertEqual(controls['effective_semantic_controls'],8)
        (OUT/'inductive-proof.json').write_text(json.dumps(report,indent=2)+'\n')
        (OUT/'proof-controls.json').write_text(json.dumps(controls,indent=2)+'\n')

    def test_08_padders_actual_Make_and_whole_image(self):
        report=match.qualify();self.assertTrue(report['strict_predicted_ELF_equal'])
        self.assertEqual((report['guard_rows'],report['exclusions'],report['function_slots']),(43,0,6051))
        self.assertEqual(report['changed_bytes'],452)
        self.assertEqual(report['actual_Make']['commands'],5)
        self.assertEqual(report['caller_actual_Make']['commands'],3)

# Imported TestCase is a reusable parent, not a second suite in this module.
del ListRenderRecoveryTests
if __name__=='__main__':
    import unittest
    unittest.main()
