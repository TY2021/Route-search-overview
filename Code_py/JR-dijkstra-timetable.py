import csv
import sqlite3
import reJR-
import os
import copy
import datetime
from math import *
from collections import defaultdict
from heapq import heappop, heappush, nlargest
#from memory_profiler import profile

#2駅間の直線距離計算
def cal_phi(ra,rb,lat):
    return atan(rb/ra*tan(lat))

def cal_rho(start, goal):
    search_latlon = 'select lat,lon from station_db where station_cd = ?'
    where = (start,)
    cur.execute(search_latlon, where)
    start_latlon = cur.fetchone()
    lat_a = float(start_latlon[0])
    lon_a = float(start_latlon[1])
    where = (goal,)
    cur.execute(search_latlon, where)
    goal_latlon = cur.fetchone()
    lat_b = float(goal_latlon[0])
    lon_b = float(goal_latlon[1])
    if lat_a == lat_b and lon_a == lon_b:
        return 0

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

#駅コードから駅名を返す
def station_name(station_cd):
    search_company_cd = 'select station_name from stations_db where station_cd = ? or station_g_cd = ?'
    where = (station_cd,station_cd)
    cur.execute(search_company_cd, where)
    station_name = cur.fetchone()
    return station_name[0]

#経路内に同じ駅が含まれていないかチェック
def is_member(path, new):
    for station in path:
        if station == new:
            return False
    return True

#幅優先探索
def line_bfs(start, goal, line_cd_follow):
    edge = graph.graph
    que_path = [[start]]

    while que_path:
        path = que_path.pop()
        end = path[-1]
        list = edge[end]
        count = 0

        #ゴール判定
        if end == goal:
            return path

        #経路追加
        for tuple in list:
            station = tuple[0]
            line_cd = int(station / 100)
            if is_member(path, station) and line_cd == line_cd_follow:
                new_path = copy.deepcopy(path)
                new_path.append(station)
                que_path.append(new_path)
                count += 1
    return None

# 時刻表の処理
class Timetable(object):
    def traintime(self, u, v, dist, weight):
        #ファイルパス・路線idなどの変数設定
        line_cd_be = int(u / 100)
        line_cd_af = int(v / 100)
        line_sql = str(line_cd_af) + '.sqlite3'
        timetable_file = None
        timetable_sql = None
        timetable_list = []
        station_direction = None
        start_time = datetime.datetime(2019, 1, 1, 6, 00) #出発時間は06:00
        path = '../TimetableSQL/'
        files = os.listdir(path)
        files_file = [f for f in files if os.path.isfile(os.path.join(path, f))]

        for file_sql in files_file:
            if line_sql == file_sql:
                timetable_file = file_sql
                break

        #時刻表DBに探索する駅の時刻表があるか確認
        if timetable_file:
            db_name = '..//TimetableSQL/' + timetable_file
            con = sqlite3.connect(db_name)
            cur = con.cursor()

            select = 'select tbl_name from sqlite_master'
            for select_sql in cur.execute(select):
                timetable_sql = select_sql[0]
                row = timetable_sql.split('_')
                station = int(row[2])
                if v == station and row[3] != '':
                    direction = int(row[3])
                    path = line_bfs(u, direction, line_cd_be)
                    if path and v in path:
                        station_direction = timetable_sql

        #概算で移動時間を計算
        sec = weight * 60
        dist_time = start_time + datetime.timedelta(seconds = dist)
        now_time = dist_time + datetime.timedelta(seconds = sec)

        #現在駅から次の駅までの移動時間（次の駅の到着時刻）を取得
        if station_direction:
            select = 'select hour, minute from ' + station_direction + ' where hour = ? and minute >= ? order by minute asc'
            where = (now_time.hour, now_time.minute)
            cur.execute(select, where)
            timetable_item1 = cur.fetchone()
            now_time = now_time + datetime.timedelta(hours = 1)
            select = 'select hour, minute from ' + station_direction + ' where hour >= ' + str(now_time.hour) + ' order by hour asc'
            cur.execute(select)
            timetable_item2 = cur.fetchone()
            if timetable_item1:
                table_time = datetime.datetime(now_time.year, now_time.month, now_time.day, timetable_item1[0], timetable_item1[1])
                now_time = (table_time - start_time).total_seconds()
            elif timetable_item2:
                table_time = datetime.datetime(now_time.year, now_time.month, now_time.day, timetable_item2[0], timetable_item2[1])
                now_time = (table_time - start_time).total_seconds()

        if not station_direction or (not timetable_item1 and not timetable_item2):
            now_time = (now_time - start_time).total_seconds()

        if dist > now_time:
            now_time = dist

        return now_time

# 隣接リストによる有向グラフ
class Graph(object):
    def __init__(self):
        self.graph = defaultdict(list)

    def __len__(self):
        return len(self.graph)

    def add_edge(self, src, dst, weight=1):
        self.graph[src].append((dst, weight))

    def get_nodes(self):
        return self.graph.keys()

