# prompts.py
import jinja2
from typing import Dict, Any

class PromptManager:
    """提示词管理类，使用Jinja2处理模板但不依赖外部文件"""

    # 将所有模板定义为类变量
    TEMPLATES = {
        "document_summary": """
你是一个专业的文档总结专家。请根据以下文档内容，提取与用户问题最相关的信息，并生成一个简洁但全面的摘要。

用户问题: {{ query }}
文档内容: {{ document }}

请确保你的总结：
1. 包含与用户问题直接相关的所有关键信息
2. 保持原文档的准确性，不添加不存在的信息
3. 组织良好，便于理解
4. 长度适中，通常不超过原文档的1/4
5. 默认添加标记，标记使用的文档内容来源于哪篇文档的那一页的哪一个标题下？
""",

        "final_answer": """
当前系统日期: {{ current_date }}
{{ system_prompt }}
{% if upload_content %}# 上传的文档内容:
{{ upload_content }}{% endif %}
{% if content %}# 知识库中的文档内容:
{{ content }}{% endif %}
{% if input_body %}# 额外接口返回数据:
{{ input_body }}{% endif %}
""",

        "normal_answer": """
{{ system_prompt }}
""",

        "convert_to_json": """
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
""",

        "relevant_metadata": """
你被要求为给定的问题及其答案识别相关的元数据ID。你将获得三个输入：问题、答案和元数据条目列表。你的目标是确定哪些元数据ID与答案中使用的信息相关联。  
以下是你的输入示例：  
<question>
{{ QUESTION }}
</question>
<answer>
{{ ANSWER }}
</answer>
<metadata_list>
{{ METADATA_LIST }}
</metadata_list>

请按以下步骤完成任务：  
1. 仔细阅读问题和答案。
2. 分析答案内容，识别可能与特定来源相关的关键信息、概念或短语。
3. 查阅元数据列表，查找与答案内容匹配的条目。关注页面号、文件名或其他可以标识答案来源的细节。
4. 如果发现明确与答案相关的元数据条目，记录它们的ID。
5. 如果无法确定任何相关元数据条目，或答案表明未找到相关信息，则视为没有可识别的相关ID。
6. 输出结果：
   - 如果确定了相关ID，创建一个包含"id"键的JSON对象，值为这些相关ID组成的字符串数组。
   - 如果没有找到相关ID，或答案表明未找到信息，则创建JSON对象，"ids"键值为null。

7. 按如下格式输出结果：  
{"ids": ["ID1", "ID2", "ID3"]}
将"ID1"、"ID2"、"ID3"替换为你识别出的实际相关ID，根据你查找的实际来源，ID数量可能会有所不同。
或
{"ids": null}
注意：如果答案中出现"未找到答案"、"未收录相关信息"、"文档中没有提及"等类似表述，无论是否提及文档来源，都要输出{"ids": null}。
不要提供任何解释或推理，只需输出JSON对象。{{ qwords }}
"""
    }

    def __init__(self):
        # 预编译所有模板以提高性能
        self.compiled_templates = {
            name: jinja2.Template(template, trim_blocks=True, lstrip_blocks=True)
            for name, template in self.TEMPLATES.items()
        }

    def render_template(self, template_name: str, **kwargs) -> str:
        """渲染指定模板"""
        if template_name not in self.compiled_templates:
            raise ValueError(f"未找到模板: {template_name}")
        return self.compiled_templates[template_name].render(**kwargs)

    def get_document_summary_prompt(self, query: str, document: str) -> str:
        """获取文档摘要提示词"""
        return self.render_template("document_summary", query=query, document=document)

    def get_final_answer_prompt(self, system_prompt: str, upload_content: str = "",
                                content: str = "", input_body: str = "", current_date: str = "") -> str:
        """获取最终回答提示词"""
        return self.render_template(
            "final_answer",
            system_prompt=system_prompt,
            upload_content=upload_content,
            content=content,
            input_body=input_body,
            current_date=current_date
        )

    def get_normal_answer_prompt(self, system_prompt: str) -> str:
        """获取普通回答提示词"""
        return self.render_template("normal_answer", system_prompt=system_prompt)

    def get_convert_to_json_prompt(self) -> str:
        """获取JSON转换提示词"""
        return self.render_template("convert_to_json")

    def get_relevant_metadata_prompt(self, question: str, answer: str,
                                     metadata_list: str, qwords: str = "") -> str:
        """获取相关元数据提示词"""
        return self.render_template(
            "relevant_metadata",
            QUESTION=question,
            ANSWER=answer,
            METADATA_LIST=metadata_list,
            qwords=qwords
        )
