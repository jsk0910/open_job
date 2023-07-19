import streamlit as st
import pandas as pd 
import sys,os
from pymongo import MongoClient
import certifi
import json
from tika import parser
import openai
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

def getToken(str = "", tk = ","):
    return str.split(tk)

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
    with open('_json/region.json', "r") as file:
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

def get_job(): # csv파일에 있는 직업 skill을 list화
    path = 'csv/skills.csv'
    df = pd.read_csv(path)
    df.fillna('', inplace=True)
    jobs = df.values.tolist()
    result = list()
    for job in jobs:
        occu3 = str(job[0])
        jobsCd = str(job[2])
        if len(occu3) == 5:
            occu3 = "0" + occu3
        if len(jobsCd) == 5:
            jobsCd = "0" + jobsCd

        skill = job[3].replace("_", ",")
        skill = skill.replace('학력',"")
        skill = skill.replace('경력',"")
        skill = skill.replace('응시자격',"")
        skill = skill.replace('지역거주자',"")
        skill = skill.replace('사설학원',"")
        skills = skill.replace('독학',"")
        skills = getToken(skills.lower(), tk=',')
        ln = len(skills)
        for i in range(ln-1,-1,-1):
            if skills[i] == " ":
                skills.pop(i)
        skills = [tok.strip() for tok in skills]
        # print(skills)
        tmp = {
            "occupation3" : occu3,
            "occupation3Nm" : job[1],
            "jobsCd" : jobsCd,
            "skill" : skills
        }
        result.append(tmp)
    return result

def jaccard_distance(user_skills, job_skills): #자카드 유사도
    s1 = set(user_skills)
    s2 = set(job_skills)
    intersection = 0 # 교집합 
    for job_skill in job_skills: #문자열 전처리가 완벽히 되지 않아 find로 찾기 ex) 'java -8' , 'java'와는 같은 skill로 처리
        for user_skill in user_skills:
            if user_skill.find(job_skill) != -1:
                intersection = intersection + 1
                break
    return float(intersection / len(s2.union(s1)))


def getUserSkill_to_GPT_Chat(resume, API_KEY): # 이력서의 skill을 GPT를 활용하여 추출
    openai.api_key= API_KEY
    MODEL = "gpt-3.5-turbo"

    question = "\n Please extract skill, graduation department, and certificate from the corresponding sentence. I don't need another sentence, but please answer in Korean. For example, do it like 'java/C++/OOP'." #prompt
    response = openai.ChatCompletion.create(
        model = MODEL,
        messages = [
            {"role" : "user", "content" : resume+question}, #request
            {"role" : "assistant", "content" : "Help me extract skill from my resume.The response format divides each skill into."}
        ],
        temperature=0
    )
    return response.choices[0].message.content

def recommend_job(pdf,API_KEY): # 직업 추천
    try:
        resume = pdf_to_text(pdf) # 이력서 pdf -> text(string)
        jobs = get_job() # csv파일의 job list
        user_skill = getUserSkill_to_GPT_Chat(resume,API_KEY) 
        # user_skill = getUserSkill_to_GPT_Text(resume) 
        # print(user_skill)
        # user_skill = "Python, C/C++, JAVA, Kotlin, React Native, SQL, NoSQL, Git" 
        user_skill = user_skill.replace('/', ',')
        user_skill = getToken(user_skill.lower(), ",")
        user_skill = [tok.strip() for tok in user_skill]
        result = list()
        for job in jobs:
            distance = jaccard_distance(user_skill, job['skill'])
            tmp = [job, distance]
            if distance > 0:
                result.append(tmp)
            # print(job['occupation3Nm'], job['occupation3'], distance)
        result.sort(key=lambda x:x[1], reverse=True) # 자카드 distance기준으로 내림차순 정렬
        return result[0]
    except Exception as e:
        print(e)
        

def recommend_similarity_job(result): #유사한 직업 추천하기
    if result is not None:
        occupation3 = result[0]['occupation3']
    else :
        occupation3 = '133200'
    jobs = get_job()
    result_similiarty = list()
    for job in jobs:
        similarity = jaccard_distance(result[0]['skill'], job['skill'])
        tmp = [job, similarity]
        if similarity > 0.1 and occupation3 != job['occupation3']:
            result_similiarty.append(tmp)
    result_similiarty.sort(key=lambda x:x[1], reverse=True)
    return result_similiarty


def pdf_to_text(pdf = "ws"): # pdf -> text 
    resume = parser.from_file(pdf)
    resume = resume['content'].strip()
    return resume
    
