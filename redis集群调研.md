# redis集群调研

## redis4.0.2版本集群
[redis集群规范](https://redis.io/topics/cluster-spec)

### 数据分片（负载均衡）
1. redis将键空间划分为 [0,16384)一共 16k个哈希槽，并通过哈希槽进行分片管理键空间。
2. 一个键对应一个哈希槽，而一个哈希槽对应多个键。
3. 一个redis节点可以拥有若干个哈希槽，而一个哈希槽只能同时属于一个redis节点。
4. 当一个redis集群中的所有master节点所拥有全部区间[0,16384)的哈希槽时，称为redis集群全覆盖所有哈希槽。
5. 只有当redis集群全覆盖所有哈希槽时，才能提供完整的服务，否则当请求的键对应的哈希槽未分片给任何redis节点时，对该键请求报错。对应redis配置文件的配置项cluster-require-full-coverage, 默认是Yes, 表示如果slot空间没有被全覆盖, 则整个集群都不对外提供服务; 如果设置为No, 表示即使slot空间没有被节点完全覆盖, 集群仍然会对外提供服务, 如果访问的key落在没有被覆盖的slot上,则请求失败.

### 高可用
1. redis通过将redis节点分为master和slave，并由slave备份master的数据的方式提供高可用。
2. 一个slave只能拥有一个master，而一个master可以拥有多个slave。
3. 当一个master故障时，其余master通过raft算法从该master的slave中投票选举出一个提升为master。
4. 由于master向slave的数据备份是异步操作，故存在一定概率在故障转移时丢失数据。 主从备份分为全量和增量, 全量是在从服务器启动的时候会发sync(psync)命令进行后台数据完全同步, 增量是在主服务器完成一个写命令后,立马通知从服务器同步, 并且同步过程均为异步方式.

    主从复制原理:
        a) 当从库和主库建立MS关系后，会向主数据库发送SYNC命令；
        b) 主库接收到SYNC命令后会开始在后台保存快照（RDB持久化过程），并将期间接收到的写命令缓存起来；
        c) 当快照完成后，主Redis会将快照文件和所有缓存的写命令发送给从Redis；
        d) 从Redis接收到后，会载入快照文件并且执行收到的缓存的命令；
        e) 之后，主Redis每当接收到写命令时就会将命令发送从Redis，从而保证数据的一致；
    主从复制会受IO性能影响, 可以开启无盘复制 repl-diskless-sync yes, 如果开启快照, rdb会不保存到磁盘, 会直接通过网络传输, 减少磁盘IO影响.

5. 当集群中master数量少于3个时，无法使用raft算法；无法使用raft算法，则无法将slave提升为master。

### 集群操作
- redis未在服务端提供简易的命令操作集群，扩展、缩减集群规模以及迁移数据均需要若干条命令。
- redis提供了一个ruby脚本redis\_trib.rb来方便手动管理集群。
- 在测试过程中发现redis\_trib.rb存在bug，故对该脚本可靠性产生怀疑。
- 虽然通过网络抓包定位并修复了该bug，但是很明显该脚本没有严格测试过，不能保证没有其他问题，故计划由代理服务通过命令实现集群操作。

#### 集群初始化
对第一个redis节点使用命令`CLUSTER ADDSLOTS slot [slot ...]` 分配所有哈希槽。
注意：
1. 该节点应已重置（reset），不包含任何集群配置。
2. 由于redis命令不支持表示一个区间内的哈希槽，故需要客户端将这16k个[0,16384)的哈希槽的每个槽都执行一遍命令。这样`CLUSTER ADDSLOTS`会需要较大缓存，考虑分批多次并使用异步的方式执行。

#### 添加redis节点
对已有redis集群中任意一个redis节点上使用命令`CLUSTER MEET ip port`添加新redis节点.
注意：
1. 新添加的节点应已重置，不包含任何集群配置。
2. 已重置的节点为master，不包含任何哈希槽，迁移哈希槽或者成为某个master的slave需要额外操作。

