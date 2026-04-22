# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import json
import chromadb 
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions
import sys
import uuid
import datetime
import random
import re

app = Flask(__name__)







######## step 0 Knowledge base setup #############

chroma_client = chromadb.Client()  # Use Chroma's Client object to access the database
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BCE_embedding_model")
collection = chroma_client.get_or_create_collection(name="chatZOC", embedding_function=emb_fn)  # Create a Collection in Chroma using Python. A collection is where embeddings, documents, and any other metadata are stored.


# Function to load data into Chroma
def load_data_to_chroma(data_path):
    """
    Load the knowledge base from the json data, paying attention to metadata
    """
    with open(data_path, 'r', encoding='utf-8') as file:
        jss = json.load(file)
        ids = list((jss['no.']).values())
        ids = [str(x) for x in ids]
        documents = list((jss['question']).values())     # Knowledge base
        metadatas = []
        for key in jss['question'].keys():
            entry = {
                # Complex list comprehension
                k: jss[k][key] if jss[k][key] is not None else "" for k in ['no.','question','answer','kb']
            }
            metadatas.append(entry)
    return documents, metadatas, ids

# @title
# Load data and insert/update into the collection
def building_collection(data_path):
    del_ids = collection.get(include=["documents"])['ids']
    if del_ids != []:
        collection.delete(ids=del_ids)
    documents, metadatas, ids = load_data_to_chroma(data_path)
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)


user_kb = 'knowledge_base/knowledge_base.json'

building_collection(user_kb)
print(user_kb)
print('成功创建知识库')


# @title
# Function to convert user input into embeddings and query the most relevant documents
def find_knowledge(user_input, n_results=1, kb = 'qitawenti', collection=collection):
    # Call the knowledge base to retrieve the most relevant reference materials
    results = collection.query(
        query_texts=[user_input],
        n_results=n_results,
        where={'kb': kb}
    )
    # print('embedding results: ',results)
    distances = results['distances'][0]
    print(distances)

    output_content = ''
    for i,distance in enumerate(distances):
        if distance < 100:
            # print('yes')
            question_s = results['metadatas'][0][i]['question']
            answer_s = results['metadatas'][0][i]['answer']
            output_content = output_content + f"###示范###\n患者：{question_s}\n输出：{answer_s}\n\n"  
    # print(output_content)       
    return output_content


def replace_punctuation(text):
    # Use re.sub to replace all English punctuation with spaces
    speak_text = re.sub(r'[!\"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~]', ' ', text)
    real_speak_text = speak_text.replace("\n"," ")
    return real_speak_text


