#!/usr/bin/env python3
# qemu.py: by Brent Hartshorn
import os, sys, subprocess, json, ctypes

target = 'riscv64-softmmu'
if 'riscv32' in sys.argv: target = 'riscv64-softmmu'
if '--shared' in sys.argv:
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

if not os.path.isdir('./build') or '--build' in sys.argv:
	cmd = [
		'./configure', 
		'--target-list=%s' % target, 
		'--extra-cflags=-fPIC -DNO_THREAD_LOCAL',
		'--prefix=/opt',
	]
	for feat in get_features():
		if feat in keep: continue
		cmd.append('--disable-%s' % feat)
	print(cmd)
	subprocess.check_call(cmd)
	cmd = ['make', '-j', '3']
	subprocess.check_call(cmd)

def get_o_files():
	obs = []
	a = json.loads( open('./build/compile_commands.json','rb').read().decode('utf-8') )
	for b in a:
		if b['file'] in stubs: pass
		elif b['file'].startswith('../stubs/'): continue
		elif b['output'].startswith('tests/'): continue
		elif b['file'] in skip: continue
		p = os.path.join('./build', b['output'])
		if os.path.isfile(p): obs.append( p )
	print(obs)
	return obs

if not os.path.isfile(LIBQEMU):
	cmd = ['gcc']
	if '--shared' in sys.argv: cmd.append('-shared')
	cmd += ['-o', LIBQEMU] + get_o_files() + ['-lglib-2.0', '-lm', '-lSDL2', '-lz']
	#subprocess.check_call(cmd)
	os.system(' '.join(cmd))

if '--shared' in sys.argv:
	qemu = ctypes.CDLL(LIBQEMU)
	print(qemu)
	print(qemu.main)
else:
	print(LIBQEMU)
	subprocess.check_call([LIBQEMU]+sys.argv[1:])
