
from sqlalchemy import Column, String, Integer, Date, create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 创建对象的基类:
Base = declarative_base()

# 定义Industry对象:
# 行业对象
class Instrument(Base):
    # 表的名字:
    __tablename__ = 's_instrument'

    # 表的结构:
    order_book_id = Column(String(32), primary_key=True)
    symbol = Column(String(32))
    abbrev_symbol = Column(String(32))
    listed_date = Column(Date)
    de_listed_date = Column(Date)


# 初始化数据库连接:
engine = None

# 创建DBSession类型:
session = None


def init_qmodel():
    global engine
    engine = create_engine('mysql+mysqlconnector://root:6H4VY6GPn3TrXm@localhost:3306/squant')
    global session
    session = sessionmaker(bind=engine)


def create_db():
    Base.metadata.create_all(engine)


def save_instrument(datas):
    with engine.connect() as con:
        sql = "INSERT INTO s_instrument(order_book_id, symbol, abbrev_symbol, listed_date, de_listed_date) VALUES (:order_book_id, :symbol, :abbrev_symbol, :listed_date, :de_listed_date)"

    statement = text(sql)

    for line in datas:
        con.execute(statement, **line)