######## step 2 Overall response function ############# (step 1 is at the bottom)
prompt_after_summary = ''
query_modified = ''
def get_response(user_input,history):
    global prompt_after_summary
    global query_modified


    intend = "系统对话"
    if user_input == 'answer':
        response = "您好，欢迎致电中山大学中山眼科中心，我是人工智能客服，请问有什么我可以帮助您的吗？"  
        prompt_after_summary = '' 
        query_modified = '' 
        time_after_intend_find = datetime.datetime.now()
        time_after_question_modify = datetime.datetime.now()
        time_after_history_sumary = datetime.datetime.now()
        time_after_find_knowledge = datetime.datetime.now()
        time_after_answer = datetime.datetime.now()      
    elif user_input == 'idle0' or user_input == 'idle1' or user_input == 'idle2' or user_input == 'noinputtimeout':
        response = "请提问，您可以用一句话问我：怎么挂号?什么时候放号？@@@@@{'hard_txt':true}"
        prompt_after_summary = '' 
        query_modified = ''
        time_after_intend_find = datetime.datetime.now()
        time_after_question_modify = datetime.datetime.now()
        time_after_history_sumary = datetime.datetime.now()
        time_after_find_knowledge = datetime.datetime.now()
        time_after_answer = datetime.datetime.now()  
    elif user_input == 'hungup':
        response = ''
        prompt_after_summary = '' 
        query_modified = ''
        time_after_intend_find = datetime.datetime.now()
        time_after_question_modify = datetime.datetime.now()
        time_after_history_sumary = datetime.datetime.now()
        time_after_find_knowledge = datetime.datetime.now()
        time_after_answer = datetime.datetime.now()  
    elif if_human(user_input):
        if not if_is_rest_time():
            # response = "您好，若需要人工服务，请重新拨打热线，按0进入人工服务"
            response = "好的，现帮您转接人工服务。#####{\\\"code\\\":3000}"
            prompt_after_summary = '' 
            query_modified = ''
        else:
            response = "您好，由于现在是班外时间，无法为您转人工服务，您可以在工作日上午八点到十二点，下午十四点三十到十七点三十拨打电话，并说：我要转人工服务"
            # response = "您好，若需要人工服务，请重新拨打热线，按0进入人工服务"
            prompt_after_summary = '' 
            query_modified = ''
        history.append({'Q':user_input})
        history.append({'A':response})
        time_after_intend_find = datetime.datetime.now()
        time_after_question_modify = datetime.datetime.now()
        time_after_history_sumary = datetime.datetime.now()
        time_after_find_knowledge = datetime.datetime.now()
        time_after_answer = datetime.datetime.now()  
    elif '再说一次' in user_input or '多一次' in user_input or '重说' in user_input or '再来一次' in user_input or '再来一遍' in user_input or '再说一遍' in user_input or '说一遍' in user_input or '说一次' in user_input or '再讲一次' in user_input or '讲一次' in user_input:
        response = history[-1]['A']
        history.append({'Q':user_input})
        history.append({'A':response})
        prompt_after_summary = '' 
        query_modified = ''
        time_after_intend_find = datetime.datetime.now()
        time_after_question_modify = datetime.datetime.now()
        time_after_history_sumary = datetime.datetime.now()
        time_after_find_knowledge = datetime.datetime.now()
        time_after_answer = datetime.datetime.now()  
    elif '好好学习天天向上' in user_input:
        response = "暗号已经对上，现帮您转接人工服务。#####{\\\"code\\\":3000}"
        history.append({'Q':user_input})
        history.append({'A':response})
        prompt_after_summary = '' 
        query_modified = ''
        time_after_intend_find = datetime.datetime.now()
        time_after_question_modify = datetime.datetime.now()
        time_after_history_sumary = datetime.datetime.now()
        time_after_find_knowledge = datetime.datetime.now()
        time_after_answer = datetime.datetime.now()  
    else:
        response,intend,time_after_intend_find,time_after_question_modify,time_after_history_sumary,time_after_find_knowledge,time_after_answer = intend_find(user_input,history)
        if response[:3] == '医生：' or response[:3] == '医生:':
            response = response[3:]
        response = replace_punctuation(response)
        response = response + "@@@@@{'hard_txt':true}"
        history.append({'Q':user_input})
        history.append({'A':response})


    # print('1111'*4,response)
    # print('1111'*4,intend)
    return response,history,intend,time_after_intend_find,time_after_question_modify,time_after_history_sumary,time_after_find_knowledge,time_after_answer


