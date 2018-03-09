#! /usr/local/bin/python3
# coding: utf-8
# __author__ = "Brady Hu"
# __date__ = 2017/10/16 16:11

from selenium import webdriver
import requests
import json
import time
import os
import settings
import transCoordinateSystem
# import sys
import math

global i_qqlimit    #one QQ crawl maxium cities 
global qq_number_sides  # QQ list
global point_total      # population at the city
#global spyder_list       save city coordinate and city name
global my_working_path  # my working directory
#global run_time          start running time 
#global station_output_fname  output data file name appending running time
#global file_output       output data file handler 

i_qqlimit = 1
qq_number_sides = 0
point_total = 0

my_working_path = "D:\\working\\easygo"


#创建一个异常类，用于在cookie失效时抛出异常
class CookieException(Exception):
    def __init__(self):
        Exception.__init__(self)

def Crawl_GStation(spyder_list):
    """爬虫主程序，负责控制时间抓取"""
    while True:
        global i_qqlimit
        global qq_number_sides
        global point_total
         

        cookie = get_cookie(qq_number_sides)
        
        run_time = time.strftime("%Y%m%d_%H%M%S",time.localtime())
        station_output_fname = my_working_path +'\\sp_'+run_time+'.csv'
        file_output = open(station_output_fname, 'w')  # open data file for writing, error for encoding = "utf-8"
        file_output.write('站名,相对人数,时间\n')   # writing first line to output file 
        path_file = my_working_path + '\\data_' + run_time 
        if not os.path.exists(path_file):
            os.mkdir(path_file)
        
        path_file = path_file + '\\'
            
        for item in spyder_list:
            
            #print("此轮抓取开始")
            
            """这部分负责每个qq号码抓取的次数，不能超过settings.fre(缺省设置为100) 次"""
            if i_qqlimit % settings.fre == 0:
                cookie = get_cookie(qq_number_sides)
                qq_number_sides += 1
                i_qqlimit = 1
                print("main: 换号了")

            place = item[0]
            print(place)
            params = spyder_params(item)
            time_now = time.time()
            time_now_str = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time_now))
            
            try:
                text = spyder(cookie, params)
                save(text, time_now_str, file_name= path_file + place + time_now_str+".csv")
            except CookieException as e:
                print("main: CookieExcepton启动")
                cookie = get_cookie(qq_number_sides)
                qq_number_sides += 1
                text = spyder(cookie, params)
                save(text, time_now_str, file_name= path_file + place + time_now_str+".csv")
            # 同一个qq号，做完一个城市，计数加1. 避免超过系统限制最大值
            i_qqlimit += 1
            
            #print("此轮抓取完成")
            
            file_output.write(place+ ','+ str(point_total)+ ','+ time_now_str +'\n')
            point_total = 0
        
        file_output.close()   # close output file 
        break


def get_cookie(num):
    """负责根据传入的qq号位次，获得对应的cookie并返回，以便用于爬虫"""
    chromedriver = r'C:\Users\Administrator\AppData\Local\Google\Chrome\Application\chromedriver.exe'
    os.environ["webdriver.chrme.driver"] = chromedriver
    chrome_login = webdriver.Chrome(chromedriver)
    chrome_login.get(
        "http://c.easygo.qq.com/eg_toc/map.html?origin=csfw&cityid=110000")
    chrome_login.find_element_by_id("u").send_keys(settings.qq_list[num][0])
    chrome_login.find_element_by_id("p").send_keys(settings.qq_list[num][1])
    chrome_login.maximize_window()
    chrome_login.find_element_by_id("go").click()
    time.sleep(10)     #note: 太短了，会来不及滑块验证，就会报错。
    cookies = chrome_login.get_cookies()
    chrome_login.quit()
    user_cookie = {}
    for cookie in cookies:
        user_cookie[cookie["name"]] = cookie["value"]

    return user_cookie


def spyder(user_cookie, params):
    """根据传入的表单，利用cookie抓取宜出行后台数据"""
    user_header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
        "Referer": "http://c.easygo.qq.com/eg_toc/map.html?origin=csfw"
    }
    url = "http://c.easygo.qq.com/api/egc/heatmapdata"
    while True:
        try:
            r = requests.get(url, headers=user_header,
                             cookies=user_cookie, params=params)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print("spyder func Exception:",e.args)
        break

def spyder_params(item):
    """将传入的块转化为网页所需的表单"""
    station,lng_mini,lng_maxi,lat_mini,lat_maxi = item
    lng_mini,lat_mini = transCoordinateSystem.wgs84_to_gcj02(lng_mini,lat_mini)
    lng_maxi,lat_maxi = transCoordinateSystem.wgs84_to_gcj02(lng_maxi,lat_maxi)
    lng = (lng_mini+lng_maxi)*0.5
    lat = (lat_mini+lat_maxi)*0.5
    params = {  "lng_min": lng_mini,
                "lat_max": lat_maxi,
                "lng_max": lng_maxi,
                "lat_min": lat_mini,
                "level": 16,
                "city": "%E6%88%90%E9%83%BD",
                "lat": lat,
                "lng": lng,
                "_token": ""}
    
    return params

