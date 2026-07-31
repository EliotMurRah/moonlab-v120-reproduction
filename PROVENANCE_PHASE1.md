# Phase 1 Provenance — recorded 2026-07-31T14:52Z

## Pinned environment (venv, Python 3.12.11, arm64)
- contourpy==1.3.3
- cycler==0.12.1
- fonttools==4.63.0
- kiwisolver==1.5.0
- matplotlib==3.11.1
- moonlab==1.2.0
- networkx==3.6.1
- numpy==2.5.1
- packaging==26.2
- pillow==12.3.0
- PyMatching==2.4.0
- pyparsing==3.3.2
- python-dateutil==2.9.0.post0
- scipy==1.18.0
- six==1.17.0
- stim==1.16.0

## MoonLab source (for phase 2 vendor harness)
- repo: https://github.com/tsotchke/moonlab.git
- tag: v1.2.0 (tag object f8e552759b19dc459b093b9ff4abaacaa22befbb)
- peeled commit: 4bf83a6c47e7f1c53db14fcb2a61053499fd82df
- build profile: cmake Release, default options, build dir build-f3 (per vendor usage note)

## Key binary hashes (pip wheel payload)
- libquantumsim.dylib: 677c8460cede2effcd25dd96c7130547e93165ae9ebd62cbfddf52fccbf29125

## Host
- macOS 26.5.2 (25F84), Apple M2 Pro, 16 GiB, arm64
- Phase 1 smoke: moonlab bell entropy=1.0; stim bell agreement=1.0; pymatching decode OK
