#!/bin/bash

# because -y is not enough - apt will still ask you wether it may restart services
export DEBIAN_FRONTEND=noninteractive

apt-get -qq update

apt-get install -qq -y software-properties-common # this installs add-apt-repository
add-apt-repository ppa:ubuntu-toolchain-r/test > /dev/null 2> /dev/null # for gcc-6

apt-get -qq update

apt-get -qq -y install  \
    pciutils \
    libjemalloc-dev \
    libnuma-dev \
    cmake \
    psmisc \
    python

apt-get -qq -y install gcc-6 g++-6 automake autoconf
