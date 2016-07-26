#!/usr/bin/env python2.7

import requests
from pyquery import PyQuery as pq
from lxml import etree
import urllib
import subprocess
import sys
import os.path
import os

def parse_out_required_packages(line):
	line = line.strip(' \t\n\r')
	return line[0 : line.index('is needed by')-1][0 : line.index(' ')]

def install_package(package_name):
	download_packages_folder = 'downloaded_packages'

	target_url = "https://www.rpmfind.net/linux/rpm2html/search.php?query={}&submit=Search+...&system=&arch=".format(package_name)

	r = requests.get(target_url)

	d = pq(r.text)

	all_td = d("td:contains('CentOS 7.2.1511')")

	if len(all_td) == 0:
		print("No rpm packages found for {}!".format(package_name))
		sys.exit(1)

	update_packages = all_td("td:contains('Updates')")

	if len(update_packages) == 0:
		# print("No update packages found!")
		target_td = all_td
	else:
		# print("Found update packages!")
		target_td = update_packages

	x86_64_packages = target_td("td:contains('x86_64')")

	if len(x86_64_packages) == 0:
		target_packages = target_td
		# print('No x86_64 packages found, use other(etc. i686) packages, please check ... {}'.format(target_packages.eq(0).next().children('a').text()))
	else:
		# print('Found x86_64 packages!')
		target_packages = x86_64_packages
		
	target_a = target_packages.eq(0).next().children('a')
	download_package_name = target_a.text()
	download_link = target_a.attr('href')

	print('Download {} ...'.format(download_package_name))

	subprocess.Popen(["wget", "--directory-prefix={}".format(download_packages_folder), '-N',  download_link], stdout = subprocess.PIPE, stderr = subprocess.PIPE).wait()
	# subprocess.Popen(["wget", "--directory-prefix={}".format(download_packages_folder), '-N',  download_link]).wait()


	download_package_path = os.path.join(download_packages_folder, download_package_name)

	if os.path.isfile(download_package_path) == False:
		print('Download to {} failed'.format(download_package_path))
		sys.exit(2)

	print('Installing {}...'.format(download_package_name))
	rpm_process = subprocess.Popen(['rpm', '-i', download_package_path], stderr=subprocess.PIPE)
	rpm_process.wait()
	output = rpm_process.communicate()[1]

	if 'error: Failed dependencies:' in output:
		# we got a dependency problem, recursive download packages
		required_packages = map(parse_out_required_packages, output.splitlines()[1:])
		print("REQUIRE packages: {}".format(required_packages))
		for required_package in required_packages:
			install_package(required_package)
	
		print('Installing {} with dependencies installed...'.format(download_package_name))
		rpm_process = subprocess.Popen(['rpm', '-i', download_package_path], stderr=subprocess.PIPE)
		rpm_process.wait()
		output = rpm_process.communicate()[1]
	
		if rpm_process.returncode != 0:
			print("Return code: {}".format(rpm_process.returncode))
			print("Installation failed!! Because:")
			print(output)
			sys.exit(3)

	if rpm_process.returncode != 0 and 'is already installed' not in output:
		print('Unknow error!')
		sys.exit(4)

if (len(sys.argv)!=2):
	print('usage: helper.py [package_name]')
	sys.exit(-1)

euid = os.geteuid()
if euid != 0:
	print "Script not started as root. Running sudo.."
	args = ['sudo', sys.executable] + sys.argv + [os.environ]
	# the next line replaces the currently-running process with the sudo
	os.execlpe('sudo', *args)

install_package(sys.argv[1])
print('Done')
