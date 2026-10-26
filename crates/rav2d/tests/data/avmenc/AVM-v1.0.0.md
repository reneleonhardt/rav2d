The `avmenc-v1-*` streams and raw displayed-sample MD5 hashes come from the
[official AVM v1.0.0 release](https://github.com/AOMediaCodec/avm/tree/v1.0.0),
commit `966a7d7cd6fcf60360caf5dc413b2aeeb65e144d`.

Regenerate with `tools/vectors/v1.0.0.sh <AVM source dir> <AVM build dir>`.
The script checks the source revision and derives three 64×64 input frames
from the shipped bus clip using AVM's decoder. It encodes 8-bit and 10-bit
4:2:0 streams, plus separate LCR and operating-point-set signaling cases.
Neither rav2d nor dav2d supplies the expected hashes.

The Configurable-profile unit test replaces only `seq_profile_idc` with 31
in the 8-bit sequence header. AVM v1.0.0 decodes that stream to the same hash;
it is a valid unsupported profile, not a reserved profile identifier.
