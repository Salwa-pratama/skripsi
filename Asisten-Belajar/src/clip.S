    .section .rodata
    .global clip_start
    .global clip_end
    .align 4
clip_start:
    .incbin "src/clip_alive.raw"
clip_end:
