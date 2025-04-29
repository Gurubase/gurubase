github_base_template = """
This question is asked on a GitHub issue. Make sure you place importance on the author association. Here are the possible values for author association:

- COLLABORATOR: Author has been invited to collaborate on the repository.
- CONTRIBUTOR: Author has previously committed to the repository.
- FIRST_TIMER: Author has not previously committed to GitHub.
- FIRST_TIME_CONTRIBUTOR: Author has not previously committed to the repository.
- MANNEQUIN: Author is a placeholder for an unclaimed user.
- MEMBER: Author is a member of the organization that owns the repository.
- USER: Author is a user of the repository.
- OWNER: Author is the owner of the repository.
- YOU: Author is the bot.

Here is the issue history:

<Github contexts>
{github_comments}
</Github contexts>
"""

github_context_template = github_base_template + """

Make sure you consider the github context while generating your answer. Treat this as a conversation history
**Critical**: Unless user does not explicitly ask about GitHub, do not talk about it in your answer.
"""

github_summary_template = github_base_template + """
Users asks questions to you on GitHub, the history of the conversation provided in <Github contexts> tag. When generating <question> and <enhanced_question>, take the conversation history into account as users may ask a follow-up question for the previous answer or ask about a new topic.

**Critical**: If the user's question is coherent and valid but implicit, assume it refers to {guru_type}. But if it is incoherent, unrelated to {guru_type}, or not a question, set `"valid_question": false`.
"""