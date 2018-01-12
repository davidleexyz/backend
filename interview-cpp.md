## <font color=red>c/c++语言基础</font>
1.  extern关键字的作用
2.  static关键字的作用
3.  volatile (volatile的对象只能访问volatile成员)
4.  const的用法 volatile和const 都可以通过 const_cast 来消除对象的const或者volatile属性
5.  new和malloc的区别
6.  c++多态和虚函数表
    a.多态分为静态多态(模板和函数重载)和动态多态(虚函数实现动态绑定)
    b.虚函数除了实现多态还有封装和抽象的作用
    c.虚函数表是针对类的, 每个类的对象有一个指向虚函数表的指针
    d.对象模型和内存布局(注意虚函数表)
7.  智能指针如何实现 (shared_ptr weak_ptr以及 unique_ptr) 
8.  static_cast/const_cast/dynamic_cast/reinterpret_cast
9.  stl容器(vector, list, deque, set和map的实现)

10. 左值和右值 (move和forward)
11. nullptr auto decltype for(:) 

## <font color=red>算法和数据结构</font>
### 树
1.  二叉树的遍历
2.  平衡二叉树(AVL rb-tree)
3.  字典树(后缀树和后缀数组)

### 链表
1.  链表的逆序(递归实现)
2.  链表的倒数第k个节点(前后指针)                    
3.  链表是否有环(快慢指针)

### 栈和队列的应用
1.  用O(1)实现栈的min操作
2.  调度

### 堆和优先队列
1.  堆的实现和堆排序
2.  优先队列

## <font color=red>Linux系统编程</font>
1.  进程和线程
2.  什么时候用多进程, 什么时候用多线程
3.  线程同步方式
4.  IPC
5.  锁的种类和使用以及实现
6.  内存管理(进程角度 系统角度 硬件角度)
7.  进程调度
8.  IO模型
    a.多进程
    b.多线程 
    c.IO复用(select/epoll)
    d.异步IO
9.  fork和vfork
10. exit和_exit
11. tcp三次握手和四次挥手(状态转移)
12. tcp重传/滑动窗口/拥塞控制
13. nagle算法
