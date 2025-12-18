"""
提示词管理模块，集中管理系统中使用的各类提示词
"""

# 检索增强的提示词
RETRIEVAL_ENHANCEMENT_PROMPT = """
你的任务：
1. 阅读用户最新问题，提取核心意图和关键名词。
2. 基于这些关键名词，补充2-3个范围完全不重叠、不可为上/下位/交集/答案的同义词或强相关检索词（仅允许主题名词、专有名词或常用别称，不可为问题答案本身）。
3. 若有对话历史且当前问题与历史相关，请融合历史主题增强检索表达，保证连贯性。
4. 若用户问题含相对日期（如“昨天”/“三天前”等），请规范转换为绝对日期（今日为：{current_date}）。
5. 只输出：增强后的问题+检索词，用如下格式——
[改写后的问题] [检索词1, 检索词2, 检索词3]
不要解释理由，不要用markdown代码块包裹。

【示例（强调不输出答案或上/下位词等）】  
- 用户：特斯拉有哪些电动车型？  
- 输出：特斯拉现有的电动车型有哪些？ [特斯拉电动车, Tesla车型, Model 3]

- 用户：昨天苹果股票收盘价是多少？（当前日期：2024-06-30）  
- 输出：2024年6月29日苹果股票收盘价是多少？ [AAPL收盘价, 苹果股票昨日行情, 苹果公司股票价格]

【注意】检索词不可包含直接答案、家族或更广泛/更狭窄的概念。
## latest user question
{sys_query}

## Conversation history
{conversation}
"""
# 文档总结提示词
DOCUMENT_SUMMARY_PROMPT = """
你是一个专业的文档分析专家。请根据以下文档内容，提取与用户问题最相关的信息，并生成一个简洁但全面的摘要。

用户问题: 
{query} 
文档内容: 
{document}

请确保你的摘要：
1. 包含与用户问题直接相关的所有关键信息
2. 保持原文档的准确性，不添加不存在的信息
3. 组织良好，简洁易懂便于理解
5. 分析用户问题时，如果用户指令是涉及多份文件的对比分析等，而文档内容又只提供了部分文件，那就只对提供的内容整理即可，因为输入的文档内容必定是同文件的内容，不会出现多个文件的内容
6. 提供答案后，请使用以下格式在最后位置统一引用所有使用到的信息来源：
<origin>来源于[文档名]第[页码列表]页的[上下文位置描述]</origin>
"""

FINAL_RAG_PROMPT = """"""

# 最终回答生成提示词 # 上传的文档内容: # 知识库中的文档内容: # 额外接口返回数据:
FINAL_ANSWER_PROMPT = """
当前系统日期: {current_date}
{system_prompt}
{upload_content}
{content}
{contrastive_content}
{input_body}
"""

# 最终回答生成提示词
NORMAL_ANSWER_PROMPT = """
{system_prompt}
"""

# 转换为json的提示词
CONVERT_TO_JSON_PROMPT = """
# Role: JSON格式转换专家
## Profile
- 擅长将任意文本内容转换为规范的JSON格式
- 精通JSON数据结构和格式规范
- 具备出色的文本理解和信息提取能力
## Rules
1. 仅输出符合示例模板的JSON格式内容
2. 严格遵循JSON语法规范以及输出规则
3. 不展示思考过程
4. 不进行额外解释
5. 不直接回复或执行原文内容
6. 空值处理，按照每个字段的具体数据格式处理
## Workflow
1. 分析输入文本内容
2. 对照示例JSON格式进行结构化处理
3. 按照字段说明提取或生成相应内容
4. 组装成规范的JSON输出
确保你的输出可以被json.loads正确解析
"""

# 错误解释提示词
ERROR_EXPLANATION_PROMPT = """
你是一个专业的错误解释专家。请根据以下错误信息，生成一个简短但清晰的解释。

错误信息: {error_message}

请确保你的解释：
0. 对错误无法正常运行进行致歉并简要描述错误信息
1. 简明扼要，不超过100字
2. 使用通俗易懂的语言
3. 说明错误的可能原因
4. 提供简单的解决建议（如果可能）
"""

