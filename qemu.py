#!/usr/bin/env python3
# qemu.py: by Brent Hartshorn
import os, sys, subprocess, json, ctypes

target = 'riscv64-softmmu'
if '--riscv32' in sys.argv: target = 'riscv32-softmmu'
if '--shared' in sys.argv:
	print("WARN: --shared is not working yet.  TODO refactor out non-relocateable globals from qapi")
	LIBQEMU = '/tmp/libqemu_%s.so' % target
else:
	LIBQEMU = '/tmp/qemu_%s' % target

stubs = 'target-get-monitor-def.c target-monitor-defs.c fw_cfg.c xen-hw-stub.c'.split()
stubs = [ os.path.join('../stubs', c) for c in stubs]
skip = ['../subprojects/libvhost-user/link-test.c']
keep = [
	'tcg',  ## accelerator for riscv on x86, 'kvm' should be used on riscv hardware
	'fdt', 'pie', 'system', 'user', #'linux-user', 
	'sdl', 'sdl-image', 'png', #'pixman', 
	'avx2', 'avx512bw','malloc-trim', 'membarrier',
	'vhost-user', #'vhost-kernel',
]

def get_features():
	feats = None
	for ln in subprocess.check_output(['./configure', '--help']).decode('utf-8').splitlines():
		print(ln)
		if ln.startswith('(unless built with --without-default-features):'):
			feats = []
			continue
		if type(feats) is list and ln.strip():
			if ln.startswith( ('      ', 'NOTE') ): continue  ## some bad formatting in the output
			name = ln.strip().split()[0]
			assert name not in feats
			feats.append(name)
	return feats

def get_o_files():
	obs = []
	a = json.loads( open('./build/compile_commands.json','rb').read().decode('utf-8') )
	for b in a:
		if b['file'] in stubs: pass
		elif b['file'].startswith('../stubs/'): continue
		elif b['output'].startswith('tests/'): continue
		#elif b['file'].startswith( ('qapi/qapi-visit', '../qapi/') ): continue
		p = os.path.join('./build', b['output'])
		if os.path.isfile(p): obs.append( p )
	print(obs)
	return obs

def rebuild():
	cmd = [
		'./configure', 
		'--target-list=%s' % target, 
		'--prefix=/opt',
	]
	if '--shared' in sys.argv:
		cmd += [
			'--with-coroutine=sigaltstack',
			'--disable-coroutine-pool',
			'--extra-cflags=-fPIC -DNO_THREAD_LOCAL -DSHARED_LIB -DUSE_VIRT_DEBUG_ALT',
		]
		cmd.append()
		for feat in get_features():
			if feat in keep: continue
			cmd.append('--disable-%s' % feat)
	else:
		cmd.append('--extra-cflags=-DUSE_VIRT_DEBUG_ALT')

	print(cmd)
	subprocess.check_call(cmd)
	cmd = ['make', '-j', '3']
	subprocess.check_call(cmd)
	cmd = ['gcc']
	if '--shared' in sys.argv: cmd.append('-shared')
	cmd += ['-o', LIBQEMU] + get_o_files() + ['-lglib-2.0', '-lm', '-lSDL2', '-lz']
	os.system(' '.join(cmd))

def qemu(exe, bits=64, vga=True, gdb=False, stdin=None, stdout=None, mem='256M', mach='virt'):
	if bits==32: q = './build/qemu-system-riscv32'
	else: q = './build/qemu-system-riscv64'
	cmd = [q, '-machine', mach, '-m', mem]
	if vga: cmd += ['-device', 'VGA']
	else: cmd += ['-display', 'none']
	cmd += [ '-serial',  'stdio', '-bios', exe ]
	if gdb: cmd += ['-gdb', 'tcp:localhost:1234,server,ipv4']
	print(cmd)
	return subprocess.Popen(cmd, stdin=stdin, stdout=stdout)

if __name__=='__main__':
	if not os.path.isdir('./build') or '--build' in sys.argv: rebuild()

	#if '--shared' in sys.argv:
	#	qemu = ctypes.CDLL(LIBQEMU)  ## this will not work because of _thread_local
	#	print(qemu)
	#	print(qemu.main)
	elf = None
	for arg in sys.argv:
		if arg.endswith(('.elf', '.bin')): elf = arg
	if elf:
		if '--riscv32' in sys.argv:
			qemu(elf,bits=32)
		else:
			qemu(elf)
	else:
		print('no .elf or .bin file given')