def getRegion(): # 지역 코드 중 1depth만 추출 ex) 11000 : 서울, 26000 : 부산
    path = 'csv/_regionCd.csv'
    df = pd.read_csv(path)
    row = df.shape[0]
    region = list()
    for i in range(row):
        cid = df.loc[i]['카테고리 ID']
        depth1 = df.loc[i]['1 depth']
        if depth1 != " ":
            region.append([cid, depth1])
    return region

def showRegion(regions):
    regionsNm = [reg[1] for reg in regions]
    st.session_state.selected_region = st.radio(label = '', options= regionsNm)
    st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)

def showJob(recommend_jobs, similarity_jobs):
    st.session_state.jobs = [[recommend_jobs[0]['occupation3'], recommend_jobs[0]['occupation3Nm']]]
    tmp2 = [[job[0]['occupation3'],job[0]['occupation3Nm']] for job in similarity_jobs]
    st.session_state.jobs.extend(tmp2)
    jobsNm = [job[1] for job in st.session_state.jobs]
    st.session_state.selected_job= st.radio(label='',options=jobsNm)
    st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
 
# def format_link(url):
#     return f'<a href="{url}">link</a>'

def main():
    st.title("이력서 PDF파일을 통한 직업 추천")
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    st.session_state.regions = getRegion()
    st.session_state.selected_region = None
    st.session_state.selected_job = None
    st.session_state.recommend_jobs = None
    st.session_state.similarity_jobs = None
    st.session_state.jobs = None
    if uploaded_file:
        if st.session_state.recommend_jobs is None:
            st.session_state.recommend_jobs = recommend_job(uploaded_file, st.secrets.KEY.GPT_KEY)
        if st.session_state.recommend_jobs :
            recommend_jobs = st.session_state.recommend_jobs
            if st.session_state.similarity_jobs is None:
                st.session_state.similarity_jobs = recommend_similarity_job(recommend_jobs)
            st.write(f"추천 직업 : {recommend_jobs[0]['occupation3Nm']}")
        if st.session_state.selected_region is None:
            with st.expander(label="지역 선택", expanded=True):
                regions = st.session_state.regions
                showRegion(regions)
                if st.session_state.selected_region is not None:
                    print("get region")
        if st.session_state.selected_job is None:
            with st.expander(label = '직업 선택', expanded=True):
                if st.session_state.recommend_jobs and st.session_state.similarity_jobs:
                    recommend_jobs = st.session_state.recommend_jobs
                    similarity_jobs = st.session_state.similarity_jobs
                    showJob(st.session_state.recommend_jobs, st.session_state.similarity_jobs)
        regionBtn_clicked = st.button("선택")
        if regionBtn_clicked:
            st.session_state.clicked_regionCd = None
            st.session_state.clicked_regionNm = None
            st.session_state.clicked_jobCd = None
            st.session_state.clicked_jobNm = None
            for region in st.session_state.regions:
                if st.session_state.selected_region == region[1]:
                    st.session_state.clicked_regionCd = region[0]
                    st.session_state.clicked_regionNm = region[1]
                    break
            if st.session_state.jobs is not None:
                for job in st.session_state.jobs:
                    if st.session_state.selected_job == job[1]:
                        st.session_state.clicked_jobCd = job[0]
                        st.session_state.clicked_jobNm = job[1]
                        break
            if st.session_state.clicked_regionCd != None and st.session_state.clicked_regionNm != None and st.session_state.clicked_jobCd != None and st.session_state.clicked_jobNm != None:
                st.session_state.gangso, st.session_state.recommend_company = find_company(st.session_state.clicked_regionCd, st.session_state.clicked_jobCd, st.secrets.KEY.MONGO_KEY)
                cols = ['기업명',' 기업규모 ',' 근로계약 ',' 기업위치 ',' 근무시간' ,'URL']
                if len(st.session_state.gangso) != 0:
                    # with st.expander(label = '강소기업 추천', expanded=True):
                    gangso_df = pd.DataFrame(st.session_state.gangso, columns=cols)
                    # gangso_df['URL'] = gangso_df['URL'].apply(format_link)
                    st.subheader('강소기업 기업목록')
                    st.table(gangso_df.head())
                if len(st.session_state.recommend_company) != 0:
                    # with st.expander(label = '일반기업 추천', expanded=True):
                    company_df = pd.DataFrame(st.session_state.recommend_company, columns=cols)
                    # company_df['URL'] = company_df['URL'].apply(format_link)
                    st.subheader('기업 기업목록')
                    # st.dataframe(company_df.to_html(escape=False), unsafe_allow_html=True)
                    st.table(company_df)
                st.session_state.clicked_regionCd = None
                st.session_state.clicked_regionNm = None
                st.session_state.clicked_jobCd = None
                st.session_state.clicked_jobNm = None

if __name__ == "__main__":
    main()