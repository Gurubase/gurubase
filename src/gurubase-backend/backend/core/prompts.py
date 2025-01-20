summary_prompt_widget_addition = """
This should be no more than {widget_answer_max_length} words.
"""

summary_prompt_non_widget_addition = """
Short answer is simple and up to 100 words, the others are SEO friendly and between 600-1200 words.
"""


summary_template = """You are a {guru_type} Guru. You have sufficient knowledge about {domain_knowledge}.
Return a summary of the question given.
<question> is the prettier version the question provided by the user. Fix grammar errors, make it more readable if needed. Maximum length is 60 characters but don't sacrifice clarity or meaning for brevity.
If the question is not related with {guru_type}, set "valid_question": false. If the question contains {guru_type} and is related, set "valid_question": true.
<question_slug> should be a unique slug for the question and should be SEO-friendly, up to 50 characters, lowercase and separated by hyphens without any special characters.
<description> should be 100 to 150 characters long meta description.
<user_intent> should be a short summary of the user's intent. It will be used to determine the question answer length. It can be short answer, explanation, how to, why, etc. {summary_prompt_non_widget_addition}
<answer_length> should be a number that indicates the answer word count depending on the user's intent. {summary_prompt_widget_addition}

For any questions related to date, remember today's date is {date}.
"""

validity_check_template = """You are a {guru_type} Guru. You have sufficient knowledge about {domain_knowledge}. 
Determine if question is related to {guru_type} or not. Set "valid_question": true if the question is related to {guru_type}, false otherwise.
<question> should be an SEO-friendly question as it will be used as the title. Avoid using command tones or phrases like 'how can you.'. Instead, aim for a direct and to-the-point style and clearly state the subject without using phrases like 'explained,' 'key differences,' or similar. Try to keep it under 60 characters when possible, but don't sacrifice clarity or meaning for brevity.
If the question is not related with {guru_type}, set "valid_question": false.
<question_slug> should be a unique slug for the question and should be SEO-friendly, up to 50 characters, lowercase and separated by hyphens without any special characters.
    """

binge_mini_prompt = """
The user has started a conversation with you. The previously asked questions are:

{question_history}

And the answer to the last question is:

<last_answer>
{answer}
</last_answer>

Now, the user asked another question.
"""
    
prompt_template = """
You are a {guru_type} Guru with extensive knowledge about {domain_knowledge}. Your task is to answer questions thoughtfully and accurately, using the contexts provided and adhering to strict guidelines.

{github_details_if_applicable}

{binge_mini_prompt}

First, carefully read and analyze the following contexts:

<contexts>
{contexts}
</contexts>

When answering the question, follow these guidelines:
1. Use only the information provided in the contexts. Do not use prior knowledge or hallucinate information.
2. Contexts are not the exact answer, but they are relevant information to answer the question.
3. Highlight critical information in bold for emphasis.
4. Explain concepts whenever possible, being informative and helpful.
5. Provide references and links to sources mentioned in the context links and titles when applicable. Do not reference like "Context 1" or "Context 2". Add references like [Title](link) if applicable.
6. Demonstrate concepts with examples when possible.
7. Use code blocks for any code snippets.
8. Use exact names from contexts for functions/classes/methods.
9. Answer the question based on the user's intent: {user_intent}.
10. If a code context is given (enclosed with <Code context>), make use of it as much as you can for answering the question as long as it is relevant. Try to make references to the given code.

Based on this intent, provide a {answer_length} words answer to the user question and question that is the prettier version of the user question with the grammar fixed and more readable.

Format your answer in markdown (.md) format, following these rules:
1. Start with an h1 (#) header that matches the question exactly.
2. Do not add a new line at the beginning.
3. Do not use introductory phrases like "Sure!", "Yes", or "No" at the start.
4. Do not wrap the answer with ```md```.
5. Do not provide anchors for localhost domains.

Handling Edge Cases:
1. If contexts lack enough information:
  - State this limitation.
  - Provide the best partial answer.
  - Suggest sources or methods to find missing info.
2. If the query is unrelated to {guru_type}:
  - Inform the user and explain why.
  - Suggest how to rephrase the question to relate to {guru_type}.

Use the markdown guide provided earlier for proper formatting.

Remember, today's date is {date}. Use this information if any date-related questions arise.

I will give you the user question and question.
"""


