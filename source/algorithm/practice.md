<font face="黑体" size=5>所有的开始，都始于无知</font>

# 实践练习

## OJ

## 二叉树

参考资料：
[wiki](https://zh.wikipedia.org/wiki/%E4%BA%8C%E5%8F%89%E6%A0%91)

构建二叉树

```python
class TreeNode:
    def __init__(self, x):
        self.val = x
        self.left = None
        self.right = None

def loadTree(arr, i):
    if i >= len(arr):
        return None
    root = TreeNode(arr[i])
    root.left = loadTree(arr, i * 2 + 1)
    root.right = loadTree(arr, i * 2 + 2)
    return root

```

1. 牛客 - NC62

[NC62-链接](https://www.nowcoder.com/questionTerminal/8b3b95850edb4115918ecebdf1b4d222)

> 答案见网站评论区
