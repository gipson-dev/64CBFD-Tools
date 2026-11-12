"""Verify the direct-match fingerprint rejects altered code and bindings."""
from tools.experiments import game_oscillating_effect_151db97c_match as p

def main():
    raw,refs=p.payload(p.out/'independent-selected.o')
    p.normalize(raw,refs)
    rejected=0
    for i in range(75):
        bad=bytearray(raw);bad[4*i]^=1
        try:p.normalize(bytes(bad),refs)
        except ValueError:rejected+=1
        else:raise AssertionError(('code mutation accepted',i))
    for at in refs:
        bad={k:list(v)for k,v in refs.items()}
        bad[at]=[(bad[at][0][0],bad[at][0][1]+'_mutated')]
        try:p.normalize(raw,bad)
        except ValueError:rejected+=1
        else:raise AssertionError(('binding mutation accepted',at))
    return dict(rejected_corruptions=rejected,word_mutations=75,relocation_mutations=len(refs),guards=0)
