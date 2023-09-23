# 代码实现

参考资料： [wiki](https://zh.wikipedia.org/wiki/%E4%BA%8C%E5%8F%89%E6%A0%91)

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

1. 牛客NC12 重建二叉树

   [NC12链接](https://www.nowcoder.com/practice/8a19cbe657394eeaac2f6ea9b0f6fcf6)

   > 答案见评论区
   >
   > 归纳:通过前序遍历序列获得根节点，通过中序序列分割前序和中序的左右子序列，递归。

2. 牛客NC62 判断平衡二叉树

   [NC62链接](https://www.nowcoder.com/questionTerminal/8b3b95850edb4115918ecebdf1b4d222)

   > 答案见评论区
   >
   > 左子树和右子树分别高度加1，判断高度差是否&gt;1，递归。

3. 牛客NC16 判断二叉树对称

   [NC16链接](https://www.nowcoder.com/practice/1b0b7f371eae4204bc4a7570c84c2de1)

   > 答案见评论区
   >
   > 递归性的了解树的对称性

4. 牛客NC8

   [NC8链接](https://www.nowcoder.com/practice/840dd2dc4fbd4b2199cd48f2dadf930a)

   > 答案见评论区