#### 迁移哈希槽
迁移哈希槽共需要四步，假设迁出哈希槽的redis节点为A，迁入哈希槽的redis节点为B。
1. 在节点B上使用执行命令`CLUSTER SETSLOT slot IMPORTING node-id`将哈希槽标记为迁入状态。
2. 在节点A上执行命令`CLUSTER SETSLOT slot MIGRATING node-id`将哈希槽标记为迁出状态。
3. 在节点A上：
	1. 执行命令`CLUSTER COUNTKEYSINSLOT slot`获取该哈希槽拥有键的个数；
	2. 执行命令`CLUSTER GETKEYSINSLOT slot count`获取该哈希槽当前拥有的键名；
	3. 执行命令`MIGRATE host port "" 0 timeout REPLACE KEYS key [key ...]]`将这些键迁移到B上。
4. 在集群中所有节点上执行命令` CLUSTER SETSLOT slot NODE node-id `以通知哈希槽迁移。
    虽然只有在A和B上执行此命令是必须的，但官方文档仍建议在集群中所有的节点上执行。（只要在B上执行这条命令，B就会通知其他节点拥有此哈希槽，在A上执行是为了清掉A上的迁出状态，尽管不清A的状态也能用）
5. 如果客户端向节点A发送请求的key不在节点A上，A会返回MOVED指令给client，client需要转到节点B上处理, 此后的查询直接指向节点B；而在迁移哈希槽的过程中，如果key不在节点A上，A会返回ASK指令给client，client需要节点B上先执行ASKING的指令，然后再在节点B上执行命令，否则节点B会返回MOVED指令给client；迁移过程中所有对该哈希槽中key的操作都要先请求节点A，如果没有才能请求节点B。

#### 成为某个master的slave
执行命令`CLUSTER REPLICATE node-id`将某个节点设置成另一个master节点的slave。

#### 删除redis节点
删除集群内的节点分为三种情况：
1. 删除slave节点。
    1. 在该slave上执行命令`CLUSTER RESET`重置节点。
    2. 在集群所有其他节点上执行命令`CLUSTER FORGET node-id`修改各自集群配置。
2.  删除master节点及其slave，这种情况下master的个数会减少。
    1. 将该master拥有的哈希槽全部迁移到其他master上。
    2. 在该master及其所有slave上执行命令`CLUSTER RESET`重置节点。
    3. 在集群所有其他节点上执行命令`CLUSTER FORGET node-id`修改各自集群配置。
3.  只删除master节点，并让其其中一个slave成为master。
    1. 使用命令`CLUSTER FAILOVER`将其其中一个slave提升为master。
    2. 将变成slave的master删除。

#### slave迁移
可以配置每个master最少拥有多少个在线slave，当某个master的在线slave少于此值时，可以从其他在线slave大于此值的master迁移slave。此值通过cluster-migration-barrier配置。

#### 重新加入集群
+ 当一个节点的master（或者由slave晋升的）在该节点离线期间将该master的哈希槽全部迁移到其他master，该节点重新加入集群后不再属于原master（因为原master已经没有哈希槽了）。
+ 重新加入集群的节点所属的master为拥有原master的哈希槽最多的，若有多个master拥有的原master的哈希槽一样多，则依据哪个master最后获取原master的哈希槽。

#### 读写分离
在默认情况下对redis集群slave节点的访问都会redirect到master node上.
但redis集群支持读写分离, 如果需要在slave节点上读取，需要先执行readonly指令.
因为支持水平扩容, 在实际的业务上已经不需要做读写分离了, 在redis集群中slave的主要作用是做HA，实现高可用。

#### 迁移超时的key管理起来，稍后加长超时再做？或者多次加时都失败了，则在系统负载低的时候再做？读写正在迁移且迁移时间较长的key，延迟情况怎样？给出测试数据。
migrate是一个原子操作（对key而言），它在执行的时候会阻塞进行迁移的两个实例，直到以下任意结果发生：迁移成功，迁移失败，等待超时.
目前同步迁移还没有比较好的解决办法, 只能和业务组协商优化key的存取.
看redis社区已经在讨论异步迁移的情况.

#### multikey的问题。事务，分布式锁。
1.  redis cluster不建议使用pipeline和multi-keys操作，减少max redirect产生的场景, 不在同一个节点上的key会产生多次redirect的问题, 影响效率。（多key操作还必须在一个slot上，在一个node上都不行）
2.  避免产生big-key，导致慢查询
3.  避免使用阻塞操作，不建议使用事务

