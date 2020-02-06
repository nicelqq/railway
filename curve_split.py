#!usr/bin/env python
#-*-coding:utf-8-*-
import pandas as pd
import time
import random
import string
import re

def GetPassword(length):
    #生成随机字符串
    Ofnum=random.randint(1,length)
    Ofletter=length-Ofnum
    slcNum=[random.choice(string.digits) for i in range(Ofnum)]
    slcLetter=[random.choice(string.ascii_letters) for i in range(Ofletter)]
    slcChar=slcLetter+slcNum
    random.shuffle(slcChar)
    getPwd=''.join([i for i in slcChar])
    return getPwd

def findNextCurve(data, currentCurve, dataLength):
    # 查找下一条曲线，返回曲线index
    i = currentCurve + 1
    while True:
        if i < dataLength:
            if (data.loc[i, 'cell_type'] == 0): # 下一条是直线，且不是最后一条
                i += 1
            else:
                break
        else:
            break
    return i


def distance300(data, currentCurve, nextCurve):
    #两条曲线距离>300m时
    #两端曲线向中间延长50m，
    # 中间的直线部分合并为一条直线，如果两条曲线之间有记录，取第一条记录ID作为新纪录id，其他删除；如果没有记录新生成一个id
    dataOne = pd.DataFrame(columns= data.columns)
    dis = nextCurve - currentCurve - 1
    data.loc[currentCurve, 'end_mileage_cell'] += 0.05
    data.loc[nextCurve, 'start_mileage_cell'] -= 0.05
    if dis > 0:
        data.loc[currentCurve+1, 'start_mileage_cell'] = data.loc[currentCurve, 'end_mileage_cell']
        data.loc[currentCurve+1, 'end_mileage_cell'] = data.loc[nextCurve, 'start_mileage_cell']
        ind = [currentCurve + i + 2 for i in range(dis-1)]
        data.drop(ind, inplace=True)
    else:
        s1 = re.sub(r'\.', '', str(time.time()))
        if len(s1) < 29:
            len_str = 29 - len(s1)
            s2 = GetPassword(len_str)
            s = s1 + s2
        else:
            s = s1[0:29]
        dataOne.loc[0, 'id'] = 'new' + s
        dataOne.loc[0, 'line_sku'] = data.loc[currentCurve, 'line_sku']
        dataOne.loc[0, 'long_chain_labeling'] = data.loc[currentCurve, 'long_chain_labeling']
        dataOne.loc[0, 'start_mileage_cell'] = data.loc[currentCurve, 'end_mileage_cell']
        dataOne.loc[0, 'end_mileage_cell'] = data.loc[nextCurve, 'start_mileage_cell']
        dataOne.loc[0, 'cell_type'] = 0
        data = data.append(dataOne, ignore_index=False)

    return data


def distance100to300(data, distance, currentCurve, nextCurve):
    #两曲线距离在100m~300m之间，从中间分隔开
    data.loc[currentCurve, 'end_mileage_cell'] += distance / 2
    data.loc[nextCurve, 'start_mileage_cell'] = data.loc[currentCurve, 'end_mileage_cell']
    dis = nextCurve - currentCurve - 1
    ind = [currentCurve + i + 1 for i in range(dis)]
    data.drop(ind, inplace=True)
    return data


def distance100(data, currentCurve, nextCurve):
    #两曲线间距小于100m，直接合并到前一条曲线上
    data.loc[currentCurve, 'end_mileage_cell'] = data.loc[nextCurve, 'start_mileage_cell']
    dis = nextCurve - currentCurve - 1
    ind = [currentCurve + i + 1 for i in range(dis)]
    data.drop(ind, inplace=True)
    return data


def splitSub(data):
    #dataTemp = pd.DataFrame(columns=data.columns)  # 存储划分后的数据
    #dataTempOne = pd.DataFrame(columns=data.columns)  # 只包含一条数据
    data['length'] = data['end_mileage_cell'] - data['start_mileage_cell']
    dataLength = len(data)
    i = 0
    while i < dataLength - 1:
        # 如果单元为曲线，则需要检测与下一条曲线的距离,
        # 可能出现两条曲线之间存在多条直线，需要进行处理
        # 如果中间所有直线长度之和>0.3km,将就近直线部分划分给曲线0.05km，如果就近曲线<0.05km,选择第二近的
        # 如果中间所有直线长度之和0.1km<l<0.3km,从一半处划分
        # <0.1,将该部分归为该曲线
        if data.loc[i, 'cell_type'] == 1:
            nextI = findNextCurve(data, i, dataLength)
            if nextI < dataLength:
                if  (data.loc[nextI, 'cell_type'] == 1):
                    distance = data.loc[nextI, 'start_mileage_cell'] - data.loc[i, 'end_mileage_cell']
                    if distance >= 0.3:
                        data = distance300(data, i, nextI)
                    elif (distance >= 0.1) & (distance < 0.3):
                        data = distance100to300(data, distance, i, nextI)
                    elif distance < 0.1:
                        data = distance100(data, i, nextI)
                    i = nextI
            else:
                break
        else:
            i += 1
    return data


def curveAndStraightSplit(data, lineSku):
    #传入数据，以及要划分的线名、行别、工务段，这里都用lineSku唯一标识
    #按照长短链区分开，分别来划分
    dataTemp = data[data.line_sku == lineSku]
    dataTempN = dataTemp[data.long_chain_labeling == 'N']
    dataTempN = dataTempN.sort_values(by='start_mileage_cell').reset_index(drop=True)
    if len(dataTempN) > 1:
        dataTempN = splitSub(dataTempN)
    dataTempY = dataTemp[data.long_chain_labeling == 'Y']
    dataTempY = dataTempY.sort_values(by='start_mileage_cell').reset_index(drop=True)
    if len(dataTempY) > 1:
        dataTempY = splitSub(dataTempY)
    data = pd.concat([dataTempN,dataTempY], axis=0)
    return data

def main():
    data = pd.read_excel('select_id_line_sku_long_chain_labeling_start_mileage_cell_end_mi_202002050914.xlsx')
    dataTemp = pd.DataFrame(columns= data.columns)
    lineSkuDistinct = data.line_sku.drop_duplicates()
    #lineSkuDistinct = [1155]
    for k in lineSkuDistinct:
        dataTemp = pd.concat([dataTemp,curveAndStraightSplit(data, k)], axis=0)

    dataTemp = dataTemp[data.columns]

    dataTemp.to_csv('curve20100206.csv',index=False)


if __name__ == '__main__':
    start = time.time()
    main()
    end = time.time()
    print(end - start)