# ダイクストラ法（二分ヒープ）による最短経路探索
# 計算量: O((E+V)logV)
class Dijkstra(object):
    def __init__(self, graph, start, dist_list, nodes):
        self.g = graph.graph

        # startノードからの最短距離
        # startノードは0, それ以外は無限大で初期化
        self.dist = defaultdict(lambda: float('inf'))
        self.dist[start] = 0
        count_loop = 0

        # 最短経路での1つ前のノード
        self.prev = defaultdict(lambda: None)

        # startノードをキューに入れる
        self.Q = []
        heappush(self.Q, (self.dist[start], 0, start))

        while self.Q:
            # 優先度（距離）が最小であるキューを取り出す
            dist_u, direct_u, u = heappop(self.Q)
            if self.dist[u] < dist_u:
                continue
            for v, weight in self.g[u]:
                if (dist_list[v] + 1) < direct_u:
                    continue
                time = Timetable()
                alt = time.traintime(u, v, dist_u, weight)
                direct_now = dist_list[v]
                #print (str(weight_now) + ' ' + str(direct_now))
                if self.dist[v] > alt:
                    self.dist[v] = alt
                    self.prev[v] = u
                    heappush(self.Q, (alt, direct_now, v))
            count_loop += 1

    # startノードからgoalノードまでの最短距離
    def shortest_distance(self, goal):
        return self.dist[goal]
    # startノードからgoalノードまでの最短経路
    def shortest_path(self, goal):
        path = []
        node = goal
        while node is not None:
            path.append(node)
            node = self.prev[node]
        return path[::-1]

#@profile
#ダイクストラ法で全探索
def all_search_dijkstra(start, graph, fp, d_dist):
    path_return = []
    dijkstra_graph = Dijkstra(graph, start, d_dist, fp)
    for row in fp:
        v = int(row)
        if v == start:
            continue
        dist = dijkstra_graph.shortest_distance(v)
        if dist <= 64800:
            path = dijkstra_graph.shortest_path(v)
            path_return.append(path)
            #path_return.append(v)
    return path_return

#Main部分
#路線図読み込み
csv_file1 = open("../Cytoscape Out/JR-all-node.csv", "r", encoding = "utf-8", errors = "", newline = "")
fp1 = csv.reader(csv_file1, delimiter = ",", doublequote = True, lineterminator = "\r\n", quotechar = '"', skipinitialspace = True)
csv_file2 = open("../Cytoscape Out/JR-all-edge-cost.csv", "r", encoding = "utf-8", errors = "", newline = "")
fp2 = csv.reader(csv_file2, delimiter = ",", doublequote = True, lineterminator = "\r\n", quotechar = '"', skipinitialspace = True)
db_name = '../SQLite/Station_DB.sqlite3'
con = sqlite3.connect(db_name)
cur = con.cursor()

#スタート駅・変数設定
start = 1122115
edges = []
nodes = []
path_list = []
direct_dist  = {}

#路線を設定
for row in fp2:
    edges.append([int(row[0]),int(row[1]),float(row[2])])

#路線設定
graph = Graph()
for src, dst, weight in edges:
    graph.add_edge(src, dst, weight)
    graph.add_edge(dst, src, weight)
for row in fp1:
    station = int(row[0])
    direct_dist[station] = cal_rho(start, station)
    nodes.append(station)

#ダイクストラ法で全探索・経路数表示
path_list = all_search_dijkstra(start, graph, nodes, direct_dist)
print (len(path_list))

"""
#Cytoscapeで路線を表示するためのテキスト作成
cytoscape_text = 'shared name:'
cytoscape_station = []
st_flag = 0
for path in path_list:
    for station in path:
        station = str(station)
        for cyt_st in cytoscape_station:
            if cyt_st == station:
                st_flag = 1
        if st_flag != 1:
            cytoscape_station.append(station)
            cytoscape_text = cytoscape_text + station + ' OR '
        st_flag = 0
#print (cytoscape_text)

search_company_cd = 'select lat,lon from stations_db where station_cd = ?'
where = (start,)
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
    if sta != start and dep_latlon is not None:
        if sta_lat != dep_latlon[0]:
            dep_lat = float(dep_latlon[0])
            dep_lon = float(dep_latlon[1])
            dist = cal_rho(start, sta)
            dist_list.append([dist,sta])

dist_list = sorted(dist_list, reverse=True)
count = 0
cytoscape_text = 'shared name:'

for list in dist_list:
    if count > 100:
        break
    dist = list[0]
    station = list[1]
    count += 1
    print (station_name(station) + ' ' + str(station) + ' ' + str(dist))
    cytoscape_text = cytoscape_text + str(station) + ' OR '
print (cytoscape_text)
"""

"""
cytoscape_text = 'shared name:'
cytoscape_station = []
st_flag = 0
for station in path_list:
    station = str(station)
    cytoscape_text = cytoscape_text + station + ' OR '
print (cytoscape_text)

"""

"""
dist_max = list(map(lambda x: x[0], self.Q))
            if (count_loop % 100) == 0:
                list.sort(dist_max, reverse=True)
                dist_u_max = dist_max[0]
                direct_u = dist_list[u]
                for node in nodes:
                    direct_n = dist_list[node]
                    if (direct_n - 1) < direct_u and direct_u < (direct_n + 1):
                        self.dist[node] == dist_u_max
"""
