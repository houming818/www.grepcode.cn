# readme

执行日期 2021-01

## 目录

* [什么是MXNet](https://github.com/apache/incubator-mxnet)
* 安装MXNet

## 环境说明

> MXNet: version=1.7.0
>
> OS: Ubuntu\_20.04
>
> 硬件: 很穷 就不写了 有个基本的GPU
>
> Python3.8

## 安装MXNet

[官方文档](https://mxnet.apache.org/versions/1.7.0/get_started)

> 注意：
>
> 如果你的机器安装的是 libcudart10.1 就安装 `mxnet-cu101`
>
> 如果你的机器安装的是 libcudart10.2 就安装 `mxnet-cu102`

[验证安装](https://mxnet.apache.org/get_started/validate_mxnet.html#python-with-gpu)

```python
>>> import mxnet as mx
>>> a = mx.nd.ones((2, 3), mx.gpu())
>>> b = a * 2 + 1
>>> b.asnumpy()
array([[ 3.,  3.,  3.],
       [ 3.,  3.,  3.]], dtype=float32)
```
