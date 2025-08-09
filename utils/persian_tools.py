from datetime import datetime
import jdatetime


def to_jalali(gregorian_date):
    if isinstance(gregorian_date, str):
        gregorian_date = datetime.strptime(gregorian_date, "%Y-%m-%d %H:%M:%S")

    jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
    return jalali_date.strftime("%Y/%m/%d %H:%M:%S")