######## step 3 Intent recognition function ############
def intend_find(user_input,history):
    global query_modified

    intend_prompt = f"根据以下###示范###的方法和格式，根据患者的问题，判断其问题属于什么###类别###，不能回答###类别###之外回复，参考###示范###格式，回答###问题###\n\n###类别###\n挂号流程问题\n导诊分诊问题\n医保费用问题\n疾病咨询问题\n手术安排\n礼貌用语\n其他问题\n\n###示范###\n\n患者问题：挂号我想问一下就是我的眼睛有点红肿啊你挂什么科呢\n类别：导诊分诊问题\n\n患者问题：那个哦我说我想问我眼睛啊他被石头砸到了有点痛你们医院没有急诊啊我怎么搞呢\n类别：导诊分诊问题\n\n患者问题：小小儿的眼科是在谁哪个医生看的最后最好\n类别：导诊分诊问题\n\n患者问题：晶体植入术的费用\n类别：医保费用问题\n\n患者问题：预约挂号怎么操作\n类别：挂号流程问题\n\n患者问题：无法绑定就诊卡\n类别：其他问题\n\n患者问题：得了青光眼怎么得了青光眼怎么治疗\n类别：疾病咨询问题\n\n患者问题：我的白内障手术要排多久呀\n类别：手术安排\n\n患者问题：好的谢谢你\n类别：礼貌用语\n\n患者问题：那个初次就诊那个\n类别：其他问题\n\n###问题###\n患者问题：{user_input}\n类别："
    intend = send_to_llm(intend_prompt)

    time_after_intend_find = datetime.datetime.now()

    # Strategy: do not supplement/modify the first sentence
    if len(history) == 0:
        prompt = user_input
        query_modified = ''
    else: 
        prompt = question_modified(user_input,history)

    time_after_question_modify = datetime.datetime.now()

    # Strategy: supplement and modify all utterances
    # prompt = question_modified(user_input,history)

    # print('22222',intend)
    if '挂号流程问题' in intend:
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = guahaoliucheng(prompt,history)
    elif '导诊分诊问题' in intend:
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = daozhenfenzhen(prompt,history)
    elif '医保费用问题' in intend:
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = yibaofeiyong(prompt,history)
    elif '疾病咨询问题' in intend:
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = jibingzixun(prompt,history)
    elif '手术安排' in intend:
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = shoushuanpai(prompt,history)
    elif '礼貌用语' in intend:
        query_modified = ''
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = limaoyongyu(user_input,history)
    else:  # Other questions
        response,time_after_history_sumary,time_after_find_knowledge,time_after_answer = qitawenti(prompt,history)


    if response[:3] == '患者：' or response[:3] == '患者:':
        response = response[3:]

    if '输出：' in response:
        response = response.split('输出：')[1]
    elif '输出:' in response:
        response = response.split('输出:')[1]

    return response,intend,time_after_intend_find,time_after_question_modify,time_after_history_sumary,time_after_find_knowledge,time_after_answer



#######  step 4 Complete/refine the question ##########
def question_modified(user_input,history):
    global query_modified
    dialogue = history2dialogue(history)
    prompt = f"\n参考###示范###，请结合医生和患者的###对话###，修改补充###患者问题###，让其更完善。\n在###任务###下面补充输出后面的内容。\n\n\n###示范###\n\n###对话###\n患者：请问应该怎么挂号\n医生：您好！可以用微信搜索“中山大学中山眼科中心”关注公众号或者下载同名APP挂号，现场与线上同步号源，正常情况很少有现场号，建议您线上预约挂号之后再过来就诊。。若未听清，您可以跟我说：请你再说一次。\n\n###患者问题###\n患者：贷多少钱\n输出：我需要带多少钱来挂号？\n\n\n###输出###\n\n###对话###\n{dialogue}\n\n###患者问题###\n{user_input}\n输出："
    prompt = send_to_llm(prompt)
    query_modified = prompt

    return prompt

