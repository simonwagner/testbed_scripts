#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

apt-get -qq update

apt-get -qq -y install  \
    pciutils \
    lshw \
    psmisc \
    libtbb-dev \
    python

apt-get -qq -y install gcc g++ make