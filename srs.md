## srs随笔记录
- 在srs中每个类都是一个app
- 有几个app是全局的包括(srs_config, srs_server)
- 在srs_config中有个subscribe的vector, 这里采用订阅-发布模式一旦config有改动会通知给subscribe vector里的对象, 订阅对象都会继承ISrsReloadHandler


## srs类关系
### kernel log模块
- ISrsLog
- ISrsThreadContext

### app log模块
- SrsFastLog (全局唯一)
- SrsThreadContext

### app config模块
- SrsConfig (全局唯一)

### app server模块
- SrsServer (全局唯一) : public ISrsReloadHandler, public ISrsSourceHandler, public IConnectionManager
- SrsSignalManager : public ISrsEndlessThreadHandler
- SrsListener (rtmp/http listener)
- SrsStreamListener (tcp listener)
- SrsHttpFlvListener (http-flv)

### app connection模块
- SrsConnection 所有connection的基类

### app listener模块
- SrsTcpListener : public ISrsReusableThreadHandler
- SrsUdpListener : public ISrsReusableThreadHandler
- ISrsTcpHandler
- ISrsUdpHandler

### app thread模块
- srs里的thread模型
- ISrsThreadHandler (internel namespace)
- SrsThread (internel namespace)
 
- ISrsEndlessThreadHandler
- SrsEndlessThread : public ISrsThreadHandler

- ISrsOneCycleThreadHandler
- SrsOneCycleThread : public ISrsThreadHandler

- ISrsReusableThreadHandler
- SrsReusableThread : public ISrsThreadHandler

- ISrsReusableThread2Handler
- SrsReusableThread2 : public ISrsThreadHandler

- 后面4种线程类都是对SrsThread的封装 并做为SrsThread的handler参数