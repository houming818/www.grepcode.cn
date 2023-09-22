# 编译安装Vim+tmux

## 环境说明

操作系统： CentOS 7
代码仓库： https://github.com/vim/vim.git

## 执行命令

```shell
$ sudo yum install \
gcc-c++ ncurses-devel \
python-devel lua-devl luajit-devel python3-devel ruby-devel

$ git clone https://github.com/vim/vim.git

$ cd vim && git checkout v8.2.3113

$ ./configure \
  --with-features=huge  \
  --enable-multibyte  \
  --enable-rubyinterp \
  --enable-pythoninterp \
  --enable-python3interp \
  --enable-perlinterp \
  --enable-luainterp \
  --enable-cscope \
  --disable-nls \
  --enable-gui=yes \
  --prefix=$HOME/.local \
  --with-tlib=ncurses \
  --without-x

$ make && make install
```

## 安装tmux

```shell
$ sudo yum install libevent-devel -y

$ git clone https://github.com/tmux/tmux.git
$ cd tmux
$ git checkout 3.2
$ sh autogen.sh
$ ./configure && make
$ cp tmux ~/.local/bin
```
