#
# This module installs a minimal yet complete Ubuntu Artful system into $CHROOT,
# but also makes your favorite terminal multiplexer available.
#
# This module takes no arguments.
#

# Bootstrap the userland
module 'lib/ubuntu.sh' 'xenial'

# Install a kernel
module 'lib/apt.sh' 'linux-image-generic'

# Install tmux since we can't live without it
module 'lib/apt.sh' 'tmux'

# Install PolicyKit so systemd-networkd can talk to systemd-hostnamed
module 'lib/apt.sh' 'policykit-1'

# We obviously need an SSH server
module 'lib/apt.sh' 'openssh-server'

# Install support for all possible locales
module 'lib/apt.sh' 'locales-all'

# Python for testbed commands
module 'lib/apt.sh' 'python2.7' 'python' 'pylint' 'pylint3'

# basic stuff
module 'lib/apt.sh' 'lshw' 'wget' 'curl' 'vim' 'less' 'bc' 'man'

# building stuff
module 'lib/apt.sh' 'build-essential' 'cmake' 'make' 'gcc'

# development stuff
module 'lib/apt.sh' 'htop' 'pciutils' 'ifstat' 'tcpdump' 'git' 'libpcap-dev'

# Finalize image
module 'lib/finalize.sh'
