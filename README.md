# coveragepy-k8s
随着目前k8s的使用越来越广泛，也对一些其他技术解决方案产生了改变，这里就讲下 如何在k8s部署的python项目中非侵入式的收集到coverage。项目地址：[Github](https://github.com/yili1992/coveragepy-k8s)

### coverage 收集在 k8s pod中

1. Dockerfile 中增加相应的依赖下载

   ```shell
   RUN pip install coverage==4.5.1
   RUN apt-get install screen
   ```

2. 在containers 中 设置tty 为true

   ```yaml
         containers:
           - name: server
             image: server:latest
             tty: true
   
   ```
   
3. 将启动服务的命令修改，因为coverage.py 采集的方式是通过进程接受 "终止"信号来进行采集的，这样修改使得，进程被kill 时候不会导致容器重启。

   ```yaml
   command: ['screen', '-S', 'coverage', 'coverage', 'run', '--branch', '--concurrency=gevent', '--parallel-mode', '/code/server/application.py']
         
   ```

4. 在yaml中对容器增加 preStop的操作，目的是 通过delete pod的时候 接受到"终止"信号，触发preStop进行采集，这样的好处是，k8s 的pod 在接受"终止信号时候"，会立即创建一个新的pod，这样能够几乎不影响服务的使用

   ```yaml
             lifecycle:
               preStop:
                 exec:
                   command:
                     - "bash"
                     - "-c"
                     - |
                       kill -SIGINT 9
                       coverage combine;
                       coverage xml -i
                       curl -X POST tool-upload.tool.svc.cluster.local:5000/upload -F  "file=@coverage.xml" -F pod="server" //将coverage.xml 通过接口上传到nfs
   ```
5. tool-upload.tool.svc.cluster.local:5000 是使用k8s的内部地址的服务，规则是{server}.{namespace}.svc.cluster.local:{port}，然后通过这个接口把coverage.xml传到固定的地方，我这边是在k8s集群里部署了一个上传服务，大家也可以本地起一个上传服务只要ip能通就行。  
  这个服务可以 从[flask_app_k8s](https://github.com/yili1992/coveragepy-k8s)这个文件中里 进行部署
  
     ```shell
   docker build -t tool-upload:v0.1 .  #docker build 出上传服务的进行
   kubectl create namespace tool #创建namespace
   kubectl create -f tool_upload.yaml  #创建上传文件的服务，在yaml中配置了 nfs，这样就可以把coverage上传到这个xml中
     ```


