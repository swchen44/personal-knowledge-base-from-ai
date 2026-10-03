from pathlib import Path
import subprocess,json,re
root=Path(__file__).resolve().parent.parent/'percepio/TraceRecorder'
work=Path('/private/tmp/percepio-research/rv32-objects'); work.mkdir(parents=True,exist_ok=True)
(work/'string.h').write_text('#include <stddef.h>\nvoid *memcpy(void *, const void *, size_t);\nvoid *memset(void *, int, size_t);\nsize_t strlen(const char *);\nchar *strncpy(char *, const char *, size_t);\nint strcmp(const char *, const char *);\n')
(work/'stdio.h').write_text('#include <stddef.h>\n#include <stdarg.h>\nint snprintf(char *, size_t, const char *, ...);\nint vsnprintf(char *, size_t, const char *, va_list);\n')
cfg=(root/'config/trcConfig.h').read_text()
cfg=re.sub(r'^#error .*\n','',cfg,flags=re.M).replace('TRC_CFG_HARDWARE_PORT TRC_HARDWARE_PORT_NOT_SET','TRC_CFG_HARDWARE_PORT TRC_HARDWARE_PORT_RISCV_RV32I')
(work/'trcConfig.h').write_text(cfg)
kcfg=(root/'kernelports/BareMetal/config/trcKernelPortConfig.h').read_text().replace('TRC_CFG_CPU_CLOCK_HZ 0','TRC_CFG_CPU_CLOCK_HZ 16000000')
(work/'trcKernelPortConfig.h').write_text(kcfg)
incs=[work,root/'include',root/'kernelports/BareMetal/include',root/'streamports/RingBuffer/include',root/'streamports/RingBuffer/config']
files=sorted(root.glob('*.c'))+[root/'kernelports/BareMetal/trcKernelPort.c',root/'streamports/RingBuffer/trcStreamPort.c']
objects=[]
for src in files:
    dst=work/(src.stem+'.o')
    cmd=['/opt/homebrew/opt/llvm/bin/clang','--target=riscv32-unknown-elf','-march=rv32imac','-mabi=ilp32','-Os','-ffreestanding','-ffunction-sections','-fdata-sections']+[a for p in incs for a in ['-I',str(p)]]+['-c',str(src),'-o',str(dst)]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:
        print(src.name,p.stderr[:2000]); raise SystemExit(p.returncode)
    objects.append(str(dst))
out=subprocess.run(['/opt/homebrew/opt/llvm/bin/llvm-size',*objects],capture_output=True,text=True,check=True).stdout
(work/'sizes.txt').write_text(out)
rows=[]
for line in out.splitlines()[1:]:
    a=line.split()
    if len(a)>=6: rows.append({'text':int(a[0]),'data':int(a[1]),'bss':int(a[2]),'file':Path(a[5]).name})
result={'target':'rv32imac / ilp32','optimization':'-Os, no LTO, no final link/GC','kernel_port':'BareMetal','stream_port':'RingBuffer, 10240 bytes','compiler':subprocess.check_output(['/opt/homebrew/opt/llvm/bin/clang','--version'],text=True).splitlines()[0],'totals':{k:sum(x[k] for x in rows) for k in ['text','data','bss']},'objects':len(rows),'scope':'All root recorder C files plus BareMetal and RingBuffer ports; standard C function declarations only; excludes libc implementations, FreeRTOS kernel/hook call-site growth, network/TLS/DFM and linker garbage collection'}
(work/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
