import pandas as pd

def getRegion(): # 지역 코드 중 1depth만 추출 ex) 11000 : 서울, 26000 : 부산
    path = './csv/_regionCd.csv'
    df = pd.read_csv(path)
    row = df.shape[0]
    region = list()
    for i in range(row):
        cid = df.loc[i]['카테고리 ID']
        depth1 = df.loc[i]['1 depth']
        if depth1 != " ":
            region.append([cid, depth1])
    return region

if __name__ == '__main__':
    print(getRegion())