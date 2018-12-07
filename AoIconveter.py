import csv
import bs4
import urllib.request
from urllib.parse import quote_plus

global layoutside
global panelside
global pcbside
global pcburls

def getwebdata(layoutname):
    global layoutside
    global panelside
    global pcbside
    global pcburls

    print("downloading layout")
    with urllib.request.urlopen('http://192.168.0.10/viewLayout.cgi?LAYOUT=' + quote_plus(layoutname)) as response:
        layoutdata = response.read()

    layoutside = bs4.BeautifulSoup(layoutdata, "lxml")

    try:
        panelurl = "http://192.168.0.10/" + layoutside.find("table", class_="DataTable").tbody.find("a")["href"]
    except AttributeError:
        exit("Layout " + layoutname + " findes ikke")

    print("downloading panel")
    with urllib.request.urlopen(panelurl) as response:
        paneldata = response.read()

    panelside = bs4.BeautifulSoup(paneldata, "lxml")
    pcburls = panelside.find("table", class_="DataTable").tbody.find_all("a")


def getPCBtable(side):
    tablels = pcbside.find_all("table", class_="")

    if len(tablels) == 2:
        table = tablels[0]
    else:
        table = tablels[1]

    return [[td.text for td in row.find_all("td")] for row in table.select("tr")][1:]


def getdict():
    print("downloading component data")
    with urllib.request.urlopen('http://192.168.0.10/viewCompTabList.cgi?HTMLTABLE') as response:
        data = response.read()

    side = bs4.BeautifulSoup(data, "lxml")
    table = side.find_all("table")[0]

    outdata = {}
    for row in table.select("tr"):
        rowdata = row.find_all("td")
        try:
            outdata[rowdata[0].text] = rowdata[2].text
        except IndexError:
            continue

    return outdata


def getfid(side):
    table = side.find("table", class_="DataTable2").find_all("table", class_="DataTable2")[2]
    return [[td.text for td in row.find_all("td")] for row in table.select("tr")][1:]


def getPanelPositions(side):
    table = side.find("table", class_="DataTable").tbody

    return [[td.text for td in row.find_all("td")] for row in table.select("tr")]


def getpackage(name):
    with urllib.request.urlopen('http://192.168.0.10/viewComponent.cgi?CMP=' + quote_plus(name)) as response:
        data = response.read()

    side = bs4.BeautifulSoup(data, "lxml")
    table = side.find_all("table", class_="DataTable2")
    return table[0].select("td")[10].text


def getConveyorWidth(side):
    table = side.find("table", class_="DataTable2").find_all("td")[7].text
    return table


def tomilli(tal):
    return int(float(tal[:-1]) * 25.4 * 1000)


def panelStep(side):
    def tomilli(tal):
        return round(float(tal[:-1]) * 25.4, 3)

    panelPositions = getPanelPositions(side)

    x = [tomilli(row[2]) for row in panelPositions]

    x = sorted(list(set(x)))
    if len(x) == 1:
        x.append(x[0])

    y = [tomilli(row[3]) for row in panelPositions]
    y = sorted(list(set(y)))
    if len(y) == 1:
        y.append(y[0])

    return [round(x[1] - x[0], 3), round(y[1] - y[0], 3)]


layoutname = input("angive layout: ")
#layoutname = sys.argv[1]
print(layoutname)
getwebdata(layoutname)

table = []
for i in pcburls:
    print("downloading PCB")
    with urllib.request.urlopen("http://192.168.0.10/" + i["href"]) as response:
        pcbdata = response.read()

    pcbside = bs4.BeautifulSoup(pcbdata, "lxml")
    table += getPCBtable(pcbside)


outdata = []
step = panelStep(panelside)
fid = getfid(panelside)
pacdick = getdict()

fidx = [tomilli(row[0]) / 1000 for row in fid]
outdata.append(["panel width", round(tomilli(getConveyorWidth(layoutside)) / 1000, 1), "panel length" , round(max(fidx) - min(fidx) + 40, 1)])

outdata.append(["Panelstep", step[0], step[1]])

outdata.append(["Tykkelse", "1.6"])

# fids
j = 1
for i in fid:
    outdata.append(
        ["FID" + str(j), i[2], "RAVI", i[2], int(float(i[0][:-1]) * 25.4 * 1000), int(float(i[1][:-1]) * 25.4 * 1000),
         0, "True"])
    j += 1

for i in table:
    line = i
    if line[1] == "Noname":
        continue
    line[1] = line[1][:-1]

    if len(line[-1]) > 5:
        line = line[:-1]
        line.append("False")

    else:
        line.append("True")

    if len(line[-2]) == 1:
        del line[-2]

    line[1] = line[1].split("\n")[0]

    try:
        line[3] = pacdick[line[1]]
    except KeyError:
        continue

    line[4] = int(float(line[4][:-1]) * 25.4 * 1000)
    line[5] = int(float(line[5][:-1]) * 25.4 * 1000)
    del line[6]

    line[6] = int(line[6][:-1])
    if 360 - line[6] >= 360:
        line[6] = -line[6]
    else:
        line[6] = 360 - line[6]
    if line[3] == "PCB":
        line[7] = "False"

    #print(line)
    outdata.append(line)

# til CSV
with open(layoutname + "-AOI.txt", "w") as f:
    wr = csv.writer(f, delimiter="\t")
    wr.writerows(outdata)

print("done")