#######  step 4 Summarize historical intent ##########
def history_summary(prompt,history):
    global prompt_after_summary
    dialogue = history2dialogue(history)
    # For now, just concatenate directly
    # prompt = dialogue + f"#########################\n患者：{prompt}"
    prompt = f"参考###示范###，请判断###患者提问###中是否有省略主语或者使用代词，若有，则需根据###历史对话###的内容，将###患者提问###中的主语补充完整，若无，则直接输出原本的###患者提问###。\n\n\n###示范###\n\n###患者提问###\n请问这个疾病需要做手术吗\n\n###历史对话###\n患者：你好，我最近眼睛老是充血发痒，早上眼睛分泌物夜很多，可能是什么问题？\n医生：您的症状可能是过敏性结膜炎\n\n输出：请问过敏性结膜炎需要做手术吗\n\n###示范###\n\n###患者提问###\n好的，谢谢您，我知道了\n\n###历史对话###\n患者：你好，我小孩眼睛近视了，应该挂什么科室？\n医生：建议挂屈光与青少年近视防控科室的号进行检查和咨询\n\n输出：好的，谢谢您，我知道了\n\n\n\n\n###输出###\n\n###患者提问###\n{prompt}\n\n###历史对话###\n{dialogue}\n\n输出："
    prompt_after_summary = send_to_llm(prompt)
    # prompt_after_summary = prompt
    return prompt_after_summary



######## step 4-1 Registration process questions ########
def guahaoliucheng(prompt,history):
    global prompt_after_summary
    # Strategy: do not synthesize history for the first sentence
    if len(history) == 0:
        prompt_after_summary = prompt
    else: 
        prompt = history_summary(prompt,history)

    # # Strategy: always let the LLM summarize and synthesize history first
    # prompt = history_summary(prompt,history)'
    time_after_history_sumary = datetime.datetime.now()

    # Get auxiliary information
    knowledge = find_knowledge(prompt,2,'guahaoliucheng')
    time_after_find_knowledge = datetime.datetime.now()
    # Retrieve fixed answer from KB
    prompt_if_doctor = f"请判断下列问题中是否提及特定医生姓名，若有，则回复 yes ，若无，则回复 no 。不要生成多余的内容。\n{prompt}"
    if_doctor = send_to_llm(prompt_if_doctor)
    if 'yes' in if_doctor:
        # response = "您好，作为一个人工智能助手，我们无法为您推荐医生或者查询指定医生的挂号情况。您可以关注我院公众号“中山大学中山眼科中心”或者下载“中山眼科中心”APP挂号预约，回复或搜索“挂号”可根据视频指引进行挂号。目前只接受线上挂号形式，每天下午六点放号，放七天后的号。"
        prompt_g = f"参考###示范###，回复###患者提问###中的相关问题。注意回复内容不要超过180字。\n\n###示范###\n患者：有没有什么医生推荐？\n输出：您好，作为一个人工智能助手，我们无法为您推荐医生或者查询指定医生的挂号情况。您可以关注我院公众号“中山大学中山眼科中心”或者下载“中山眼科中心”APP挂号预约，回复或搜索“挂号”可根据视频指引进行挂号。目前只接受线上挂号形式，每天下午六点放号，放七天后的号。\n\n{knowledge}\n\n###输出###\n\n###患者提问###\n患者：{prompt}\n输出："
        response = send_to_llm(prompt_g)
    elif 'no' in if_doctor:
        prompt_g = f"参考###示范###，回复###患者提问###中的相关问题。注意回复内容不要超过180字。\n\n###示范###\n患者：我应该怎么挂号？\n输出：您好，您可以关注我院公众号“中山大学中山眼科中心”或者下载“中山眼科中心”APP挂号预约，回复或搜索“挂号”可根据视频指引进行挂号。目前只接受线上挂号形式，每天下午六点放号，放七天后的号。\n\n{knowledge}\n\n###输出###\n\n###患者提问###\n患者：{prompt}\n输出："
        response = send_to_llm(prompt_g)
    time_after_answer = datetime.datetime.now()
    return response,time_after_history_sumary,time_after_find_knowledge,time_after_answer

