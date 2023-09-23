# numpy100问及答案

## 题目说明

原题目链接: [github](https://github.com/rougier/numpy-100)

## 题目及答案

1.Import the numpy package under the name np (★☆☆)

```python
import numpy as np
```

2.Print the numpy version and the configuration (★☆☆)

```python
print(np.__version__)
np.show_config()
```

3.Create a null vector of size 10 (★☆☆)

```python
z10 = np.zeros(10).astype("float64")
z10
array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
```

4.How to find the memory size of any array (★☆☆)

```python
np.size(z10) * z10.itemsize
80
```

5.How to get the documentation of the numpy add function from the command line? (★☆☆)

```python
print(np.add.__doc__)
```

6.Create a null vector of size 10 but the fifth value which is 1 (★☆☆)

```python
x1=np.zeros(10)
x1[4]=1

x2 = np.arange(10) == 4
# [False False False False  True False False False False False]
x2 = x2 * 1

x3 = (np.arange(10) == 4).view(np.uint8)

x4 = (np.arange(10) == 4).astype(np.uint8)

x1, x2, x3, x4

(array([0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]),
 array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0]),
 array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0], dtype=uint8),
 array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0], dtype=uint8))
```

7.Create a vector with values ranging from 10 to 49 (★☆☆)

```python
np.arange(10, 50)
array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
       27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43,
       44, 45, 46, 47, 48, 49])
```

8.Reverse a vector (first element becomes last) (★☆☆)

```python
np.arange(0, 11)[::-1]
array([10,  9,  8,  7,  6,  5,  4,  3,  2,  1,  0])
```

9.Create a 3x3 matrix with values ranging from 0 to 8 (★☆☆)

```python
np.arange(0,9).reshape(3,3).astype(np.uint8)
array([[0, 1, 2],
       [3, 4, 5],
       [6, 7, 8]], dtype=uint8)
```

10.Find indices of non-zero elements from [1,2,0,0,4,0] (★☆☆)

```python
nz = [i for i, v in enumerate(np.array([1,2,0,0,4,0])) if v != 0]
print(nz)
nz = np.nonzero([1,2,0,0,4,0])
print(nz)
```

11.Create a 3x3 identity matrix (★☆☆)

```python
idm = np.identity(3)
print(idm)
idm = np.eye(3)
print(idm)
[[1. 0. 0.]
 [0. 1. 0.]
 [0. 0. 1.]]
[[1. 0. 0.]
 [0. 1. 0.]
 [0. 0. 1.]]
```

12.Create a 3x3x3 array with random values (★☆☆)

```python
np.random.random((3,3,3))
```

13.Create a 10x10 array with random values and find the minimum and maximum values (★☆☆)

```python
a13 = np.random.random((10, 10))
print(np.min(a13), a13.min())
print(np.max(a13), a13.max())
```

14.Create a random vector of size 30 and find the mean value (★☆☆)

```python
a14 = np.random.random((30,))
np.mean(a14), a14.mean()
```

15.Create a 2d array with 1 on the border and 0 inside (★☆☆)

```python
x = np.ones((5,5))
print("Original array:")
print(x)
print("1 on the border and 0 inside in the array")
x[1:-1,1:-1] = 0
print(x)
Original array:
[[1. 1. 1. 1. 1.]
 [1. 1. 1. 1. 1.]
 [1. 1. 1. 1. 1.]
 [1. 1. 1. 1. 1.]
 [1. 1. 1. 1. 1.]]
1 on the border and 0 inside in the array
[[1. 1. 1. 1. 1.]
 [1. 0. 0. 0. 1.]
 [1. 0. 0. 0. 1.]
 [1. 0. 0. 0. 1.]
 [1. 1. 1. 1. 1.]]
```

16.How to add a border (filled with 0's) around an existing array? (★☆☆)

```python
import numpy as np
x = np.ones((3,3))
print("Original array:")
print(x)
print("0 on the border and 1 inside in the array")
x = np.pad(x, pad_width=1, mode='constant', constant_values=0)
print(x)
Original array:
[[1. 1. 1.]
 [1. 1. 1.]
 [1. 1. 1.]]
0 on the border and 1 inside in the array
[[0. 0. 0. 0. 0.]
 [0. 1. 1. 1. 0.]
 [0. 1. 1. 1. 0.]
 [0. 1. 1. 1. 0.]
 [0. 0. 0. 0. 0.]]
```

17.What is the result of the following expression? (★☆☆)

```
0 * np.nan                # nan
np.nan == np.nan          # false
np.inf > np.nan           # false
np.nan - np.nan           # nan
np.nan in set([np.nan])   # true
0.3 == 3 * 0.1            # false
```

18.Create a 5x5 matrix with values 1,2,3,4 just below the diagonal (★☆☆)

```python
m18 = np.diag(1+np.arange(4),k=-1)
print(m18)
[[0 0 0 0 0]
 [1 0 0 0 0]
 [0 2 0 0 0]
 [0 0 3 0 0]
 [0 0 0 4 0]]
```

19.Create a 8x8 matrix and fill it with a checkerboard pattern (★☆☆)

```python
import numpy as np
m19 = np.ones((3,3))
print("Checkerboard pattern:")
m19 = np.zeros((8,8),dtype=int)
m19[1::2,::2] = 1
m19[::2,1::2] = 1
print(m19)
Checkerboard pattern:
[[0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]
 [0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]
 [0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]
 [0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]]
```

20.Consider a (6,7,8) shape array, what is the index (x,y,z) of the 100th element?

```python
print(np.unravel_index(100,(6,7,8)))
(1, 5, 4)
```

21.Create a checkerboard 8x8 matrix using the tile function (★☆☆)

```python
m21 = np.tile( np.array([[0,1],[1,0]]), (4,4))
print(m21)
[[0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]
 [0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]
 [0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]
 [0 1 0 1 0 1 0 1]
 [1 0 1 0 1 0 1 0]]
```

22.Normalize a 5x5 random matrix (★☆☆)

```
m12 = np.random.random((5,5))
m12max, m12min = m12.max(), m12.min()
m12 = (m12 - m12min)/(m12max - m12min)
print(m12)
[[0.85442542 0.22883797 0.78085492 0.23635551 0.43549801]
 [0.25477835 0.06158647 0.27308979 0.61113236 0.64205788]
 [0.96970467 0.61906173 0.99942083 1.         0.79717199]
 [0.40729604 0.08377946 0.44189285 0.01586257 0.7631526 ]
 [0.0191264  0.11894259 0.         0.83184673 0.79758231]]
```

23.Create a custom dtype that describes a color as four unsigned bytes (RGBA) (★☆☆)

```python
color = np.dtype([("r", np.ubyte, (1,)), ("g", np.ubyte, (1,)), ("b", np.ubyte, (1,)), ("a", np.ubyte, (1,))])
print(color)
[('r', 'u1', (1,)), ('g', 'u1', (1,)), ('b', 'u1', (1,)), ('a', 'u1', (1,))]
```

24.Multiply a 5x3 matrix by a 3x2 matrix (real matrix product) (★☆☆)

```python
m24 = np.dot(np.ones((5,3)), np.ones((3,2)))
print(m24)
# Alternative solution, in Python 3.5 and above
m24_ = np.ones((5,3)) @ np.ones((3,2))
print(m24_)
```

25.Given a 1D array, negate all elements which are between 3 and 8, in place. (★☆☆)

```python
# Author: Evgeni Burovski
m25 = np.arange(11)
m25[(3 < m25) & (m25 <= 8)] *= -1
print(m25)
```

26.What is the output of the following script? (★☆☆)

```python
# Author: Jake VanderPlas
print(sum(range(5),-1)) # 9
from numpy import *
print(sum(range(5),-1)) # 10
```

27.Consider an integer vector Z, which of these expressions are legal? (★☆☆)

```python
Z = np.ones(3)
Z**Z         # ok
2 << Z >> 2  # error
Z <- Z       # ok
1j*Z         # ok
Z/1/1        # ok
Z<Z>Z        # error
```

28.What are the result of the following expressions?

```python
np.array(0) / np.array(0)    # RuntimeWarning: invalid value encountered in true_divide
np.array(0) // np.array(0)   # RuntimeWarning: divide by zero encountered in floor_divide
np.array([np.nan]).astype(int).astype(float) # array([-9.22337204e+18])
```

29.How to round away from zero a float array ? (★☆☆)

```python
# Author: Charles R Harris
Z = np.random.uniform(-10,+10,10)
print(np.copysign(np.ceil(np.abs(Z)), Z))
# More readable but less efficient
print(np.where(Z>0, np.ceil(Z), np.floor(Z)))
[ 4. -6.  6.  8. -6.  9.  6.  3.  8.  1.]
[ 4. -6.  6.  8. -6.  9.  6.  3.  8.  1.]
```

30.How to find common values between two arrays? (★☆☆)

```python
Z1 = np.random.randint(0,10,10)
Z2 = np.random.randint(0,10,10)
print(Z1, Z2)
print(np.intersect1d(Z1,Z2))
[4 7 3 8 4 2 0 9 3 4] [0 7 8 3 6 0 2 5 1 4]
[0 2 3 4 7 8]
```

31.How to ignore all numpy warnings (not recommended)? (★☆☆)

```python
# Suicide mode on
defaults = np.seterr(all="ignore")
Z = np.ones(1) / 0
# Back to sanity
_ = np.seterr(**defaults)
# Equivalently with a context manager
with np.errstate(all="ignore"):
    np.arange(3) / 0
# Back to sanity
_ = np.seterr(**defaults)
Z = np.ones(1) / 0
```

32.Is the following expressions true? (★☆☆)

```python
np.sqrt(-1) == np.emath.sqrt(-1) # False, RuntimeWarning: invalid value encountered in sqrt
```

33.How to get the dates of yesterday, today and tomorrow? (★☆☆)

```python
yesterday = np.datetime64('today') - np.timedelta64(1)
print(yesterday)
today     = np.datetime64('today')
print(today)
tomorrow  = np.datetime64('today') + np.timedelta64(1)
print(tomorrow)
```

34.How to get all the dates corresponding to the month of July 2016? (★★☆)

```python
Z = np.arange('2016-07', '2016-08', dtype='datetime64[D]')
print(Z)
['2016-07-01' '2016-07-02' '2016-07-03' '2016-07-04' '2016-07-05'
 '2016-07-06' '2016-07-07' '2016-07-08' '2016-07-09' '2016-07-10'
 '2016-07-11' '2016-07-12' '2016-07-13' '2016-07-14' '2016-07-15'
 '2016-07-16' '2016-07-17' '2016-07-18' '2016-07-19' '2016-07-20'
 '2016-07-21' '2016-07-22' '2016-07-23' '2016-07-24' '2016-07-25'
 '2016-07-26' '2016-07-27' '2016-07-28' '2016-07-29' '2016-07-30'
 '2016-07-31']
```

35.How to compute ((A+B)*(-A/2)) in place (without copy)? (★★☆)

```python
A = np.ones(3)*1
B = np.ones(3)*2
C = np.ones(3)*3
np.add(A,B,out=B)
np.divide(A,2,out=A)
np.negative(A,out=A)
np.multiply(A,B,out=A)
array([-1.5, -1.5, -1.5])
```

36.Extract the integer part of a random array of positive numbers using 4 different methods (★★☆)

```python
Z = np.random.uniform(0,10,3)
print(Z)
print(Z - Z%1)
print(Z // 1)
print(np.floor(Z))
print(Z.astype(int))
print(np.trunc(Z))
[3.82800091 3.62691898 5.41095198]
[3. 3. 5.]
[3. 3. 5.]
[3. 3. 5.]
[3 3 5]
[3. 3. 5.]
```

37.Create a 5x5 matrix with row values ranging from 0 to 4 (★★☆)

```python
Z = np.zeros((5,5))
Z += np.arange(5)
print(Z)
[[0. 1. 2. 3. 4.]
 [0. 1. 2. 3. 4.]
 [0. 1. 2. 3. 4.]
 [0. 1. 2. 3. 4.]
 [0. 1. 2. 3. 4.]]
```

38.Consider a generator function that generates 10 integers and use it to build an array (★☆☆)

```python
def generate():
    for x in range(10):
        yield x
Z = np.fromiter(generate(),dtype=float,count=-1)
print(Z)
[0. 1. 2. 3. 4. 5. 6. 7. 8. 9.]
```

39.Create a vector of size 10 with values ranging from 0 to 1, both excluded (★★☆)

```python
Z = np.linspace(0,1,11,endpoint=False)[1:]
print(Z)
[0.09090909 0.18181818 0.27272727 0.36363636 0.45454545 0.54545455
 0.63636364 0.72727273 0.81818182 0.90909091]
```

40.Create a random vector of size 10 and sort it (★★☆)

```python
Z = np.random.random(10)
Z.sort()
print(Z)
[0.01587923 0.02508115 0.07846027 0.18149546 0.39769476 0.44368795
 0.72868308 0.89587122 0.8997383  0.91283174]
```

41.How to sum a small array faster than np.sum? (★★☆)

```python
# Author: Evgeni Burovski
Z = np.arange(10)
np.add.reduce(Z)
```

42.Consider two random array A and B, check if they are equal (★★☆)

```python
A = np.random.randint(0,2,5)
B = np.random.randint(0,2,5)
print(A, B)
# Assuming identical shape of the arrays and a tolerance for the comparison of values
equal = np.allclose(A,B)
print(equal)
# Checking both the shape and the element values, no tolerance (values have to be exactly equal)
equal = np.array_equal(A,B)
print(equal)
[1 0 0] [1 0 0]
True
True
```

43.Make an array immutable (read-only) (★★☆)

```python
Z = np.zeros(10)
Z.flags.writeable = False
Z[0] = 1
---------------------------------------------------------------------------
ValueError                                Traceback (most recent call last)
<ipython-input-188-dcc5e7f145b5> in <module>
      1 Z = np.zeros(10)
      2 Z.flags.writeable = False
----> 3 Z[0] = 1

ValueError: assignment destination is read-only
```

44.Consider a random 10x2 matrix representing cartesian coordinates, convert them to polar coordinates (★★☆)

```python
Z = np.random.random((10,2))
X,Y = Z[:,0], Z[:,1]
R = np.sqrt(X**2+Y**2)
T = np.arctan2(Y,X)
print(R)
print(T)
```

45.Create random vector of size 10 and replace the maximum value by 0 (★★☆)

```python
Z = np.random.random(10)
Z[Z.argmax()] = 0
print(Z)
[0.07863547 0.43727021 0.17999108 0.74089074 0.83303473 0.36449307
 0.         0.77454629 0.27679335 0.47163397]
```

46.Create a structured array with x and y coordinates covering the [0,1]x[0,1] area (★★☆)

```python
Z = np.zeros((5,5), [('x',float),('y',float)])
Z['x'], Z['y'] = np.meshgrid(np.linspace(0,1,5),
                             np.linspace(0,1,5))
print(Z)
```

47.Given two arrays, X and Y, construct the Cauchy matrix C (Cij =1/(xi - yj))

```python
# Author: Evgeni Burovski

X = np.arange(8)
Y = X + 0.5
C = 1.0 / np.subtract.outer(X, Y)
print(np.linalg.det(C))
3638.163637117973
```

48.Print the minimum and maximum representable value for each numpy scalar type (★★☆)

```python
for dtype in [np.int8, np.int32, np.int64]:
   print(np.iinfo(dtype).min)
   print(np.iinfo(dtype).max)
for dtype in [np.float32, np.float64]:
   print(np.finfo(dtype).min)
   print(np.finfo(dtype).max)
   print(np.finfo(dtype).eps)
```

49.How to print all the values of an array? (★★☆)

```python
np.set_printoptions(threshold=float("inf"))
Z = np.random.random((4,4))
print(Z)
[[0.87917303 0.98308802 0.95841257 0.03982705]
 [0.76427132 0.67025061 0.98293393 0.78114347]
 [0.60425323 0.19322756 0.20237949 0.09480219]
 [0.43615221 0.15394132 0.30531145 0.79316806]]
```

50.How to find the closest value (to a given scalar) in a vector? (★★☆)

```python
Z = np.arange(100)
v = np.random.uniform(0,100)
print(v)
index = (np.abs(Z-v)).argmin()
print(Z[index])
71.66530197333344
72
```

51.Create a structured array representing a position (x,y) and a color (r,g,b) (★★☆)

```python
Z = np.ones(3, [ ('position', [ ('x', float, (1,)),
                                  ('y', float, (1,))]),
                   ('color',    [ ('r', float, (1,)),
                                  ('g', float, (1,)),
                                  ('b', float, (1,))])])
print(Z["color"][0])
print(Z)
([1.], [1.], [1.])
[(([1.], [1.]), ([1.], [1.], [1.])) (([1.], [1.]), ([1.], [1.], [1.]))
 (([1.], [1.]), ([1.], [1.], [1.]))]
```

52.Consider a random vector with shape (100,2) representing coordinates, find point by point distances (★★☆)

```python
Z = np.linspace((1,1),(3,3),3)
print(Z)
X,Y = np.atleast_2d(Z[:,0], Z[:,1])
D = np.sqrt( (X-X.T)**2 + (Y-Y.T)**2)
print(D)

# Much faster with scipy
import scipy
# Thanks Gavin Heverly-Coulson (#issue 1)
import scipy.spatial

D = scipy.spatial.distance.cdist(Z,Z)
print(D)

[[1. 1.]
 [2. 2.]
 [3. 3.]]
[[0.         1.41421356 2.82842712]
 [1.41421356 0.         1.41421356]
 [2.82842712 1.41421356 0.        ]]
[[0.         1.41421356 2.82842712]
 [1.41421356 0.         1.41421356]
 [2.82842712 1.41421356 0.        ]]
```

53.How to convert a float (32 bits) array into an integer (32 bits) in place?

```python
# Thanks Vikas (https://stackoverflow.com/a/10622758/5989906)
# & unutbu (https://stackoverflow.com/a/4396247/5989906)
Z = (np.random.rand(3)*100).astype(np.float32)
print(Z)
Y = Z.view(np.int32)
Y[:] = Z
print(Y)
print(Y.base is Z)
[55.397587 16.270485 34.524364]
[55 16 34]
True
```

54.How to read the following file? (★★☆)

    1, 2, 3, 4, 5
    6,  ,  , 7, 8
    ,  , 9,10,11

```python
from io import StringIO

# Fake file
s = StringIO('''1, 2, 3, 4, 5
                6,  ,  , 7, 8
                 ,  , 9,10,11
''')
Z = np.genfromtxt(s, delimiter=",", dtype=np.int)
print(Z)
[[ 1  2  3  4  5]
 [ 6 -1 -1  7  8]
 [-1 -1  9 10 11]]
```

55.What is the equivalent of enumerate for numpy arrays? (★★☆)

```python
Z = np.arange(4).reshape(2,2)
for index, value in np.ndenumerate(Z):
    print(index, value)
for index in np.ndindex(Z.shape):
    print(index, Z[index])
(0, 0) 0
(0, 1) 1
(1, 0) 2
(1, 1) 3
(0, 0) 0
(0, 1) 1
(1, 0) 2
(1, 1) 3
```

56.Generate a generic 2D Gaussian-like array (★★☆)

```python
X, Y = np.meshgrid(np.linspace(-1,1,4), np.linspace(-1,1,5))
D = np.sqrt(X*X+Y*Y)
sigma, mu = 1.0, 0.0
G = np.exp(-( (D-mu)**2 / ( 2.0 * sigma**2 ) ) )
print(G.shape)
print(G)
(5, 4)
[[0.36787944 0.57375342 0.57375342 0.36787944]
 [0.53526143 0.8348063  0.8348063  0.53526143]
 [0.60653066 0.94595947 0.94595947 0.60653066]
 [0.53526143 0.8348063  0.8348063  0.53526143]
 [0.36787944 0.57375342 0.57375342 0.36787944]]
```
