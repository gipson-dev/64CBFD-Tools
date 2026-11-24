#!/usr/bin/env python3
"""Fail closed before binding this compact owner's literal pool to retail data."""
import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from .pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, read_c_string
else:
    from pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, read_c_string

NAME='func_150C8A68'

def verify(path):
    path=Path(path);data=path.read_bytes();header=ELF_HEADER.unpack_from(data)
    if header[0][:6]!=b'\x7fELF\x01\x02' or header[1]!=1 or header[2]!=8:
        raise ValueError('Expected a big-endian MIPS ELF32 relocatable object')
    headers=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
    names=headers[header[13]];strings=data[names[4]:names[4]+names[5]]
    rodata=[h for h in headers if read_c_string(strings,h[0])=='.rodata']
    if len(rodata)!=1 or rodata[0][1]!=1 or rodata[0][2]&1 or not rodata[0][2]&2:
        raise ValueError('Expected one allocated, non-writable literal section')
    manifest=json.loads((Path(__file__).parent/'experiments/game_ring_updater_150c8a68_manifest.json').read_text())
    section=rodata[0];pool=data[section[4]:section[4]+section[5]]
    if len(pool)!=16 or hashlib.sha256(pool).hexdigest()!=manifest['constant_pool_sha256']:
        raise ValueError('Ring updater literal values/order changed; retail binding rejected')
    text,functions,relocations=parse_object(path)
    if NAME not in functions:raise ValueError('Ring updater function missing from owner')
    fn=functions[NAME];raw=text[fn['value']:fn['value']+fn['size']]
    if len(raw)!=848 or hashlib.sha256(raw).hexdigest()!=manifest['raw_body_sha256']:
        raise ValueError('Ring updater compiler body changed; update qualification first')
    refs={str(at-fn['value']):[list(x) for x in values] for at,values in relocations.items() if fn['value']<=at<fn['value']+fn['size']}
    if refs!=manifest['raw_relocations']:raise ValueError('Ring updater relocation set changed')
    if any(name=='.rodata' for at,values in relocations.items() if not fn['value']<=at<fn['value']+fn['size'] for kind,name in values):
        raise ValueError('Another function uses this pool; owner binding needs review')
    return dict(function=NAME,body_words=212,literal_bytes=16,pool_sha256=manifest['constant_pool_sha256'],verified=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('object',type=Path);args=parser.parse_args()
    try:report=verify(args.object)
    except (ValueError,OSError) as exc:parser.exit(1,'Ring updater literal binding check failed: '+str(exc)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
