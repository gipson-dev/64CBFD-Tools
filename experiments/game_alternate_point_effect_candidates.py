"""Screen the alternate point/height effect callback using the established family."""
import hashlib,itertools,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_point_interval_effect_candidates import OLD_TYPE,RESULT_TYPE
from tools.experiments.game_point_interval_effect_candidates import SELECTED as FAMILY_BODY
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_15146D60','generated_173D40'
SOURCE='conker/src/game/generated_173D40.c'
BUILD='conker/build/game-alternate-point-effect-candidates'
ENTRY,ROM,WORDS,SLOT_WORDS=0x15146D60,0x174210,73,73
PLACEHOLDER='s32 func_15146D60() {\n    return 0;\n}'
DECLARATIONS='''extern f32 D_800A5728, D_800A572C;
void func_15141F78(u8, u8 *, f32, u8, f32 *, u8);

'''
SELECTED=FAMILY_BODY.replace('func_150EB090','func_15146D60').replace('func_150EAF50','func_15146890').replace('D_800A1470','D_800A5728').replace('D_800A1474','D_800A572C')
SELECTED=SELECTED.replace('    HeightResult71820 result;','    HeightResult71820 result;\n    s32 selected = (u8)mode;').replace('&result, mode)','&result, selected)').replace('position, mode);','position, selected);')

def source_states(live):
    marker='#include <ultra64.h>\n\n'
    if live.count(PLACEHOLDER)==1 and live.count(OLD_TYPE)==1 and SELECTED not in live and DECLARATIONS not in live:
        return live,live.replace(OLD_TYPE,RESULT_TYPE,1).replace(marker,marker+DECLARATIONS,1).replace(PLACEHOLDER,SELECTED,1),False
    if live.count(SELECTED)==1 and live.count(RESULT_TYPE)==1 and live.count(DECLARATIONS)==1 and PLACEHOLDER not in live:
        return live.replace(RESULT_TYPE,OLD_TYPE,1).replace(DECLARATIONS,'',1).replace(SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Alternate point effect source state changed')

def source_with(body=SELECTED):return source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)

def compare(label='selected',body=SELECTED):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    obj,diagnostics=compile_owner(ROOT,out,source_with(body),label)
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];raw=text[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+WORDS*4]
    differences=[dict(offset=i*4,ours=a,retail=b)for i,(a,b)in enumerate(itertools.zip_longest(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>%dI'%WORDS,truth),fillvalue=0))if a!=b]
    return dict(words=size//4,differences=differences,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),
        diagnostics=diagnostics,bindings={at-start:r for at,r in rs.items()if start<=at<start+size})

if __name__=='__main__':print(json.dumps(compare(),indent=2))
