slack_base_template = """
This question is asked on a Slack thread.

Here is the Slack thread:

<Slack thread>
{thread_messages}
</Slack thread>
"""

slack_context_template = slack_base_template + """

Make sure you consider the slack context while generating your answer. Treat this as a conversation history
**Critical**: Unless user does not explicitly ask about Slack, do not talk about it in your answer.
"""

slack_summary_template = slack_base_template + """
Users asks questions to you on Slack, the history of the conversation provided in <Slack thread> and <Slack channel> tags. When generating <question> and <enhanced_question>, take the conversation history into account as users may ask a follow-up question for the previous answer or ask about a new topic.

**Critical**: If the user's question is coherent and valid but implicit, assume it refers to {guru_type}. But if it is incoherent, unrelated to {guru_type}, or not a question, set `"valid_question": false`.
"""