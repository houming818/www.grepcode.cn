---
title: 初始化设置
link_title: blueking004
categories:
  - 01 蓝鲸计划
tags: 运维 开发 DevOps 蓝鲸 blueking 初始化
date: 2023-09-26 13:00:00
---


## 这里列举了一些常用文档，用于初始化环境

### [初始化邮件通知](https://bk.tencent.com/docs/markdown/ZH/PaaS/1.0/UserGuide/UserCase/send_mail.md)

需要注意的是，文中说的测试接口：

用法一：
{
    "bk_app_code":"{{bk_app_code}}",
    "bk_app_secret":"{{BK_APP_SECRET}}",
    "bk_username": "admin",
    "receiver": "****@qq.com",
    "sender": "houming@domain.cn",
    "title": "This is a Test",
    "content": "<html>Welcome to Blueking</html>"
}


用法二：
{
    "bk_app_code":"{{bk_app_code}}",
    "bk_app_secret":"{{BK_APP_SECRET}}",
    "bk_username": "admin",
    "receiver": "****@qq.com",
    "sender": "蓝鲸<houming@domain.cn>",
    "title": "This is a Test",
    "content": "<html>Welcome to Blueking</html>"
}

这里的sender，只能写smtp配置的sender。否则会发送失败。

    ERROR [2023-09-26 16:08:43] /app/components/generic/templates/cmsi/toolkit/send_mail_with_smtp.py 77 send_mail 22 140579342142536 
            1306205 send mail exception, server: smtp.exmail.qq.com:465 
    Traceback (most recent call last):  File "/app/components/generic/templates/cmsi/toolkit/send_mail_with_smtp.py", line 70, in send_mail    smtp.sendmail(mail_sender, all_receiver, msg.as_string())
      File "/usr/local/lib/python3.6/smtplib.py", line 872, in sendmail    raise SMTPSenderRefused(code, resp, from_addr)smtplib.SMTPSenderRefused: (501, b'mail from address must be same as authorization user', 'admin')

然后，测试下通过邮箱进行密码找回，应该是可以了。