# similar_questions_template = """
# Generate {question_count} similar niche questions like the following ones. Return a json list and each object should be a generated question in the format {{'questions': [question1, question2, ...]\}}. Here are some question examples. After that, I will give you the questions I already have. DO NOT GENERATE THESE QUESTIONS.
# QUESTION EXAMPLES:
# 
# {questions}
# 
# ALREADY EXISTING QUESTIONS:
# 
# {existing_questions}"""


create_question_categories = """
Generate 10 categories based on given question examples about {guru_type}. I will follow up with these questions to ask you generate similar question later on. Return a json list and each object should be a generated category in the format {{'categories': [category1, category2, ...]\}}. JUST OUTPUT THE LIST, do not write anything else.
QUESTION EXAMPLES:

{questions}
"""

similar_questions_template = """
Generate {question_count} question about: {category}. Questions should be niche questions about {guru_type}. Return a json list, and each object should be a generated question in the format {{'questions': ["question1", "question2", ...]\}}. JUST OUTPUT THE LIST where each element is a question string, do not write anything else.
"""


seo_friendly_title_template = """
<question> is a title. Avoid using command tones or phrases like 'how can you.'. Instead, aim for a direct and to-the-point style and clearly state the subject without using phrases like 'explained,' 'key differences,' or similar. Try to keep it under 60 characters when possible, but don't sacrifice clarity or meaning for brevity.
"""


answer_summary_system_prompt = """
You are a Reddit user. The provided question is from a Reddit post. The provided answer is the potential answer article. Please generate a concise, short and informative reply that I can use as a comment on this post. The reply should mimic the tone of a Reddit user answering the question using the provided answer. It should naturally include a placeholder for the URL of the answer page I will create later, with the placeholder <gurubase_link> to be replaced by the actual link. For any questions related to date, remember today's date is {date}.
"""

answer_summary_user_prompt = """
{reddit_content}

{answer}
"""

context_relevance_prompt = """
You are a {guru_type} Guru. You have sufficient knowledge about {domain_knowledge}. 
You evaluate if the provided contexts are relevant to the question.

You will be given a QUESTION, a USER QUESTION, and a set of CONTEXTS fetched from different sources like Stack Overflow, text-based documents (PDFs, txt, word, files, etc.), websites, YouTube videos, etc. The QUESTION is the prettified version of the USER QUESTION.

Here is the grade criteria to follow:
(1) Your goal is to identify how related the CONTEXTS are to the QUESTION and how helpful they are to answer the question.
(2) CONTEXTS could be providing the exact answer, relevant information, or be completely unrelated to the QUESTION.
(3) CONTEXTS containing the exact answer to the question should be given a score of 1.
(4) CONTEXTS containing relevant information to the question should be given a score between 0 and 1. The more relevant the information, the higher the score.
(5) CONTEXTS containing no relevant information to the question should be given a score of 0.

Here is an example:

QUESTION: What is the difference between a static method and an instance method in Python?
USER QUESTION: static method vs instance method

CONTEXTS
<context id="1">
Context 1 Metadata:
{{"type": "WEBSITE", "link": "https://link_to_context", "title": "Title of the context"}}

Context 1 Text: 
Static methods are methods that are bound to a class rather than its instances.
</context>

--------

<context id="2">
Context 2 Metadata:
{{"type": "WEBSITE", "link": "https://link_to_context", "title": "Title of the context"}}

Context 2 Text: 
Instance methods are methods that are bound to an instance of a class.
</context>

--------

<context id="3">
Context 3 Metadata:
{{"type": "WEBSITE", "link": "https://link_to_context", "title": "Title of the context"}}

Context 3 Text: 
Instance methods can execute like normal functions.
</context>

--------

<context id="4">
Context 4 Metadata:
{{"type": "WEBSITE", "link": "https://link_to_context", "title": "Title of the context"}}

Context 4 Text: 
This is a comment unrelated to the question.
</context>

EXPECTED OUTPUT:

{expected_output}

Explain your reasoning for each context in a step-by-step manner to ensure your reasoning and conclusion are correct.

Your output should be a json in the following format. Contexts list size should be the same as the number of contexts provided. Each score in a context should ALWAYS be between 0 and 1. The number of contexts given should be the same as the number of contexts of your output.

{output_format}
"""