######## step 4-2 Guidance/triage questions ########
def daozhenfenzhen(prompt,history):
    global prompt_after_summary
    # Strategy: do not synthesize history for the first sentence
    if len(history) == 0:
        prompt_after_summary = prompt
    else: 
        prompt = history_summary(prompt,history)

    time_after_history_sumary = datetime.datetime.now()

    # # Strategy: always let the LLM summarize and synthesize history first
    # prompt = history_summary(prompt,history)

    # Get auxiliary information
    knowledge = find_knowledge(prompt,2,'daozhenfenzhen')
    time_after_find_knowledge = datetime.datetime.now()
    # print('7777',prompt)
    prompt = f"根据以下###眼科分诊方法###，根据患者提问，说出其最适合的科室，参考###示范###格式，回答###问题###，注意回复内容不要超过180字。\n\n###眼科分诊方法###\n\n患者：老人看白内障\n科室：白内障\n\n患者：眼睛肿痛，在外院诊断青光眼\n科室：青光眼科\n\n患者：主要处理不需要手术的眼底疾病，如糖尿病视网膜病变早期阶段、黄斑变性、视网膜血管阻塞、葡萄膜炎、视神经炎等，通过药物治疗、激光治疗\n科室：眼底内科\n\n患者：需要手术干预的眼底疾病，如视网膜脱离、严重的糖尿病视网膜病变晚期、玻璃体出血、眼睛看东西变形、眼底病变等\n科室：眼底外科\n\n患者：不明确，无法判断明确判断\n科室：眼科综合门诊\n\n患者：近视做激光手术\n科室：激光近视科\n\n患者：高度近视\n科室：高度近视科\n\n患者：眼睛干涩、眼球长块肉、眼膜发炎、换角膜\n科室：角膜科\n\n患者：眼部整形，做双眼皮、割眼袋、换假眼，眼周长肉粒、祛痣、祛斑、瘦脸除皱\n科室：眼整形科\n\n患者：眼睛突、眼睛长肿瘤、眼睛像猫眼晚上发亮\n科室：眼眶肿瘤科\n\n患者：眼睛受到外部伤害\n科室：眼外伤科\n\n患者：眼睛突然看不见、眼睛突然红、肿、热、痛、流泪、眼屎多\n科室：急诊科\n\n患者：近视、远视、散光、验光、配眼镜\n科室：屈光与青少年近视防控\n\n患者：小儿对对眼、斗鸡眼、看电视歪脖子、偏头、斜弱视疾病等\n科室：斜视弱视科\n\n患者：小儿眼红、流泪、有很多眼屎\n科室：急诊科\n\n患者：小儿眼痒，经常揉眼睛、眼皮长颗痘痘\n科室：综合门诊\n\n患者：小儿眼皮下垂、眼睛特小伴塌鼻梁\n科室：眼整形科\n\n患者：小儿白内障\n科室：小儿白内障科\n\n患者：小儿眼底疾病\n科室：小儿眼底病\n\n患者：眼睛不舒服，第一次看眼睛不知道挂什么号\n科室：综合门诊\n\n###示范###\n患者：我眼睛很痛，持续了3个月了\n输出：你眼睛疼痛持续时间较长，但未明确诊断具体病情，因此建议先到眼科综合门诊进行全面检查和评估\n\n###示范###\n患者：我眼睛看不清楚，有很多年了，我75岁\n输出：根据您的描述，您有多年视力模糊的情况，并且您已经75岁，可能患有白内障。建议您到白内障科就诊，进行详细检查和治疗。\n\n###示范###\n患者：我眼睛看东西有飞蚊症应该挂什么科？\n输出：根据您的描述，您有飞蚊症的症状，这通常与眼底病变有关。建议您到眼底科就诊，进行详细检查和治疗。\n\n{knowledge}###问题###\n患者：{prompt}\n输出："
    response = send_to_llm(prompt)
    time_after_answer = datetime.datetime.now()
    # print('66666',response)
    return response,time_after_history_sumary,time_after_find_knowledge,time_after_answer

