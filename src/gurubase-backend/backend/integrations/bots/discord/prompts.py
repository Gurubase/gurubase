discord_base_template = """
This question is asked on a Discord channel.

Here is the Discord history:

<Discord thread>
{thread_messages}
</Discord thread>

<Discord channel>
{channel_messages}
</Discord channel>
"""

discord_context_template = discord_base_template + """

Make sure you consider the discord context while generating your answer. Treat this as a conversation history
**Critical**: Unless user does not explicitly ask about Discord, do not talk about it in your answer.
"""

discord_summary_template = discord_base_template + """
Users asks questions to you on Discord, the history of the conversation provided in <Discord thread> and <Discord channel> tags. When generating <question> and <enhanced_question>, take the conversation history into account as users may ask a follow-up question for the previous answer or ask about a new topic.

**Critical**: If the user's question is coherent and valid but implicit, assume it refers to {guru_type}. But if it is incoherent, unrelated to {guru_type}, or not a question, set `"valid_question": false`.
"""