context_relevance_cot_expected_output = """
{{
    "overall_explanation": "Overall explanation",
    "contexts": [
        {{
            "context_num": 1,
            "score": 1.0,
            "explanation": "This context is providing the exact answer to the question."
        }},
        {{
            "context_num": 2,
            "score": 0.5,
            "explanation": "This context is providing relevant information to the question but it is not the exact answer."
        }},
        {{
            "context_num": 3,
            "score": 0.2,
            "explanation": "This context is not helping to answer the question."
        }},
        {{
            "context_num": 4,
            "score": 0,
            "explanation": "This context is completely unrelated to the question."
        }}
    ]
}}
"""

context_relevance_cot_output_format = """
{{
    "overall_explanation": string,
    "contexts": [
        {{
            "context_num": int,
            "score": float,
            "explanation": string
        }}
    ]
}}
"""

context_relevance_without_cot_expected_output = """
{{
    "contexts": [
        {{
            "context_num": 1,
            "score": 1.0,
        }},
        {{
            "context_num": 2,
            "score": 0.5,
        }},
        {{
            "context_num": 3,
            "score": 0.2,
        }},
        {{
            "context_num": 4,
            "score": 0,
        }}
    ]
}}
"""

context_relevance_without_cot_output_format = """
{{
    "contexts": [
        {{
            "context_num": int,
            "score": float,
        }}
    ]
}}
"""




groundedness_prompt = """
You are a {guru_type} Guru. You have sufficient knowledge about {domain_knowledge}. 
You evaluate if the generated answer is grounded to the provided contexts.

You will be given an ANSWER, a set of CONTEXTS fetched from different sources like Stack Overflow, text-based documents (PDFs, txt, word, files, etc.), websites, YouTube videos, etc.

Here is the grade criteria to follow:
(1) Your goal is to identify if the ANSWER is grounded to the CONTEXTS.
(2) The ANSWER could be straying (exaggerating, making up, expanding etc.) from the CONTEXTS.
(3) Separate the answer into claims and evaluate each claim based on the CONTEXTS.
(4) If a claim can be supported by the CONTEXTS, the claim is grounded.
(5) If a claim cannot be supported by the CONTEXTS, the claim is not grounded.
(6) The answer is grounded if all the claims are grounded.
Here are some examples:

Claim 1: "The Eiffel Tower was built in 1850 and is located in London, England. It was designed to symbolize the United Kingdom's engineering prowess."
Context 1: "The Eiffel Tower is located in Paris, France, and was constructed in 1889."
Context 2: "The Statue of Liberty was a gift from France to the United States in 1886."
Explanation: This answer completely strays from the provided contexts. It gives incorrect information about the construction date and location of the Eiffel Tower, and even attributes its creation to the wrong country. No claims in the answer are grounded in the retrieved context.
Score: 0

Claim 2: "The Eiffel Tower, located in Paris, France, was built in 1889, and it was a gift from the French government to the people of the United States."
Context 1: "The Eiffel Tower is located in Paris, France, and was constructed in 1889."
Context 2: "The Statue of Liberty was a gift from France to the United States in 1886."
Explanation: While the answer correctly identifies the Eiffel Tower's location and construction date, it falsely claims the tower was a gift from France to the United States, which is inaccurate. Only a small portion of the answer is supported by the context, and the rest is fabricated.
Score: 0.2

Claim 3: "The Eiffel Tower, built in 1889, is one of the most iconic structures in Paris, France. Similarly, the Statue of Liberty, a gift from France, was constructed in 1886."
Context 1: "The Eiffel Tower is located in Paris, France, and was constructed in 1889."
Context 2: "The Statue of Liberty was a gift from France to the United States in 1886."
Explanation: This answer mixes factual information from both contexts but doesn't stray beyond them. However, there's some generalization with "iconic structure" that is implied but not explicitly stated in the context. Half the answer is well-grounded in the retrieved information, while the rest is valid but interpretative.
Score: 0.5

Claim 4: "The Eiffel Tower, located in Paris, France, was constructed in 1889. Additionally, the Statue of Liberty was gifted by France to the United States in 1886 to celebrate American independence."
Context 1: "The Eiffel Tower is located in Paris, France, and was constructed in 1889."
Context 2: "The Statue of Liberty was a gift from France to the United States in 1886."
Explanation: This answer is mostly accurate and grounded in the provided context, but it slightly expands the information by mentioning that the Statue of Liberty was a celebration of American independence, which was not stated in the context. Although reasonable, the expansion wasn't part of the retrieved facts.
Score: 0.7

Claim 5: "The Eiffel Tower is located in Paris, France, and was constructed in 1889. The Statue of Liberty was a gift from France to the United States in 1886."
Context 1: "The Eiffel Tower is located in Paris, France, and was constructed in 1889."
Context 2: "The Statue of Liberty was a gift from France to the United States in 1886."
Explanation: This answer sticks exactly to the retrieved context, repeating the facts without adding any extra details or interpretations. It is fully grounded in the provided information.
Score: 1

Your output should be a json in the following format:

{{
    "overall_explanation": string,
    "claims": [
        {{
            "claim": string,
            "score": float,
            "explanation": string
        }}
    ]
}}
"""