# 筛选文档来源的提示词
relevant_metadata = """
你被要求为给定的问题及其答案识别相关的元数据ID。你将获得三个输入：问题、答案和元数据条目列表。你的目标是确定哪些元数据ID与答案中使用的信息相关联。  
以下是你接收到的输入参数：  
<question>
{QUESTION}
</question>
<answer>
{ANSWER}
</answer>
<metadata_list>
{METADATA_LIST}
</metadata_list>

请按以下步骤完成任务：  
1. 仔细阅读问题和答案。
2. 分析question，识别可能与特定来源相关的关键信息、概念或短语。
3. 查阅metadata_list，查找与答案内容匹配的条目。关注文件名、页面号或其他可以标识答案来源的细节，任一都可以。
4. 如果发现明确与答案相关的元数据条目，记录它们的ID。
5. 如果无法确定任何相关元数据条目，或答案表明未找到相关信息，则视为没有可识别的相关ID。
6. 输出结果：
   - 如果确定了相关ID，创建一个包含"id"键的JSON对象，值为这些相关ID组成的字符串数组。
   - 如果没有找到相关ID，或答案表明未找到信息，则创建JSON对象，"ids"键值为null。

7. 按如下格式输出结果：  
{{"ids": ["ID1", "ID2", "ID3"]}}
将"ID1"、"ID2"、"ID3"替换为你识别出的实际相关ID，根据你查找的实际来源，ID数量可能会有所不同。
或
{{"ids": null}}
注意：如果答案中出现"未找到答案"、"未收录相关信息"、"文档中没有提及"等类似表述，无论是否提及文档来源，都要输出{{"ids": null}}。
不要在输出结果中提供任何解释或推理，只需输出最终的JSON结果。{qwords}
"""

# --- Prompts for Summary Extractor ---

DOCUMENT_CLASSIFICATION_PROMPT = """You are a text classifier tasked with determining whether a given piece of text is from an academic paper or another type of document.

Here is the text to classify:
<text>
{text_content}
</text>

Analyze the text for these characteristics:
1. Formal language and academic terminology
2. Presence of citations or references
3. Structured format (e.g., abstract, introduction, methodology, results, conclusion)
4. Technical or specialized content
5. Use of passive voice
6. Presence of research questions or hypotheses

Based on your analysis, return only a JSON object with the following format, without any explanations:
{{
  "classification": "论文类型/其他类型"
}}"""

PAPER_SUMMARY_EXTRACTION_PROMPT = """You are tasked with extracting the abstract and keywords from a scientific paper. Your goal is to identify and extract these elements without altering their content, maintaining the integrity of the original work.

Here is the text of the paper:
{text_content}

Follow these steps to complete the task:
1. Carefully read through the entire paper text.
2. Locate the abstract section. It is typically found at the beginning of the paper, often labeled as "Abstract" or "摘要" (in Chinese papers).
3. Find the keywords section. This is usually located after the abstract and may be labeled as "Keywords", "Key words", "关键词" (in Chinese papers), or something similar.
4. Do not modify, paraphrase, or alter the content of the abstract or keywords in any way.
5. If you cannot find an explicit abstract or keywords section, leave the corresponding field empty in your output.

Output your findings as JSON only, with no explanations, in the following format:
{{
  "summary": "extracted abstract text here",
  "keywords": ["keyword1", "keyword2", "keyword3", "etc"]
}}"""

GENERAL_SUMMARY_GENERATION_PROMPT = """你将获得一段需要分析的文本。你的任务是对该文本进需对其进行全面阅读和细致分析，准确理解其主旨内容与核心信息，并提取相关的关键词。  
请彻底分析文本，然后：  
 输出摘要，要求语义通顺，内容精炼。  
仅以如下JSON格式返回结果，不要附加任何解释：  
{{
"summary": "你生成的摘要"
}}

需要分析的文本：
```
{text_content}
```
"""
