import csv
import sqlite3
import networkx as nx
import itertools
from math import *
import matplotlib.pyplot as plt
from graphillion import GraphSet
from memory_profiler import profile

#駅名取り出し（駅コードから）
def station_name(station_cd):
    search_company_cd = 'select station_name from stations_db where station_cd = ? or station_g_cd = ?'
    where = (station_cd,station_cd)
    cur.execute(search_company_cd, where)
    station_name = cur.fetchone()
    return station_name[0]

#2駅間の直線距離計算
def cal_phi(ra,rb,lat):
    return atan(rb/ra*tan(lat))

def cal_rho(lat_a,lon_a,lat_b,lon_b):
    ra=6378.140  # equatorial radius (km)
    rb=6356.755  # polar radius (km)
    F=(ra-rb)/ra # flattening of the earth
    rad_lat_a=radians(lat_a)
    rad_lon_a=radians(lon_a)
    rad_lat_b=radians(lat_b)
    rad_lon_b=radians(lon_b)
    pa=cal_phi(ra,rb,rad_lat_a)
    pb=cal_phi(ra,rb,rad_lat_b)
    xx=acos(sin(pa)*sin(pb)+cos(pa)*cos(pb)*cos(rad_lon_a-rad_lon_b))
    c1=(sin(xx)-xx)*(sin(pa)+sin(pb))**2/cos(xx/2)**2
    c2=(sin(xx)+xx)*(sin(pa)-sin(pb))**2/sin(xx/2)**2
    dr=F/8*(c1-c2)
    rho=ra*(xx+dr)
    return rho

#Graphillionの経路並び替え
def order_path(start_station,path):
    list_end_station = ''
    path_return = []
    path_return.append(start_station)
    path_list = list(path)

    while (len(path_list) > 0):
        for edge in path_list:
            station_cd1 = edge[0]
            station_cd2 = edge[1]
            list_end_station = path_return[-1]
            if station_cd1 == list_end_station:
                path_return.append(station_cd2)
                path_list.remove(edge)
                break
            elif station_cd2 == list_end_station:
                path_return.append(station_cd1)
                path_list.remove(edge)
                break
    return path_return

#Graphillionの経路を木構造で並び替え
def order_tree_path(start_station,path):
    list_end_station = ''
    path_return = []
    path_return.append(start_station)
    path_list = list(path)
    for edge in path:
        if start_station == edge[0]:
            path_return.append(edge[1])
            path_list.remove(edge)
    while (len(path_list) > 0):
        for edge in path_list:
            station_cd1 = edge[0]
            station_cd2 = edge[1]
            list_end_station = path_return[-1]
            if station_cd1 == list_end_station:
                path_return.append(station_cd2)
                path_list.remove(edge)
                break
        if len(path_list) == pre_length:
            return -1
        pre_length = len(path_list)
    return path_return

#@profile
#Graphiilionで全探索
def search_all_station_graphillion(start, tree, tree_uni, deg):
    path_return = []
    for v in tree._vertices:
        if v == start:
            continue
        end = v
        deg[end] = 1
        #one_path = tree.graphs(vertex_groups = [[start, end]], degree_constraints = deg, linear_constraints = [(tree_uni, (0, 360))], no_loop = True)
        one_path = tree.paths(start, end)
        #print (len(one_path))
        for path in one_path.min_iter():
            path_return.append(path)
            break
        deg[end] = range(0, 3, 2)
    return path_return

#Main部分
#JRの駅と路線読み込み
csv_file1 = open("../Cytoscape Out/JR-tohoku-node.csv", "r", encoding = "utf-8", errors = "", newline = "")
fp1 = csv.reader(csv_file1, delimiter = ",", doublequote = True, lineterminator = "\r\n", quotechar = '"', skipinitialspace = True)
csv_file2 = open("../Cytoscape Out/JR-tohoku-edge.csv", "r", encoding = "utf-8", errors = "", newline = "")
fp2 = csv.reader(csv_file2, delimiter = ",", doublequote = True, lineterminator = "\r\n", quotechar = '"', skipinitialspace = True)
db_name = '../SQLite/Station_DB.sqlite3'
con = sqlite3.connect(db_name)
cur = con.cursor()

#グラフオブジェクト作成
G = nx.Graph()
pos = {}
edges = {}
universe = []
tree_uni = []
minmax_count = 0
zero_to_two = range(3)
zero_or_two = range(0, 3, 2)
dc = {}
edge_list = []
path_list = []

#駅と座標を設定
for row in fp1:
    G.add_node(int(row[0]))
    G.add_node(int(row[1]))
    row[4] = float(row[4]) * -1
    x_pos = float(row[3]) - 1355555.55
    y_pos = float(row[4]) - 465555.55
    pos[int(row[0])] = (x_pos,y_pos)
    pos[int(row[1])] = (x_pos,y_pos)

