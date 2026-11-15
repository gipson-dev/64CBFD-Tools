"""Check both override APIs and show why a padded fit alone cannot earn credit."""
import json,subprocess,sys
from tools.experiments import game_attachment_effect_150f97ec_lifetime as s
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections
def main():
    s.immutable();base=s.OUT/'lifetime-owner-before.o';guards=s.ROOT/'conker/retail_word_patches.us.csv'
    def emit(kind,label):
        kwargs=dict(word_patches_path=guards,function_objects={s.NAME:s.OUT/('lifetime-'+label+'.o')})
        if kind=='generated':return pg.emit_padded_assembly(base,s.ROOT/'conker/asm/124920.s',filename='generated_124920',**kwargs)
        return pc.emit_padded_assembly(base,s.ROOT/'conker/retail_layout.us.txt','generated_124920',**kwargs)
    rejected=[];trampolines=[]
    def assemble(text,label):
        path=s.OUT/('lifetime-'+label+'.s');obj=path.with_suffix('.o');path.write_text(text)
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=s.ROOT/'conker',capture_output=True,check=True)
        return obj
    for kind in ('generated','c'):
        for label in ('conditional_pair','conditional_triple'):
            if kind=='generated':
                try:emit(kind,label)
                except (ValueError,RuntimeError,AssertionError) as error:
                    message=str(error);assert s.NAME in message and any(w in message.lower() for w in ('size','large','exceed','fit','overflow','bytes')),message;rejected.append(dict(padder=kind,candidate=label,error=message))
                else:raise AssertionError('The strict generated padder accepted an oversized body')
            else:
                # pad_c_object intentionally supports non-matching overflow
                # trampolines. This is an acceptance of storage, not a match.
                text=emit(kind,label);obj=assemble(text,'c-overflow-'+label);raw,refs=payload(obj,s.NAME)
                overflow='__retail_overflow_'+s.NAME
                assert raw==b'\x08\0\0\0'+b'\0'*(s.SIZE-4) and refs=={0:[('R_MIPS_26',overflow)]}
                assert sections(obj)['.game_overflow'][1]==payload(s.OUT/('lifetime-'+label+'.o'),s.NAME)[0]
                assert same_functions(s.ROOT/'conker/build/src/game/generated_124920.c.o',obj,(s.NAME,))==16
                trampolines.append(dict(candidate=label,slot_bytes=s.SIZE,out_of_line_bytes=len(sections(obj)['.game_overflow'][1]),byte_match=False))
        obj=assemble(emit(kind,'early_triple'),kind+'-false-fit')
        assert same_functions(s.ROOT/'conker/build/src/game/generated_124920.c.o',obj,(s.NAME,))==16
        # Compare padded objects at the same stage. GNU as adds an empty
        # .data section; both raw compiler owners lack that section entirely.
        assert normalized_pools(s.ROOT/'conker/build/src/game/generated_124920.c.o')==normalized_pools(obj)
        assert payload(obj,s.NAME)==payload(s.OUT/'lifetime-early_triple.o',s.NAME)
        assert s.programs()['early_triple']!=s.programs()['retail']
    s.immutable();result=dict(padders=2,strict_overflow_rejections=rejected,nonmatching_c_trampolines=trampolines,apparent_fit_acceptances=2,neighbors=16,apparent_fit_not_retail=True,strict_image_and_production_adoption_not_attempted=True,c_match_credit=0)
    (s.OUT/'lifetime-padder.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
