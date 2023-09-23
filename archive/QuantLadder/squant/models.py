from django.db import models


class BsHistory(models.Model):
    code = models.CharField(max_length=16)
    date = models.DateTimeField()
    time = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()
    amount = models.FloatField()
    adjustflag = models.IntegerField()
    frequency = models.CharField(max_length=16)

    class Meta:
        db_table = 'bs_history'


class Instrument(models.Model):
    code = models.CharField(max_length=16, primary_key=True)
    code_name = models.CharField(max_length=16)
    source = models.CharField(max_length=8)
    industry = models.CharField(max_length=32)
    update_date = models.DateField()

    class Meta:
        db_table = 'std_instrument'


class RqInstrument(models.Model):
    order_book_id = models.CharField(max_length=32, primary_key=True)
    symbol = models.CharField(max_length=45, unique=True)
    abbrev_symbol = models.CharField(max_length=45, unique=True)
    listed_date = models.DateField()
    de_listed_date = models.DateField()

    class Meta:
        db_table = 'rq_instrument'


class AuHistory(models.Model):
    amount = models.FloatField()
    bob = models.DateTimeField()
    close = models.FloatField()
    eob = models.DateTimeField()
    frequency = models.CharField(max_length=8)
    high = models.FloatField()
    low = models.FloatField()
    open = models.FloatField()
    position = models.IntegerField()
    pre_close = models.FloatField()
    symbol = models.CharField(max_length=45)
    volume = models.IntegerField()

    class Meta:
        db_table = 'au_history'


class AuInstrument(models.Model):
    listed_date = models.DateTimeField()
    delisted_date = models.DateTimeField()
    exchange = models.CharField(max_length=45)
    sec_abbr = models.CharField(max_length=45)
    sec_name = models.CharField(max_length=45)
    symbol = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = 'au_instrument'