#路線を設定
for row in fp2:
    edge_list.append([int(row[0]),int(row[1]),float(row[2])])
    G.add_edge(int(row[0]),int(row[1]))
    edges = int(row[0]),int(row[1]),float(row[2])
    universe.append(edges)

print (len(universe))
#グラフ作成
start_station = 1122115 #スタート駅コード
end_station = ''
degree_constraints = {start_station: 1}
GraphSet.set_universe(universe)
tree = GraphSet.trees(root = start_station)
for edge in tree._weights:
    for row in edge_list:
        if row[0] in (edge[0], edge[1]) and row[1] in (edge[0], edge[1]):
            edges = int(edge[0]),int(edge[1]),float(row[2])
            tree_uni.append(edges)
for v in tree._vertices:
    if v == start_station:
        dc.setdefault(v, 1)
        continue
    dc.setdefault(v, zero_or_two)

#Graphillionで全探索・経路数表示
path_list = search_all_station_graphillion(start_station, tree, tree_uni, dc)
print (len(path_list))

"""
#Cytoscapeで路線を表示するためのテキスト作成
cytoscape_text = 'shared name:'
cytoscape_station = []
st1_flag = 0
st2_flag = 0
for path in path_list:
    for station in path:
        station1 = str(station[0])
        station2 = str(station[1])
        for cyt_st in cytoscape_station:
            if cyt_st == station1:
                st1_flag = 1
            if cyt_st == station2:
                st2_flag = 1
        if st1_flag != 1:
            cytoscape_station.append(station1)
            cytoscape_text = cytoscape_text + station1 + ' OR '
        if st2_flag != 1:
            cytoscape_station.append(station2)
            cytoscape_text = cytoscape_text + station2 + ' OR '
        st1_flag = 0
        st2_flag = 0
#print (cytoscape_text)


search_company_cd = 'select lat,lon from stations_db where station_cd = ?'
where = (start_station,)
cur.execute(search_company_cd, where)
start_latlon = cur.fetchone()
sta_lat = float(start_latlon[0])
sta_lon = float(start_latlon[1])
dist_list = []

for station in cytoscape_station:
    sta = int(station)
    where = (sta,)
    cur.execute(search_company_cd, where)
    dep_latlon = cur.fetchone()
    if sta != start_station and dep_latlon is not None:
        if sta_lat != dep_latlon[0]:
            dep_lat = float(dep_latlon[0])
            dep_lon = float(dep_latlon[1])
            dist = cal_rho(sta_lat,sta_lon,dep_lat,dep_lon)
            dist_list.append([dist,sta])

dist_list = sorted(dist_list, reverse=True)
count = 0
cytoscape_text = 'shared name:'

for list in dist_list:
    if count > 100:
        break
    station = list[1]
    count += 1
    dist = list[0]
    print (station_name(station) + ' ' + str(station) + ' ' + str(dist))
    cytoscape_text = cytoscape_text + str(station) + ' OR '
print (cytoscape_text)
"""
"""
print ('----')
all_path = tree.paths(1160708,1163402)
path = all_path.min_iter()
or_text = ''
for station in path:
    or_text = or_text + str(station) + ' OR '

print (or_text)
"""

"""
出発駅から出発駅以外の全ての最短経路 linearでコスト指定あり

1111801(tohoku)
0-30
real	0m34.364s
user	0m28.501s
sys	    0m2.699s

1111801(tohoku)
0-40
83
real	0m31.983s
user	0m28.055s
sys 	0m2.622s

1111801(tohoku)
0-50
116
real	0m39.243s
user	0m28.437s
sys	    0m3.098s

1111801(tohoku)
0-60
real	0m37.734s
user	0m28.893s
sys	    0m2.836s

1121422(chubu))
0-30
63
real	0m28.406s
user	0m21.775s
sys	    0m1.029s

1121422(chubu))
0-40
106
real	0m28.558s
user	0m22.827s
sys	    0m1.012s

1121422(chubu))
0-50
145
real	0m31.087s
user	0m24.820s
sys	    0m1.050s

1121422(chubu))
0-60
184
real	0m32.612s
user	0m25.853s
sys	    0m1.026s

1141501(kinki)
0-30
135
real	0m49.834s
user	0m45.185s
sys	    0m2.716s

1141501(kinki)
0-40
309
real	1m9.967s
user	0m54.258s
sys	    0m3.515s

1141501(kinki)
0-50
399
real	1m41.451s
user	1m36.009s
sys	    0m5.588s

1141501(kinki)
0-60
484
real	3m28.805s
user	3m12.106s
sys	    0m16.865s

1141501(kinki)
0-70
520
real	6m11.294s
user	5m22.325s
sys	    0m37.212s

1141501(kinki)
0-80
531
real	9m16.439s
user	8m4.180s
sys 	1m4.691s
"""
