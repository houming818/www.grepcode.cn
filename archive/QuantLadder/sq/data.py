import datetime
from influxdb_client import InfluxDBClient

import pandas as pd

import logging

from .error import (
    SqParamError
)

log = logging.getLogger(__name__)


class Dao(object):
    ctx = None

    def __init__(self, ctx):
        self.ctx = ctx

    def save_history(self, datas):
        org = self.ctx.config["influx_settings"]["org"]
        token = self.ctx.config["influx_settings"]["token"]
        url = self.ctx.config["influx_settings"]["url"]
        bucket = self.ctx.config["influx_settings"]["bucket"]
        client = InfluxDBClient(
            url=url,
            token=token,
            org=org
        )
        metrics = []
        for i in datas:
            m = {}
            m["measurement"] = "history"
            tags = {
                "source": i["source"],
                "code": i["code"],
                "frequency": i["frequency"],
                "adjustflag": i["adjustflag"]
            }
            m["tags"] = tags
            fields = {
                "open": float(i["open"]),
                "high": float(i["high"]),
                "low": float(i["low"]),
                "close": float(i["close"]),
                "volume": int(float(i["volume"])),
                "amount": int(float(i["amount"]))
            }
            m["fields"] = fields
            m["time"] = datetime.datetime.strptime(i["time"], "%Y%m%d%H%M%S000")
            metrics.append(m)
        write_api = client.write_api()
        write_api.write(bucket, org, metrics)

    def get_history(
        self,
        code: str,
        frequency: str,
        start: datetime.datetime,
        end: datetime.datetime,
        source: str
    ):
        if source not in ("bs", "au"):
            raise SqParamError("source required")

        org = self.ctx.config["influxdb_settings"]["org"]
        token = self.ctx.config["influxdb_settings"]["token"]
        url = self.ctx.config["influxdb_settings"]["url"]
        bucket = self.ctx.config["influxdb_settings"]["bucket"]
        client = InfluxDBClient(
            url=url,
            token=token,
            org=org
        )
        query_api = client.query_api()
        ql = " \
        from(bucket: \"{}\") \
        |> range(start: {}, stop: {}) \
        |> filter(fn: (r) => r._measurement == \"history\") \
        |> filter(fn: (r) => r.code == \"{}\") \
        ".format(bucket, start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ"), code)

        log.info("query {}".format(ql))
        try:
            result = query_api.query(org=org, query=ql)
            data = []
            for table in result:
                for record in table.records:
                    data.append(
                        {
                            "code": record["code"],
                            "time": record.get_time(),
                            record.get_field(): record.get_value()
                        },
                    )

            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data=data)
            df = df.set_index(["time", "code"])
#            df.fillna(0, inplace=True)
            df = df.groupby(df.index).sum()
#            df3 = df2.join(df, on="time")
            print(df.head())
            return df
        except Exception as e:
            log.exception(e)
            return pd.DataFrame()
