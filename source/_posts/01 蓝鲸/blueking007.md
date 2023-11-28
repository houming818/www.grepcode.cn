---
title: 蓝鲸安装命令归纳
link_title: blueking007
categories:
  - 01 蓝鲸
tags: 运维 开发 DevOps 蓝鲸 blueking 安装
date: 2023-11-22 12:00:00
---


```
BK_DOMAIN=ftjd.org

IP1=$(kubectl get svc -A -l app.kubernetes.io/instance=ingress-nginx -o jsonpath='{.items[0].spec.clusterIP}')

./scripts/control_coredns.sh update "$IP1" \
$BK_DOMAIN \
bk7.$BK_DOMAIN \
bkrepo.$BK_DOMAIN \
docker.$BK_DOMAIN \
helm.$BK_DOMAIN \
bkpaas.$BK_DOMAIN \
bkuser.$BK_DOMAIN \
bkuser-api.$BK_DOMAIN \
bkapi.$BK_DOMAIN \
apigw.$BK_DOMAIN \
bkiam.$BK_DOMAIN \
bkiam-api.$BK_DOMAIN \
cmdb.$BK_DOMAIN \
job.$BK_DOMAIN \
jobapi.$BK_DOMAIN \
bknodeman.$BK_DOMAIN \
apps.$BK_DOMAIN \
bcs.$BK_DOMAIN \
bcs-api.$BK_DOMAIN \
bklog.$BK_DOMAIN \
bkmonitor.$BK_DOMAIN \
devops.$BK_DOMAIN \
codecc.$BK_DOMAIN \
lesscode.$BK_DOMAIN \
bk-apicheck.$BK_DOMAIN

/data/script/ddns.sh $BK_DOMAIN bk7 ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkrepo ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN docker ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN helm ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkpaas ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkuser ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkuser-api ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkapi ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN apigw ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkiam ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkiam-api ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN cmdb ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN job ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN jobapi ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bknodeman ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN apps ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bcs ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bcs-api ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bklog ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bkmonitor ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN devops ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN codecc ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN lesscode ne.ftjd.org;
/data/script/ddns.sh $BK_DOMAIN bk-apicheck ne.ftjd.org;

```

## 删除某个app的资源
kubectl delete deploy,sts,cronjob,job,pod,svc,ingress,secret,cm,sa,role,rolebinding,pvc -n "$NAMESPACE" -l app.kubernetes.io/instance="$2"