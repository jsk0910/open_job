import pandas as pd
import sys,os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from tika import parser
import openai
from . import api

def get_job(): # csv파일에 있는 직업 skill을 list화
    path = './csv/skills.csv'
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
        skills = api.getToken(skills.lower(), tk=',')
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
        user_skill = api.getToken(user_skill.lower(), ",")
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
    # pdf_path = f"./_pdf/{pdf}.pdf"
    # resume = parser.from_file(pdf_path)
    resume = parser.from_file(pdf)
    resume = resume['content'].strip()
    return resume
    