# hypothesis-假设检验

[参考Wiki](https://zh.wikipedia.org/wiki/%E5%81%87%E8%AA%AA%E6%AA%A2%E5%AE%9A)

[参考知乎](https://zhuanlan.zhihu.com/p/86178674)

## 概要

推论统计中用于检验统计假设的一种方法

该方法可能两种错误，一型\(弃真错误\)和二型\(取伪错误\)

## 过程

![](../.gitbook/assets/hypothesis_1.jpg)

## 实验代码

1. 确立实验总体模型

   > 实验总体为正态分布，均值为0

2. 首先提出统计假设，即（原假设和备择假设）

   > 原假设 **模型均值为0** 备择假设 **模型均值不为0**

3. 从所研究总体中采样一个随机样本

   > 采样实验数据

4. 在承认原假设的前提下，构造检验**样本**统计量

   > 1. 计算样本均值
   > 2. 输入假设均值
   > 3. 计算样本标准差
   > 4. 输入样本量
   > 5. 带入公式,计算统计量z

5. 输入拒绝域临界值
6. 输出结果

[代码样例](https://github.com/stdhi/NoteML/tree/b8f2edf020bdf022194fe9a92d44446a1e780bb0/hypothesis/code.ipynb)