#### 心跳消息的实现策略
1. 每隔1s钟从节点list中随机选取5个节点,这5个节点必须满足以下条件:
    - 节点是连接的
    - 上一次发送给这个节点的ping包已经收到了该节点pong的回复
    - 该节点是除自己之外的并且不在handshake状态
2. 从5个节点中选取一个上次最早收到pong消息的节点, 发送ping消息
3. 再遍历node list, 选择上一次发了ping包, 而且收到了pong包, 但pong包收到的时间到现在已经超过了node-timeout / 2 时间的节点, 并立刻向其发送ping包
4. 在发送的ping包中,会携带一些随机选择的已知节点(一般是集群节点数的1/10)的信息

其代码实现逻辑如下:
```c++
void clusterCron(void) {  
    ...
    /* Ping some random node 1 time every 10 iterations, so that we usually ping 
     * one random node every second. */  
    if (!(iteration % 10)) {  
        int j;  
  
        /* Check a few random nodes and ping the one with the oldest 
         * pong_received time. */  
        for (j = 0; j < 5; j++) {  
            de = dictGetRandomKey(server.cluster->nodes);  
            clusterNode *this = dictGetVal(de);  
  
            /* Don't ping nodes disconnected or with a ping currently active. */  
            if (this->link == NULL || this->ping_sent != 0) continue;  
            if (this->flags & (REDIS_NODE_MYSELF|REDIS_NODE_HANDSHAKE))  
                continue;  
            if (min_pong_node == NULL || min_pong > this->pong_received) {  
                min_pong_node = this;  
                min_pong = this->pong_received;  
            }  
        }  
        if (min_pong_node) {  
            redisLog(REDIS_DEBUG,"Pinging node %.40s", min_pong_node->name);  
            clusterSendPing(min_pong_node->link, CLUSTERMSG_TYPE_PING);  
        }  
    }  
      
    ...  
    di = dictGetSafeIterator(server.cluster->nodes);  
    while((de = dictNext(di)) != NULL) {  
        clusterNode *node = dictGetVal(de);  
        now = mstime(); /* Use an updated time at every iteration. */  
        mstime_t delay;  
  
        if (node->flags &  
            (REDIS_NODE_MYSELF|REDIS_NODE_NOADDR|REDIS_NODE_HANDSHAKE))  
                continue;  
        ...  
        /* If we have currently no active ping in this instance, and the 
         * received PONG is older than half the cluster timeout, send 
         * a new ping now, to ensure all the nodes are pinged without 
         * a too big delay. */  
        if (node->link &&  
            node->ping_sent == 0 &&  
            (now - node->pong_received) > server.cluster_node_timeout/2)  
        {  
            clusterSendPing(node->link, CLUSTERMSG_TYPE_PING);  
            continue;  
        }  
        ...  
    }  
    dictReleaseIterator(di);  
    ...  
}     
```

#### 节点下线的实现策略
1. 集群通过判断节点是否及时回复ping包来判断节点是否下线, 下线有两种状态: 疑似下线(pfail)和下线(fail)
2. 如果某个节点超过node-timeout / 2的时间没有回复ping消息, 那么会立刻断开和这个节点的连接, 并进行重连而且该节点的ping_sent不会被清除(此举是消除暂时的网络问题导致的pfail)
3. 如果该节点超过node-timeout的时间没有回复ping消息, 那么该节点就会被标记为pfail
4. 稍后在每次的心跳消息中就会携带该节点的下线报告, 收到下线报告的节点会将下线报告插入下线报告列表中
5. 如果在 node-timeout * 2 (失效时间窗口, 超过这个时间的失效报告会被清除)的时间内某个节点的下线报告列表中的节点个数超过总节点数的一半, 就会将该节点标记为fail,并广播给整个集群

因此通过以上分析, cluster-node-timeout的意义在于:
1. 如果集群的节点个数太多而 cluster-node-timeout设置的太小, 会导致整个集群的ping包过多.(redis spec中有举列子) [For example in a 100 node cluster with a node timeout set to 60 seconds, every node will try to send 99 pings every 30 seconds, with a total amount of pings of 3.3 per second. Multiplied by 100 nodes, this is 330 pings per second in the total cluster.]
2. 如果cluster-node-timeout设置太小,而集群节点过多, 会导致失效链表的节点很快被清除, 失效链表的节点个数永远不会超过一半的集群个数, 失效的节点无法被标记为下线(fail).
3. 如果集群节点数不多, cluster-node-timeout可以设置成一个比较小的值是合理的.

