#!/usr/bin/env python3
# qemu.py: by Brent Hartshorn
import os, sys, subprocess

keep = [
	'tcg',  ## accelerator for riscv on x86, 'kvm' should be used on riscv hardware
	'fdt', 'pie', 'system', 'user', 'linux-user', 'sdl', 'sdl-image', 'png', 'pixman', 
	'avx2', 'avx512bw','malloc-trim', 'membarrier'
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
			#print(name)
			assert name not in feats
			feats.append(name)
	return feats

if not os.path.isdir('./build') or '--build' in sys.argv:
	target = 'riscv64-softmmu'
	cmd = [
		'./configure', 
		'--target-list=%s' % target, 
		'--extra-cflags=-fPIC',
		'--prefix=/opt',
	]
	for feat in get_features():
		if feat in keep: continue
		cmd.append('--disable-%s' % feat)
	print(cmd)
	subprocess.check_call(cmd)
	cmd = ['make', '-j', '1']
	subprocess.check_call(cmd)
