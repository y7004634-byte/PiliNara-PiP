.text
.p2align 2
.globl _probe_replacement
_probe_replacement:
  sub sp, sp, #0x180
  stp x0,  x1,  [sp, #0x00]
  stp x2,  x3,  [sp, #0x10]
  stp x4,  x5,  [sp, #0x20]
  stp x6,  x7,  [sp, #0x30]
  stp x8,  x9,  [sp, #0x40]
  stp x10, x11, [sp, #0x50]
  stp x12, x13, [sp, #0x60]
  stp x14, x15, [sp, #0x70]
  stp x16, x17, [sp, #0x80]
  stp x18, x19, [sp, #0x90]
  stp x20, x21, [sp, #0xa0]
  stp x22, x23, [sp, #0xb0]
  stp x24, x25, [sp, #0xc0]
  stp x26, x27, [sp, #0xd0]
  stp x28, x29, [sp, #0xe0]
  str x30, [sp, #0xf0]
  mrs x9, nzcv
  str x9, [sp, #0xf8]
  stp q0, q1, [sp, #0x100]
  stp q2, q3, [sp, #0x120]
  stp q4, q5, [sp, #0x140]
  stp q6, q7, [sp, #0x160]

  mov x0, sp
  bl _probe_capture

  ldp q0, q1, [sp, #0x100]
  ldp q2, q3, [sp, #0x120]
  ldp q4, q5, [sp, #0x140]
  ldp q6, q7, [sp, #0x160]
  ldr x9, [sp, #0xf8]
  msr nzcv, x9
  ldp x0,  x1,  [sp, #0x00]
  ldp x2,  x3,  [sp, #0x10]
  ldp x4,  x5,  [sp, #0x20]
  ldp x6,  x7,  [sp, #0x30]
  ldp x8,  x9,  [sp, #0x40]
  ldp x10, x11, [sp, #0x50]
  ldp x12, x13, [sp, #0x60]
  ldp x14, x15, [sp, #0x70]
  ldp x16, x17, [sp, #0x80]
  ldp x18, x19, [sp, #0x90]
  ldp x20, x21, [sp, #0xa0]
  ldp x22, x23, [sp, #0xb0]
  ldp x24, x25, [sp, #0xc0]
  ldp x26, x27, [sp, #0xd0]
  ldp x28, x29, [sp, #0xe0]
  ldr x30, [sp, #0xf0]
  add sp, sp, #0x180

  adrp x16, _g_orig@PAGE
  ldr x16, [x16, _g_orig@PAGEOFF]
  br x16
