---
title: tornado,openresty性能测试
date: 2017-05-19 19:54:39
categories: "testing"
tags: [tornado, openresty, 性能测试]
---
# 测试结果
{% echarts 400 '81%' %}
{
    tooltip : {
        trigger: 'axis',
        axisPointer : {            // 坐标轴指示器，坐标轴触发有效
            type : 'shadow'        // 默认为直线，可选为：'line' | 'shadow'
        }
    },
    legend: {
        data:['GET', 'POST', 'SUM']
    },
    grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
    },
    yAxis : [
        {
            type : 'value'
        }
    ],
    xAxis : [
        {
            type : 'category',
            axisTick : {show: false},
            data : ['tornado', 'openresty']
        }
    ],
    series : [
        {
            name:'GET',
            type:'bar',
            itemStyle : {
                normal: {
                    label: {show: true, position: 'inside'}
                }
            },
            data:[679, 7734]
        },
        {
            name:'POST',
            type:'bar',
            itemStyle: {
                normal: {
                    label : {show: true}
                }
            },
            data:[679, 7735]
        },
        {
            name:'SUM',
            type:'bar',
            itemStyle: {normal: {
                label : {show: true, position: 'left'}
            }},
            data:[1538, 15469]
        }
    ]
};
{% endecharts %}
<!-- more -->

# 测试架构
- tornado
{% mermaid %}
graph TD
jmeter-->|10.116.22.119:10000|Tornado
Tornado-->|127.0.0.1:6397|Redis
{% endmermaid %}
- openresty+lua
{% mermaid %}
graph TD
jmeter-->|10.116.22.119:10000|openresty
openresty-->|127.0.0.1:6397|Redis
{% endmermaid %}


# tornado测试
## 测试代码
```
#! /bin/python
from __future__ import print_function
from __future__ import unicode_literals
import concurrent.futures
import redis
from tornado import gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import json
from tornado.web import asynchronous
from tornado.options import define, options
define("port", default=10000, help="run on the given port", type=int)
executor = concurrent.futures.ThreadPoolExecutor(2)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/tokens", TokenHandler),]
        settings = dict(debug=False)
        super(Application, self).__init__(handlers, **settings)

class BaseHandler(tornado.web.RequestHandler):
    pass

class TokenHandler(BaseHandler):
    r = redis.StrictRedis(host='127.0.0.1', port=6379)

    def get(self):
        token = self.r.spop('tokens')
        if token is not None:
            self.write(token)
        else:
            self.write('null')

    def post(self):
        data = json.loads(self.request.body.decode('utf8'))
        [self.r.sadd('tokens', x) for x in data]
        self.write('ok')


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
 
 
if __name__ == "__main__":
    main()
```


## 测试结果截图
- GET请求配置
![img](http://stduolc-1251158187.cosgz.myqcloud.com/img/screenshot001.jpg)
- POST请求配置
![img](http://stduolc-1251158187.cosgz.myqcloud.com/img/screenshot002.jpg)
- jmeter线程数配置
![img](http://stduolc-1251158187.cosgz.myqcloud.com/img/screenshot003.jpg)
- tornado系统消耗
![img](http://stduolc-1251158187.cosgz.myqcloud.com/img/screenshot004.jpg)
- GET请求测试结果
![img](http://stduolc-1251158187.cosgz.myqcloud.com/img/screenshot005.jpg)
- POST请求测试结果
![img](http://stduolc-1251158187.cosgz.myqcloud.com/img/screenshot006.jpg)

# openresty+lua测试 
## 测试代码
```
worker_processes  1;

events {
    worker_connections  1024;
    use epoll;
}

lua_package_path '/usr/local/openresty/lualib/?.lua;;';
lua_package_cpath '/usr/local/openresety/lualib/?.so;;';

server {
    listen       10000;

    access_log  logs/tredis.access.log  main;

    lua_need_request_body on;

    location /tokens {

        content_by_lua_block {
                local cjson = require "cjson"
                local cjson2 = cjson.new()
                local cjson_safe = require "cjson.safe"

                local redis = require "resty.redis"
                local red = redis:new()

                red:set_timeout(1000) -- 1 sec

                -- or connect to a unix domain socket file listened
                -- by a redis server:
                --     local ok, err = red:connect("unix:/path/to/redis.sock")

                local ok, err = red:connect("127.0.0.1", 6379)
                if not ok then
                    ngx.say("failed to connect: ", err)
                    return
                end

                method_name = ngx.req.get_method()
                if (method_name == 'POST') then
                    local data = ngx.req.get_body_data()
                    data = cjson.decode(data)
                    for k, v in pairs(data) do
                        ok, err = red:sadd("token", v)
                        if not ok then
                            ngx.say("POST failed to set ", err)
                            return
                        end
                    end
                    ngx.say("set result: ", ok)
                end

                if (method_name == 'GET' ) then
                    local res, err = red:spop("token")
                    if not res then
                        ngx.say("GET failed ", err)
                        return
                    end
                    ngx.say(res)
                end

                local ok, err = red:set_keepalive(10000, 100)
                if not ok then
                    ngx.say("failed to set keepalive: ", err)
                    return
                end
                return
            }
        }
    location / {
        root html;
    }
}
```