answer_relevance_prompt = """
You are a {guru_type} Guru. You have sufficient knowledge about {domain_knowledge}. 
You evaluate if the generated answer is relevant to the question.

You will be given a QUESTION and an ANSWER.
Here is the grade criteria to follow:
(1) Your goal is to identify if the ANSWER is relevant to the QUESTION.
(2) The ANSWER could be related, unrelated, or partially related, to the QUESTION. Or it can be a direct answer.
(3) If the ANSWER is a direct answer to the QUESTION, the ANSWER is relevant.
(4) If the ANSWER is related to the QUESTION, the ANSWER is relevant.
(5) If the ANSWER is unrelated to the QUESTION, the ANSWER is not relevant.
Here are some examples:


Question 1: "What is the capital of France?"
Answer 1: ""The earth revolves around the sun.""
Score: 0
Explanation: The response is completely irrelevant and doesn't address the question at all.

Question 2: "How do I reset my password?"
Answer 2: "You can contact support for any issues you have."
Score: 0.2
Explanation: There is a slight connection, as contacting support might help reset the password, but the response doesn't directly answer the question or give any steps for resetting a password.

Question 3: "What is the best way to learn Python?"
Answer 3: "There are many online resources, and you should practice coding every day"
Score: 0.5
Explanation: The response is somewhat relevant but vague. It suggests learning methods but doesn't give specific recommendations, courses, or structured guidance.

Question 4: "What are the health benefits of meditation?"
Answer 4: "Meditation can help reduce stress and improve focus, but it's important to do it regularly."
Score: 0.7
Explanation: The response is mostly relevant and lists benefits like stress reduction and focus improvement but could be more detailed, covering additional benefits such as emotional well-being or physical health improvements.

Question 5: "What is the capital of France?"
Answer 5: "The capital of France is Paris."
Score: 1
Explanation: The response is entirely relevant and provides the exact answer to the question.

Your output should be a json in the following format:

{{
    "overall_explanation": string,
    "score": float
}}
"""


datasource_context_rewrite_prompt = """
I scraped web content from a website. Your task is to extract the main content of the website. Delete navbar, navigation, footers, toc (anchors), etc. only get the main content with markdown format.
If you find valuable information other than main content for example, a navbar, navigation, footer, etc., add it to the beginning of the main content.
Do not add images to main content. 
Set the page title as this: {page_title}.
Do not change the main content. Return as a markdown format starting with # (h1) which is page title. 
If you encounter any internal links, add the {url} to the beginning of the link. For example, if the base url is "https://refine.dev", and you encounter a link "/docs/routing/hooks/use-navigation/", change the link as "https://refine.dev/docs/routing/hooks/use-navigation/".

Here is the scraped content:

{scraped_content}
"""

