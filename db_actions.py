import dateutil.parser as dparser
from tinydb import TinyDB, Query
from datetime import date
from dateutil.relativedelta import relativedelta


db = TinyDB('db.json')
conf_table = db.table('conferences')
alerted_table = db.table('alerted')
confcolumns = ['name', 'place', 'website', 'twitter', 'date', 'tags']


def get_entry(confname):
    found = conf_table.search(Query().name == format_string(confname))
    if len(found) > 1:
        return found[0]
    elif len(found) == 1:
        return found[0]
    else:
        return None


def create_entry_object(confrow):
    """
    create entry without inserting
    """
    entry = dict()

    for idx, val in enumerate(confrow):
        colname = confcolumns[idx]
        if colname == 'date':
            entry[colname] = format_date(confrow[idx])
        elif colname == 'tags':
            entry[colname] = format_tags(confrow[idx])
        else:
            entry[colname] = format_string(confrow[idx])
    return entry


def create_entry(confrow):
    entry = create_entry_object(confrow)
    conf_table.insert(entry)
    return entry


def alert_for_change(conf_gs, conf_db):
    return len(conf_gs) > 4 and conf_db.get('date') != format_date(conf_gs[4])


def update_entry(confrow):
    entry = create_entry_object(confrow)
    conf_table.update(entry, Query().name == format_string(confrow[0]))
    return entry


def should_plan(conf_db, conf_date):
    if not conf_date:
        return False
    future_date = conf_date.today() + relativedelta(months=+4)
    if future_date.month == conf_date.month:
        this_year = date.today().year
        confname = conf_db.get('name')
        alerted = alerted_get(confname)
        if alerted and alerted == this_year:
            return False
        elif alerted and alerted != this_year:
            alerted_update(confname, this_year)
            return False
        else:
            alerted_create(confname, this_year)
            return True
    else:
        return False


def alerted_create(confname, year):
    entry = {'name': confname, 'year': year}
    alerted_table.insert(entry)
    return entry


def alerted_update(confname, year):
    entry = {'name': confname, 'year': year}
    alerted_table.update(entry, Query().name == format_string(confname))
    return entry


def alerted_get(confname):
    found = alerted_table.search(Query().name == format_string(confname))
    if len(found):
        return found[0]
    else:
        return False


def format_date(datestring):
    try:
        date_obj = dparser.parse(datestring)
        return date_obj.timestamp()
    except ValueError:
        print("errored on datestring", datestring)
    return datestring


def format_string(miscstring):
    if type(miscstring) != str:
        return miscstring
    return miscstring.lower()


def format_tags(tagstring):
    return tagstring.lower().replace(",", "").split(" ")
