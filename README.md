# ReqsMiner

*ReqsMiner* is an innovative fuzzing framework developed to discover previously unexamined inconsistencies in CDN forwarding requests.
The framework uses techniques derived from reinforcement learning to generate valid test cases, even with minimal feedback, and incorporates real field values into the grammar-based fuzzer.

<p align="center">
<kbd>
<img src="img/architecture.png" max-height="300">
</kbd>
<br>The Architecture of ReqsMiner.
</p>

## Why build this tool?

ReqsMiner was developed to address the need for a systematic and efficient method to identify forwarding request inconsistencies in Content Delivery Networks (CDNs). Traditional methods of manually discovering these discrepancies may overlook certain variations in forwarding requests, leading to potential security vulnerabilities. 

By automating the process through grammar-based fuzzing with the UCT-Rand algorithm, ReqsMiner can efficiently generate valid test cases and detect differences in CDN forwarding requests with minimal feedback. This tool aims to enhance the security of websites hosted on CDNs by uncovering potential attack vectors, such as DoS attacks, and providing valuable insights to CDN vendors for mitigation.

## Installation

- Download this tool
```
git clone https://github.com/Konano/Reqsminer
```

- Install dependencies
```
pip3 install -r requirements.txt
```

> *Python version: Python 3 (**>=3.10**).*

## Usage

#### 1. Configure the origin server 

`server.py` creates a new echo HTTP service that, upon receiving an HTTP request, encodes the original HTTP request into base64 and sends it as a response. To prevent the response from being lost, it also attaches the encoded base64 content to the response header "ReqsMiner". 

| Form        | Description                          |
| ----------- | ------------------------------------ |
| --host      | listening host (default: localhost)  |
| --port      | listening port (default: 8080)       |
| --packet-maxsize | packet maxsize (default: 2048)  |
| --verbose   | verbose mode (default: False)        |

#### 2. Configure the CDN service

<!-- 
对于将要测试的 CDN 服务，我们需要将其后端绑定到 origin server 提供的 HTTP 服务上。
这一步骤根据不同的 CDN 服务提供商有所不同。
最后得到一个对应该 CDN 服务的域名用于后续测试。

注意：CDN 和 origin server 中间不要引入类似 Nginx 的反代，因为 Nginx 也会对请求进行修改，会引入一些外部因素导致结果不准。
-->

#### 3. Configure the database

`docker-compose.yml` creates a new MongoDB service to store the results of the fuzzing process, which includes the original HTTP text of the test requests before and after they were forwarded by the CDN, as well as the differences detected.

Run the following command to start the MongoDB service:

```sh
docker-compose up -d
```

#### 4. Configure the client

| Form          | Description                         |
| ------------- | ----------------------------------- |
| -t, --target  | target host (default: localhost)    |
| --thread-num  | thread num (default: 100)           |
| --round-num   | round num (default: 100)            |
| --round-size  | round size (default: 100)           |
| --packet-maxsize | packet maxsize (default: 1024)   |
| --random      | random mode (default: False)        |
| --verbose     | verbose mode (default: False)       |

#### 5. Analyze the results

| Form         | Description                              |
| ------------ | ---------------------------------------- |
| -t, --target | target host                              |
| -f, --field  | field to be compared                     |
| --type       | type of difference (0-6 / DiffTypeName)  |
| --quiet      | quiet mode                               |

<!-- 可选项？
1. 修改 ABNF 规则
准备 `rfc/*.abnf` 和 `predefined.json` 还有 `custom.abnf` 并放到 `grammar/` 目录下
运行 `python3 src/rule_gen.py`
 -->

## License

ReqsMiner is a free software and licensed under the [MIT license](/LICENSE).