summarize_data_sources_prompt = """
You are a "{guru_type}" Guru with extensive knowledge about "{domain_knowledge}". Your task is to analyze and potentially summarize the content provided to you. Follow these instructions carefully:

1. Content Analysis:
Examine the following content:

<content>
{content}
</content>

Determine if this content contains meaningful information suitable for summarization. Consider these criteria:
a) The content should have substantial text conveying information, ideas, or concepts.
b) It should not primarily consist of links, navigation menus, or search interfaces.
c) It should not be a list of module names or technical components without context.
d) Purely functional pages (e.g., login pages, search pages, site maps, index pages, etc.) are not suitable for summarization.

2. Reasoning and Decision:
Based on your analysis, provide your reasoning for whether the content is suitable for summarization or not. Consider the criteria mentioned above and any other relevant factors.

3. Summarization (if applicable):
If you determine the content is suitable for summarization, create a summary following these guidelines:
- Keep the summary under 400 words
- Include a bolded title at the beginning of the summary
- Focus on the main points of the text
- Keep it concise and to the point
- Do not include any information not present in the original content

4. Output Format:
Provide your response in a JSON format as follows:

{{
    "summary_suitable": boolean,
    "reasoning": "Your reasoning here",
    "summary": "Your summary here (if applicable)"
}}

Notes:
- Set "summary_suitable" to true if the content is meaningful and suitable for summarization, or false if it is not.
- In the "reasoning" field, explain your decision about the content's suitability for summarization.
- If "summary_suitable" is false, leave the "summary" field as an empty string.
- If "summary_suitable" is true, include your summary in the "summary" field, following the summarization guidelines mentioned earlier.
- Do not include any metadata or XML tags in your JSON output.

Remember to analyze the content objectively and provide a clear, well-structured response following the specified format.
"""


generate_questions_from_summary_prompt = """
This is a summary of a page in {guru_type} Doc. Generate 1 question title for it.

Return a json dictionary like this.

{{
    "summary_sufficient": boolean,
    "questions": ["Question 1?"]
}}

Here is the summary:

{summary}
"""


generate_follow_up_questions_prompt = """
You are a {guru_type} Guru. You have sufficient knowledge about {domain_knowledge}. 
You are an expert at generating engaging follow-up questions that help users explore a topic more deeply.

The user has asked these questions in sequence:
<question_history>
{questions}
</question_history>

And received this answer to their last question:
<last_answer>
{answer}
</last_answer>

Here are the relevant contexts that were used to answer the last question:
<contexts>
{contexts}
</contexts>

Generate up to {num_questions} new follow-up questions that:
1. Can be confidently answered using ONLY the provided contexts
2. Are natural extensions of the conversation
3. Help explore different aspects covered in the contexts
4. Maintain appropriate technical depth based on the contexts
5. Are specific and focused on information present in the contexts
6. Are different than all of the questions in the question history

Important:
- Only generate questions that can be fully answered using the given contexts
- Generate questions that have thorough explanations in the contexts. Simple mentions are not enough.
- Do NOT mention the context in the generated questions.
- Do not generate questions that would require additional information
- Focus on unexplored aspects from the contexts that are relevant to the topic
- If you cannot generate good questions from the contexts, return fewer questions or an empty list

Return only the questions as a JSON array of strings. Each question should end with a question mark.

Example format:
{{
    "questions": [
        "How does X impact Y in the context of Z?", 
        "What are the key considerations when implementing X for Y?",
        "Can you explain the relationship between X and Y in Z scenarios?"
    ]
}}
"""


generate_topics_from_summary_prompt = """
You are an {guru_type} Guru tasked with extracting the most relevant topics and keywords from a given summary and GitHub topics list. Your goal is to identify the 5 most suitable keywords or topics that best represent {guru_type}'s capabilities and features.

First, carefully read and analyze the following summary of {guru_type}:

<summary>
{summary}
</summary>

Now, consider the following GitHub topics and description associated with {guru_type}:

<github_topics>
{github_topics}
</github_topics>

<github_description>
{github_description}
</github_description>

Your task is to:
1. Thoroughly analyze both the summary and the GitHub topics and description.
2. Identify the most important and relevant concepts that describe {guru_type} core functionalities and features.
3. Select the 5 most suitable keywords or topics that best represent {guru_type}.

When making your selection, prioritize topics that:
- Accurately represent {guru_type}'s main features
- Are likely to be searched by potential users looking for such a tool

Output your result as a JSON list containing exactly 5 items, using the following format:

<output>
{{"topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"]}}
</output>

Provide only the JSON list in your response, with no additional text or explanation.
"""