######## step 4-3 Medical insurance / fee questions ########
def yibaofeiyong(prompt,history):
    global prompt_after_summary
    # Strategy: do not synthesize history for the first sentence
    if len(history) == 0:
        prompt_after_summary = prompt
    else: 
        prompt = history_summary(prompt,history)

    time_after_history_sumary = datetime.datetime.now()

    # Get auxiliary information
    knowledge = find_knowledge(prompt,2,'yibaofeiyong')
    time_after_find_knowledge = datetime.datetime.now()
    # Retrieve a reference answer from KB and then improvise?
    if knowledge == '':
        response = "识别到您的问题与医保费用的相关，该问题涉及详细医保政策，请转人工服务。我们将竭诚为您提供帮助，确保您的问题得到妥善解答。"
    else:
        response = send_to_llm(f"参考###示范###格式，用180个字以内简要回答###问题###。\n\n{knowledge}\n\n###问题###\n患者情况：{prompt}\n输出：")
    time_after_answer = datetime.datetime.now()
    return response,time_after_history_sumary,time_after_find_knowledge,time_after_answer


def jibingzixun(prompt,history):
    global prompt_after_summary
    # Strategy: do not synthesize history for the first sentence
    if len(history) == 0:
        prompt_after_summary = prompt
    else: 
        prompt = history_summary(prompt,history)

    time_after_history_sumary = datetime.datetime.now()

    time_after_find_knowledge = datetime.datetime.now()

    res = send_to_llm(prompt='请简单的回答患者的问题，不要超过100字。患者：'+prompt)
    # st.write("direct out")
    answer = re.sub(r'[^\w\s]', '，', res)
    if len(answer) > 150:
        answer = answer[:150]

    time_after_answer = datetime.datetime.now()
    return answer,time_after_history_sumary,time_after_find_knowledge,time_after_answer

######## step 4-5 Surgery scheduling ########
def shoushuanpai(prompt,history):
    # response = '识别到您的问题与手术安排相关，该安排涉及治疗效果，需要医生审核，请转人工服务，我们将竭诚为您提供帮助，确保您的问题得到妥善解答。'
    # Get auxiliary information
    time_after_history_sumary = datetime.datetime.now()
    knowledge = find_knowledge(prompt,2,'shoushuanpai')
    time_after_find_knowledge = datetime.datetime.now()
    # Retrieve a reference answer from KB and then improvise?
    if knowledge == '':
        response = '识别到您的问题与手术安排相关，该安排涉及治疗效果，需要医生审核，请转人工服务，我们将竭诚为您提供帮助，确保您的问题得到妥善解答。'
    else:
        response = send_to_llm(f"参考###示范###格式，用50个字简要回答###问题###。\n\n{knowledge}\n\n###问题###\n患者情况：{prompt}\n输出：")
    time_after_answer = datetime.datetime.now()
    return response,time_after_history_sumary,time_after_find_knowledge,time_after_answer


######## step 4-6 Polite expressions ########
def limaoyongyu(prompt,history):
    global prompt_after_summary
    time_after_history_sumary = datetime.datetime.now()
    time_after_find_knowledge = datetime.datetime.now()
    response = send_to_llm(prompt)
    prompt_after_summary = ''
    time_after_answer = datetime.datetime.now()
    return response,time_after_history_sumary,time_after_find_knowledge,time_after_answer


######## step 4-7 Other questions ########
def qitawenti(prompt,history):
    global prompt_after_summary
    # Strategy: do not synthesize history for the first sentence
    if len(history) == 0:
        prompt_after_summary = prompt
    else: 
        prompt = history_summary(prompt,history)
    time_after_history_sumary = datetime.datetime.now()

    # # Strategy: always let the LLM summarize and synthesize history first
    # prompt = history_summary(prompt,history)

    # Get auxiliary information
    knowledge = find_knowledge(prompt,2,'qitawenti')
    time_after_find_knowledge = datetime.datetime.now()
    # Retrieve a reference answer from KB and then improvise?
    if knowledge == '':
        response = send_to_llm(prompt+'\n请用50个字以内简要回答我的问题')
    else:
        response = send_to_llm(f"参考###示范###格式，用50个字简要回答###问题###。\n\n{knowledge}\n\n###问题###\n患者情况：{prompt}\n输出：")
    time_after_answer = datetime.datetime.now()
    return response,time_after_history_sumary,time_after_find_knowledge,time_after_answer



