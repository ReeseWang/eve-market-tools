from prettytable import PrettyTable
from datetime import datetime

sellOrdersTable = PrettyTable()
sellOrdersTable.field_names = [
    '',
    'Location',
    'Remaining',
    'Ask price / ISK',
    'Sum / ISK',
    'Updated ago',
    'Issued ago'
]
sellOrdersTable.align = 'r'
sellOrdersTable.align['Location'] = 'l'

buyOrdersTable = PrettyTable()
buyOrdersTable.field_names = [
    '',
    'Location',
    'Remaining',
    'Bid price / ISK',
    'Sum / ISK',
    'Min volume',
    'Range',
    'Updated ago',
    'Issued ago'
]
buyOrdersTable.align = 'r'
buyOrdersTable.align['Location'] = 'l'
buyOrdersTable.align['Range'] = 'l'

regionTradeSumTable = PrettyTable()
regionTradeSumTable.field_names = [
    '',
    'From Region',
    'Cost / ISK',
    'Profit / ISK',
    'Avg. Margin',
    'To Region'
]
regionTradeSumTable.align = 'r'
regionTradeSumTable.align['From Region'] = 'l'
regionTradeSumTable.align['To Region'] = 'l'


def ISK(price):
    return format(price, ',.2f')


def timefmt(timestamp, level=3):
    time = datetime.strptime(
        timestamp,
        '%Y-%m-%d %H:%M:%S'
    )
    secs = int((datetime.utcnow() -
                time).total_seconds())
    d, h, m, s = '', '', '', ''
    if secs >= 86400 and level >= 3:
        d = '{}D '.format(secs // 86400)
        secs %= 86400
        h, m = '00:', '00'
        pass
    if secs > 3600 and level >= 2:
        if not d:
            h = '{:d}:'.format(secs // 3600)
        else:
            h = '{:02d}:'.format(secs // 3600)
        secs %= 3600
        m = '00'
        pass
    if secs > 60 and level >= 1:
        if not h:
            m = '{:d}'.format(secs // 60)
        else:
            m = '{:02d}'.format(secs // 60)
        secs %= 60
        pass
    s = ':{:02d}'.format(secs)
    return (d + h + m + s)


def printSellOrdersTable(li):
    sellOrdersTable.clear_rows()
    for i, e in enumerate(li):
        sellOrdersTable.add_row(
            [
                i,
                '{:.1f} '.format(e['security']) +
                ' - '.join(
                    [
                        e['regionName'],  # Region name
                        e['solarSystemName'],  # Solar system name
                        # Station name, solar system name inc.
                        # e[3][0:50]
                    ]
                ),
                format(e['volumeRemain'], ',d'),  # Volume remain
                format(e['price'], ',.2f'),  # Price
                format(e['price']*e['volumeRemain'], ',.2f'),  # Sum
                timefmt(e['updated'], 1),  # Updated
                timefmt(e['issued'], 3)  # Issued
            ]
        )
        pass
    print(sellOrdersTable)


def rangeString(r):
    assert isinstance(r, str)
    if r.isdigit():
        if int(r) == 1:
            return '1 jump'
        else:
            return (r + ' jumps')
    else:
        if r == 'solarsystem':
            return 'System'
        else:
            return r.capitalize()


def printBuyOrdersTable(li):
    buyOrdersTable.clear_rows()
    for i, e in enumerate(li):
        buyOrdersTable.add_row(
            [
                i,
                '{:.1f} '.format(e['security']) +
                ' - '.join(
                    [
                        e['regionName'],  # Region name
                        e['solarSystemName'],  # Solar system name
                        # Station name, solar system name inc.
                        # e[3][0:40]
                    ]
                ),
                format(e['volumeRemain'], ',d'),  # Volume remain
                format(e['price'], ',.2f'),  # Price
                format(e['price']*e['volumeRemain'], ',.2f'),  # Sum
                format(e['minVolume'], ',d'),  # Min volume
                rangeString(e['range']),  # Range
                timefmt(e['updated'], 1),  # Updated
                timefmt(e['issued'], 3)  # Issued
            ]
        )
        pass
    print(buyOrdersTable)


def printRegionTradeSumTable(li):
    regionTradeSumTable.clear_rows()
    for i, e in enumerate(li):
        regionTradeSumTable.add_row(
            [
                i,
                e['buyRegionName'],
                ISK(e['buyTotalISK']),
                ISK(e['profit']),
                format(e['profit']/e['buyTotalISK'], '.2%'),
                e['sellRegionName']
            ]
        )
        pass
    print(regionTradeSumTable)
