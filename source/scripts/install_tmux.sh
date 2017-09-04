#! /bin/bash

# install deps

init_env() {
    echo 'init env'
    if [ "$(id -u)" == "0" ]; then
        :
    else
        echo $(id -u)
        echo 'need root or sudo'
        exit 1
    fi
    cd /tmp
    UNAME=$(uname | tr "[:upper:]" "[:lower:]") 
    # If Linux, try to determine specific distribution 
    if [ "$UNAME" == "linux" ]; then 
        # If available, use LSB to identify distribution 
        if [ -f /etc/lsb-release -o -d /etc/lsb-release.d ]; then 
            DISTRO=$(lsb_release -i | cut -d: -f2 | sed s/'^\t'//) 
            # Otherwise, use release info file 
        else 
            DISTRO=$(cat /etc/system-release | cut -d" " -f 1) 
        fi 
    fi 
    DISTRO=$(echo $DISTRO | tr '[:upper:]' '[:lower:]')
    echo "current OS distribution is" $DISTRO
    if [ "$DISTRO" == "centos" ]; then
        echo "install deps from yum"
        yum groupinstall "Development Tools" -y
        yum install gcc kernel-devel libevent-devel make ncurses-devel cmake -y
        install_tmux_git
    else
        echo 'only support centos now'
        exit 0
    fi
}

install_tmux_git() {
    # DOWNLOAD SOURCES FOR TMUX AND MAKE AND INSTALL
    git clone https://github.com/tmux/tmux.git
    cd tmux
    sh autogen.sh
    ./configure --prefix=/usr/local
    make
    make install
    cd ..
}


# pkill tmux
# close your terminal window (flushes cached tmux executable)
# open new shell and check tmux version
init_env
tmux -V
