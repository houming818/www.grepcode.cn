from gm.api import *
import qmodel

def init(context):
    datas = get_instruments(exchanges="SHSE,SZSE")
    [print(i["symbol"]) for i in datas]
    context.user_data = 'balabala'

if __name__ == "__main__":
#    run(strategy_id='93405576-5a4d-11ec-9766-00155d7828a8',
#        filename='hello_gm.py',
#        mode=MODE_BACKTEST,
#        token='ee80a887e88e31d6b9a4b0d528f80f9037a9fac0',
#        backtest_start_time='2020-11-01 08:00:00',
#        backtest_end_time='2020-11-10 16:00:00',
#        serv_addr="192.168.1.101:7001")
    pass
