# SVM 支持向量机


### 参考资料

[sklearn官方文档](https://scikit-learn.org/stable/modules/svm.html)

[sklearn官方中文文档](http://doc.codingdict.com/sklearn/5/)

[图例说明](https://jakevdp.github.io/PythonDataScienceHandbook/05.07-support-vector-machines.html)

### 概述

SVM 是一种有监督学习方法，可用于分类、回归以及异常值检测。

优势：

1. 高维空间有效
2. 维度数大于样本数时任然有效
3. 在决策函数中使用的是训练点的子集（称为支持向量），因此更有内存效率
4. 通用性：可为决策函数可指定不同的内核函数。提供了通用内核，但是也可以指定自定义内核

缺陷:

1. 如果特征数量远大于样本数量，则在选择内核函数时应避免过度拟合，并且正则化项至关重要
2. SVM不直接提供概率估计，而是使用高代价的五折交叉验证来计算的

### Classification 分类

SVC，NuSVC和LinearSVC能够对数据集执行二分类和多分类。

![分类效果图](/images/svm_1.jpg "分类效果图")

SVC和NuSVC是类似的方法，但接受略有不同的参数集并具有不同的数学公式。

但是，对于线性内核，LinearSVC是SVC分类的另一种（更快）实现。但是由于假定是线性的，LinearSVC不接受参数内核（parameter kernel）。它还缺少SVC和NuSVC的某些属性，例如 `support_`

与其他分类器一样，SVC，NuSVC和LinearSVC将两个数组作为输入：一个保存了训练样本的形状为（n_samples，n_features）的X数组，一个形状为形状为（n_samples）的Y类标签数组（字符串或整数）

```python
>>> from sklearn import svm
>>> X = [[0, 0], [1, 1]]
>>> y = [0, 1]
>>> clf = svm.SVC()
>>> clf.fit(X, y)
SVC()
```

**拟合（fit）后，该模型可用于预测新值**

```python
>>> clf.predict([[0.4999, 0.4999], [0.5, 0.5], [0.5001, 0.5001]])
array([0, 1, 1])
```

SVM的决策功能取决于训练数据的某些子集，称为支持向量。 这些支持向量的某些属性可以在属性support_vectors_，support_和n_support_中找到：

```python
>>> # get support vectors
>>> clf.support_vectors_
array([[0., 0.],
       [1., 1.]])
>>> # get indices of support vectors
>>> clf.support_
array([0, 1]...)
>>> # get number of support vectors for each class
>>> clf.n_support_
array([1, 1]...)
```

#### Multi-class classification 多类分类

SVC和NuSVC为多类分类实施“一对一（one-versus-one）”方法。 总共构造了 n_classes *（n_classes-1）/ 2 个分类器，每个分类器训练来自两个类的数据。 为了提供与其他分类器的一致接口，decision_function_shape选项允许将“一对一”分类器的结果单调转换为形状（n_samples，n_classes）的“一对剩余（one-vs-rest）”决策函数。

```python
>>> X = [[0], [1], [2], [3]]
>>> Y = [0, 1, 2, 3]
>>> clf = svm.SVC(decision_function_shape='ovo')
>>> clf.fit(X, Y)
SVC(decision_function_shape='ovo')
>>> dec = clf.decision_function([[1]])
>>> dec.shape[1] # 4 classes: 4*3/2 = 6
6
>>> clf.decision_function_shape = "ovr"
>>> dec = clf.decision_function([[1]])
>>> dec.shape[1] # 4 classes
4
```

另一方面，LinearSVC实施了“一对剩余（one-vs-rest）”策略，从而训练了n_classes个模型。

```python
>>> lin_clf = svm.LinearSVC()
>>> lin_clf.fit(X, Y)
LinearSVC()
>>> dec = lin_clf.decision_function([[1]])
>>> dec.shape[1]
4
```

详细数学细节

请注意，通过使用选项multi_class='crammer_singer'，LinearSVC还实现了可选择的多类策略，即由Crammer和Singer制定的所谓多分类SVM。 在实践中，通常首选“一对多（one-vs-rest）”分类，因为结果大多相似，但运行时间显著减少。

对于“一对剩余”的LinearSVC，属性coef_和intercept_分别具有（n_classes，n_features）和（n_classes）的形状。 系数的每一行对应于n_classes的“一对剩余”分类器之一，并且对于截距，按“一”类别的顺序类似。

> For “one-vs-rest” LinearSVC the attributes coef_ and intercept_ have the shape (n_classes, n_features) and (n_classes,) respectively. Each row of the coefficients corresponds to one of the n_classes “one-vs-rest” classifiers and similar for the intercepts, in the order of the “one” class.

#### Scores and probabilities 分值和概率

SVC和NuSVC的Decision_function方法为每个样本提供每个类别的分数（或在二进制情况下为每个样本单个分数）。 当构造函数选项概率设置为True时，将启用类成员资格概率估计（来自predict_proba和predict_log_proba方法）。 在二进制情况下，概率是使用Platt缩放比例进行校准的：对SVM得分进行逻辑回归，并通过对训练数据进行额外的交叉验证来拟合。

