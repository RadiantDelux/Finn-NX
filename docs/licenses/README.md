# Dependency notices

- `libnx.txt`: ISC notice from
  [aks796/libnx32](https://github.com/aks796/libnx32/blob/master/LICENSE.md),
  also covering the original libnx authors.
- `mesa.txt`: text of the license documentation from the
  [mesa32 Switch branch](https://github.com/aks796/mesa32/blob/switch-20.1.0-rc3/docs/license.html).

`tools/licenses.py` assembles these with the project's, android32's, miniz's
and nx-hbloader's notices. The result is embedded in the NRO and included in
release archives. Source-file notices and the attribution in `THIRD_PARTY.md`
remain applicable.
