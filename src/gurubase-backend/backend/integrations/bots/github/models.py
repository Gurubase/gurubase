import enum


class GithubEvent(enum.Enum):
    # Reopens are not caught as comments are caught separately
    ISSUE_OPENED = "issue_opened"
    ISSUE_COMMENT = "issue_comment"

    DISCUSSION_OPENED = "discussion_opened"
    DISCUSSION_COMMENT = "discussion_comment"

    PULL_REQUEST_OPENED = "pull_request_opened"
    PULL_REQUEST_COMMENT = "pull_request_comment"

    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    # PULL_REQUEST_REVIEW_REOPENED = "pull_request_review_reopened"

    PULL_REQUEST_REVIEW_REQUESTED = "pull_request_review_requested"
    # PULL_REQUEST_REVIEW_REQUESTED_REOPENED = "pull_request_review_requested_reopened"
