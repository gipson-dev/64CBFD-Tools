"""Checked bijective FP schedule, with a logical adapter for the fixed leaf frame.

The adapter initializes SP and presents its already checked return-delay restore
to the existing linear expression model. It never changes an emitted object.
NaN payloads, FCSR and fault timing are outside this raw expression proof.
"""
import hashlib,struct
from tools.experiments.game_linear_float_dataflow import derive
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_dual_point_weighted_motion_candidates as candidate
BINDINGS={0:[('R_MIPS_HI16','D_800BE9A4')],4:[('R_MIPS_LO16','D_800BE9A4')]}
RAW_SHA='927093f0ba456cfad81ef1edffd861e8ed79f70842661b4fb8962fe61e36ace5'
RETAIL_SHA='829cec7ca3ab5bb329bde5c47bc0700f06f40dc36a274dee944842f31fc71ec8'
SCHEDULE=(
    (0x0BC,0xC48E0038,0xC4800038),
    (0x0C4,0xC490003C,0xC482003C),
    (0x0D0,0x460E4281,0x46004281),
    (0x0D4,0x46123100,0x46069100),
    (0x0E8,0x46105181,0x46025181),
    (0x0EC,0x460E2200,0x46040200),
    (0x0FC,0x46104280,0x46081280),
)

def logical(words,home):
    if len(words)!=67 or words[2]!=0x27BDFFE8 or words[-2:]!=[0x03E00008,0x27BD0018]:raise ValueError('Weighted-motion real frame or return delay changed')
    if words[22]!=0x24020001:raise ValueError('Weighted-motion return lifetime changed')
    prefix=[0x3C1D0000|(((home+0x8000)>>16)&65535),0x27BD0000|(home&65535)]
    return prefix+words[:-2]+[words[-1],words[-2],0]

def normalized(raw,bindings,truth,step=0x800BE9A4,home=0x40000):
    if len(raw)!=268 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Weighted-motion complete raw body/bindings changed')
    if len(truth)!=268 or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA:raise ValueError('Weighted-motion retail body changed')
    natural=list(struct.unpack('>67I',raw));unbound=list(struct.unpack('>67I',truth));unbound[0]&=0xFFFF0000;unbound[1]&=0xFFFF0000
    wanted=bound_blob(struct.pack('>67I',*unbound),BINDINGS,dict(D_800BE9A4=step));resolved=bound_blob(raw,bindings,dict(D_800BE9A4=step))
    bases=[0x30000]+[step-i for i in range(0,0x144,4)]+[home-20-i for i in range(0,0x144,4)]
    proof=derive(logical(resolved,home),logical(wanted,home),bases);fitted=proof.pop('fitted_words')
    if proof['permutation']!=list(range(70)):raise ValueError('Weighted-motion proof moved an instruction')
    fitted=fitted[2:-3]+[fitted[-2],fitted[-3]]
    if fitted!=wanted:raise ValueError('Weighted-motion logical adapter lost original words')
    fitted[:2]=natural[:2];result=struct.pack('>67I',*fitted)
    changes=[(4*i,a,b)for i,(a,b)in enumerate(zip(natural,fitted))if a!=b]
    if changes!=list(SCHEDULE):raise ValueError('Weighted-motion derived schedule changed')
    proof.update(words=67,modeled_words=70,changed_words=len(SCHEDULE),instruction_permutation_identity=True,real_frame=24,real_weight_SP_offset=4,logical_adapter_not_emitted=True,raw_fault_or_NaN_payload_parity_claimed=False)
    return result,proof
