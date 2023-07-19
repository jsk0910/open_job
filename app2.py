import streamlit as st
import pandas as pd 
import sys,os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from recommend import jaccard
from recommend import region as r
from recommend import company as corp


def showRegion(regions):
    regionsNm = [reg[1] for reg in regions]
    select = st.radio(label = '', options= regionsNm)
    st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
    return select

def showJob(recommend_jobs, similarity_jobs):
    jobs = [[recommend_jobs[0]['occupation3'], recommend_jobs[0]['occupation3Nm']]]
    tmp2 = [[job[0]['occupation3'],job[0]['occupation3Nm']] for job in similarity_jobs]
    jobs.extend(tmp2)
    jobsNm = [job[1] for job in jobs]
    select= st.radio(label='',options=jobsNm)
    st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
    return select, jobs

def format_link(url):
    return f'<a href="{url}">link</a>'

def main():
    st.title("이력서 PDF파일을 통한 직업 추천")
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    regions = r.getRegion()
    if uploaded_file:
        recommend_jobs = jaccard.recommend_job(uploaded_file, st.session_state['GPT_KEY'])
        if recommend_jobs :
            similarity_jobs = jaccard.recommend_similarity_job(recommend_jobs)
            st.write(f"추천 직업 : {recommend_jobs[0]['occupation3Nm']}")
        with st.expander(label="지역 선택", expanded=True):
            selected_region = showRegion(regions)
        with st.expander(label = '직업 선택', expanded=True):
            if recommend_jobs and similarity_jobs:
                selected_job, jobs = showJob(recommend_jobs, similarity_jobs)
        regionBtn_clicked = st.button("선택")
        if regionBtn_clicked:
            for region in regions:
                if selected_region == region[1]:
                    clicked_regionCd = region[0]
                    clicked_regionNm = region[1]
                    break
            if jobs is not None:
                for job in jobs:
                    if selected_job == job[1]:
                        clicked_jobCd = job[0]
                        clicked_jobNm = job[1]
                        break
            if clicked_regionCd != None and clicked_regionNm != None and clicked_jobCd != None and clicked_jobNm != None:
                gangso, recommend_company = corp.find_company(clicked_regionCd, clicked_jobCd, st.session_state['MONGO_KEY'])
                cols = ['기업명','기업규모','근로계약','기업위치','근무시간','URL']
                if len(gangso) != 0:
                    # with st.expander(label = '강소기업 추천', expanded=True):
                    gangso_df = pd.DataFrame(gangso, columns=cols)
                    gangso_df['URL'] = gangso_df['URL'].apply(format_link)
                    st.subheader('강소기업 기업목록')
                    st.table(gangso_df.head())
                if len(recommend_company) != 0:
                    # with st.expander(label = '일반기업 추천', expanded=True):
                    print(len(recommend_company))
                    company_df = pd.DataFrame(recommend_company, columns=cols)
                    company_df['URL'] = company_df['URL'].apply(format_link)
                    st.subheader('기업 기업목록')
                    # st.dataframe(company_df.to_html(escape=False), unsafe_allow_html=True)
                    st.table(company_df)
                print(clicked_regionCd,clicked_regionNm,clicked_jobCd,clicked_jobNm)

if __name__ == "__main__":
    main()