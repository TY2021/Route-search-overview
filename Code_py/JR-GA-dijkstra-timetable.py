import random
import csv
import sqlite3
import re
import os
import copy
import datetime
import GeneticAlgorithm as ga
from deap import base
from deap import creator
from deap import tools
from math import *
from collections import defaultdict
from heapq import heappop, heappush
#from operator import itemgetter
from decimal import Decimal
random.seed()

# 遺伝子情報の長さ
GENOM_LENGTH = 100
# 遺伝子集団の大きさ
MAX_GENOM_LIST = 100
# 遺伝子選択数
SELECT_GENOM = 50
# 個体突然変異確率
INDIVIDUAL_MUTATION = 0.3
# 遺伝子突然変異確率
GENOM_MUTATION = 0.3
# 繰り返す世代数
MAX_GENERATION = 40

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

class genom:
    genom_list = None
    evaluation = None

    def __init__(self, genom_list, evaluation):
        self.genom_list = genom_list
        self.evaluation = evaluation


    def getGenom(self):
        return self.genom_list


    def getEvaluation(self):
        return self.evaluation


    def setGenom(self, genom_list):
        self.genom_list = genom_list


    def setEvaluation(self, evaluation):
        self.evaluation = evaluation

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
    def __init__(self, graph, start):
        self.g = graph.graph

        # startノードからの最短距離
        # startノードは0, それ以外は無限大で初期化
        self.dist = defaultdict(lambda: float('inf'))
        self.dist[start] = 0

        # 最短経路での1つ前のノード
        self.prev = defaultdict(lambda: None)

        # startノードをキューに入れる
        self.Q = []
        heappush(self.Q, (self.dist[start], start))

        while self.Q:
            # 優先度（距離）が最小であるキューを取り出す
            dist_u, u = heappop(self.Q)
            if self.dist[u] < dist_u:
                continue
            for v, weight in self.g[u]:
                time = Timetable()
                weight = time.traintime(u, v, dist_u, weight)
                alt = weight
                if self.dist[v] > alt:
                    self.dist[v] = alt
                    self.prev[v] = u
                    heappush(self.Q, (alt, v))
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



#個体生成（ランダムに到着駅を選出）
def create_genom(length):
    station_genom = []
    for count in range(length):
        station_genom.append([station_list[random.randint(0, 5133)], 0])
    return ga.genom(station_genom, 0)

#評価関数（直線距離）
def evaluation(ga_temp):
    evaluate_list = []
    station_genom = []
    list_total = 0
    genom_list = ga_temp.getGenom()
    for station, dist in genom_list:
        weight = dijkstra_graph.shortest_distance(station)
        if weight > 64800:
            evaluate_list.append([station, -1])
            continue
        direct_dist = cal_rho(departure, station)
        evaluate_list.append([station, direct_dist])
        for station, dist in evaluate_list:
            list_total = list_total + dist
    return ga.genom(evaluate_list, list_total), list_total

#選択（ランダム）
def select(ga_temp, elite_length):
    sort_result = sorted(ga_temp, reverse=True, key=lambda u: u.evaluation)
    result = [sort_result.pop(0) for i in range(elite_length)]
    return result

#交叉（重複除去）
def crossover(ga_temp):
    genom_list = []
    progeny = []
    progeny = ga_temp.getGenom()

    #重複駅を別の駅に変える
    for count1 in range(SELECT_GENOM - 1):
        count2 = count1 + 1
        one_station = progeny[count1][0]
        second_station = progeny[count2][0]
        if one_station == second_station:
            line_cd = int(second_station / 100)
            search_line_name = 'select line_name_h from line_list_db where line_cd = ?'
            where = (line_cd,)
            cur.execute(search_line_name, where)
            line_name = cur.fetchone()
            search_station = 'select station_cd from station_db where line_name = ?'
            where = (line_name[0],)
            cur.execute(search_station, where)
            line_stations = cur.fetchall()
            length = len(line_stations) - 1
            one_station = line_stations[random.randint(0, length)]
            dist = cal_rho(departure, second_station)
            progeny[count1][0] = one_station
            progeny[count1][1] = dist

    genom_list.append(ga.genom(progeny, 0))
    return genom_list