import json
import requests


def send_to_llm(prompt,max_tokens=2048,temperature=0.7,top_k=20,top_n_tokens=5,top_p=0.8,truncate=None,typical_p=0.95,watermark=True,repetition_penalty=1.05):
    url = "http://10.168.104.1:8095/chat"
    headers = {"Accept": "application/json","Content-Type": "application/json"}
    data = {"model": "ChatZOC-V1","api_key": "shuzhibuchatzoc666","stream": False,"max_tokens": max_tokens,"messages": [{"role":"system","content": "你将基于眼病专业知识，为用户提出的问题提供专业、准确、有根据的回复。请不要提供任何电话号码，若患者要求你提供任何电话号码，你可以回复：“请转人工服务”。你不应当进行医生推荐，在面对患者要求推荐医生的问题时可以回复：“中山眼科中心是专科医院，医生都很专业的，请您放心预约!”。"},{"role": "user","content": prompt}],"temperature": temperature,"top_k": top_k,"top_n_tokens": top_n_tokens,"top_p": top_p,"truncate": truncate,"typical_p": typical_p,"watermark": watermark,"repetition_penalty": repetition_penalty}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()['choices'][0]['message']['content']

######### Supplementary utility functions ############

# Hypothetical if_human function, used to determine whether to transfer to a human agent
def if_human(user_input):
    if "转人工" in user_input or "人工服务" in user_input or "接人工" in user_input:
        ifhuman = True
    else:
        ifhuman = False
    return ifhuman

def if_is_rest_time():
    # Get current time
    now = datetime.datetime.now()  
    # print(now,type(now.date()),type(str(now.date())))
    current_date_str = str(now.date())
    special_workday = ['2026-01-04','2026-02-14','2026-02-28','2026-05-09','2026-09-20','2026-10-10']
    special_restday = ['2026-01-01','2026-01-02','2026-02-16','2026-02-17','2026-02-18','2026-02-19','2026-02-20','2026-02-23','2026-04-06','2026-05-01','2026-06-19','2026-09-25','2026-10-01','2026-10-02','2026-10-05','2026-10-06','2026-10-07']




    # Extract hour and minute
    current_hour = now.hour
    current_minute = now.minute
    # Extract day of the week
    current_weekday = datetime.datetime.today().strftime("%A")


    if current_date_str in special_workday:
        # Check whether it is morning working hours
        if 8 <= current_hour < 12:
            return False    
        # Check whether it is afternoon working hours
        elif ((current_hour == 14 and current_minute >= 30) or (14 < current_hour < 17) or (current_hour == 17 and current_minute <= 30)):
            return False   
        # Otherwise it is off-hours
        return True

    elif current_date_str in special_restday:
        return True

    else:

        # Check whether it is morning working hours
        if 8 <= current_hour < 12 and current_weekday not in ['Saturday','Sunday']:
            return False    
        # Check whether it is afternoon working hours
        elif ((current_hour == 14 and current_minute >= 30) or (14 < current_hour < 17) or (current_hour == 17 and current_minute <= 30)) and current_weekday not in ['Saturday','Sunday']:
            return False   
        # Otherwise it is off-hours
        return True

user_id_global = ''
history = []
def new_phonecall_check(user_id):
    global user_id_global
    # global global_iter  # Used for switching knowledge bases
    # global iteration
    global history
    if user_id != user_id_global:
        # iteration = 1
        user_id_global = user_id
        # global_iter = 0'
        history = []

def post_process(result):
    result_dict = dict(result)
    result_dict['similarities'] = [
        [round(1 - distance, 5) for distance in distances_list]
        for distances_list in result['distances']
    ]
    return result_dict