def save(text, time_now,file_name):
    """将抓取下来的流数据处理保存到文本文件"""
    global point_total
    
    #判断文件是否存在，若不存在则创建文件并写入头
    try:
        with open(file_name, mode='r') as f:
            f.readline()
    except FileNotFoundError as e:
        with open(file_name, mode='w', encoding='utf-8') as f:
            f.write('count,wgs_lng,wgs_lat,time\n')
    #写入数据, append
    with open(file_name, mode="a", encoding="utf-8") as f:
        node_list = json.loads(text)["data"]
        try:
            min_count = node_list[0]["count"]
            for i in node_list:
                min_count = min(i['count'],min_count)
            for i in node_list:
                i['count'] = i['count']/min_count
                #此处的算法在宜出行网页后台的js可以找到，
                #文件路径是http://c.easygo.qq.com/eg_toc/js/map-55f0ea7694.bundle.js
                gcj_lng = 1e-6 * (250.0 * i['grid_x'] + 125.0) 
                gcj_lat = 1e-6 * (250.0 * i['grid_y'] + 125.0)
                lng, lat = transCoordinateSystem.gcj02_to_wgs84(gcj_lng, gcj_lat)
                point_total += i['count']
                f.write(str(i['count'])+","+str(lng)+","+str(lat)+","+time_now+"\n")
        except IndexError as e:
            #print("Save1 IndexError: 此区域没有点信息",)  # Test is ok
            pass
            
        except TypeError as e:
            print("save2 TypeError: ", node_list)
            """
            save:  http://ui.ptlogin2.qq.com/cgi-bin/login?appid=1600000601&style=9&s_url=http%3A%2F%2Fc.easygo.qq.com%2Feg_toc%2Fmap.html
            """
            raise CookieException
            """如果同一个QQ号在一天内频繁登陆，则报错：
            该用户访问次数过多,CookieExcepton启动,该用户访问次数过多
            """
def stationArea(center):
    """
    input: center (lng, lat)  --->tuple or list
    output: center_area(lng_min,lat_min,lng_max,lat_max) --->  RectangleArea
            OR center_area(center, radius) --->   CircleArea
            
    """
    #import math
    #中心经纬度 center(lng,lat)
    delta = math.pi*2*6371/360
    lng_center, lat_center = float(center[0]), float(center[1])

    lng_range = 0.5/(delta*math.cos(lat_center/180*math.pi))
    lat_range = 0.5/delta

    #四边形，矩形框，站点坐标为中心，爬取算法范围的确定算法，未检验？？ TODO
    lng_min, lng_max = lng_center - lng_range, lng_center + lng_range
  
    lat_min, lat_max = lat_center - lat_range, lat_center + lat_range
    # construct a list:[min,max] , not tuple:(lng_min, lat_min, lng_max, lat_max)
    sa = [lng_min, lat_min, lng_max, lat_max]
    
    return sa

def stationList():
    """
    get station name, station area (rectangle) list
    such as :  [[上海虹桥，最小经度，最大经度，最小纬度，最大纬度],[北京南，...],...]
    input: station_name, station_longitude,station_latitude
    output: station_name, min_longitude, max_longitude, min_latitude,max_latitude
    from stations_wgs.cvs to station_rect_list
    """
    wgs_infile = my_working_path + '\\stations_wgs.csv'
    file_input = open(wgs_infile, mode='r')

    station_rectlist = []   # inital local variable station_list
    for one_line in file_input:  # why I change 'line' to 'one_line'?? TODO
       # line = line.strip()
       # line = line.split(',')
        line = one_line.strip().split(',')
        
        if (line[0] == '') or (line[1] =='') or (line[2] ==''):
            continue
        
        #中心经纬度，站点名称
        delta = math.pi*2*6371/360
        lng_center, lat_center = float(line[1]), float(line[2])

        lng_range = 0.5/(delta*math.cos(lat_center/180*math.pi))
        lat_range = 0.5/delta

        #四边形，矩形框，站点坐标为中心，爬取算法范围的确定算法，未检验？？ TODO
        lng_min, lng_max = lng_center - lng_range, lng_center + lng_range
      
        lat_min, lat_max = lat_center - lat_range, lat_center + lat_range

        #获取spyder_list
        station_rectlist.append([line[0],round(lng_min,5),round(lng_max,5),round(lat_min,5),round(lat_max,5)])
    
    file_input.close()
    return station_rectlist

    
if __name__ == "__main__":
    
    spyder_list = stationList()
    
    Crawl_GStation(spyder_list)    
    
    print("Good, Game Over")
    