#世代交代
def next_generation_gene_create(ga_temp, ga_elite, ga_progeny):
    # 現行世代個体集団の評価を低い順番にソートする
    next_generation_geno = sorted(ga_temp, reverse=False, key=lambda u: u.evaluation)
    # 追加するエリート集団と子孫集団の合計ぶんを取り除く
    for i in range(0, len(ga_elite) + len(ga_progeny)):
        next_generation_geno.pop(0)
    # エリート集団と子孫集団を次世代集団を次世代へ追加
    next_generation_geno.extend(ga_elite)
    next_generation_geno.extend(ga_progeny)
    return next_generation_geno

#突然変異（適当な到着駅挿入）
def mutation(ga_temp, individual_mutation, genom_mutation):
    ga_list = []
    for i in ga_temp:
        if individual_mutation > (random.randint(0, 100) / Decimal(100)):
            for i_ in i.getGenom():
                genom_list = []
                if individual_mutation > (random.randint(0, 100) / Decimal(100)):
                    matation_num = random.randint(0, SELECT_GENOM-1)
                    station = station_list[matation_num]
                    weight = dijkstra_graph.shortest_distance(station)
                    dist = cal_rho(departure, station)
                    if weight > 64800:
                        genom_list.append([station, -1])
                    else:
                        genom_list.append([station, dist])
                else:
                    genom_list.append(i_)
            i.setGenom(genom_list)
            ga_list.append(i)
        else:
            ga_list.append(i)
    return ga_list

#@profile
def GeneticAlgorithm():
    # 一番最初の現行世代個体集団を生成
    current_generation_individual_group = []
    for i in range(MAX_GENOM_LIST):
        current_generation_individual_group.append(create_genom(GENOM_LENGTH))

    for count_ in range(1, MAX_GENERATION + 1):
        # 現行世代個体集団の遺伝子を評価し、genomClassに代入
        for i in range(MAX_GENOM_LIST):
            evaluation_result, list_total = evaluation(current_generation_individual_group[i])
            current_generation_individual_group[i].setEvaluation(list_total)
            current_generation_individual_group[i] = evaluation_result
        # エリート個体を選択
        elite_genes = select(current_generation_individual_group, SELECT_GENOM)
        # エリート遺伝子を交叉させ、リストに格納
        progeny_gene = []
        for i in range(0, SELECT_GENOM):
            progeny_gene.extend(crossover(elite_genes[i]))
        # 次世代個体集団を現行世代、エリート集団、子孫集団から作成
        next_generation_individual_group = next_generation_gene_create(current_generation_individual_group,elite_genes, progeny_gene)
        # 次世代個体集団全ての個体に突然変異
        next_generation_individual_group = mutation(next_generation_individual_group,INDIVIDUAL_MUTATION,GENOM_MUTATION)

        # 1世代の進化的計算終了

        # 各個体適用度を配列化。
        fits = [i.getEvaluation() for i in current_generation_individual_group]

        # 現行世代と次世代を入れ替え
        current_generation_individual_group = next_generation_individual_group

    # 最終結果出力
    paths = elite_genes[0].getGenom()
    paths = sorted(paths, reverse=True, key=lambda x: x[1])
    print (paths)

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
departure = 1121438
station_list = []
edges = []

#駅・路線作成
for row in fp1:
    station_list.append(int(row[0]))
for row in fp2:
    edges.append([int(row[0]),int(row[1]),float(row[2])])
graph = Graph()
for src, dst, weight in edges:
    graph.add_edge(src, dst, weight)
    graph.add_edge(dst, src, weight)
dijkstra_graph = Dijkstra(graph, departure)

#遺伝的アルゴリズム開始
GeneticAlgorithm()
