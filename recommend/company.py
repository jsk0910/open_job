from pymongo import MongoClient
import certifi
import json


def pre_processing(jobs, isGangso = False):
    jobList = list()
    for job in jobs: # 데이터 가공
        corpNm = job['corpInfo']['corpNm']
        busiSize = job['corpInfo']['busiSize']
        if isGangso:
            busiSize = "강소기업"
        elif busiSize == "" or busiSize == " ":
            busiSize = "중소기업"

        empTpCd= job['wantedInfo']['empTpCd']
        if empTpCd == '10' or empTpCd == '11':
            empTpNm = "정규직"
        else:
            empTpNm = "계약직"
        workRegion = job['selMthdInfo']['workRegion']
        workday = job['workInfo']['workdayWorkhrCont']
        workday = workday.split(',')
        dtlRecrContUrl = job['wantedInfo']['dtlRecrContUrl']
        tmp = [corpNm,busiSize,empTpNm,workRegion,workday[0],dtlRecrContUrl]
        jobList.append(tmp)

    return jobList

def compare(total_jobs, mongoKey): # 공공데이터 활용, worknet 부산 IT기업 중 강소기업 찾기 
    client = MongoClient(mongoKey, tlsCAFile=certifi.where())
    db = client.job
    gangso = list()
    for company in total_jobs:
        compare = db.publicData.find_one({"corpNm" : company['corpInfo']['corpNm']}, {"_id" : False})
        if compare is not None:
            gangso.append(company)
    return gangso

def find_company(clicked_regionCd, clicked_jobCd, mongoKey): # worknet에 채용공고 찾기, param : 지역코드/직업코드 , 지역코드 입력받고 상세 지역 하나하나 검색해서 output
    client = MongoClient(mongoKey, tlsCAFile=certifi.where())
    db = client.job
    with open('./_json/region.json', "r") as file:
        json_data = json.load(file)
    tmp_rg = json_data[str(clicked_regionCd)]['depth2']
    if len(tmp_rg) == 0: #세종시 처리
        region = [clicked_regionCd]
    else:
        region = [tmp[0] for tmp in tmp_rg]
    total_jobs = list()
    for rg in region:
        company_lists = list(db.employment.find({"regionCd" : str(rg), "occupation3" : str(clicked_jobCd)}, {"_id" : False}))
        if len(company_lists) != 0:
            for company_list in company_lists:
                total_jobs.append(company_list)
    
    gangso = compare(total_jobs, mongoKey) # 해당 직업 중 강소기업 찾기 
    if len(gangso) != 0:
        for g in gangso: # 강소기업과 일반기업의 중복을 방지하기 위하여 중복 제거
            ln = len(total_jobs)
            for i in range(ln-1,-1,-1):
                if g['corpInfo']['corpNm'] == total_jobs[i]['corpInfo']['corpNm']:
                    total_jobs.pop(i)
                    break
    
    gangso = pre_processing(gangso, isGangso = True)
    total_jobs = pre_processing(total_jobs)
    return gangso, total_jobs