def chromadb_simi_to_clickhouse_simi(x):
    return 0.4015 * x + 0.5635


def history2dialogue(history):
    # Convert history into a dialogue string, keeping at most 5 items
    if len(history) == 0:
        dialogue = ''
    elif len(history) == 2:
        dialogue = f"患者：{history[-2]['Q']}\n医生：{history[-1]['A']}"
    elif len(history) >= 4:
        dialogue = f"患者：{history[-4]['Q']}\n医生：{history[-3]['A']}\n患者：{history[-2]['Q']}\n医生：{history[-1]['A']}"
    else:
        print('***'*10)
    return dialogue


def save_txt_detail(user_id,user_input,response,current_time,logging_path,history,intend,prompt_after_summary,time_after_intend_find,time_after_question_modify,time_after_history_sumary,time_after_find_knowledge,time_after_answer):

    rid = uuid.uuid4()

    # Get the current datetime object
    current_datetime = datetime.datetime.now()
    # Format the datetime object as a string
    human_readable_time = current_datetime.strftime("%Y-%m-%d %H:%M:%S")

    response_all = [{'id':rid, 'timestamp':human_readable_time, 'time_spent_of_total_generation:':current_datetime - current_time, 'time_spent_of_intend_find:':time_after_intend_find - current_time, 'time_spent_of_question_modify:':time_after_question_modify - time_after_intend_find, 'time_spent_of_history_sumary:':time_after_history_sumary - time_after_question_modify, 'time_spent_of_find_knowledge:':time_after_find_knowledge - time_after_history_sumary, 'time_spent_of_answer:':time_after_answer - time_after_find_knowledge,'sid':user_id,'history':history,'prompt_after_summary':prompt_after_summary,'input':user_input,'output':response,'intend':intend}]

    original_stdout = sys.stdout
    # Open the file in append mode and redirect standard output to the file
    with open(logging_path, "a") as file:
        sys.stdout = file
        print(user_input)
        print(response_all)
        print('----------------ChatZOC database log over ----------------')
    sys.stdout = original_stdout


# Function to replace phone number with a new number
def replace_phone_number(text, new_number="020-66607666"):
    # Use the same pattern to detect the phone number
    pattern = r'\d{3}[-\s]?\d{8}'
    
    # Replace the found phone number with the new number
    new_text = re.sub(pattern, new_number, text)
    
    return new_text


########### step 1 Main functionality starts here ##########


@app.route('/chat', methods=['POST'])
def chat_with_chatZOC():
    global history
    global prompt_after_summary
    global query_modified

    current_time = datetime.datetime.now()

    user_id = request.json['sid']
    user_input = request.json['message']
    user_input = str(user_input)

    logging_path = 'phonecall_log_detail_time_check/' + user_id + '.txt'

    new_phonecall_check(user_id)

    response,history,intend,time_after_intend_find,time_after_question_modify,time_after_history_sumary,time_after_find_knowledge,time_after_answer = get_response(user_input,history)

    response = replace_phone_number(response)

    if len(response) > 180:
        response = response[:180]

    save_txt_detail(user_id,user_input,response,current_time,logging_path,history,intend,prompt_after_summary,time_after_intend_find,time_after_question_modify,time_after_history_sumary,time_after_find_knowledge,time_after_answer)

    response_json = [{"sid":user_id, "recipient_id": "123456", "utterance_id": "utter_1","text": response,"soft_text": response,"object_name": "greeting","timestamp": 1590227722.11, "sys_state": "READY"}]
    response_json = json.dumps(response_json)

    response_debug = [{"sid":user_id, "query_modified":query_modified,"prompt_after_summary": prompt_after_summary, "intend": intend,"text": response,"soft_text": response,"recipient_id": "123456", "utterance_id": "utter_1","object_name": "greeting","timestamp": 1590227722.11, "sys_state": "READY"}]


    # return response_json
    return response_debug



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8181, debug=True)