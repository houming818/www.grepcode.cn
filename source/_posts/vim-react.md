---
title: vim搭建react开发环境
link_title: vim_react
date: 2017-09-15 16:37:43
tags:
---
[TOC]

# 1. 配置vim编辑器
## 1.1 装vim插件
```
Bundle 'mxw/vim-jsx'
```
## 1.2 配置vim插件
```
let g:syntastic_javascript_checkers = ['eslint']
```
## 1.3 配置eslintrc
```json
{
  "parser": "babel-eslint",
  "env": {
    "browser": true,
    "node": true
  },
  "settings": {
    "ecmascript": 6,
    "jsx": true
  },
  "plugins": [
    "react"
  ],
  "rules": {
    "strict": 0,
    "quotes": 0,
    "no-unused-vars": 0,
    "camelcase": 0,
    "no-underscore-dangle": 0
  }
}
```

> [vimrc参考](https://coding.net/u/stduolc/p/rc_in_one/git/raw/master/vimrc)
> 
> [eslintrc参考](https://coding.net/u/stduolc/p/rc_in_one/git/raw/master/eslintrc)
>

# 2. 装工具
```bash
npm install -g eslint
npm install -g babel-eslint
npm install -g eslint-plugin-react
```

# 3. 开始编码

## 3.1 setup workspace and init a hello world project
```bash
cd /path/to/your/workspace
sudo npm install -g create-react-app
create-react-app react-hello-world
cd react-hello-world
PORT=$dev_port react-scripts start
```

> [参考链接](https://jaxbot.me/articles/setting-up-vim-for-react-js-jsx-02-03-2015)
>


# 错误与异常
## 新建react-app失败
错误信息
```
Creating a new React app in /home/workspace/react-hello-world.

Installing packages. This might take a couple minutes.
Installing react, react-dom, and react-scripts...

npm WARN optional SKIPPING OPTIONAL DEPENDENCY: fsevents@1.0.17 (node_modules/react-scripts/node_modules/fsevents):
npm WARN notsup SKIPPING OPTIONAL DEPENDENCY: Unsupported platform for fsevents@1.0.17: wanted {"os":"darwin","arch":"any"} (current: {"os":"linux","arch":"x64"})

npm ERR! code ETARGET
npm ERR! notarget No matching version found for regenerator-transform@0.9.11
npm ERR! notarget In most cases you or one of your dependencies are requesting
npm ERR! notarget a package version that doesn't exist.
npm ERR! notarget
npm ERR! notarget It was specified as a dependency of 'babel-plugin-transform-regenerator'
npm ERR! notarget

npm ERR! A complete log of this run can be found in:
npm ERR!     /home/stduolc/.npm/_logs/xxx-debug.log

Aborting installation.
  npm install --save --save-exact react react-dom react-scripts has failed.

Deleting generated file... package.json
Deleting react-hello-world / from /home/workspace
Done.
```
解决方案
```
使用了腾讯云的npm源,这个源很坑,删掉,就好了.
```