## redis代理服务

### redis协议
redis1.2以后使用统一格式的协议，协议每项通过前置int32表示每项长度和用\r\n分割各项的方式表示。[redis协议规范](https://redis.io/topics/protocol)


## redis状态服务

### 集群管理
+ 通过与每个redis实例保持一个tcp长连接定时获取每个redis实例当前信息，通过比较信息变化判断redis集群状态改变。
	+ 命令`INFO`获取redis节点信息，含主从备份。
	+ 命令`CLUSTER INFO`获取redis集群信息。
	+ 命令`CLUSTER NODES`获取redis集节点信息，含主从备份。
+ 通过上述方法发送指令在一个redis集群中添加/删除节点。
+ 通过上述方式发送指令在添加节点后或者删除节点前迁移哈希槽。

## 部分常用redis config详细解释
- timeout 0 
    表示客户端空闲多少秒后redis主动关闭连接(0表示禁用)
- tcp-keepalive 300
    表示是否为长连接, 发送tcp心跳包的间隔时间(0表示禁用)
- loglevel notice
    指定redis的日志输出级别, notice用于生产环境
- save 900 1
  save 300 10
  save 60 10000   
    表示在多长时间(s)内有多少更新操作就写磁盘rdb
- stop-writes-on-bgsave-error yes
    表示如果后台写rdb失败, redis将停止接受写操作
- rdbcompression yes
    表示是否对rdb文件进行压缩, 开启会占用额外的CPU, 不开启会占用更大的内存空间
- dbfilename dump.rdb
    磁盘快照(rdb)的文件名
- dir ./
    数据库rdb和aof的目录
- #slaveof <masterip> <masterport>
    让当前的redis变成指定节点的slave
- #masterauth <masterpasswd>
    开启主从备份设置的密码, 如果master设置过访问密码, 就需要在这里设置, 否则master会拒绝replicate请求
- slave-read-only yes (此项在集群模式下无效)
    配置slave是否可写, 默认是只读
- repl-diskless-sync no
    主从同步是否采用无盘模式
- #repl-timeout 60 (默认关闭)
    主从复制超时时间
- repl-disable-tcp-nodelay no
    主从复制是否开启TCP_NODELAY选项, 如果开启主的数据传送会有更少延迟但占用更多带宽, 如果关闭则数据传送延迟增驾但占用更少带宽
- maxmemory <bytes>
    内存的最大使用量
- maxmemory-policy noeviction (lru/lfu/random)
    当到达最大内存使用值后的内存淘汰策略
- appendonly no
    是否开启更新操作日志, no表示不开启
- appendfilename "appendonly.aof"
    aof文件名称
- appendfsync everysec
    写aof文件到磁盘时调用fsync的策略
- slowlog-log-slower-than 10000
    表示慢操作日志记录时间, 超过这个时间的操作会被记录下来
- slowlog-max-len 128
    慢操作日志的最大保留条数
- hash-max-ziplist-entries 512 (个数)
- hash-max-ziplist-value 64 (字节)
    hash类型数据在编码上可以采用ziplist和hashtable.redis默认采用ziplist, 如果hash中条目个数或者value长度超过阈值,将重新采用hashtable编码
- list-max-ziplist-entries 512
  list-max-ziplist-value 64
    list类型采用ziplist和linkedlist两种编码方式,意义同上
- zset-max-ziplist-entries 128
  zset-max-ziplist-value 64
    zset类型采用ziplist和skiplist两种编码方式,意义同上

以下是集群模式
- cluster-enabled yes
    redis节点以集群方式运行
- cluster-config-file nodes-xxx.conf
    节点的集群配置文件,包含了集群节点信息
- cluster-node-timeout 15000
    节点失效时间,如果节点超过timeout时间不可达,就会被集群标记下线(节点标记下线的具体策略可以参考 #### 节点下线的实现策略)
- cluster-migration-barrier 1
    表示只有当master的working slave数大于这个值时, slave才能被迁移给其它的master
- cluster-require-full-coverage yes
    当集群的hash slot没有被节点完全覆盖时, 集群停止服务; 如果设置为No, 表示即使hash slot没有被完全覆盖, 集群还可以接受客户端请求和提供服务.

